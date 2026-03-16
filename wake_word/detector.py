"""
ONNX로 export한 wake word classifier를 로드해 feature 단위 추론을 수행한다.

주의:
- 이 모듈은 raw audio가 아니라 Google Speech Embedding feature를 입력으로 받는다.
- 단일 입력은 `(16, 96)` window 또는 `(T, 96)` clip feature를 받을 수 있다.
- clip feature가 들어오면 `(16, 96)` sliding window들을 만든 뒤 max score를 사용한다.
- 실제 마이크 추론에서는 upstream embedding 추출 단계가 별도로 필요하다.
- feature backbone ONNX는 `wake_word/assets/feature_models/` 아래의 로컬 파일을 사용한다.
"""

import time
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort

from .features import AudioFeatures, ensure_feature_models

TARGET_SR = 16000
STREAM_CHUNK_SAMPLES = 1280
WINDOW_FRAMES = 16
FEATURE_DIM = 96


def _default_providers():
    """
    기능:
    - 현재 환경에서 사용할 기본 ONNX provider 목록을 구성한다.
    
    입력:
    - 없음.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    available = set(ort.get_available_providers())
    providers = []
    if "CUDAExecutionProvider" in available:
        providers.append("CUDAExecutionProvider")
    providers.append("CPUExecutionProvider")
    return providers


def _normalize_provider_name(provider):
    """
    기능:
    - 짧은 provider 이름을 onnxruntime 표준 이름으로 바꾼다.
    
    입력:
    - `provider`: 정규화할 provider 이름 문자열.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
    key = provider.strip().lower()
    if key == "cpu":
        return "CPUExecutionProvider"
    if key == "cuda":
        return "CUDAExecutionProvider"
    return provider


def _ensure_feature_models():
    """
    기능:
    - wake word feature backbone ONNX 두 개의 기본 경로를 반환한다.
    
    입력:
    - 없음.
    
    반환:
    - mel spectrogram ONNX 경로와 embedding ONNX 경로를 순서대로 반환한다.
    """
    return ensure_feature_models()


