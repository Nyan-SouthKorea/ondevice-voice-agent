"""
OpenVoice reference 음성을 준비한다.
"""

import argparse
import json
import subprocess
from pathlib import Path

import soundfile as sf


def parse_args():
    """
    기능:
    - reference preparation 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse namespace를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--language", default="ko")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/data2/iena/260318_ondevice-voice-agent/results/tts_custom/references"),
    )
    parser.add_argument("--start-sec", type=float, default=0.0)
    parser.add_argument("--duration-sec", type=float)
    return parser.parse_args()


def main():
    """
    기능:
    - 입력 오디오/비디오에서 OpenVoice용 mono wav reference를 만든다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    output_dir = args.output_root / args.reference_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.reference_id}.wav"

    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if args.start_sec > 0:
        command += ["-ss", str(args.start_sec)]
    command += ["-i", str(args.input)]
    if args.duration_sec is not None:
        command += ["-t", str(args.duration_sec)]
    command += ["-ac", "1", "-ar", "16000", str(output_path)]
    subprocess.run(command, check=True)

    audio, sample_rate = sf.read(str(output_path))
    duration_sec = round(float(len(audio) / sample_rate), 3)
    manifest = {
        "reference_id": args.reference_id,
        "language": args.language,
        "source_path": str(args.input.resolve()),
        "prepared_path": str(output_path.resolve()),
        "sample_rate": int(sample_rate),
        "duration_sec": duration_sec,
        "start_sec": float(args.start_sec),
        "requested_duration_sec": args.duration_sec,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
