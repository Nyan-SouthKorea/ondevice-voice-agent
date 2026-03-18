"""
각 TTS 전용 env에서 실행되는 benchmark worker.
"""

import argparse
import json
import traceback
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tts import TTSSynthesizer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    job = json.loads(args.job.read_text(encoding="utf-8"))
    backend_kwargs = dict(job["backend_kwargs"])
    prompts = list(job["prompts"])

    synthesizer = TTSSynthesizer(**backend_kwargs)
    results = []

    for prompt in prompts:
        output_path = Path(prompt["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "prompt_id": prompt["prompt_id"],
            "language": prompt["language"],
            "text": prompt["text"],
            "output_path": str(output_path),
            "success": False,
            "elapsed_sec": None,
            "error": "",
        }
        try:
            saved_path = synthesizer.synthesize_to_file(prompt["text"], output_path)
            record["success"] = True
            record["output_path"] = str(saved_path)
            record["elapsed_sec"] = float(synthesizer.last_duration_sec)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        results.append(record)

    summary = {
        "entry_id": job["entry_id"],
        "display_name": job["display_name"],
        "backend": job["backend"],
        "prompt_language": job["prompt_language"],
        "family": job["family"],
        "model_load_sec": float(getattr(synthesizer, "model_load_sec", 0.0)),
        "results": results,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "entry_id": summary["entry_id"],
                "backend": summary["backend"],
                "prompts": len(results),
                "success_count": sum(1 for row in results if row["success"]),
                "model_load_sec": summary["model_load_sec"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
