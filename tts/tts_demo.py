"""
아주 단순한 TTS demo.

텍스트를 받아 오디오 파일로 저장한다.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tts import TTSSynthesizer


def parse_args():
    """
    기능:
    - TTS demo 실행에 필요한 명령행 인자를 정의하고 파싱한다.

    입력:
    - 없음.

    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["api"],
        default="api",
        help="사용할 TTS 백엔드",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="백엔드별 실제 모델 이름",
    )
    parser.add_argument(
        "--voice",
        default="alloy",
        help="사용할 음성 이름",
    )
    parser.add_argument(
        "--text",
        required=True,
        help="음성으로 합성할 텍스트",
    )
    parser.add_argument(
        "--instructions",
        default=None,
        help="말투 제어용 추가 지시 문자열",
    )
    parser.add_argument(
        "--response-format",
        default="wav",
        choices=["mp3", "opus", "aac", "flac", "wav", "pcm"],
        help="출력 오디오 포맷",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="합성 속도 배율",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tts_outputs") / "speech.wav",
        help="생성 오디오 파일 경로",
    )
    parser.add_argument(
        "--usage-purpose",
        default=None,
        help="API TTS 사용 목적 기록용 문자열",
    )
    return parser.parse_args()


def main():
    """
    기능:
    - 텍스트를 받아 TTS 합성을 수행하고 결과 경로를 출력한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    args = parse_args()
    synthesizer = TTSSynthesizer(
        model=args.model,
        model_name=args.model_name,
        voice=args.voice,
        instructions=args.instructions,
        response_format=args.response_format,
        speed=args.speed,
        usage_purpose=args.usage_purpose,
    )
    output_path = synthesizer.synthesize_to_file(args.text, args.output)
    print(f"output: {output_path}")
    print(f"elapsed_sec: {synthesizer.last_duration_sec:.3f}")


if __name__ == "__main__":
    main()
