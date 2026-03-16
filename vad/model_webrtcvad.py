"""
webrtcvad 기반 VAD 백엔드.
"""

import numpy as np
import webrtcvad


def _coerce_audio_to_pcm16(audio):
    """
    기능:
    - 입력 오디오를 mono PCM16 배열로 변환한다.

    입력:
    - `audio`: 처리할 오디오 배열.

    반환:
    - mono PCM16 numpy 배열을 반환한다.
    """
    arr = np.asarray(audio)
    if arr.ndim > 2:
        raise ValueError(f"mono 오디오만 지원합니다. 현재 shape={arr.shape}")
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


class WebRTCVADModel:
    def __init__(self, sample_rate=16000, frame_ms=30, mode=2):
        """
        기능:
        - webrtcvad 모델과 스트리밍 버퍼 상태를 초기화한다.

        입력:
        - `sample_rate`: 입력 오디오 샘플레이트.
        - `frame_ms`: 프레임 길이(ms).
        - `mode`: webrtcvad 공격성 모드.

        반환:
        - 없음.
        """
        if sample_rate != 16000:
            raise ValueError(f"현재 프로젝트는 16000 Hz만 지원합니다. sample_rate={sample_rate}")
        if frame_ms not in (10, 20, 30):
            raise ValueError(f"webrtcvad frame_ms는 10, 20, 30만 지원합니다. frame_ms={frame_ms}")
        if mode not in (0, 1, 2, 3):
            raise ValueError(f"webrtcvad mode는 0~3만 지원합니다. mode={mode}")

        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.chunk_samples = sample_rate * frame_ms // 1000
        self.vad = webrtcvad.Vad(mode)
        self._remainder = np.zeros(0, dtype=np.int16)
        self.status = False
        self.last_score = 0.0

    def infer(self, audio_chunk):
        """
        기능:
        - 입력 오디오 청크를 프레임 단위로 잘라 현재 음성 여부를 판단한다.

        입력:
        - `audio_chunk`: mono 오디오 청크.

        반환:
        - 현재 청크에서 음성이 감지됐는지 불리언으로 반환한다.
        """
        pcm16 = _coerce_audio_to_pcm16(audio_chunk)
        if self._remainder.size:
            pcm16 = np.concatenate([self._remainder, pcm16])

        if pcm16.size < self.chunk_samples:
            self._remainder = pcm16
            return self.status

        usable_size = (pcm16.size // self.chunk_samples) * self.chunk_samples
        usable = pcm16[:usable_size]
        self._remainder = pcm16[usable_size:]

        frame_statuses = []
        for start in range(0, usable.size, self.chunk_samples):
            frame = usable[start:start + self.chunk_samples]
            frame_status = self.vad.is_speech(frame.tobytes(), self.sample_rate)
            frame_statuses.append(bool(frame_status))

        if frame_statuses:
            self.last_score = float(sum(frame_statuses)) / float(len(frame_statuses))
            self.status = any(frame_statuses)
        return self.status

    def reset(self):
        """
        기능:
        - 스트리밍 버퍼와 마지막 결과를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self._remainder = np.zeros(0, dtype=np.int16)
        self.status = False
        self.last_score = 0.0
