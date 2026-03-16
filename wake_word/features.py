"""
Google Speech Embedding feature backbone을 로컬에서 직접 다루는 모듈.

이 파일은 wake word 추론과 feature extraction 학습 스크립트가 공통으로 사용하는
mel spectrogram ONNX와 embedding ONNX 호출 로직만 포함한다.
"""

from collections import deque
from multiprocessing.pool import ThreadPool
from pathlib import Path

import numpy as np
import onnxruntime as ort


TARGET_SR = 16000
FEATURE_DIM = 96
FEATURE_MODEL_DIR = Path(__file__).resolve().parent / "assets" / "feature_models"
MELSPECTROGRAM_MODEL_PATH = FEATURE_MODEL_DIR / "melspectrogram.onnx"
EMBEDDING_MODEL_PATH = FEATURE_MODEL_DIR / "embedding_model.onnx"
FEATURE_MODEL_URLS = {
    "melspectrogram.onnx": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/melspectrogram.onnx",
    "embedding_model.onnx": "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/embedding_model.onnx",
}


def _resolve_providers(device):
    """
    기능:
    - 요청한 장치 이름과 현재 시스템 provider 상태를 바탕으로 사용할 provider 목록을 만든다.

    입력:
    - `device`: 사용자가 요청한 장치 이름.

    반환:
    - onnxruntime 세션에 전달할 provider 목록을 반환한다.
    """
    available = set(ort.get_available_providers())
    if str(device).lower() == "gpu" and "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]


def ensure_feature_models(melspec_model_path=None, embedding_model_path=None):
    """
    기능:
    - wake word feature backbone ONNX 두 개가 현재 리포 경로에 존재하는지 확인한다.

    입력:
    - `melspec_model_path`: 사용할 mel spectrogram ONNX 경로.
    - `embedding_model_path`: 사용할 embedding ONNX 경로.

    반환:
    - mel spectrogram ONNX 경로와 embedding ONNX 경로를 순서대로 반환한다.
    """
    melspec_path = Path(melspec_model_path) if melspec_model_path else MELSPECTROGRAM_MODEL_PATH
    embedding_path = Path(embedding_model_path) if embedding_model_path else EMBEDDING_MODEL_PATH

    missing = []
    if not melspec_path.exists():
        missing.append(("melspectrogram.onnx", melspec_path))
    if not embedding_path.exists():
        missing.append(("embedding_model.onnx", embedding_path))

    if missing:
        lines = [
            "wake word feature backbone ONNX 파일이 없습니다.",
            "다음 파일을 리포 안에 두어야 합니다.",
        ]
        for filename, path in missing:
            lines.append(f"- {filename}: {path}")
            lines.append(f"  공식 URL: {FEATURE_MODEL_URLS[filename]}")
        raise FileNotFoundError("\n".join(lines))

    return str(melspec_path), str(embedding_path)


