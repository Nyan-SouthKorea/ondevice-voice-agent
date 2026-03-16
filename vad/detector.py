"""
VAD 공통 진입점.

동일한 `infer(audio_chunk) -> bool` 사용법으로
`webrtcvad`와 ONNX 기반 VAD를 갈아끼울 수 있게 한다.
"""

from .model_silero import SileroVADModel
from .model_webrtcvad import WebRTCVADModel


class VADDetector:
    def __init__(
        self,
        model="silero",
        sample_rate=16000,
        frame_ms=30,
        mode=2,
        model_path=None,
        speech_threshold=0.5,
        providers=None,
        min_speech_frames=3,
        min_silence_frames=10,
    ):
        """
        기능:
        - 선택한 백엔드에 맞는 VAD 모델을 초기화하고 공통 인터페이스를 제공한다.

        입력:
        - `model`: 사용할 VAD 백엔드 이름.
        - `sample_rate`: 입력 오디오 샘플레이트.
        - `frame_ms`: `webrtcvad`가 사용할 프레임 길이(ms).
        - `mode`: `webrtcvad` 공격성 모드.
        - `model_path`: ONNX VAD 모델 경로.
        - `speech_threshold`: ONNX VAD의 speech 판정 기준값.
        - `providers`: ONNX Runtime provider 목록.
        - `min_speech_frames`: `True`로 바꾸기 전에 필요한 연속 speech frame 수.
        - `min_silence_frames`: `False`로 바꾸기 전에 필요한 연속 silence frame 수.

        반환:
        - 없음.
        """
        self.model = model
        if model == "webrtcvad":
            self.backend = WebRTCVADModel(
                sample_rate=sample_rate,
                frame_ms=frame_ms,
                mode=mode,
            )
        elif model == "silero":
            self.backend = SileroVADModel(
                sample_rate=sample_rate,
                model_path=model_path,
                speech_threshold=speech_threshold,
                providers=providers,
            )
        else:
            raise ValueError(f"지원하지 않는 VAD 모델입니다: {model}")

        if int(min_speech_frames) < 1:
            raise ValueError(f"min_speech_frames는 1 이상이어야 합니다. min_speech_frames={min_speech_frames}")
        if int(min_silence_frames) < 1:
            raise ValueError(f"min_silence_frames는 1 이상이어야 합니다. min_silence_frames={min_silence_frames}")

        self.sample_rate = self.backend.sample_rate
        self.chunk_samples = self.backend.chunk_samples
        self.min_speech_frames = int(min_speech_frames)
        self.min_silence_frames = int(min_silence_frames)
        self.status = False
        self.raw_status = False
        self.last_score = 0.0
        self._speech_run = 0
        self._silence_run = 0

    def infer(self, audio_chunk):
        """
        기능:
        - 입력 오디오 청크에 대해 현재 음성 여부를 반환한다.

        입력:
        - `audio_chunk`: mono 오디오 청크.

        반환:
        - 현재 청크에서 음성이 감지됐는지 불리언으로 반환한다.
        """
        self.raw_status = bool(self.backend.infer(audio_chunk))
        self.last_score = float(self.backend.last_score)

        if self.raw_status:
            self._speech_run += 1
            self._silence_run = 0
            if not self.status and self._speech_run >= self.min_speech_frames:
                self.status = True
        else:
            self._silence_run += 1
            self._speech_run = 0
            if self.status and self._silence_run >= self.min_silence_frames:
                self.status = False

        return self.status

    def reset(self):
        """
        기능:
        - 내부 백엔드 상태와 마지막 결과를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.backend.reset()
        self.status = False
        self.raw_status = False
        self.last_score = 0.0
        self._speech_run = 0
        self._silence_run = 0
