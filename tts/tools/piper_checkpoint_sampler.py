"""
Piper 학습 checkpoint를 감시하고 중요한 epoch마다 샘플 음성을 저장한다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List

import piper_phonemize


def parse_args():
    """
    기능:
    - checkpoint sampler 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - argparse namespace.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prompt-tsv", type=Path, required=True)
    parser.add_argument("--important-every", type=int, default=5)
    parser.add_argument("--poll-sec", type=float, default=20.0)
    parser.add_argument("--stop-when-file", type=Path)
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--language", default="ko")
    return parser.parse_args()


def load_prompts(path: Path) -> List[Dict[str, str]]:
    """
    기능:
    - review prompt TSV를 읽는다.

    입력:
    - `path`: prompt TSV 경로.

    반환:
    - prompt row list.
    """
    with open(path, "r", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file, delimiter="\t"))


def checkpoint_epoch(path: Path) -> int:
    """
    기능:
    - checkpoint 파일명에서 epoch를 읽는다.

    입력:
    - `path`: ckpt 경로.

    반환:
    - epoch int. 없으면 -1.
    """
    match = re.search(r"epoch=(\d+)", path.name)
    return int(match.group(1)) if match else -1


def should_keep(epoch: int, important_every: int) -> bool:
    """
    기능:
    - 중요한 checkpoint인지 판단한다.

    입력:
    - `epoch`: epoch 번호.
    - `important_every`: 몇 epoch마다 남길지.

    반환:
    - bool.
    """
    if epoch < 0:
        return False
    return epoch in {0, 1} or (epoch % important_every == 0)


def build_jsonl(prompts: List[Dict[str, str]]) -> str:
    """
    기능:
    - prompt를 Piper infer 입력 JSONL로 변환한다.

    입력:
    - `prompts`: prompt row list.

    반환:
    - JSONL 문자열.
    """
    lines: List[str] = []
    for row in prompts:
        phonemes_nested = piper_phonemize.phonemize_espeak(row["text"], "ko")
        phonemes = [phoneme for segment in phonemes_nested for phoneme in segment]
        phoneme_ids = piper_phonemize.phoneme_ids_espeak(phonemes)
        lines.append(json.dumps({"phoneme_ids": phoneme_ids}, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def generate_samples(
    checkpoint_path: Path,
    prompts: List[Dict[str, str]],
    output_dir: Path,
    python_bin: str,
    sample_rate: int,
) -> None:
    """
    기능:
    - checkpoint에서 review sample wav들을 생성한다.

    입력:
    - `checkpoint_path`: checkpoint 경로.
    - `prompts`: prompt row list.
    - `output_dir`: 출력 디렉토리.
    - `python_bin`: 실행할 python.
    - `sample_rate`: 출력 sample rate.

    반환:
    - 없음.
    """
    tmp_dir = output_dir / "_tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.run(
        [
            python_bin,
            "-m",
            "piper_train.infer",
            "--checkpoint",
            str(checkpoint_path),
            "--output-dir",
            str(tmp_dir),
            "--sample-rate",
            str(sample_rate),
        ],
        input=build_jsonl(prompts),
        text=True,
        capture_output=True,
        check=True,
    )
    manifest_rows: List[Dict[str, str]] = []
    for index, row in enumerate(prompts):
        src = tmp_dir / f"{index}.wav"
        dst = output_dir / f"{row['prompt_id']}.wav"
        shutil.move(str(src), str(dst))
        manifest_rows.append(
            {
                "prompt_id": row["prompt_id"],
                "text": row["text"],
                "wav_path": str(dst),
            }
        )
    with open(output_dir / "manifest.tsv", "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=["prompt_id", "text", "wav_path"], delimiter="\t")
        writer.writeheader()
        writer.writerows(manifest_rows)
    (output_dir / "stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_dir / "stderr.log").write_text(process.stderr, encoding="utf-8")
    shutil.rmtree(tmp_dir)


def write_status(path: Path, processed: List[str]) -> None:
    """
    기능:
    - sampler 상태를 로컬 문서로 기록한다.

    입력:
    - `path`: 상태 파일 경로.
    - `processed`: 처리된 checkpoint 목록.

    반환:
    - 없음.
    """
    lines = [
        "# Piper Checkpoint Sampler Status",
        "",
        f"- processed_count: {len(processed)}",
    ]
    for checkpoint_name in processed[-10:]:
        lines.append(f"- processed: {checkpoint_name}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    """
    기능:
    - 중요한 checkpoint를 감시하고 review sample을 만든다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    important_dir = args.output_dir / "important_checkpoints"
    sample_root = args.output_dir / "review_samples"
    important_dir.mkdir(parents=True, exist_ok=True)
    sample_root.mkdir(parents=True, exist_ok=True)
    prompts = load_prompts(args.prompt_tsv)
    processed = set()
    status_path = args.output_dir / "sampler_status.local.md"

    while True:
        checkpoint_paths = sorted(args.checkpoint_dir.rglob("*.ckpt"))
        for checkpoint_path in checkpoint_paths:
            if checkpoint_path.name in processed:
                continue
            epoch = checkpoint_epoch(checkpoint_path)
            if not should_keep(epoch, args.important_every):
                processed.add(checkpoint_path.name)
                continue
            important_target = important_dir / checkpoint_path.name
            if not important_target.exists():
                shutil.copy2(checkpoint_path, important_target)
            sample_dir = sample_root / checkpoint_path.stem
            sample_dir.mkdir(parents=True, exist_ok=True)
            generate_samples(
                checkpoint_path=checkpoint_path,
                prompts=prompts,
                output_dir=sample_dir,
                python_bin=args.python_bin,
                sample_rate=args.sample_rate,
            )
            processed.add(checkpoint_path.name)
            write_status(status_path, sorted(processed))

        if args.stop_when_file and args.stop_when_file.exists():
            break
        time.sleep(args.poll_sec)


if __name__ == "__main__":
    main()
