"""
생성 디렉토리의 진행 상황을 주기적으로 스캔해 progress 문서를 덮어쓴다.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf


def parse_args():
    """
    기능:
    - generation progress monitor 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse namespace를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--target-audio-hours", type=float, required=True)
    parser.add_argument("--label", default="generation")
    parser.add_argument("--start-epoch", type=float, default=None)
    parser.add_argument("--interval-sec", type=float, default=60.0)
    parser.add_argument("--shards", nargs="*", default=None)
    return parser.parse_args()


def seconds_to_hms(seconds):
    """
    기능:
    - 초 단위를 읽기 쉬운 문자열로 바꾼다.

    입력:
    - `seconds`: 초 단위 float.

    반환:
    - `HH:MM:SS` 문자열을 반환한다.
    """
    seconds = max(0, int(round(seconds)))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remain = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remain:02d}"


def iter_wavs(wav_dir):
    """
    기능:
    - wav 디렉토리 아래 파일을 정렬해 순회한다.

    입력:
    - `wav_dir`: wav 디렉토리 경로.

    반환:
    - Path iterator를 반환한다.
    """
    if not wav_dir.exists():
        return []
    return sorted(wav_dir.glob("*.wav"))


def scan_run(run_root, shards):
    """
    기능:
    - shard별 파일 수와 총 오디오 길이를 스캔한다.

    입력:
    - `run_root`: run 루트 디렉토리.
    - `shards`: shard 이름 목록.

    반환:
    - shard summary list와 전체 count/sec를 반환한다.
    """
    shard_rows = []
    total_count = 0
    total_audio_sec = 0.0
    for shard in shards:
        wav_dir = run_root / shard / "wavs"
        files = iter_wavs(wav_dir)
        count = 0
        audio_sec = 0.0
        for wav_path in files:
            info = sf.info(str(wav_path))
            count += 1
            audio_sec += info.frames / info.samplerate
        shard_rows.append(
            {
                "shard": shard,
                "wav_dir": str(wav_dir),
                "count": count,
                "audio_sec": round(audio_sec, 3),
                "audio_hour": round(audio_sec / 3600.0, 3),
            }
        )
        total_count += count
        total_audio_sec += audio_sec
    return shard_rows, total_count, total_audio_sec


def write_progress(run_root, payload):
    """
    기능:
    - progress markdown/json을 덮어쓴다.

    입력:
    - `run_root`: run 루트 디렉토리.
    - `payload`: progress dict.

    반환:
    - 없음.
    """
    json_path = run_root / "progress.local.json"
    md_path = run_root / "progress.local.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {payload['label']} Progress",
        "",
        f"- updated_at_kst: {payload['updated_at_kst']}",
        f"- run_root: {payload['run_root']}",
        f"- target_audio_hours: {payload['target_audio_hours']}",
        f"- total_wavs: {payload['total_wavs']}",
        f"- generated_audio_hours: {payload['generated_audio_hours']}",
        f"- progress_ratio: {payload['progress_ratio']}",
        f"- elapsed_wall: {payload['elapsed_wall_hms']}",
        f"- observed_rtf: {payload['observed_rtf']}",
        f"- estimated_remaining: {payload['estimated_remaining_hms']}",
        f"- estimated_finish_kst: {payload['estimated_finish_kst']}",
        "",
        "## Shards",
        "",
        "| shard | wav_count | audio_hour | wav_dir |",
        "|---|---:|---:|---|",
    ]
    for row in payload["shards"]:
        lines.append(f"| {row['shard']} | {row['count']} | {row['audio_hour']:.3f} | {row['wav_dir']} |")
    lines.append("")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    """
    기능:
    - 생성 진행률을 주기적으로 기록한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    run_root = args.run_root.resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    shards = args.shards or [path.name for path in sorted(run_root.glob("shard_*")) if path.is_dir()]
    start_epoch = args.start_epoch or time.time()
    target_audio_sec = float(args.target_audio_hours) * 3600.0

    while True:
        shard_rows, total_count, total_audio_sec = scan_run(run_root, shards)
        now_epoch = time.time()
        elapsed_wall_sec = max(0.0, now_epoch - start_epoch)
        observed_rtf = (elapsed_wall_sec / total_audio_sec) if total_audio_sec > 0 else None
        remaining_audio_sec = max(0.0, target_audio_sec - total_audio_sec)
        remaining_wall_sec = (remaining_audio_sec * observed_rtf) if observed_rtf is not None else None
        finish_epoch = (now_epoch + remaining_wall_sec) if remaining_wall_sec is not None else None
        payload = {
            "label": args.label,
            "run_root": str(run_root),
            "target_audio_hours": round(args.target_audio_hours, 3),
            "total_wavs": total_count,
            "generated_audio_hours": round(total_audio_sec / 3600.0, 3),
            "progress_ratio": round((total_audio_sec / target_audio_sec), 4) if target_audio_sec > 0 else None,
            "elapsed_wall_hms": seconds_to_hms(elapsed_wall_sec),
            "observed_rtf": round(observed_rtf, 4) if observed_rtf is not None else None,
            "estimated_remaining_hms": seconds_to_hms(remaining_wall_sec) if remaining_wall_sec is not None else None,
            "estimated_finish_kst": (
                datetime.fromtimestamp(finish_epoch, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
                if finish_epoch is not None
                else None
            ),
            "updated_at_kst": datetime.now().astimezone().isoformat(timespec="seconds"),
            "shards": shard_rows,
        }
        write_progress(run_root, payload)
        time.sleep(args.interval_sec)


if __name__ == "__main__":
    main()
