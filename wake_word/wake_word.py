"""
ONNX로 export한 wake word classifier를 로드해 feature 단위 추론을 수행한다.

주의:
- 이 모듈은 raw audio가 아니라 Google Speech Embedding feature를 입력으로 받는다.
- 단일 입력은 `(16, 96)` window 또는 `(T, 96)` clip feature를 받을 수 있다.
- clip feature가 들어오면 `(16, 96)` sliding window들을 만든 뒤 max score를 사용한다.
- 실제 마이크 추론에서는 upstream embedding 추출 단계가 별도로 필요하다.
"""

from __future__ import annotations

import sys
import time
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import onnxruntime as ort

REPO_ROOT = Path(__file__).resolve().parent
OPENWAKEWORD_ROOT = REPO_ROOT / "openWakeWord"
if str(OPENWAKEWORD_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENWAKEWORD_ROOT))

from openwakeword.utils import AudioFeatures, download_models

TARGET_SR = 16000
STREAM_CHUNK_SAMPLES = 1280
WINDOW_FRAMES = 16
FEATURE_DIM = 96
OWW_MODEL_DIR = OPENWAKEWORD_ROOT / "openwakeword" / "resources" / "models"


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


def _ensure_feature_models() -> tuple[str, str]:
    OWW_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    melspec_path = OWW_MODEL_DIR / "melspectrogram.onnx"
    embedding_path = OWW_MODEL_DIR / "embedding_model.onnx"
    if not melspec_path.exists() or not embedding_path.exists():
        download_models(target_directory=str(OWW_MODEL_DIR))
    return str(melspec_path), str(embedding_path)


def _coerce_audio_to_pcm16(audio: np.ndarray) -> np.ndarray:
    arr = np.asarray(audio)
    if arr.ndim > 2:
        raise ValueError(f"Expected mono audio with ndim 1 or 2, got shape {arr.shape}")
    if arr.ndim == 2:
        if arr.shape[1] == 1:
            arr = arr[:, 0]
        else:
            arr = arr.mean(axis=1)

    if np.issubdtype(arr.dtype, np.floating):
        arr = np.clip(arr, -1.0, 1.0)
        return (arr * 32767.0).astype(np.int16)

    if arr.dtype != np.int16:
        arr = np.clip(arr, -32768, 32767).astype(np.int16)
    return arr


@dataclass
class StreamingPrediction:
    score: float
    detected: bool
    threshold: float
    audio_level: float
    timestamp: float


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


class HiPopoWakeWordRealtime:
    def __init__(
        self,
        model_path: str | Path,
        threshold: float | None = None,
        metadata_path: str | Path | None = None,
        providers: Sequence[str] | None = None,
        feature_device: str = "cpu",
        cooldown_sec: float = 1.0,
        melspec_model_path: str | Path | None = None,
        embedding_model_path: str | Path | None = None,
    ) -> None:
        self.classifier = HiPopoWakeWordONNX(
            model_path=model_path,
            threshold=threshold,
            metadata_path=metadata_path,
            providers=providers,
        )
        if melspec_model_path is None or embedding_model_path is None:
            default_melspec, default_embedding = _ensure_feature_models()
            melspec_model_path = melspec_model_path or default_melspec
            embedding_model_path = embedding_model_path or default_embedding

        self.preprocessor = AudioFeatures(
            melspec_model_path=str(melspec_model_path),
            embedding_model_path=str(embedding_model_path),
            sr=TARGET_SR,
            ncpu=1,
            inference_framework="onnx",
            device=feature_device,
        )
        self.feature_execution_provider = getattr(self.preprocessor, "onnx_execution_provider", "unknown")
        self.cooldown_sec = cooldown_sec
        self._streamed_feature_frames = 0
        self._last_detection_time = 0.0

    @property
    def threshold(self) -> float:
        return self.classifier.threshold

    def reset(self) -> None:
        self.preprocessor.reset()
        self._streamed_feature_frames = 0
        self._last_detection_time = 0.0

    def process_audio(
        self,
        audio_chunk: np.ndarray,
        threshold: float | None = None,
    ) -> list[StreamingPrediction]:
        pcm16 = _coerce_audio_to_pcm16(audio_chunk)
        audio_level = float(np.sqrt(np.mean(np.square(pcm16.astype(np.float32) / 32768.0)))) if pcm16.size else 0.0

        processed_samples = self.preprocessor(pcm16)
        n_new_feature_frames = processed_samples // STREAM_CHUNK_SAMPLES
        if n_new_feature_frames <= 0:
            return []

        previous_frames = self._streamed_feature_frames
        self._streamed_feature_frames += n_new_feature_frames
        effective_threshold = float(self.threshold if threshold is None else threshold)

        predictions: list[StreamingPrediction] = []
        for offset in range(n_new_feature_frames - 1, -1, -1):
            available_frames = self._streamed_feature_frames - offset
            if available_frames < WINDOW_FRAMES:
                continue

            window = self.preprocessor.get_features(
                n_feature_frames=WINDOW_FRAMES,
                start_ndx=-WINDOW_FRAMES - offset,
            )[0]
            score = self.classifier.predict_score(window)
            now = time.monotonic()
            detected = score >= effective_threshold and (now - self._last_detection_time) >= self.cooldown_sec
            if detected:
                self._last_detection_time = now
            predictions.append(
                StreamingPrediction(
                    score=score,
                    detected=detected,
                    threshold=effective_threshold,
                    audio_level=audio_level,
                    timestamp=now,
                )
            )

        if previous_frames < WINDOW_FRAMES and self._streamed_feature_frames >= WINDOW_FRAMES and not predictions:
            window = self.preprocessor.get_features(n_feature_frames=WINDOW_FRAMES)[0]
            score = self.classifier.predict_score(window)
            now = time.monotonic()
            detected = score >= effective_threshold and (now - self._last_detection_time) >= self.cooldown_sec
            if detected:
                self._last_detection_time = now
            predictions.append(
                StreamingPrediction(
                    score=score,
                    detected=detected,
                    threshold=effective_threshold,
                    audio_level=audio_level,
                    timestamp=now,
                )
            )

        return predictions
