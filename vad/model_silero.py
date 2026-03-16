"""
Silero ONNX 기반 VAD 백엔드.
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "silero_vad.onnx"


def _coerce_audio_to_float32(audio):
    """
    기능:
    - 입력 오디오를 mono float32 배열로 변환한다.

    입력:
    - `audio`: 처리할 오디오 배열.

    반환:
    - mono float32 numpy 배열을 반환한다.
    """
    arr = np.asarray(audio)
    if arr.ndim > 2:
        raise ValueError(f"mono 오디오만 지원합니다. 현재 shape={arr.shape}")
    if arr.ndim == 2:
        if arr.shape[1] == 1:
            arr = arr[:, 0]
        else:
            arr = arr.mean(axis=1)

    if np.issubdtype(arr.dtype, np.integer):
        arr = arr.astype(np.float32) / 32768.0
    else:
        arr = arr.astype(np.float32)
    return np.clip(arr, -1.0, 1.0)


def _default_providers():
    """
    기능:
    - 작은 ONNX VAD에 사용할 기본 provider 목록을 만든다.

    입력:
    - 없음.

    반환:
    - ONNX Runtime provider 이름 목록을 반환한다.
    """
    return ["CPUExecutionProvider"]


class SileroVADModel:
    def __init__(self, sample_rate=16000, model_path=None, speech_threshold=0.5, providers=None):
        """
        기능:
        - Silero ONNX 세션과 스트리밍 상태를 초기화한다.

        입력:
        - `sample_rate`: 입력 오디오 샘플레이트.
        - `model_path`: Silero ONNX 모델 경로.
        - `speech_threshold`: speech 판정 기준값.
        - `providers`: ONNX Runtime provider 목록.

        반환:
        - 없음.
        """
        if sample_rate != 16000:
            raise ValueError(f"현재 프로젝트는 16000 Hz만 지원합니다. sample_rate={sample_rate}")

        self.sample_rate = sample_rate
        self.chunk_samples = 512
        self.context_samples = 64
        self.speech_threshold = speech_threshold
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Silero ONNX 모델이 없습니다: {self.model_path}\n"
                "공식 Silero VAD ONNX 파일을 vad/models/ 아래에 두거나 --model-path로 경로를 넘겨주세요."
            )

        self.providers = providers or _default_providers()
        self.session = ort.InferenceSession(str(self.model_path), providers=self.providers)
        self.status = False
        self.last_score = 0.0
        self.reset()

    def reset(self):
        """
        기능:
        - Silero streaming 상태와 잔여 버퍼를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((0,), dtype=np.float32)
        self._remainder = np.zeros((0,), dtype=np.float32)
        self._last_sr = 0
        self._last_batch_size = 0
        self.status = False
        self.last_score = 0.0

    def _run_frame(self, frame):
        """
        기능:
        - Silero ONNX 모델에 단일 프레임을 넣고 speech probability를 계산한다.

        입력:
        - `frame`: 512샘플 길이의 float32 오디오 프레임.

        반환:
        - 현재 프레임의 speech probability를 반환한다.
        """
        x = np.asarray(frame, dtype=np.float32).reshape(1, -1)
        batch_size = x.shape[0]

        if x.shape[1] != self.chunk_samples:
            raise ValueError(
                f"Silero VAD는 16kHz에서 {self.chunk_samples} samples chunk만 지원합니다. "
                f"현재 길이={x.shape[1]}"
            )

        if not self._last_batch_size:
            self._state = np.zeros((2, batch_size, 128), dtype=np.float32)
        if self._last_sr and self._last_sr != self.sample_rate:
            self._state = np.zeros((2, batch_size, 128), dtype=np.float32)
        if self._last_batch_size and self._last_batch_size != batch_size:
            self._state = np.zeros((2, batch_size, 128), dtype=np.float32)

        if self._context.size == 0:
            self._context = np.zeros((batch_size, self.context_samples), dtype=np.float32)

        x = np.concatenate([self._context, x], axis=1)
        ort_inputs = {
            "input": x,
            "state": self._state,
            "sr": np.array(self.sample_rate, dtype=np.int64),
        }
        ort_outs = self.session.run(None, ort_inputs)
        out, state = ort_outs

        self._state = np.asarray(state, dtype=np.float32)
        self._context = x[:, -self.context_samples:]
        self._last_sr = self.sample_rate
        self._last_batch_size = batch_size

        return float(np.asarray(out).reshape(-1)[0])

    def infer(self, audio_chunk):
        """
        기능:
        - 입력 오디오 청크를 Silero ONNX 프레임으로 나눠 현재 음성 여부를 판단한다.

        입력:
        - `audio_chunk`: mono 오디오 청크.

        반환:
        - 현재 청크에서 음성이 감지됐는지 불리언으로 반환한다.
        """
        audio = _coerce_audio_to_float32(audio_chunk)
        if self._remainder.size:
            audio = np.concatenate([self._remainder, audio])

        if audio.size < self.chunk_samples:
            self._remainder = audio
            return self.status

        usable_size = (audio.size // self.chunk_samples) * self.chunk_samples
        usable = audio[:usable_size]
        self._remainder = audio[usable_size:]

        frame_statuses = []
        for start in range(0, usable.size, self.chunk_samples):
            frame = usable[start:start + self.chunk_samples]
            score = self._run_frame(frame)
            frame_statuses.append(score >= self.speech_threshold)
            self.last_score = score

        if frame_statuses:
            self.status = any(frame_statuses)
        return self.status
