"""
ONNX로 export한 wake word classifier를 로드해 feature 단위 추론을 수행한다.

주의:
- 이 모듈은 raw audio가 아니라 Google Speech Embedding feature를 입력으로 받는다.
- 단일 입력은 `(16, 96)` window 또는 `(T, 96)` clip feature를 받을 수 있다.
- clip feature가 들어오면 `(16, 96)` sliding window들을 만든 뒤 max score를 사용한다.
- 실제 마이크 추론에서는 upstream embedding 추출 단계가 별도로 필요하다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np
import onnxruntime as ort

WINDOW_FRAMES = 16
FEATURE_DIM = 96


def _default_providers() -> list[str]:
    available = set(ort.get_available_providers())
    providers: list[str] = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers


def _normalize_provider_name(provider: str) -> str:
    key = provider.strip().lower()
    if key == "cpu":
        return "CPUExecutionProvider"
    if key == "cuda":
        return "CUDAExecutionProvider"
    return provider


class HiPopoWakeWordONNX:
    def __init__(
        self,
        model_path: str | Path,
        threshold: float | None = None,
        metadata_path: str | Path | None = None,
        providers: Sequence[str] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path) if metadata_path else self.model_path.with_name(
            self.model_path.stem + "_onnx.json"
        )
        self.providers = (
            [_normalize_provider_name(provider) for provider in providers]
            if providers is not None
            else _default_providers()
        )
        self.session = ort.InferenceSession(str(self.model_path), providers=self.providers)
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

        metadata_threshold = None
        if self.metadata_path.exists():
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            metadata_threshold = metadata.get("threshold")

        self.threshold = float(threshold if threshold is not None else (metadata_threshold or 0.8))

    def _predict_window_scores(self, features: np.ndarray) -> np.ndarray:
        arr = np.asarray(features, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)
        if arr.ndim != 3:
            raise ValueError(f"Expected input ndim 2 or 3, got shape {arr.shape}")
        if arr.shape[1:] != (WINDOW_FRAMES, FEATURE_DIM):
            raise ValueError(f"Expected feature shape (*, 16, 96), got {arr.shape}")

        outputs = self.session.run([self.output_name], {self.input_name: arr})[0]
        return np.asarray(outputs, dtype=np.float32).reshape(-1)

    def predict_window_scores(self, features: np.ndarray) -> np.ndarray:
        return self._predict_window_scores(features)

    def predict_clip_scores(self, clip_features: np.ndarray) -> np.ndarray:
        arr = np.asarray(clip_features, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)
        if arr.ndim != 3:
            raise ValueError(f"Expected clip ndim 2 or 3, got shape {arr.shape}")
        if arr.shape[-1] != FEATURE_DIM:
            raise ValueError(f"Expected clip feature dim 96, got {arr.shape}")

        clip_scores: list[float] = []
        for clip in arr:
            if clip.shape[0] < WINDOW_FRAMES:
                raise ValueError(f"Clip must have at least {WINDOW_FRAMES} frames, got {clip.shape}")
            windows = []
            for start in range(0, clip.shape[0] - WINDOW_FRAMES + 1):
                windows.append(clip[start:start + WINDOW_FRAMES, :])
            window_scores = self._predict_window_scores(np.stack(windows, axis=0))
            clip_scores.append(float(np.max(window_scores)))
        return np.asarray(clip_scores, dtype=np.float32)

    def predict_score(self, features: np.ndarray) -> float:
        arr = np.asarray(features, dtype=np.float32)
        if arr.ndim == 2 and arr.shape == (WINDOW_FRAMES, FEATURE_DIM):
            return float(self._predict_window_scores(arr)[0])
        if arr.ndim == 2 and arr.shape[1] == FEATURE_DIM and arr.shape[0] >= WINDOW_FRAMES:
            return float(self.predict_clip_scores(arr)[0])
        if arr.ndim == 3 and arr.shape[1:] == (WINDOW_FRAMES, FEATURE_DIM):
            return float(np.max(self._predict_window_scores(arr)))
        raise ValueError(f"Unsupported feature shape for score prediction: {arr.shape}")

    def is_detected(self, features: np.ndarray, threshold: float | None = None) -> bool:
        score = self.predict_score(features)
        return score >= float(self.threshold if threshold is None else threshold)
