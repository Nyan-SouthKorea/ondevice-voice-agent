"""
STT 공통 진입점.

동일한 `transcribe(audio) -> text` 사용법으로
온디바이스 Whisper와 API 기반 STT를 갈아끼울 수 있게 한다.
"""

from pathlib import Path
import wave

import numpy as np

from .stt_api import OpenAIAPISTTModel
from .stt_whisper_trt import WhisperTRTSTTModel
from .stt_whisper import WhisperSTTModel


class STTTranscriber:
    def __init__(
        self,
        model="whisper",
        model_name=None,
        language="ko",
        device=None,
        download_root=None,
        api_key=None,
        prompt=None,
        usage_purpose=None,
        checkpoint_path=None,
        workspace_mb=128,
        max_text_ctx=64,
    ):
        """
        기능:
        - 선택한 백엔드에 맞는 STT 모델을 초기화하고 공통 인터페이스를 제공한다.

        입력:
        - `model`: 사용할 STT 백엔드 이름.
        - `model_name`: 백엔드별 실제 모델 이름.
        - `language`: 기본 언어 코드.
        - `device`: 온디바이스 STT 실행 장치.
        - `download_root`: Whisper 모델 다운로드 경로.
        - `api_key`: API STT용 키.
        - `prompt`: STT 힌트 프롬프트.
        - `usage_purpose`: API 사용 목적 기록용 문자열.
        - `checkpoint_path`: WhisperTRT checkpoint 경로.
        - `workspace_mb`: WhisperTRT 기록용 workspace 크기.
        - `max_text_ctx`: WhisperTRT 기록용 최대 text context 길이.

        반환:
        - 없음.
        """
        self.model = model
        if model == "whisper":
            self.backend = WhisperSTTModel(
                model_name=model_name or "tiny",
                language=language,
                device=device,
                download_root=download_root,
                prompt=prompt,
            )
        elif model == "whisper_trt":
            resolved_checkpoint = checkpoint_path or (
                Path(__file__).resolve().parent
                / "models"
                / "whisper_trt_base_ko_ctx64"
                / "whisper_trt_split.pth"
            )
            self.backend = WhisperTRTSTTModel(
                checkpoint_path=resolved_checkpoint,
                model_name=model_name or "base",
                language=language,
                workspace_mb=workspace_mb,
                max_text_ctx=max_text_ctx,
            )
        elif model == "api":
            self.backend = OpenAIAPISTTModel(
                model_name=model_name or "gpt-4o-mini-transcribe",
                language=language,
                api_key=api_key,
                prompt=prompt,
                usage_purpose=usage_purpose,
            )
        else:
            raise ValueError(f"지원하지 않는 STT 모델입니다: {model}")

        self.language = language
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0
        self.last_usage = None

    def close(self):
        """
        기능:
        - 현재 STT 백엔드가 잡고 있는 자원을 정리한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        close_fn = getattr(self.backend, "close", None)
        if callable(close_fn):
            close_fn()

    def load_audio(self, audio):
        """
        기능:
        - STT 입력을 float32 mono 16kHz numpy 배열로 정규화한다.

        입력:
        - `audio`: numpy 배열 또는 16kHz mono wav 파일 경로.

        반환:
        - float32 mono 16kHz numpy 배열을 반환한다.
        """
        if isinstance(audio, (str, Path)):
            return self._load_wav_file(audio)

        audio_array = np.asarray(audio, dtype=np.float32)
        if audio_array.ndim == 2:
            audio_array = audio_array[:, 0]
        if audio_array.ndim != 1:
            raise ValueError("audio는 mono 1차원 배열이어야 합니다.")

        peak = float(np.max(np.abs(audio_array))) if audio_array.size else 0.0
        if peak > 1.5:
            audio_array = audio_array / 32768.0

        return np.clip(audio_array, -1.0, 1.0)

    def transcribe(self, audio):
        """
        기능:
        - 입력 오디오를 텍스트로 변환한다.

        입력:
        - `audio`: numpy 배열 또는 16kHz mono wav 파일 경로.

        반환:
        - 변환된 텍스트를 문자열로 반환한다.
        """
        normalized_audio = self.load_audio(audio)
        text = self.backend.transcribe(normalized_audio)
        self.last_text = str(text).strip()
        self.last_result = self.backend.last_result
        self.last_duration_sec = float(self.backend.last_duration_sec)
        self.last_usage = getattr(self.backend, "last_usage", None)
        return self.last_text

    def reset(self):
        """
        기능:
        - 마지막 STT 결과를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.backend.reset()
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0
        self.last_usage = None

    def _load_wav_file(self, audio_path):
        """
        기능:
        - 16kHz mono wav 파일을 읽어 float32 배열로 반환한다.

        입력:
        - `audio_path`: wav 파일 경로.

        반환:
        - float32 mono 오디오 배열을 반환한다.
        """
        path = Path(audio_path)
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            frames = wav_file.readframes(wav_file.getnframes())

        if channels != 1:
            raise ValueError(f"wav 파일은 mono여야 합니다. channels={channels}")
        if sample_rate != 16000:
            raise ValueError(f"wav 파일은 16kHz여야 합니다. sample_rate={sample_rate}")
        if sample_width != 2:
            raise ValueError(f"wav 파일은 PCM16이어야 합니다. sample_width={sample_width}")

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return np.clip(audio, -1.0, 1.0)
