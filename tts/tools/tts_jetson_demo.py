"""
Jetson용 TTS thin demo wrapper.

backend별 env python을 선택해 기존 `tts/tts_demo.py`를 호출한다.
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent

JETSON_ENV_BY_MODEL = {
    "api": "tts_network_jetson",
    "openai_api": "tts_network_jetson",
    "chatgpt_api": "tts_network_jetson",
    "edge_tts": "tts_network_jetson",
    "melotts": "tts_melotts_jetson",
    "piper": "tts_piper_jetson",
    "kokoro": "tts_kokoro_jetson",
}

DEFAULT_TEXT_BY_MODEL = {
    "api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "openai_api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "chatgpt_api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "edge_tts": "안녕하세요. Jetson Edge TTS 테스트입니다.",
    "melotts": "안녕하세요. Jetson MeloTTS 테스트입니다.",
    "piper": "Hello. This is a Jetson Piper test.",
    "kokoro": "Hello. This is a Jetson Kokoro test.",
}


def parse_args():
    """
    기능:
    - Jetson thin demo 실행 인자를 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=sorted(JETSON_ENV_BY_MODEL))
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--voice", default=None)
    parser.add_argument("--text", default=None)
    parser.add_argument("--instructions", default=None)
    parser.add_argument("--response-format", default="wav")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--rate", default=None)
    parser.add_argument("--pitch", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--reference-audio", type=Path, default=None)
    parser.add_argument("--checkpoint-root", type=Path, default=None)
    parser.add_argument("--usage-purpose", default=None)
    parser.add_argument(
        "--env-root",
        type=Path,
        default=WORKSPACE_ROOT / "env",
        help="Jetson env 루트. 기본값은 ../env",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="생성 파일 경로. 비우면 ../results/tts/jetson_demo/<model>/demo.wav",
    )
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="실행 전 최종 subprocess 명령을 출력한다.",
    )
    return parser.parse_args()


def build_command(args):
    """
    기능:
    - backend별 env python으로 `tts_demo.py`를 실행하는 명령을 만든다.

    입력:
    - `args`: 명령행 인자 객체.

    반환:
    - subprocess 명령 리스트를 반환한다.
    """
    env_name = JETSON_ENV_BY_MODEL[args.model]
    env_python = args.env_root / env_name / "bin" / "python"
    if not env_python.is_file():
        raise FileNotFoundError(f"Jetson env python을 찾지 못했습니다: {env_python}")

    output_path = args.output
    if output_path is None:
        output_path = (
            WORKSPACE_ROOT / "results" / "tts" / "jetson_demo" / args.model / "demo.wav"
        )

    command = [
        str(env_python),
        str(REPO_ROOT / "tts" / "tts_demo.py"),
        "--model",
        args.model,
        "--text",
        args.text or DEFAULT_TEXT_BY_MODEL[args.model],
        "--output",
        str(output_path),
        "--response-format",
        args.response_format,
        "--speed",
        str(args.speed),
    ]

    optional_pairs = [
        ("--model-name", args.model_name),
        ("--voice", args.voice),
        ("--instructions", args.instructions),
        ("--rate", args.rate),
        ("--pitch", args.pitch),
        ("--device", args.device),
        ("--usage-purpose", args.usage_purpose),
    ]
    for key, value in optional_pairs:
        if value is not None:
            command.extend([key, str(value)])

    if args.reference_audio is not None:
        command.extend(["--reference-audio", str(args.reference_audio)])
    if args.checkpoint_root is not None:
        command.extend(["--checkpoint-root", str(args.checkpoint_root)])

    return command


def main():
    """
    기능:
    - Jetson thin demo wrapper를 실행한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    command = build_command(args)
    if args.print_command:
        print("command:", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