class AudioFeatures:
    def __init__(
        self,
        melspec_model_path="",
        embedding_model_path="",
        sr=16000,
        ncpu=1,
        inference_framework="onnx",
        device="cpu",
    ):
        """
        기능:
        - mel spectrogram ONNX와 embedding ONNX를 초기화하고 streaming buffer 상태를 준비한다.

        입력:
        - `melspec_model_path`: mel spectrogram ONNX 파일 경로.
        - `embedding_model_path`: embedding ONNX 파일 경로.
        - `sr`: 오디오 샘플레이트.
        - `ncpu`: ONNX 세션 스레드 수.
        - `inference_framework`: 현재는 `onnx`만 허용한다.
        - `device`: `cpu` 또는 `gpu`.

        반환:
        - 없음.
        """
        if inference_framework != "onnx":
            raise ValueError("현재 wake word feature backbone은 onnx만 지원합니다.")

        melspec_model_path, embedding_model_path = ensure_feature_models(
            melspec_model_path or None,
            embedding_model_path or None,
        )

        session_options = ort.SessionOptions()
        session_options.inter_op_num_threads = int(ncpu)
        session_options.intra_op_num_threads = int(ncpu)

        self.sr = int(sr)
        self.ncpu = int(ncpu)
        self.providers = _resolve_providers(device)
        self.melspec_model = ort.InferenceSession(
            str(melspec_model_path),
            sess_options=session_options,
            providers=self.providers,
        )
        self.embedding_model = ort.InferenceSession(
            str(embedding_model_path),
            sess_options=session_options,
            providers=self.providers,
        )
        self.melspec_input_name = self.melspec_model.get_inputs()[0].name
        self.embedding_input_name = self.embedding_model.get_inputs()[0].name
        self.onnx_execution_provider = self.embedding_model.get_providers()[0]
        self.melspec_model_predict = lambda batch: self.melspec_model.run(None, {self.melspec_input_name: batch})
        self.embedding_model_predict = lambda batch: self._predict_embedding_batch(batch)
        self.raw_data_buffer = deque(maxlen=self.sr * 10)
        self.melspectrogram_buffer = np.ones((76, 32), dtype=np.float32)
        self.melspectrogram_max_len = 10 * 97
        self.accumulated_samples = 0
        self.raw_data_remainder = np.empty(0, dtype=np.int16)
        self.feature_buffer_max_len = 120
        self.feature_buffer = self._seed_feature_buffer()

    def _seed_feature_buffer(self):
        """
        기능:
        - streaming 초기 상태에서 사용할 기본 feature buffer를 만든다.

        입력:
        - 없음.

        반환:
        - 초기 feature buffer 배열을 반환한다.
        """
        seed_audio = np.zeros(self.sr * 4, dtype=np.int16)
        seed_features = self._get_embeddings(seed_audio)
        if seed_features.size == 0:
            return np.zeros((1, FEATURE_DIM), dtype=np.float32)
        return seed_features.astype(np.float32)

    def reset(self):
        """
        기능:
        - streaming 추론에 쓰는 내부 버퍼 상태를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.raw_data_buffer.clear()
        self.melspectrogram_buffer = np.ones((76, 32), dtype=np.float32)
        self.accumulated_samples = 0
        self.raw_data_remainder = np.empty(0, dtype=np.int16)
        self.feature_buffer = self._seed_feature_buffer()

    def _get_melspectrogram(self, x, melspec_transform=None):
        """
        기능:
        - PCM16 오디오에서 mel spectrogram ONNX를 실행해 feature map을 만든다.

        입력:
        - `x`: PCM16 오디오 배열 또는 배치 배열.
        - `melspec_transform`: 원본 ONNX 출력에 적용할 변환 함수.

        반환:
        - 계산된 mel spectrogram 배열을 반환한다.
        """
        arr = np.asarray(x)
        if np.issubdtype(arr.dtype, np.floating):
            arr = np.clip(arr, -1.0, 1.0)
            arr = (arr * 32767.0).astype(np.int16)
        elif arr.dtype != np.int16:
            arr = np.clip(arr, -32768, 32767).astype(np.int16)
        if arr.ndim == 1:
            arr = arr[None, :]
        if arr.ndim != 2:
            raise ValueError(f"Expected audio shape (samples) or (batch, samples), got {arr.shape}")

        outputs = self.melspec_model.run(None, {self.melspec_input_name: arr.astype(np.float32)})[0]
        spec = np.squeeze(outputs)
        transform = melspec_transform or (lambda value: value / 10.0 + 2.0)
        return transform(spec)

    def _predict_embedding_batch(self, batch):
        """
        기능:
        - embedding ONNX를 배치로 실행하고 `(N, 96)` 형태의 결과로 정리한다.

        입력:
        - `batch`: embedding ONNX 입력 배치 배열.

        반환:
        - 각 window에 대한 embedding 배열을 반환한다.
        """
        outputs = self.embedding_model.run(None, {self.embedding_input_name: batch})[0]
        outputs = np.asarray(outputs, dtype=np.float32)
        return outputs.reshape(outputs.shape[0], FEATURE_DIM)

    def _get_embeddings_from_melspec(self, melspec):
        """
        기능:
        - mel spectrogram window 하나에서 embedding 1개를 계산한다.

        입력:
        - `melspec`: embedding ONNX에 넣을 mel spectrogram window.

        반환:
        - 계산된 embedding 한 개를 반환한다.
        """
        batch = np.asarray(melspec, dtype=np.float32)
        if batch.ndim == 3:
            batch = batch[None, :]
        return self._predict_embedding_batch(batch)[0]

    def _get_embeddings(self, x, window_size=76, step_size=8, melspec_transform=None):
        """
        기능:
        - 단일 오디오 clip에서 sliding window embedding 시퀀스를 계산한다.

        입력:
        - `x`: PCM16 오디오 clip.
        - `window_size`: embedding window 길이.
        - `step_size`: window 이동 간격.
        - `melspec_transform`: mel spectrogram 후처리 함수.

        반환:
        - `(frames, 96)` 형태의 embedding 배열을 반환한다.
        """
        spec = self._get_melspectrogram(x, melspec_transform=melspec_transform)
        windows = []
        for start in range(0, spec.shape[0], step_size):
            window = spec[start : start + window_size]
            if window.shape[0] == window_size:
                windows.append(window)

        if not windows:
            return np.empty((0, FEATURE_DIM), dtype=np.float32)

        batch = np.expand_dims(np.asarray(windows, dtype=np.float32), axis=-1)
        return self._predict_embedding_batch(batch)

    def get_embedding_shape(self, audio_length, sr=16000):
        """
        기능:
        - 지정한 길이의 오디오가 몇 개의 embedding frame으로 바뀌는지 계산한다.

        입력:
        - `audio_length`: 초 단위 오디오 길이.
        - `sr`: 계산에 사용할 샘플레이트.

        반환:
        - embedding 배열 shape를 반환한다.
        """
        samples = int(float(audio_length) * int(sr))
        melspec_frames = int(np.ceil(samples / 160 - 3))
        embedding_frames = max((melspec_frames - 76) // 8 + 1, 0)
        return (embedding_frames, FEATURE_DIM)

    def _get_melspectrogram_batch(self, x, batch_size=128, ncpu=1):
        """
        기능:
        - 여러 오디오 clip에 대해 mel spectrogram을 배치로 계산한다.

        입력:
        - `x`: `(N, samples)` 형태의 PCM16 오디오 배치.
        - `batch_size`: 한 번에 처리할 clip 수.
        - `ncpu`: CPU 실행 시 사용할 스레드 수.

        반환:
        - `(N, frames, 32)` 형태의 mel spectrogram 배열을 반환한다.
        """
        arr = np.asarray(x)
        if arr.ndim != 2:
            raise ValueError(f"Expected audio batch shape (N, samples), got {arr.shape}")

        n_frames = int(np.ceil(arr.shape[1] / 160 - 3))
        melspecs = np.empty((arr.shape[0], n_frames, 32), dtype=np.float32)
        pool = None
        if "CPU" in self.onnx_execution_provider:
            pool = ThreadPool(processes=max(int(ncpu), 1))

        try:
            for start in range(0, arr.shape[0], batch_size):
                batch = arr[start : start + batch_size]
                if "CUDA" in self.onnx_execution_provider:
                    result = self._get_melspectrogram(batch)
                else:
                    chunksize = batch.shape[0] // max(int(ncpu), 1) if batch.shape[0] >= max(int(ncpu), 1) else 1
                    result = np.asarray(pool.map(self._get_melspectrogram, batch, chunksize=chunksize))
                melspecs[start : start + batch.shape[0], :, :] = np.asarray(result, dtype=np.float32).reshape(
                    batch.shape[0],
                    n_frames,
                    32,
                )
        finally:
            if pool is not None:
                pool.close()

        return melspecs

    def _get_embeddings_batch(self, x, batch_size=128, ncpu=1):
        """
        기능:
        - 여러 mel spectrogram clip에서 embedding 시퀀스를 배치로 계산한다.

        입력:
        - `x`: `(N, frames, 32, 1)` 형태의 mel spectrogram 배치.
        - `batch_size`: embedding ONNX에 넣을 window batch 크기.
        - `ncpu`: CPU 실행 시 사용할 스레드 수.

        반환:
        - `(N, feature_frames, 96)` 형태의 embedding 배열을 반환한다.
        """
        arr = np.asarray(x, dtype=np.float32)
        if arr.shape[1] < 76:
            raise ValueError("Embedding model requires at least 76 mel frames.")

        n_feature_frames = (arr.shape[1] - 76) // 8 + 1
        embeddings = np.empty((arr.shape[0], n_feature_frames, FEATURE_DIM), dtype=np.float32)
        pool = None
        if "CPU" in self.onnx_execution_provider:
            pool = ThreadPool(processes=max(int(ncpu), 1))

        try:
            windows = []
            clip_indices = []
            for clip_index, melspec in enumerate(arr):
                for start in range(0, melspec.shape[0], 8):
                    window = melspec[start : start + 76]
                    if window.shape[0] == 76:
                        windows.append(window)
                clip_indices.append(clip_index)

                if len(windows) >= batch_size or clip_index + 1 == arr.shape[0]:
                    if not windows:
                        continue

                    window_batch = np.asarray(windows, dtype=np.float32)
                    if "CUDA" in self.onnx_execution_provider:
                        result = self._predict_embedding_batch(window_batch)
                    else:
                        chunksize = (
                            window_batch.shape[0] // max(int(ncpu), 1)
                            if window_batch.shape[0] >= max(int(ncpu), 1)
                            else 1
                        )
                        result = np.asarray(
                            pool.map(self._get_embeddings_from_melspec, window_batch, chunksize=chunksize)
                        )

                    for result_index, target_clip_index in zip(
                        range(0, result.shape[0], n_feature_frames),
                        clip_indices,
                    ):
                        embeddings[target_clip_index, :, :] = result[result_index : result_index + n_feature_frames]

                    windows = []
                    clip_indices = []
        finally:
            if pool is not None:
                pool.close()

        return embeddings

    def embed_clips(self, x, batch_size=128, ncpu=1):
        """
        기능:
        - 여러 PCM16 clip을 한 번에 embedding 시퀀스로 변환한다.

        입력:
        - `x`: `(N, samples)` 형태의 PCM16 오디오 배치.
        - `batch_size`: 배치 처리 크기.
        - `ncpu`: CPU 실행 시 사용할 스레드 수.

        반환:
        - `(N, frames, 96)` 형태의 embedding 배열을 반환한다.
        """
        melspecs = self._get_melspectrogram_batch(x, batch_size=batch_size, ncpu=ncpu)
        return self._get_embeddings_batch(melspecs[:, :, :, None], batch_size=batch_size, ncpu=ncpu)

    def _buffer_raw_data(self, x):
        """
        기능:
        - streaming 입력 오디오를 내부 raw buffer 뒤에 이어 붙인다.

        입력:
        - `x`: raw buffer에 추가할 PCM16 오디오 배열.

        반환:
        - 없음.
        """
        values = np.asarray(x, dtype=np.int16).tolist()
        self.raw_data_buffer.extend(values)

    def get_features(self, n_feature_frames=16, start_ndx=-1):
        """
        기능:
        - 현재 feature buffer에서 원하는 구간의 feature window를 꺼낸다.

        입력:
        - `n_feature_frames`: 가져올 feature frame 수.
        - `start_ndx`: feature buffer 기준 시작 인덱스.

        반환:
        - `(1, frames, 96)` 형태의 feature 배열을 반환한다.
        """
        if start_ndx != -1:
            end_ndx = start_ndx + int(n_feature_frames) if start_ndx + n_feature_frames != 0 else len(self.feature_buffer)
            return self.feature_buffer[start_ndx:end_ndx, :][None, :].astype(np.float32)
        return self.feature_buffer[int(-1 * n_feature_frames) :, :][None, :].astype(np.float32)
