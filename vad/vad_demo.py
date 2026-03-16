"""
아주 단순한 VAD demo.

기본 마이크를 받아서 현재 음성 여부를 `True` / `False`로만 계속 출력한다.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vad import VADDetector


def parse_args():
    """
    기능:
    - VAD demo 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["webrtcvad", "silero"],
        default="silero",
        help="사용할 VAD 백엔드",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=None,
        help="Silero ONNX 모델 경로",
    )
    parser.add_argument(
        "--mode",
        type=int,
        default=2,
        help="webrtcvad 공격성 모드(0~3)",
    )
    parser.add_argument(
        "--speech-threshold",
        type=float,
        default=0.5,
        help="Silero speech 판정 기준값",
    )
    parser.add_argument(
        "--input-device",
        default=None,
        help="입력 장치 index 또는 이름",
    )
    parser.add_argument(
        "--min-speech-frames",
        type=int,
        default=3,
        help="True 전환 전 필요한 연속 speech frame 수",
    )
    parser.add_argument(
        "--min-silence-frames",
        type=int,
        default=10,
        help="False 전환 전 필요한 연속 silence frame 수",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="오디오 장치 목록 출력 후 종료",
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


def compute_audio_level(audio_chunk):
    """
    기능:
    - 현재 오디오 청크의 마이크 입력 레벨을 RMS 기준으로 계산한다.

    입력:
    - `audio_chunk`: float32 mono 오디오 청크.

    반환:
    - 0.0~1.0 범위의 입력 레벨 값을 반환한다.
    """
    audio = np.asarray(audio_chunk, dtype=np.float32)
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def format_status_line(detector, status, audio_level):
    """
    기능:
    - 현재 VAD 상태를 터미널 한 줄 문자열로 정리한다.

    입력:
    - `detector`: 현재 사용 중인 VAD detector 객체.
    - `status`: filtering 이후 최종 speech 상태.
    - `audio_level`: 현재 마이크 입력 레벨.

    반환:
    - 터미널에 출력할 상태 문자열을 반환한다.
    """
    if detector.model == "silero":
        return (
            f"status={str(status):<5} | "
            f"level={audio_level:.4f} | "
            f"conf={detector.last_score:.4f}"
        )

    return (
        f"status={str(status):<5} | "
        f"level={audio_level:.4f} | "
        f"voiced_ratio={detector.last_score:.4f}"
    )


def main():
    """
    기능:
    - 기본 마이크를 열고 현재 음성 여부, 입력 레벨, 점수 정보를 계속 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    if args.list_devices:
        print_devices()
        return

    detector = VADDetector(
        model=args.model,
        model_path=args.model_path,
        mode=args.mode,
        speech_threshold=args.speech_threshold,
        min_speech_frames=args.min_speech_frames,
        min_silence_frames=args.min_silence_frames,
    )
    input_device = resolve_input_device(args.input_device)

    try:
        with sd.InputStream(
            samplerate=detector.sample_rate,
            blocksize=detector.chunk_samples,
            channels=1,
            dtype="float32",
            device=input_device,
        ) as stream:
            while True:
                audio_chunk, _overflowed = stream.read(detector.chunk_samples)
                mono_chunk = audio_chunk[:, 0]
                audio_level = compute_audio_level(mono_chunk)
                status = detector.infer(mono_chunk)
                line = format_status_line(detector, status, audio_level)
                sys.stdout.write(f"\r{line:<64}")
                sys.stdout.flush()
    except KeyboardInterrupt:
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
