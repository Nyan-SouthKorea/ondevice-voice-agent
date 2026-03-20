#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LabelRecord:
    utt_id: str
    split: str
    gender: str
    age: str
    text: str
    literature: str
    styles: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AIHub 문학작품 낭송·낭독 데이터에서 OpenVoice reference 후보를 준비한다."
    )
    parser.add_argument("--raw-root", required=True, help="AIHub raw root")
    parser.add_argument("--output-dir", required=True, help="candidate output dir")
    parser.add_argument("--min-sec", type=float, default=6.0)
    parser.add_argument("--max-sec", type=float, default=12.0)
    parser.add_argument("--max-per-speaker", type=int, default=1)
    parser.add_argument("--speaker-limit", type=int, default=0)
    parser.add_argument("--copy", action="store_true", help="symlink 대신 copy")
    return parser.parse_args()


def load_labels(raw_root: Path) -> dict[str, LabelRecord]:
    label_files = [
        (raw_root / "extracted" / "labels" / "train" / "1.학습레이블.json", "train"),
        (raw_root / "extracted" / "labels" / "validation" / "2.검증레이블.json", "validation"),
    ]
    records: dict[str, LabelRecord] = {}
    for path, split in label_files:
        items = json.loads(path.read_text())
        for item in items:
            styles = item.get("recite_src", {}).get("styles", []) or []
            style_text = []
            for style in styles:
                if isinstance(style, dict):
                    style_text.append(f"{style.get('style', '')}:{style.get('emotion', '')}")
                else:
                    style_text.append(str(style))
            records[item["id"]] = LabelRecord(
                utt_id=item["id"],
                split=split,
                gender=item.get("reciter", {}).get("gender", "UNKNOWN"),
                age=item.get("reciter", {}).get("age", ""),
                text=item.get("recite_src", {}).get("text", ""),
                literature=item.get("recite_src", {}).get("literature", ""),
                styles="|".join(style_text),
            )
    return records


def duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_f:
        return wav_f.getnframes() / wav_f.getframerate()


def derive_utt_id(path: Path) -> str:
    stem = path.stem
    parts = stem.split("-")
    if parts and parts[-1].isdigit():
        return "-".join(parts[:-1])
    return stem


def main() -> None:
    args = parse_args()
    raw_root = Path(args.raw_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    labels = load_labels(raw_root)
    audio_root = raw_root / "extracted" / "audio"
    wav_paths = sorted(audio_root.rglob("*.wav"))

    chosen_per_speaker: dict[str, int] = {}
    selected_rows: list[dict[str, str]] = []

    for wav_path in wav_paths:
        dur = duration_sec(wav_path)
        if dur < args.min_sec or dur > args.max_sec:
            continue

        utt_id = derive_utt_id(wav_path)
        label = labels.get(utt_id)
        speaker_id = utt_id.split("-")[0]
        if chosen_per_speaker.get(speaker_id, 0) >= args.max_per_speaker:
            continue

        chosen_per_speaker[speaker_id] = chosen_per_speaker.get(speaker_id, 0) + 1
        out_name = f"{speaker_id}__{utt_id}__{wav_path.stem}.wav"
        target = candidate_dir / out_name
        if target.exists() or target.is_symlink():
            target.unlink()
        if args.copy:
            shutil.copy2(wav_path, target)
        else:
            target.symlink_to(wav_path)

        selected_rows.append(
            {
                "speaker_id": speaker_id,
                "utt_id": utt_id,
                "split_wav_stem": wav_path.stem,
                "duration_sec": f"{dur:.3f}",
                "gender": label.gender if label else "UNKNOWN",
                "age": label.age if label else "",
                "split": label.split if label else "",
                "literature": label.literature if label else "",
                "styles": label.styles if label else "",
                "text": label.text if label else "",
                "source_wav": str(wav_path),
                "candidate_path": str(target),
            }
        )

        if args.speaker_limit and len(chosen_per_speaker) >= args.speaker_limit:
            break

    manifest = output_dir / "manifest.tsv"
    with manifest.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "speaker_id",
                "utt_id",
                "split_wav_stem",
                "duration_sec",
                "gender",
                "age",
                "split",
                "literature",
                "styles",
                "text",
                "source_wav",
                "candidate_path",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(selected_rows)

    summary = {
        "raw_root": str(raw_root),
        "output_dir": str(output_dir),
        "min_sec": args.min_sec,
        "max_sec": args.max_sec,
        "max_per_speaker": args.max_per_speaker,
        "speaker_limit": args.speaker_limit,
        "selected_speakers": len(chosen_per_speaker),
        "selected_clips": len(selected_rows),
        "copy_mode": bool(args.copy),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
