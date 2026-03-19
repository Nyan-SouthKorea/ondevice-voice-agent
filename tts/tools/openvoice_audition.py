"""
OpenVoice audition 샘플을 생성한다.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tts import TTSSynthesizer


def parse_args():
    """
    기능:
    - audition 실행 인자를 읽는다.

    입력:
    - 없음.

    반환:
    - 파싱된 argparse namespace를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-id", required=True)
    parser.add_argument("--reference-audio-path", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, default=REPO_ROOT / "tts" / "evaluation" / "prompts" / "openvoice_audition_prompts_ko_v1.tsv")
    parser.add_argument("--model-name", default="KR")
    parser.add_argument("--voice", default="KR")
    parser.add_argument("--speed", type=float, default=1.1)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("/data2/iena/260318_ondevice-voice-agent/results/tts_custom/audition"),
    )
    parser.add_argument("--run-name", default="openvoice_audition_v1")
    return parser.parse_args()


def load_prompts(path):
    """
    기능:
    - TSV 프롬프트 파일을 읽는다.

    입력:
    - `path`: prompt TSV 경로.

    반환:
    - prompt dict list를 반환한다.
    """
    with open(path, "r", encoding="utf-8") as input_file:
        return list(csv.DictReader(input_file, delimiter="\t"))


def main():
    """
    기능:
    - 지정한 reference로 audition wav들을 생성한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    prompts = load_prompts(args.prompt_file)
    run_dir = args.output_root / args.run_name / args.reference_id
    run_dir.mkdir(parents=True, exist_ok=True)

    synthesizer = TTSSynthesizer(
        model="openvoice_v2",
        model_name=args.model_name,
        voice=args.voice,
        speed=args.speed,
        device=args.device,
        reference_audio_path=args.reference_audio_path,
    )

    rows = []
    for prompt in prompts:
        output_path = run_dir / f"{prompt['prompt_id']}.wav"
        saved_path = synthesizer.synthesize_to_file(prompt["text"], output_path)
        rows.append(
            {
                "reference_id": args.reference_id,
                "prompt_id": prompt["prompt_id"],
                "language": prompt["language"],
                "text": prompt["text"],
                "output_path": str(saved_path),
                "speed": args.speed,
                "elapsed_sec": round(float(synthesizer.last_duration_sec), 3),
                "model_load_sec": round(float(synthesizer.model_load_sec), 3),
            }
        )

    manifest_path = run_dir / "manifest.tsv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"reference_id": args.reference_id, "sample_count": len(rows), "manifest": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