def _coerce_audio_to_pcm16(audio):
    """
    기능:
    - 입력 오디오를 mono PCM16 배열로 변환한다.
    
    입력:
    - `audio`: 처리할 오디오 배열.
    
    반환:
    - 함수 실행 결과를 반환한다.
    """
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
        model_path,
        threshold=None,
        metadata_path=None,
        providers=None,
    ):
        """
        기능:
        - ONNX classifier 세션과 threshold를 초기화한다.
        
        입력:
        - `model_path`: wake word ONNX 모델 경로.
        - `threshold`: 검출 기준값. `None`이면 기본 threshold를 사용한다.
        - `metadata_path`: 메타데이터 저장 또는 로드 경로.
        - `providers`: 사용할 ONNX provider 목록 또는 문자열.
        
        반환:
        - 없음.
        """
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

    def _predict_window_scores(self, features):
        """
        기능:
        - window feature 배치에 대한 classifier score를 계산한다.
        
        입력:
        - `features`: score를 계산할 feature 배열.
        
        반환:
        - 함수 실행 결과를 반환한다.
        """
        arr = np.asarray(features, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)
        if arr.ndim != 3:
            raise ValueError(f"Expected input ndim 2 or 3, got shape {arr.shape}")
        if arr.shape[1:] != (WINDOW_FRAMES, FEATURE_DIM):
            raise ValueError(f"Expected feature shape (*, 16, 96), got {arr.shape}")

        outputs = self.session.run([self.output_name], {self.input_name: arr})[0]
        return np.asarray(outputs, dtype=np.float32).reshape(-1)

    def predict_window_scores(self, features):
        """
        기능:
        - window feature 입력에 대한 score 배열을 반환한다.
        
        입력:
        - `features`: score를 계산할 feature 배열.
        
        반환:
        - 계산된 결과 목록 또는 배열을 반환한다.
        """
        return self._predict_window_scores(features)

    def predict_clip_scores(self, clip_features):
        """
        기능:
        - clip feature 배열에 대해 clip 단위 score를 계산한다.
        
        입력:
        - `clip_features`: clip 단위 feature 배열.
        
        반환:
        - 계산된 결과 목록 또는 배열을 반환한다.
        """
        arr = np.asarray(clip_features, dtype=np.float32)
        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)
        if arr.ndim != 3:
            raise ValueError(f"Expected clip ndim 2 or 3, got shape {arr.shape}")
        if arr.shape[-1] != FEATURE_DIM:
            raise ValueError(f"Expected clip feature dim 96, got {arr.shape}")

        clip_scores = []
        for clip in arr:
            if clip.shape[0] < WINDOW_FRAMES:
                raise ValueError(f"Clip must have at least {WINDOW_FRAMES} frames, got {clip.shape}")
            windows = []
            for start in range(0, clip.shape[0] - WINDOW_FRAMES + 1):
                windows.append(clip[start:start + WINDOW_FRAMES, :])
            window_scores = self._predict_window_scores(np.stack(windows, axis=0))
            clip_scores.append(float(np.max(window_scores)))
        return np.asarray(clip_scores, dtype=np.float32)

    def predict_score(self, features):
        """
        기능:
        - window 또는 clip feature 입력에서 대표 score 하나를 계산한다.
        
        입력:
        - `features`: score를 계산할 feature 배열.
        
        반환:
        - 계산된 점수 하나를 반환한다.
        """
        arr = np.asarray(features, dtype=np.float32)
        if arr.ndim == 2 and arr.shape == (WINDOW_FRAMES, FEATURE_DIM):
            return float(self._predict_window_scores(arr)[0])
        if arr.ndim == 2 and arr.shape[1] == FEATURE_DIM and arr.shape[0] >= WINDOW_FRAMES:
            return float(self.predict_clip_scores(arr)[0])
        if arr.ndim == 3 and arr.shape[1:] == (WINDOW_FRAMES, FEATURE_DIM):
            return float(np.max(self._predict_window_scores(arr)))
        raise ValueError(f"Unsupported feature shape for score prediction: {arr.shape}")

    def is_detected(self, features, threshold=None):
        """
        기능:
        - 현재 score가 threshold 이상인지 판단한다.
        
        입력:
        - `features`: score를 계산할 feature 배열.
        - `threshold`: 검출 기준값. `None`이면 기본 threshold를 사용한다.
        
        반환:
        - threshold 충족 여부를 불리언으로 반환한다.
        """
        score = self.predict_score(features)
        return score >= float(self.threshold if threshold is None else threshold)


