"""
아주 단순한 STT demo.

짧은 wav 파일 또는 기본 마이크 녹음을 받아 텍스트로 변환한다.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stt import STTTranscriber


def parse_args():
    """
    기능:
    - STT demo 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["whisper", "api"],
        default="whisper",
        help="사용할 STT 백엔드",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="백엔드별 실제 모델 이름",
    )
    parser.add_argument(
        "--language",
        default="ko",
        help="기본 언어 코드",
    )
    parser.add_argument(
        "--audio",
        type=Path,
        default=None,
        help="16kHz mono wav 파일 경로",
    )
    parser.add_argument(
        "--record-seconds",
        type=float,
        default=4.0,
        help="마이크 녹음 길이(초)",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="입력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="오디오 장치 목록 출력 후 종료",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Whisper 실행 장치(cpu 또는 cuda)",
    )
    parser.add_argument(
        "--download-root",
        type=Path,
        default=None,
        help="Whisper 모델 다운로드 경로",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="STT 힌트 프롬프트",
    )
    return parser.parse_args()


def print_devices():
    """
    기능:
    - 현재 시스템에서 사용할 수 있는 오디오 장치 목록을 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    for index, device in enumerate(sd.query_devices()):
        print(
            f"[{index}] {device['name']} | "
            f"in={device['max_input_channels']} | out={device['max_output_channels']} | "
            f"default_sr={int(device['default_samplerate'])}"
        )


def resolve_input_device(device_arg):
    """
    기능:
    - 입력 장치 인자를 실제 sounddevice 장치 값으로 변환한다.

    입력:
    - `device_arg`: 사용자가 전달한 입력 장치 인자.

    반환:
    - 실제 실행에 사용할 장치 값을 반환한다.
    """
    if device_arg is not None:
        if str(device_arg).isdigit():
            return int(device_arg)
        return device_arg

    default_input = sd.default.device[0]
    if default_input is None or default_input < 0:
        raise RuntimeError("기본 입력 마이크가 설정되어 있지 않습니다.")
    return int(default_input)


def record_audio(record_seconds, input_device):
    """
    기능:
    - 기본 마이크에서 지정한 시간만큼 mono 16kHz 오디오를 녹음한다.

    입력:
    - `record_seconds`: 녹음 길이(초).
    - `input_device`: 사용할 입력 장치.

    반환:
    - float32 mono 오디오 배열을 반환한다.
    """
    sample_rate = 16000
    frame_count = int(record_seconds * sample_rate)
    audio = sd.rec(
        frame_count,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=input_device,
    )
    sd.wait()
    return np.asarray(audio[:, 0], dtype=np.float32)


def main():
    """
    기능:
    - wav 파일 또는 기본 마이크 녹음을 STT로 변환해 결과를 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    transcriber = STTTranscriber(
        model=args.model,
        model_name=args.model_name,
        language=args.language,
        device=args.device,
        download_root=args.download_root,
        prompt=args.prompt,
    )

    if args.audio is not None:
        audio_input = args.audio
    else:
        input_device = resolve_input_device(args.input_device)
        print(f"기본 마이크에서 {args.record_seconds:.1f}초 녹음합니다...")
        audio_input = record_audio(args.record_seconds, input_device)

    text = transcriber.transcribe(audio_input)
    print(f"text: {text}")
    print(f"elapsed_sec: {transcriber.last_duration_sec:.3f}")


if __name__ == "__main__":
    main()
