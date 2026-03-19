"""
Synthetic manifest를 Piper 학습용 single-speaker LJSpeech 포맷으로 변환한다.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque, Dict, List


def parse_args():
    """
    기능:
    - Piper 학습용 dataset builder 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - argparse namespace.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--deduped-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-hours", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=1234)
    return parser.parse_args()


def load_rows(path: Path) -> List[Dict[str, str]]:
    """
    기능:
    - deduped manifest TSV를 읽는다.

    입력:
    - `path`: TSV 경로.

    반환:
    - row list.
    """
    with open(path, "r", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file, delimiter="\t"))


def select_balanced_subset(rows: List[Dict[str, str]], target_hours: float, seed: int) -> List[Dict[str, str]]:
    """
    기능:
    - category 기준으로 round-robin 하며 target_hours까지 subset을 고른다.

    입력:
    - `rows`: 전체 deduped row.
    - `target_hours`: 목표 오디오 시간.
    - `seed`: 셔플 시드.

    반환:
    - 선택된 subset row list.
    """
    rng = random.Random(seed)
    buckets: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        buckets[row.get("category") or "uncategorized"].append(row)
    for bucket_rows in buckets.values():
        rng.shuffle(bucket_rows)

    queues: Dict[str, Deque[Dict[str, str]]] = {
        category: deque(bucket_rows) for category, bucket_rows in buckets.items()
    }
    categories = sorted(queues.keys())
    selected: List[Dict[str, str]] = []
    total_sec = 0.0
    target_sec = target_hours * 3600.0
    while categories and total_sec < target_sec:
        next_categories: List[str] = []
        for category in categories:
            queue = queues[category]
            if not queue:
                continue
            row = queue.popleft()
            selected.append(row)
            total_sec += float(row.get("audio_sec") or 0.0)
            if queue:
                next_categories.append(category)
            if total_sec >= target_sec:
                break
        categories = next_categories
    return selected


def write_tsv(path: Path, rows: List[Dict[str, str]]) -> None:
    """
    기능:
    - TSV를 기록한다.

    입력:
    - `path`: 출력 경로.
    - `rows`: row list.

    반환:
    - 없음.
    """
    if not rows:
        raise ValueError("rows is empty")
    with open(path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def create_ljspeech_dataset(rows: List[Dict[str, str]], output_dir: Path) -> None:
    """
    기능:
    - single-speaker LJSpeech 포맷 디렉토리를 만든다.

    입력:
    - `rows`: 선택된 row list.
    - `output_dir`: 출력 디렉토리.

    반환:
    - 없음.
    """
    wav_dir = output_dir / "wav"
    wav_dir.mkdir(parents=True, exist_ok=True)
    metadata_lines: List[str] = []
    for index, row in enumerate(rows, start=1):
        utterance_id = f"pilot_{index:06d}"
        source_wav = Path(row["output_path"])
        target_wav = wav_dir / f"{utterance_id}.wav"
        if target_wav.exists() or target_wav.is_symlink():
            target_wav.unlink()
        target_wav.symlink_to(source_wav)
        metadata_lines.append(f"{utterance_id}|{row['text']}")
        row["dataset_utterance_id"] = utterance_id
        row["dataset_wav_path"] = str(target_wav)
    (output_dir / "metadata.csv").write_text("\n".join(metadata_lines) + "\n", encoding="utf-8")


def main():
    """
    기능:
    - Piper pilot 학습용 LJSpeech dataset snapshot을 만든다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = load_rows(args.deduped_manifest)
    selected_rows = select_balanced_subset(rows, target_hours=args.target_hours, seed=args.seed)
    if not selected_rows:
        raise SystemExit("no rows selected")

    create_ljspeech_dataset(selected_rows, args.output_dir)
    write_tsv(args.output_dir / "selected_manifest.tsv", selected_rows)

    summary = {
        "selected_count": len(selected_rows),
        "selected_audio_sec": round(sum(float(row.get("audio_sec") or 0.0) for row in selected_rows), 3),
        "selected_audio_hour": round(
            sum(float(row.get("audio_sec") or 0.0) for row in selected_rows) / 3600.0,
            3,
        ),
        "source_manifest": str(args.deduped_manifest),
        "target_hours": args.target_hours,
        "seed": args.seed,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "README.local.md").write_text(
        "\n".join(
            [
                "# Piper Pilot Dataset Snapshot",
                "",
                f"- selected_count: {summary['selected_count']}",
                f"- selected_audio_hour: {summary['selected_audio_hour']}",
                f"- source_manifest: {summary['source_manifest']}",
                f"- target_hours: {summary['target_hours']}",
                f"- seed: {summary['seed']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
