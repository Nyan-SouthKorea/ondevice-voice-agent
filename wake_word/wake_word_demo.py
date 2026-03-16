"""
Export한 ONNX classifier를 간단히 테스트하는 CLI 예제.

예시:
python wake_word/wake_word_demo.py \
  --model wake_word/models/hi_popo/hi_popo_classifier.onnx \
  --providers cpu \
  --features /tmp/feature_window.npy
"""

import argparse
from pathlib import Path

import numpy as np

from wake_word import HiPopoWakeWordONNX


def parse_args():
    """
    기능:
    - 명령행 인자를 정의하고 파싱한다.
    
    입력:
    - 없음.
    
    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier.onnx"),
        help="ONNX classifier path",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("wake_word/models/hi_popo/hi_popo_classifier_onnx.json"),
        help="Export metadata path",
    )
    parser.add_argument(
        "--features",
        type=Path,
        required=True,
        help="Feature .npy path: (16, 96) window or (T, 96) clip feature",
    )
    parser.add_argument("--threshold", type=float, default=None, help="Override detection threshold")
    parser.add_argument(
        "--providers",
        type=str,
        default=None,
        help="Comma-separated ONNX providers, e.g. cpu or cuda,cpu",
    )
    return parser.parse_args()


def main():
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    args = parse_args()
    providers = args.providers.split(",") if args.providers else None
    detector = HiPopoWakeWordONNX(
        model_path=args.model,
        metadata_path=args.metadata,
        threshold=args.threshold,
        providers=providers,
    )
    features = np.load(args.features)
    score = detector.predict_score(features)
    detected = detector.is_detected(features)
    print(f"model={args.model}")
    print(f"features={args.features} shape={features.shape}")
    print(f"providers={detector.session.get_providers()}")
    print(f"threshold={detector.threshold:.4f}")
    print(f"score={score:.6f}")
    print(f"detected={detected}")


if __name__ == "__main__":
    main()
