#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import wave
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SplitClip:
    path: Path
    utt_id: str
    split_index: str
    duration_sec: float


@dataclass
class LabelRow:
    utt_id: str
    split: str
    gender: str
    age: str
    text: str
    literature_json: str
    styles_text: str
    speaker_slot: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AIHub 문학작품 낭송·낭독 데이터에서 OpenVoice용 46개 canonical reference bank를 만든다."
    )
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-sec", type=float, default=6.0)
    parser.add_argument("--max-sec", type=float, default=12.0)
    parser.add_argument("--female-count", type=int, default=23)
    parser.add_argument("--male-count", type=int, default=23)
    parser.add_argument("--target-sec", type=float, default=8.0)
    return parser.parse_args()


def duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_f:
        return wav_f.getnframes() / wav_f.getframerate()


def load_labels(raw_root: Path) -> list[LabelRow]:
    label_files = [
        (raw_root / "extracted" / "labels" / "train" / "1.학습레이블.json", "train"),
        (raw_root / "extracted" / "labels" / "validation" / "2.검증레이블.json", "validation"),
    ]
    rows: list[LabelRow] = []
    for path, split in label_files:
        items = json.loads(path.read_text())
        for item in items:
            stem = Path(item["voice"]["filename"]).stem
            parts = stem.split("-")
            if len(parts) < 3:
                continue
            slot = parts[2]
            styles = item.get("recite_src", {}).get("styles", []) or []
            style_parts = []
            for style in styles:
                if isinstance(style, dict):
                    style_parts.append(f"{style.get('style', '')}:{style.get('emotion', '')}")
                else:
                    style_parts.append(str(style))
            rows.append(
                LabelRow(
                    utt_id=item["id"],
                    split=split,
                    gender=item.get("reciter", {}).get("gender", "UNKNOWN"),
                    age=str(item.get("reciter", {}).get("age", "")),
                    text=item.get("recite_src", {}).get("text", ""),
                    literature_json=json.dumps(item.get("recite_src", {}).get("literature", {}), ensure_ascii=False),
                    styles_text="|".join(style_parts),
                    speaker_slot=slot,
                )
            )
    return rows


def build_split_index(audio_root: Path, min_sec: float, max_sec: float) -> dict[str, list[SplitClip]]:
    index: dict[str, list[SplitClip]] = defaultdict(list)
    for wav_path in audio_root.rglob("*.wav"):
        parts = wav_path.stem.split("-")
        if len(parts) < 4:
            continue
        utt_id = "-".join(parts[:-1])
        clip = SplitClip(
            path=wav_path,
            utt_id=utt_id,
            split_index=parts[-1],
            duration_sec=duration_sec(wav_path),
        )
        if min_sec <= clip.duration_sec <= max_sec:
            index[utt_id].append(clip)
    return index


def style_rank(styles_text: str) -> int:
    # neutral references are preferred for cloning
    if "무감정:무감정" in styles_text:
        return 0
    if "편안한:기쁨" in styles_text or "느긋한:기쁨" in styles_text:
        return 1
    if "걱정" in styles_text or "분노" in styles_text or "슬픔" in styles_text:
        return 3
    return 2


def choose_best_candidate(
    label_rows: list[LabelRow],
    split_index: dict[str, list[SplitClip]],
    target_sec: float,
) -> tuple[LabelRow, SplitClip] | None:
    candidates: list[tuple[tuple[float, float, int], LabelRow, SplitClip]] = []
    for row in label_rows:
        for clip in split_index.get(row.utt_id, []):
            score = (
                style_rank(row.styles_text),
                abs(clip.duration_sec - target_sec),
                0 if row.split == "train" else 1,
            )
            candidates.append((score, row, clip))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    _, row, clip = candidates[0]
    return row, clip


def main() -> None:
    args = parse_args()
    raw_root = Path(args.raw_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    refs_dir = output_dir / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)

    label_rows = load_labels(raw_root)
    audio_root = raw_root / "extracted" / "audio"
    split_index = build_split_index(audio_root, args.min_sec, args.max_sec)

    combo_rows: dict[tuple[str, str], list[LabelRow]] = defaultdict(list)
    combo_counts: Counter[tuple[str, str]] = Counter()
    for row in label_rows:
        combo = (row.gender, row.speaker_slot)
        combo_rows[combo].append(row)
        combo_counts[combo] += 1

    female_combos = [combo for combo, _ in combo_counts.most_common() if combo[0] == "FEMALE"]
    male_combos = [combo for combo, _ in combo_counts.most_common() if combo[0] == "MALE"]
    selected_combos = female_combos[: args.female_count] + male_combos[: args.male_count]

    manifest_rows = []
    selected_count = Counter()
    for combo in selected_combos:
        chosen = choose_best_candidate(combo_rows[combo], split_index, args.target_sec)
        if not chosen:
            continue
        row, clip = chosen
        gender, slot = combo
        bank_id = f"{'F' if gender == 'FEMALE' else 'M'}_{slot}"
        target = refs_dir / f"{bank_id}.wav"
        shutil.copy2(clip.path, target)
        selected_count[gender] += 1
        manifest_rows.append(
            {
                "bank_id": bank_id,
                "gender": gender,
                "speaker_slot": slot,
                "utt_id": row.utt_id,
                "split": row.split,
                "age": row.age,
                "duration_sec": f"{clip.duration_sec:.3f}",
                "styles": row.styles_text,
                "text": row.text,
                "literature": row.literature_json,
                "source_split_wav": str(clip.path),
                "archived_ref_wav": str(target),
            }
        )

    manifest_path = output_dir / "manifest.tsv"
    with manifest_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "bank_id",
                "gender",
                "speaker_slot",
                "utt_id",
                "split",
                "age",
                "duration_sec",
                "styles",
                "text",
                "literature",
                "source_split_wav",
                "archived_ref_wav",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary = {
        "raw_root": str(raw_root),
        "output_dir": str(output_dir),
        "min_sec": args.min_sec,
        "max_sec": args.max_sec,
        "target_sec": args.target_sec,
        "female_target": args.female_count,
        "male_target": args.male_count,
        "selected_total": len(manifest_rows),
        "selected_female": selected_count["FEMALE"],
        "selected_male": selected_count["MALE"],
        "note": "공식 narrator id가 라벨에 직접 노출되지 않아 gender+speaker_slot 조합 기준으로 canonical bank를 구성했다.",
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
