"""
05c_evaluate.py
저장된 wake word 분류기 checkpoint를 불러와 held-out split의 positive-only / negative-only 성능을 평가한다.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = REPO_ROOT / "data" / "hi_popo" / "features"
MODEL_DIR = REPO_ROOT / "models" / "hi_popo"


def load_train_module():
    """
    기능:
    - 평가에 필요한 05_train 모듈을 동적으로 로드한다.
    
    입력:
    - 없음.
    
    반환:
    - 읽어 온 데이터 또는 객체를 반환한다.
    """
    path = Path(__file__).with_name("05_train.py")
    spec = importlib.util.spec_from_file_location("train05_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    """
    기능:
    - 명령행 인자를 정의하고 파싱한다.
    
    입력:
    - 없음.
    
    반환:
    - 파싱된 명령행 인자 객체를 반환한다.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--positive", type=Path, default=FEATURE_DIR / "positive_features_test.npy")
    parser.add_argument("--negative", type=Path, default=FEATURE_DIR / "negative_features_test.npy")
    return parser.parse_args()


def resolve_device(requested: str) -> torch.device:
    """
    기능:
    - 요청한 장치 문자열을 실제 실행 장치로 변환한다.
    
    입력:
    - `requested`: 사용자가 요청한 장치 문자열.
    
    반환:
    - 실제 실행에 사용할 장치 값을 반환한다.
    """
    if requested == "gpu" and torch.cuda.is_available():
        return torch.device("cuda:0")
    return torch.device("cpu")


def main() -> None:
    """
    기능:
    - 스크립트 또는 데모의 전체 실행 흐름을 시작한다.
    
    입력:
    - 없음.
    
    반환:
    - 없음.
    """
    args = parse_args()
    train_module = load_train_module()

    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    threshold = checkpoint["threshold"] if args.threshold is None else args.threshold
    layer_dim = checkpoint["layer_dim"]
    n_blocks = checkpoint["n_blocks"]
    input_shape = tuple(checkpoint["input_shape"])

    device = resolve_device(args.device)
    model = train_module.WakeWordFCModel(
        input_shape=input_shape,
        layer_dim=layer_dim,
        n_blocks=n_blocks,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    pos = np.load(args.positive, mmap_mode="r")
    neg = np.load(args.negative, mmap_mode="r")

    pos_scores = train_module.predict_clip_scores(model, pos, device, args.batch_size)
    neg_scores = train_module.predict_clip_scores(model, neg, device, args.batch_size)

    pos_pred = pos_scores >= threshold
    neg_pred = neg_scores >= threshold

    tp = int(pos_pred.sum())
    fn = int((~pos_pred).sum())
    fp = int(neg_pred.sum())
    tn = int((~neg_pred).sum())

    result = {
        "checkpoint": str(args.checkpoint),
        "device_resolved": str(device),
        "threshold": float(threshold),
        "positive_test": {
            "total": int(len(pos_pred)),
            "true_positives": tp,
            "false_negatives": fn,
            "recall": float(tp / max(len(pos_pred), 1)),
        },
        "negative_test": {
            "total": int(len(neg_pred)),
            "false_positives": fp,
            "true_negatives": tn,
            "false_positive_rate": float(fp / max(len(neg_pred), 1)),
            "specificity": float(tn / max(len(neg_pred), 1)),
        },
        "overall": {
            "balanced_accuracy": float(
                ((tp / max(len(pos_pred), 1)) + (tn / max(len(neg_pred), 1))) / 2.0
            )
        },
    }

    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
