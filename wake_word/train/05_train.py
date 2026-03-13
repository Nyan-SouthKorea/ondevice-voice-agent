"""
05_train.py
openWakeWord의 FC 분류기 구조를 사용해 사전 추출한 feature로 wake word 분류기를 학습한다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/numba_cache")

REPO_ROOT = Path(__file__).resolve().parents[1]

SEED = 42
WINDOW_FRAMES = 16
FEATURE_DIM = 96
PROGRESS_INTERVAL_SEC = 60

BASE_DIR = REPO_ROOT / "data" / "hi_popo"
FEATURE_DIR = BASE_DIR / "features"
MODEL_DIR = REPO_ROOT / "models" / "hi_popo"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = MODEL_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cpu", "gpu"], default="gpu")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--layer-dim", type=int, default=32)
    parser.add_argument("--n-blocks", type=int, default=1)
    parser.add_argument("--negative-weight", type=float, default=5.0)
    parser.add_argument("--progress-interval-sec", type=int, default=PROGRESS_INTERVAL_SEC)
    parser.add_argument("--run-name", type=str, default=None)
    parser.add_argument("--limit-train-positive", type=int, default=None)
    parser.add_argument("--limit-train-negative", type=int, default=None)
    parser.add_argument("--limit-val-positive", type=int, default=None)
    parser.add_argument("--limit-val-negative", type=int, default=None)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_device(requested: str) -> torch.device:
    if requested == "gpu" and torch.cuda.is_available():
        return torch.device("cuda:0")
    return torch.device("cpu")


def load_feature_file(path: Path, limit: int | None = None) -> np.memmap:
    arr = np.load(path, mmap_mode="r")
    if limit is None:
        return arr
    return arr[:limit]


class RandomWindowDataset(Dataset):
    def __init__(self, pos: np.ndarray, neg: np.ndarray):
        self.pos = pos
        self.neg = neg
        self.n_pos = len(pos)
        self.n_neg = len(neg)
        self.length = self.n_pos + self.n_neg

    def __len__(self) -> int:
        return self.length

    def _sample_window(self, clip: np.ndarray) -> np.ndarray:
        max_start = clip.shape[0] - WINDOW_FRAMES
        start = 0 if max_start <= 0 else np.random.randint(0, max_start + 1)
        return clip[start:start + WINDOW_FRAMES, :]

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        if index % 2 == 0:
            clip = self.pos[np.random.randint(0, self.n_pos)]
            label = 1.0
        else:
            clip = self.neg[np.random.randint(0, self.n_neg)]
            label = 0.0
        window = self._sample_window(clip).astype(np.float32, copy=False)
        return torch.from_numpy(window.copy()), torch.tensor(label, dtype=torch.float32)


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


@dataclass
class ClipEvalResult:
    recall: float
    accuracy: float
    false_positives: int
    false_positive_rate: float
    threshold: float


def predict_clip_scores(model: nn.Module, clips: np.ndarray, device: torch.device, batch_size: int) -> np.ndarray:
    scores: list[float] = []
    model.eval()
    with torch.no_grad():
        for clip in clips:
            windows = []
            for start in range(0, clip.shape[0] - WINDOW_FRAMES + 1):
                windows.append(clip[start:start + WINDOW_FRAMES, :])
            batch_scores = []
            for start in range(0, len(windows), batch_size):
                x = torch.from_numpy(np.stack(windows[start:start + batch_size]).astype(np.float32)).to(device)
                preds = model(x).squeeze(-1)
                batch_scores.append(preds.detach().cpu().numpy())
            clip_score = float(np.max(np.concatenate(batch_scores))) if batch_scores else 0.0
            scores.append(clip_score)
    return np.array(scores, dtype=np.float32)


def evaluate_clip_level(
    model: nn.Module,
    pos_val: np.ndarray,
    neg_val: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> ClipEvalResult:
    pos_scores = predict_clip_scores(model, pos_val, device, batch_size)
    neg_scores = predict_clip_scores(model, neg_val, device, batch_size)
    thresholds = np.linspace(0.1, 0.9, 17)

    best_result: ClipEvalResult | None = None
    best_score = -1e9
    for threshold in thresholds:
        pos_pred = pos_scores >= threshold
        neg_pred = neg_scores >= threshold
        recall = float(pos_pred.mean()) if len(pos_pred) else 0.0
        neg_acc = float((~neg_pred).mean()) if len(neg_pred) else 0.0
        accuracy = (recall + neg_acc) / 2.0
        false_positives = int(neg_pred.sum())
        false_positive_rate = false_positives / max(len(neg_pred), 1)
        score = recall - 0.25 * false_positive_rate
        if score > best_score:
            best_score = score
            best_result = ClipEvalResult(
                recall=recall,
                accuracy=accuracy,
                false_positives=false_positives,
                false_positive_rate=false_positive_rate,
                threshold=float(threshold),
            )

    assert best_result is not None
    return best_result


def log_progress(prefix: str, step: int, total_steps: int, start_time: float, loss: float) -> None:
    elapsed = time.monotonic() - start_time
    rate = step / elapsed if elapsed > 0 else 0.0
    eta = int((total_steps - step) / rate) if rate > 0 else -1
    eta_text = f"{eta // 60}m{eta % 60}s" if eta >= 0 else "unknown"
    percent = step / total_steps * 100 if total_steps else 100.0
    print(
        f"[progress] {prefix}: {step}/{total_steps} ({percent:.1f}%) | "
        f"loss {loss:.6f} | {rate:.2f} steps/s | eta {eta_text}",
        flush=True,
    )


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    device = resolve_device(args.device)
    print(f"Training device: {device}", flush=True)

    if args.run_name is None:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        args.run_name = f"{timestamp}_baseline"

    run_dir = RUNS_DIR / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run dir: {run_dir}", flush=True)

    pos_train = load_feature_file(FEATURE_DIR / "positive_features_train.npy", args.limit_train_positive)
    neg_train = load_feature_file(FEATURE_DIR / "negative_features_train.npy", args.limit_train_negative)
    pos_val = load_feature_file(FEATURE_DIR / "positive_features_test.npy", args.limit_val_positive)
    neg_val = load_feature_file(FEATURE_DIR / "negative_features_test.npy", args.limit_val_negative)

    print(
        f"Train features: positive={len(pos_train):,}, negative={len(neg_train):,}\n"
        f"Val features: positive={len(pos_val):,}, negative={len(neg_val):,}",
        flush=True,
    )

    dataset = RandomWindowDataset(pos_train, neg_train)
    steps_per_epoch = math.ceil(len(dataset) / args.batch_size)
    train_loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        drop_last=False,
    )

    model = WakeWordFCModel(
        input_shape=(WINDOW_FRAMES, FEATURE_DIM),
        layer_dim=args.layer_dim,
        n_blocks=args.n_blocks,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_state = None
    best_metrics = None
    history: list[dict[str, float | int]] = []

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_start = time.monotonic()
        last_report = epoch_start
        running_loss = 0.0

        for step, (x, y) in enumerate(train_loader, start=1):
            x = x.to(device)
            y = y.to(device).unsqueeze(-1)

            optimizer.zero_grad()
            preds = model(x)
            weights = torch.ones_like(y)
            weights[y == 0] = args.negative_weight
            loss = torch.nn.functional.binary_cross_entropy(preds, y, weight=weights)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            now = time.monotonic()
            if now - last_report >= args.progress_interval_sec:
                log_progress(
                    prefix=f"train epoch {epoch}",
                    step=step,
                    total_steps=steps_per_epoch,
                    start_time=epoch_start,
                    loss=running_loss / step,
                )
                last_report = now

        avg_loss = running_loss / max(steps_per_epoch, 1)
        metrics = evaluate_clip_level(model, pos_val, neg_val, device, batch_size=1024)
        history.append(
            {
                "epoch": epoch,
                "train_loss": avg_loss,
                "val_recall": metrics.recall,
                "val_accuracy": metrics.accuracy,
                "val_false_positive_rate": metrics.false_positive_rate,
                "val_false_positives": metrics.false_positives,
                "threshold": metrics.threshold,
            }
        )

        print(
            f"[epoch] {epoch}/{args.epochs} | loss {avg_loss:.6f} | "
            f"val_recall {metrics.recall:.4f} | val_accuracy {metrics.accuracy:.4f} | "
            f"val_fp_rate {metrics.false_positive_rate:.4f} | threshold {metrics.threshold:.2f}",
            flush=True,
        )

        current_score = metrics.recall - 0.25 * metrics.false_positive_rate
        best_score = -1e9 if best_metrics is None else best_metrics.recall - 0.25 * best_metrics.false_positive_rate
        if current_score > best_score:
            best_state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
            best_metrics = metrics

    if best_state is None or best_metrics is None:
        raise RuntimeError("학습이 정상적으로 완료되지 않았습니다.")

    checkpoint = {
        "model_state_dict": best_state,
        "input_shape": (WINDOW_FRAMES, FEATURE_DIM),
        "layer_dim": args.layer_dim,
        "n_blocks": args.n_blocks,
        "threshold": best_metrics.threshold,
        "best_metrics": {
            "recall": best_metrics.recall,
            "accuracy": best_metrics.accuracy,
            "false_positives": best_metrics.false_positives,
            "false_positive_rate": best_metrics.false_positive_rate,
        },
        "train_args": vars(args),
    }

    checkpoint_path = run_dir / "hi_popo_classifier.pt"
    history_path = run_dir / "training_history.json"
    metadata_path = run_dir / "run_metadata.json"
    latest_checkpoint_path = MODEL_DIR / "hi_popo_classifier.pt"
    latest_history_path = MODEL_DIR / "hi_popo_training_history.json"
    latest_metadata_path = MODEL_DIR / "hi_popo_latest_run.json"

    torch.save(checkpoint, checkpoint_path)
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    metadata = {
        "run_name": args.run_name,
        "created_at": dt.datetime.now().isoformat(),
        "device_requested": args.device,
        "device_resolved": str(device),
        "train_sizes": {
            "positive": len(pos_train),
            "negative": len(neg_train),
        },
        "val_sizes": {
            "positive": len(pos_val),
            "negative": len(neg_val),
        },
        "best_metrics": checkpoint["best_metrics"],
        "threshold": best_metrics.threshold,
        "train_args": vars(args),
        "artifacts": {
            "checkpoint": str(checkpoint_path),
            "history": str(history_path),
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    torch.save(checkpoint, latest_checkpoint_path)
    latest_history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    latest_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Saved checkpoint: {checkpoint_path}", flush=True)
    print(f"Saved history: {history_path}", flush=True)
    print(f"Saved metadata: {metadata_path}", flush=True)
    print(f"Updated latest checkpoint: {latest_checkpoint_path}", flush=True)


if __name__ == "__main__":
    main()
