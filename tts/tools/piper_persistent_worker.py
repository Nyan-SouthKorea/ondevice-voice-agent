"""
Jetson용 persistent Piper TTS worker.

모델을 한 번만 로드하고, stdin JSON line 요청을 받아 임시 wav를 만든 뒤
JSON line 응답을 stdout으로 돌려준다.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tts import TTSSynthesizer


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--temp-root", type=Path, default=Path("/tmp/ondevice_voice_agent_tts"))
    return parser.parse_args()


def emit(payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def main():
    args = parse_args()
    args.temp_root.mkdir(parents=True, exist_ok=True)
    synthesizer = TTSSynthesizer(
        model="piper",
        model_name=str(args.model_path),
        device=args.device,
    )
    emit(
        {
            "type": "ready",
            "model_load_sec": synthesizer.model_load_sec,
            "model_path": str(args.model_path),
            "device": args.device,
        }
    )

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except Exception as exc:
            emit({"ok": False, "error": f"JSONDecodeError: {exc}"})
            continue

        command = request.get("cmd", "synthesize")
        if command == "shutdown":
            emit({"ok": True, "type": "shutdown"})
            return
        if command != "synthesize":
            emit({"ok": False, "error": f"unsupported cmd: {command}"})
            continue

        text = str(request.get("text", "")).strip()
        if not text:
            emit({"ok": False, "error": "empty text"})
            continue

        fd, temp_path = tempfile.mkstemp(
            prefix="piper_gui_",
            suffix=".wav",
            dir=str(args.temp_root),
        )
        os.close(fd)
        temp_path = Path(temp_path)
        try:
            saved_path = synthesizer.synthesize_to_file(text, temp_path)
            emit(
                {
                    "ok": True,
                    "audio_path": str(saved_path),
                    "elapsed_sec": synthesizer.last_duration_sec,
                    "model_load_sec": synthesizer.model_load_sec,
                    "text": text,
                }
            )
        except Exception as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
            emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


if __name__ == "__main__":
    main()
