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
    "openvoice_v2": "tts_openvoice_v2_jetson",
    "piper": "tts_piper_jetson",
    "kokoro": "tts_kokoro_jetson",
}

JETSON_RECOMMENDED_DEVICE_BY_MODEL = {
    "api": None,
    "openai_api": None,
    "chatgpt_api": None,
    "edge_tts": None,
    "melotts": "cpu",
    "openvoice_v2": "cpu",
    "piper": "cpu",
    "kokoro": "cuda",
}

DEFAULT_TEXT_BY_MODEL = {
    "api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "openai_api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "chatgpt_api": "안녕하세요. Jetson TTS API 경로 테스트입니다.",
    "edge_tts": "안녕하세요. Jetson Edge TTS 테스트입니다.",
    "melotts": "안녕하세요. Jetson MeloTTS 테스트입니다.",
    "openvoice_v2": "안녕하세요. Jetson OpenVoice V2 테스트입니다.",
    "piper": "Hello. This is a Jetson Piper test.",
    "kokoro": "Hello. This is a Jetson Kokoro test.",
}


def read_jetson_model_string():
    """
    기능:
    - 장치 트리에서 Jetson 모델 문자열을 읽는다.

    입력:
    - 없음.

    반환:
    - 모델 문자열을 반환한다. 읽지 못하면 빈 문자열을 반환한다.
    """
    model_path = Path("/proc/device-tree/model")
    try:
        return model_path.read_text(errors="ignore").replace("\x00", "").strip()
    except OSError:
        return ""


def detect_jetson_profile():
    """
    기능:
    - 현재 Jetson 장비를 단순 프로파일 이름으로 분류한다.

    입력:
    - 없음.

    반환:
    - `orin_nano`, `agx_orin`, `unknown` 중 하나를 반환한다.
    """
    model_text = read_jetson_model_string().lower()
    if "orin nano" in model_text:
        return "orin_nano"
    if "agx orin" in model_text or ("agx" in model_text and "orin" in model_text):
        return "agx_orin"
    return "unknown"


def get_recommended_device(model):
    """
    기능:
    - 현재 Jetson 장비 프로파일에 맞는 backend 기본 device를 반환한다.

    입력:
    - `model`: backend 이름.

    반환:
    - 기본 device 문자열 또는 `None`을 반환한다.
    """
    if model in {"api", "openai_api", "chatgpt_api", "edge_tts"}:
        return None
    if model == "piper":
        return "cpu"
    if model == "kokoro":
        return "cuda"

    profile = detect_jetson_profile()
    if model in {"melotts", "openvoice_v2"}:
        if profile == "agx_orin":
            return "cuda"
        if profile == "orin_nano":
            return "cpu"

    return JETSON_RECOMMENDED_DEVICE_BY_MODEL.get(model)


def can_import_module(env_python, module_name):
    """
    기능:
    - 특정 env python에서 주어진 모듈 import 가능 여부를 확인한다.

    입력:
    - `env_python`: 확인할 python 실행 파일 경로.
    - `module_name`: import 확인 대상 모듈명.

    반환:
    - import 가능하면 `True`, 아니면 `False`를 반환한다.
    """
    if not env_python.is_file():
        return False
    result = subprocess.run(
        [str(env_python), "-c", f"import {module_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def resolve_env_python(model, env_root):
    """
    기능:
    - backend별 실행에 실제 사용할 env python 경로를 결정한다.

    입력:
    - `model`: backend 이름.
    - `env_root`: Jetson env 루트 경로.

    반환:
    - 사용할 python 실행 파일 경로를 반환한다.
    """
    env_name = JETSON_ENV_BY_MODEL[model]
    env_python = env_root / env_name / "bin" / "python"
    if model == "openvoice_v2" and not can_import_module(env_python, "openvoice"):
        fallback_python = env_root / "tts_melotts_jetson" / "bin" / "python"
        if can_import_module(fallback_python, "openvoice"):
            return fallback_python
    if not env_python.is_file():
        raise FileNotFoundError(f"Jetson env python을 찾지 못했습니다: {env_python}")
    return env_python


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
    env_python = resolve_env_python(args.model, args.env_root)

    output_path = args.output
    if output_path is None:
        output_path = (
            WORKSPACE_ROOT / "results" / "tts" / "jetson_demo" / args.model / "demo.wav"
        )

    reference_audio = args.reference_audio
    checkpoint_root = args.checkpoint_root
    if args.model == "openvoice_v2":
        if reference_audio is None:
            reference_audio = (
                WORKSPACE_ROOT
                / "results"
                / "tts_assets"
                / "openvoice_v2"
                / "references"
                / "ko_benchmark_reference.wav"
            )
        if checkpoint_root is None:
            checkpoint_root = (
                WORKSPACE_ROOT
                / "results"
                / "tts_assets"
                / "openvoice_v2"
                / "checkpoints_v2"
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

    effective_device = args.device
    if effective_device is None:
        effective_device = get_recommended_device(args.model)

    optional_pairs = [
        ("--model-name", args.model_name),
        ("--voice", args.voice),
        ("--instructions", args.instructions),
        ("--rate", args.rate),
        ("--pitch", args.pitch),
        ("--device", effective_device),
        ("--usage-purpose", args.usage_purpose),
    ]
    for key, value in optional_pairs:
        if value is not None:
            command.extend([key, str(value)])

    if reference_audio is not None:
        command.extend(["--reference-audio", str(reference_audio)])
    if checkpoint_root is not None:
        command.extend(["--checkpoint-root", str(checkpoint_root)])

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
