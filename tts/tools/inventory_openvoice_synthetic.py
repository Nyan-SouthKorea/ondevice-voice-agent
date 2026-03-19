"""
OpenVoice synthetic dataset run들을 모아 중복 없이 inventory를 만든다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import wave


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def normalize_text(text: str) -> str:
    """
    기능:
    - 중복 판정용 텍스트 정규화를 수행한다.

    입력:
    - `text`: 원문 텍스트.

    반환:
    - 공백이 정리된 정규화 문자열.
    """
    return " ".join((text or "").split()).strip()


def parse_args():
    """
    기능:
    - synthetic inventory 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - argparse namespace.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--synthetic-root",
        type=Path,
        default=Path("/data2/iena/260318_ondevice-voice-agent/results/tts_custom/synthetic_dataset"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


@dataclass
class RunMeta:
    """
    기능:
    - run root의 최소 메타데이터를 보관한다.

    입력:
    - 각 필드는 README.local.md와 run 경로에서 채운다.

    반환:
    - 없음.
    """

    run_root: Path
    run_name: str
    status: str
    mode: str
    reference_id: str
    reference_audio_path: str
    speed: str
    corpus_tsv: Optional[Path]
    synthetic_root: Path


def parse_readme_meta(readme_path: Path) -> Dict[str, str]:
    """
    기능:
    - README.local.md의 `- key: value` 형식을 읽는다.

    입력:
    - `readme_path`: 로컬 README 경로.

    반환:
    - key/value dict.
    """
    meta: Dict[str, str] = {}
    pattern = re.compile(r"^- ([^:]+):\s*(.*)$")
    for line in readme_path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            meta[match.group(1).strip()] = match.group(2).strip()
    return meta


def discover_runs(synthetic_root: Path) -> List[RunMeta]:
    """
    기능:
    - synthetic dataset run root들을 찾는다.

    입력:
    - `synthetic_root`: synthetic dataset 루트.

    반환:
    - RunMeta 목록.
    """
    runs: List[RunMeta] = []
    for readme_path in sorted(synthetic_root.glob("**/README.local.md")):
        if "_local_supervisor" in str(readme_path):
            continue
        run_root = readme_path.parent
        if "preprocess_smoke" in str(run_root):
            continue
        meta = parse_readme_meta(readme_path)
        corpus_tsv = Path(meta["corpus_tsv"]) if meta.get("corpus_tsv") else None
        runs.append(
            RunMeta(
                run_root=run_root,
                run_name=str(run_root.relative_to(synthetic_root)),
                status=meta.get("status", ""),
                mode=meta.get("mode", ""),
                reference_id=meta.get("reference_id", ""),
                reference_audio_path=meta.get("reference_audio_path", ""),
                speed=meta.get("speed", ""),
                corpus_tsv=corpus_tsv,
                synthetic_root=synthetic_root,
            )
        )
    return runs


def load_corpus_map(corpus_tsv: Optional[Path]) -> Dict[str, Dict[str, str]]:
    """
    기능:
    - text_id 기준 corpus row map을 만든다.

    입력:
    - `corpus_tsv`: corpus TSV 경로.

    반환:
    - text_id -> row dict map.
    """
    if corpus_tsv is None or (not corpus_tsv.exists()):
        return {}
    with open(corpus_tsv, "r", encoding="utf-8") as input_file:
        return {row["text_id"]: row for row in csv.DictReader(input_file, delimiter="\t")}


def iter_manifest_rows(manifest_path: Path) -> Iterable[Dict[str, str]]:
    """
    기능:
    - manifest TSV row들을 순회한다.

    입력:
    - `manifest_path`: manifest TSV 경로.

    반환:
    - row iterator.
    """
    with open(manifest_path, "r", encoding="utf-8") as input_file:
        yield from csv.DictReader(input_file, delimiter="\t")


def load_rows_from_run(run: RunMeta) -> List[Dict[str, str]]:
    """
    기능:
    - run root에서 현재까지 생성된 행을 읽는다.

    입력:
    - `run`: RunMeta.

    반환:
    - row dict list.
    """
    corpus_map = load_corpus_map(run.corpus_tsv)
    rows: List[Dict[str, str]] = []
    manifest_paths = sorted(run.run_root.glob("shard_*/manifest.tsv"))
    if manifest_paths:
        for manifest_path in manifest_paths:
            for row in iter_manifest_rows(manifest_path):
                if str(row.get("success", "")).lower() != "true":
                    continue
                output_path = Path(row["output_path"])
                if not output_path.exists():
                    continue
                rows.append(
                    {
                        "run_name": run.run_name,
                        "run_root": str(run.run_root),
                        "status": run.status,
                        "mode": run.mode,
                        "reference_id": row.get("reference_id", run.reference_id),
                        "reference_audio_path": row.get(
                            "reference_audio_path", run.reference_audio_path
                        ),
                        "speed": str(row.get("speed", run.speed)),
                        "text_id": row["text_id"],
                        "text": row["text"],
                        "source_corpus": row.get("source_corpus", ""),
                        "category": row.get("category", ""),
                        "output_path": str(output_path),
                        "audio_sec": row.get("audio_sec", ""),
                    }
                )
        return rows

    # active run: manifest가 아직 없으면 wav 디렉토리와 corpus TSV를 합쳐 읽는다.
    for wav_dir in sorted(run.run_root.glob("shard_*/wavs")):
        for wav_path in sorted(wav_dir.glob("*.wav")):
            text_id = wav_path.stem
            corpus_row = corpus_map.get(text_id, {})
            with wave.open(str(wav_path), "rb") as wav_file:
                frame_count = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
            rows.append(
                {
                    "run_name": run.run_name,
                    "run_root": str(run.run_root),
                    "status": run.status,
                    "mode": run.mode,
                    "reference_id": run.reference_id,
                    "reference_audio_path": run.reference_audio_path,
                    "speed": str(run.speed),
                    "text_id": text_id,
                    "text": corpus_row.get("text", ""),
                    "source_corpus": corpus_row.get("source_corpus", ""),
                    "category": corpus_row.get("category", ""),
                    "output_path": str(wav_path),
                    "audio_sec": f"{frame_count / sample_rate:.3f}",
                }
            )
    return rows


def run_priority(row: Dict[str, str]) -> tuple:
    """
    기능:
    - 중복 텍스트에서 어떤 row를 남길지 우선순위를 계산한다.

    입력:
    - `row`: inventory row.

    반환:
    - 정렬 가능한 priority tuple.
    """
    run_name = row["run_name"]
    mode = row.get("mode", "")
    is_tts_only = "tts only" in mode.lower() or "_tts_only" in run_name
    version_match = re.search(r"full_v(\d+)", run_name)
    version_num = int(version_match.group(1)) if version_match else 0
    status_score = 1 if row.get("status") == "completed" else 0
    return (1 if is_tts_only else 0, version_num, status_score, row.get("audio_sec", "0"))


def write_tsv(path: Path, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    """
    기능:
    - TSV 파일을 기록한다.

    입력:
    - `path`: 출력 경로.
    - `rows`: row list.
    - `fieldnames`: 컬럼 순서.

    반환:
    - 없음.
    """
    with open(path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main():
    """
    기능:
    - synthetic dataset inventory를 만들고 deduped snapshot을 기록한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    runs = discover_runs(args.synthetic_root)
    all_rows: List[Dict[str, str]] = []
    for run in runs:
        all_rows.extend(load_rows_from_run(run))

    for row in all_rows:
        row["normalized_text"] = normalize_text(row.get("text", ""))

    usable_rows = [row for row in all_rows if row["normalized_text"]]
    archival_only_rows = [row for row in all_rows if not row["normalized_text"]]

    deduped: Dict[str, Dict[str, str]] = {}
    duplicate_rows: List[Dict[str, str]] = []
    for row in usable_rows:
        key = row["normalized_text"]
        current = deduped.get(key)
        if current is None:
            deduped[key] = row
            continue
        if run_priority(row) > run_priority(current):
            duplicate_rows.append(current)
            deduped[key] = row
        else:
            duplicate_rows.append(row)

    deduped_rows = sorted(deduped.values(), key=lambda row: row["normalized_text"])

    per_run = Counter(row["run_name"] for row in all_rows)
    per_run_hours = defaultdict(float)
    for row in all_rows:
        try:
            per_run_hours[row["run_name"]] += float(row.get("audio_sec") or 0.0)
        except ValueError:
            pass

    total_audio_sec = sum(float(row.get("audio_sec") or 0.0) for row in all_rows)
    unique_audio_sec = sum(float(row.get("audio_sec") or 0.0) for row in deduped_rows)

    all_fieldnames = [
        "run_name",
        "run_root",
        "status",
        "mode",
        "reference_id",
        "reference_audio_path",
        "speed",
        "text_id",
        "text",
        "normalized_text",
        "source_corpus",
        "category",
        "output_path",
        "audio_sec",
    ]
    write_tsv(args.output_dir / "all_rows.tsv", all_rows, all_fieldnames)
    write_tsv(args.output_dir / "deduped_rows.tsv", deduped_rows, all_fieldnames)
    write_tsv(args.output_dir / "duplicate_rows.tsv", duplicate_rows, all_fieldnames)

    summary = {
        "run_count": len(runs),
        "all_row_count": len(all_rows),
        "usable_row_count": len(usable_rows),
        "archival_only_row_count": len(archival_only_rows),
        "unique_row_count": len(deduped_rows),
        "duplicate_row_count": len(duplicate_rows),
        "total_audio_sec": round(total_audio_sec, 3),
        "total_audio_hour": round(total_audio_sec / 3600.0, 3),
        "unique_audio_sec": round(unique_audio_sec, 3),
        "unique_audio_hour": round(unique_audio_sec / 3600.0, 3),
        "per_run_count": dict(per_run),
        "per_run_hour": {key: round(value / 3600.0, 3) for key, value in per_run_hours.items()},
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# OpenVoice Synthetic Inventory",
        "",
        f"- run_count: {summary['run_count']}",
        f"- all_row_count: {summary['all_row_count']}",
        f"- usable_row_count: {summary['usable_row_count']}",
        f"- archival_only_row_count: {summary['archival_only_row_count']}",
        f"- unique_row_count: {summary['unique_row_count']}",
        f"- duplicate_row_count: {summary['duplicate_row_count']}",
        f"- total_audio_hour: {summary['total_audio_hour']}",
        f"- unique_audio_hour: {summary['unique_audio_hour']}",
        "",
        "## per_run",
        "",
    ]
    for run_name in sorted(per_run):
        lines.append(
            f"- {run_name}: {per_run[run_name]} rows, {summary['per_run_hour'].get(run_name, 0.0)} hours"
        )
    (args.output_dir / "README.local.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
