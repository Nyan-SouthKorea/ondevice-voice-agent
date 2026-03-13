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
        super().__init__()
        self.fcn_layer = nn.Linear(layer_dim, layer_dim)
        self.relu = nn.ReLU()
        self.layer_norm = nn.LayerNorm(layer_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.relu(self.layer_norm(self.fcn_layer(x)))


class WakeWordFCModel(nn.Module):
    def __init__(self, input_shape: tuple[int, int], layer_dim: int, n_blocks: int):
        super().__init__()
        self.flatten = nn.Flatten()
        self.layer1 = nn.Linear(input_shape[0] * input_shape[1], layer_dim)
        self.relu1 = nn.ReLU()
        self.layernorm1 = nn.LayerNorm(layer_dim)
        self.blocks = nn.ModuleList([FCNBlock(layer_dim) for _ in range(n_blocks)])
        self.last_layer = nn.Linear(layer_dim, 1)
        self.last_act = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.relu1(self.layernorm1(self.layer1(self.flatten(x))))
        for block in self.blocks:
            x = block(x)
        return self.last_act(self.last_layer(x))


def parse_args() -> argparse.Namespace:
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
    checkpoint = torch.load(path, map_location="cpu")
    if "model_state_dict" not in checkpoint:
        raise ValueError(f"Invalid checkpoint format: {path}")
    return checkpoint


def export_model(checkpoint: dict, output_path: Path, opset: int) -> None:
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
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    dummy = np.zeros((1, *checkpoint["input_shape"]), dtype=np.float32)
    outputs = session.run(["scores"], {"features": dummy})[0]
    if outputs.shape != (1, 1):
        raise RuntimeError(f"Unexpected ONNX output shape: {outputs.shape}")


def main() -> None:
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
