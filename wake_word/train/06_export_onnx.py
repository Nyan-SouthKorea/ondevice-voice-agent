"""
학습된 wake word classifier checkpoint를 ONNX로 export한다.

입력 shape:
- (batch, 16, 96)

출력 shape:
- (batch, 1)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = REPO_ROOT / "models" / "hi_popo"


class FCNBlock(nn.Module):
    def __init__(self, layer_dim: int):
        """
        기능:
        - FCN block의 레이어 구성을 초기화한다.
        
        입력:
        - `layer_dim`: 은닉층 차원 크기.
        
        반환:
        - 없음.
        """
        super().__init__()
        self.fcn_layer = nn.Linear(layer_dim, layer_dim)
        self.relu = nn.ReLU()
        self.layer_norm = nn.LayerNorm(layer_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        기능:
        - FCN block 한 단계를 적용해 다음 표현을 만든다.
        
        입력:
        - `x`: 모델에 전달할 입력 텐서.
        
        반환:
        - 모델이 계산한 출력 텐서를 반환한다.
        """
        return self.relu(self.layer_norm(self.fcn_layer(x)))


class WakeWordFCModel(nn.Module):
    def __init__(self, input_shape: tuple[int, int], layer_dim: int, n_blocks: int):
        """
        기능:
        - wake word 분류기 모델 구조를 초기화한다.
        
        입력:
        - `input_shape`: 모델 입력 feature shape.
        - `layer_dim`: 은닉층 차원 크기.
        - `n_blocks`: FCN block 개수.
        
        반환:
        - 없음.
        """
        super().__init__()
        self.flatten = nn.Flatten()
        self.layer1 = nn.Linear(input_shape[0] * input_shape[1], layer_dim)
        self.relu1 = nn.ReLU()
        self.layernorm1 = nn.LayerNorm(layer_dim)
        self.blocks = nn.ModuleList([FCNBlock(layer_dim) for _ in range(n_blocks)])
        self.last_layer = nn.Linear(layer_dim, 1)
        self.last_act = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        기능:
        - 입력 텐서를 wake word score 출력으로 변환한다.
        
        입력:
        - `x`: 모델에 전달할 입력 텐서.
        
        반환:
        - 모델이 계산한 출력 텐서를 반환한다.
        """
        x = self.relu1(self.layernorm1(self.layer1(self.flatten(x))))
        for block in self.blocks:
            x = block(x)
        return self.last_act(self.last_layer(x))


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
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=MODEL_DIR / "hi_popo_classifier.pt",
        help="Input checkpoint path",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=MODEL_DIR / "hi_popo_classifier.onnx",
        help="Output ONNX path",
    )
    parser.add_argument(
        "--metadata-output",
        type=Path,
        default=MODEL_DIR / "hi_popo_classifier_onnx.json",
        help="Output metadata JSON path",
    )
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--skip-validate", action="store_true")
    return parser.parse_args()


def load_checkpoint(path: Path) -> dict:
    """
    기능:
    - `load_checkpoint` 역할에 맞는 데이터를 읽어 온다.
    
    입력:
    - `path`: 처리할 파일 경로.
    
    반환:
    - 읽어 온 데이터 또는 객체를 반환한다.
    """
    checkpoint = torch.load(path, map_location="cpu")
    if "model_state_dict" not in checkpoint:
        raise ValueError(f"Invalid checkpoint format: {path}")
    return checkpoint


def export_model(checkpoint: dict, output_path: Path, opset: int) -> None:
    """
    기능:
    - checkpoint를 ONNX 모델 파일로 export한다.
    
    입력:
    - `checkpoint`: 학습 결과 checkpoint 데이터.
    - `output_path`: 저장할 출력 파일 경로.
    - `opset`: ONNX export에 사용할 opset 버전.
    
    반환:
    - 없음.
    """
    input_shape = tuple(checkpoint["input_shape"])
    layer_dim = int(checkpoint["layer_dim"])
    n_blocks = int(checkpoint["n_blocks"])

    model = WakeWordFCModel(input_shape=input_shape, layer_dim=layer_dim, n_blocks=n_blocks)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    dummy = torch.zeros(1, *input_shape, dtype=torch.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy,
        str(output_path),
        input_names=["features"],
        output_names=["scores"],
        dynamic_axes={
            "features": {0: "batch"},
            "scores": {0: "batch"},
        },
        opset_version=opset,
    )


def write_metadata(checkpoint: dict, checkpoint_path: Path, onnx_path: Path, metadata_path: Path) -> None:
    """
    기능:
    - ONNX export 결과를 설명하는 metadata JSON을 저장한다.
    
    입력:
    - `checkpoint`: 학습 결과 checkpoint 데이터.
    - `checkpoint_path`: checkpoint 파일 경로.
    - `onnx_path`: 검증하거나 기록할 ONNX 파일 경로.
    - `metadata_path`: 메타데이터 저장 또는 로드 경로.
    
    반환:
    - 없음.
    """
    metadata = {
        "checkpoint": str(checkpoint_path),
        "onnx_path": str(onnx_path),
        "input_shape": list(checkpoint["input_shape"]),
        "threshold": float(checkpoint["threshold"]),
        "layer_dim": int(checkpoint["layer_dim"]),
        "n_blocks": int(checkpoint["n_blocks"]),
        "best_metrics": checkpoint["best_metrics"],
        "train_args": checkpoint["train_args"],
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def validate_export(onnx_path: Path, checkpoint: dict) -> None:
    """
    기능:
    - export된 ONNX 모델의 기본 입출력 shape를 검증한다.
    
    입력:
    - `onnx_path`: 검증하거나 기록할 ONNX 파일 경로.
    - `checkpoint`: 학습 결과 checkpoint 데이터.
    
    반환:
    - 없음.
    """
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    dummy = np.zeros((1, *checkpoint["input_shape"]), dtype=np.float32)
    outputs = session.run(["scores"], {"features": dummy})[0]
    if outputs.shape != (1, 1):
        raise RuntimeError(f"Unexpected ONNX output shape: {outputs.shape}")


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
    checkpoint = load_checkpoint(args.checkpoint)

    export_model(checkpoint, args.output, args.opset)
    write_metadata(checkpoint, args.checkpoint, args.output, args.metadata_output)

    run_dir = args.checkpoint.parent
    if run_dir.name == "runs":
        # not expected; keep latest-only export as-is
        pass
    elif run_dir.parent.name == "runs":
        run_onnx_path = run_dir / args.output.name
        run_metadata_path = run_dir / args.metadata_output.name
        if run_onnx_path != args.output:
            run_onnx_path.write_bytes(args.output.read_bytes())
        if run_metadata_path != args.metadata_output:
            run_metadata_path.write_text(args.metadata_output.read_text(encoding="utf-8"), encoding="utf-8")

    if not args.skip_validate:
        validate_export(args.output, checkpoint)

    print(f"Checkpoint: {args.checkpoint}")
    print(f"Saved ONNX: {args.output}")
    print(f"Saved metadata: {args.metadata_output}")
    print(f"Threshold: {float(checkpoint['threshold']):.4f}")
    print(f"Input shape: {tuple(checkpoint['input_shape'])}")


if __name__ == "__main__":
    main()