class HiPopoWakeWordRealtime:
    def __init__(
        self,
        model_path,
        threshold=None,
        metadata_path=None,
        providers=None,
        feature_device="cpu",
        cooldown_sec=1.0,
        melspec_model_path=None,
        embedding_model_path=None,
    ):
        """
        기능:
        - 실시간 추론에 필요한 classifier와 feature extractor를 초기화한다.
        
        입력:
        - `model_path`: wake word ONNX 모델 경로.
        - `threshold`: 검출 기준값. `None`이면 기본 threshold를 사용한다.
        - `metadata_path`: 메타데이터 저장 또는 로드 경로.
        - `providers`: 사용할 ONNX provider 목록 또는 문자열.
        - `feature_device`: feature extractor를 실행할 장치 이름.
        - `cooldown_sec`: 감지 이벤트 사이에 둘 최소 간격(초).
        - `melspec_model_path`: mel spectrogram ONNX 모델 경로.
        - `embedding_model_path`: embedding ONNX 모델 경로.
        
        반환:
        - 없음.
        """
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
        self.last_runtime_stats = self._make_runtime_stats(STREAM_CHUNK_SAMPLES)

    @property
    def threshold(self):
        """
        기능:
        - 현재 detector가 사용하는 threshold 값을 반환한다.
        
        입력:
        - 없음.
        
        반환:
        - 현재 threshold 값을 반환한다.
        """
        return self.classifier.threshold

    def reset(self):
        """
        기능:
        - 실시간 추론 상태를 초기화한다.
        
        입력:
        - 없음.
        
        반환:
        - 없음.
        """
        self.preprocessor.reset()
        self._streamed_feature_frames = 0
        self._last_detection_time = 0.0
        self.last_runtime_stats = self._make_runtime_stats(STREAM_CHUNK_SAMPLES)

    def _make_runtime_stats(self, chunk_samples):
        """
        기능:
        - GUI에 표시할 기본 runtime timing 정보를 만든다.

        입력:
        - `chunk_samples`: 이번 처리 단위의 샘플 수.

        반환:
        - timing 정보를 담은 딕셔너리를 반환한다.
        """
        chunk_ms = float(chunk_samples) / TARGET_SR * 1000.0
        return {
            "chunk_samples": int(chunk_samples),
            "chunk_ms": chunk_ms,
            "feature_step_ms": float(STREAM_CHUNK_SAMPLES) / TARGET_SR * 1000.0,
            "classifier_window_frames": WINDOW_FRAMES,
            "classifier_window_ms": float(WINDOW_FRAMES * STREAM_CHUNK_SAMPLES) / TARGET_SR * 1000.0,
            "feature_frames_emitted": 0,
            "melspectrogram_ms": 0.0,
            "embedding_ms": 0.0,
            "classifier_ms": 0.0,
            "total_ms": 0.0,
            "melspectrogram_calls": 0,
            "embedding_calls": 0,
            "classifier_calls": 0,
        }

    def _stream_feature_audio(self, pcm16, runtime_stats):
        """
        기능:
        - raw audio chunk를 feature buffer로 반영하면서 ONNX별 실행 시간을 기록한다.

        입력:
        - `pcm16`: PCM16으로 정규화된 입력 오디오 배열.
        - `runtime_stats`: 이번 chunk 처리에 누적할 timing 딕셔너리.

        반환:
        - 이번 호출에서 실제로 처리된 sample 수를 반환한다.
        """
        processed_samples = 0
        preprocessor = self.preprocessor
        buffered = pcm16

        if preprocessor.raw_data_remainder.shape[0] != 0:
            buffered = np.concatenate((preprocessor.raw_data_remainder, buffered))
            preprocessor.raw_data_remainder = np.empty(0, dtype=buffered.dtype)

        if preprocessor.accumulated_samples + buffered.shape[0] >= STREAM_CHUNK_SAMPLES:
            remainder = (preprocessor.accumulated_samples + buffered.shape[0]) % STREAM_CHUNK_SAMPLES
            if remainder != 0:
                even_chunks = buffered[0:-remainder]
                preprocessor._buffer_raw_data(even_chunks)
                preprocessor.accumulated_samples += len(even_chunks)
                preprocessor.raw_data_remainder = buffered[-remainder:]
            else:
                preprocessor._buffer_raw_data(buffered)
                preprocessor.accumulated_samples += buffered.shape[0]
                preprocessor.raw_data_remainder = np.empty(0, dtype=buffered.dtype)
        else:
            preprocessor.accumulated_samples += buffered.shape[0]
            preprocessor._buffer_raw_data(buffered)

        if (
            preprocessor.accumulated_samples >= STREAM_CHUNK_SAMPLES
            and preprocessor.accumulated_samples % STREAM_CHUNK_SAMPLES == 0
        ):
            if len(preprocessor.raw_data_buffer) < 400:
                raise ValueError("The number of input frames must be at least 400 samples @ 16khz (25 ms)!")

            recent_audio = list(preprocessor.raw_data_buffer)[-preprocessor.accumulated_samples - 160 * 3 :]

            melspec_start = time.perf_counter()
            new_melspec = preprocessor._get_melspectrogram(recent_audio)
            runtime_stats["melspectrogram_ms"] += (time.perf_counter() - melspec_start) * 1000.0
            runtime_stats["melspectrogram_calls"] += 1

            preprocessor.melspectrogram_buffer = np.vstack(
                (preprocessor.melspectrogram_buffer, new_melspec)
            )
            if preprocessor.melspectrogram_buffer.shape[0] > preprocessor.melspectrogram_max_len:
                preprocessor.melspectrogram_buffer = preprocessor.melspectrogram_buffer[
                    -preprocessor.melspectrogram_max_len :,
                    :,
                ]

            emitted_frames = preprocessor.accumulated_samples // STREAM_CHUNK_SAMPLES
            for index in range(emitted_frames - 1, -1, -1):
                feature_end = -8 * index
                if feature_end == 0:
                    feature_end = len(preprocessor.melspectrogram_buffer)

                feature_input = preprocessor.melspectrogram_buffer[-76 + feature_end : feature_end]
                feature_input = feature_input.astype(np.float32)[None, :, :, None]
                if feature_input.shape[1] != 76:
                    continue

                embedding_start = time.perf_counter()
                embedding = preprocessor.embedding_model_predict(feature_input)
                runtime_stats["embedding_ms"] += (time.perf_counter() - embedding_start) * 1000.0
                runtime_stats["embedding_calls"] += 1
                preprocessor.feature_buffer = np.vstack((preprocessor.feature_buffer, embedding))

            processed_samples = preprocessor.accumulated_samples
            preprocessor.accumulated_samples = 0

        if preprocessor.feature_buffer.shape[0] > preprocessor.feature_buffer_max_len:
            preprocessor.feature_buffer = preprocessor.feature_buffer[-preprocessor.feature_buffer_max_len :, :]

        return processed_samples if processed_samples != 0 else preprocessor.accumulated_samples

    def process_audio(
        self,
        audio_chunk,
        threshold=None,
    ):
        """
        기능:
        - 실시간 오디오 chunk를 받아 score와 detection 결과를 만든다.
        
        입력:
        - `audio_chunk`: 실시간으로 들어온 오디오 chunk.
        - `threshold`: 검출 기준값. `None`이면 기본 threshold를 사용한다.
        
        반환:
        - 계산된 결과 목록 또는 배열을 반환한다.
        """
        total_start = time.perf_counter()
        pcm16 = _coerce_audio_to_pcm16(audio_chunk)
        runtime_stats = self._make_runtime_stats(len(pcm16))
        audio_level = float(np.sqrt(np.mean(np.square(pcm16.astype(np.float32) / 32768.0)))) if pcm16.size else 0.0

        processed_samples = self._stream_feature_audio(pcm16, runtime_stats)
        n_new_feature_frames = processed_samples // STREAM_CHUNK_SAMPLES
        runtime_stats["feature_frames_emitted"] = int(n_new_feature_frames)
        if n_new_feature_frames <= 0:
            runtime_stats["total_ms"] = (time.perf_counter() - total_start) * 1000.0
            self.last_runtime_stats = runtime_stats
            return []

        previous_frames = self._streamed_feature_frames
        self._streamed_feature_frames += n_new_feature_frames
        effective_threshold = float(self.threshold if threshold is None else threshold)

        predictions = []
        for offset in range(n_new_feature_frames - 1, -1, -1):
            available_frames = self._streamed_feature_frames - offset
            if available_frames < WINDOW_FRAMES:
                continue

            window = self.preprocessor.get_features(
                n_feature_frames=WINDOW_FRAMES,
                start_ndx=-WINDOW_FRAMES - offset,
            )[0]
            classifier_start = time.perf_counter()
            score = self.classifier.predict_score(window)
            runtime_stats["classifier_ms"] += (time.perf_counter() - classifier_start) * 1000.0
            runtime_stats["classifier_calls"] += 1
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
            classifier_start = time.perf_counter()
            score = self.classifier.predict_score(window)
            runtime_stats["classifier_ms"] += (time.perf_counter() - classifier_start) * 1000.0
            runtime_stats["classifier_calls"] += 1
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

        runtime_stats["total_ms"] = (time.perf_counter() - total_start) * 1000.0
        self.last_runtime_stats = runtime_stats
        return predictions
