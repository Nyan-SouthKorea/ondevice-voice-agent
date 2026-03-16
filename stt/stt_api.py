"""
API 기반 STT 백엔드.
"""

import io
import time
import wave

import numpy as np


class OpenAIAPISTTModel:
    def __init__(
        self,
        model_name="gpt-4o-mini-transcribe",
        language="ko",
        api_key=None,
        prompt=None,
    ):
        """
        기능:
        - OpenAI Audio Transcriptions API를 사용하는 STT 백엔드를 초기화한다.

        입력:
        - `model_name`: 사용할 OpenAI STT 모델 이름.
        - `language`: 기본 언어 코드.
        - `api_key`: OpenAI API 키.
        - `prompt`: 전사 힌트 프롬프트.

        반환:
        - 없음.
        """
        try:
            from openai import OpenAI
        except Exception as exc:
            raise ImportError(
                "API STT를 사용하려면 `openai` 패키지가 필요합니다."
            ) from exc

        self.model_name = model_name
        self.language = language
        self.prompt = prompt
        self.client = OpenAI(api_key=api_key)
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0

    def transcribe(self, audio):
        """
        기능:
        - float32 mono 오디오를 OpenAI API로 전사한다.

        입력:
        - `audio`: float32 mono 16kHz numpy 배열.

        반환:
        - 전사된 텍스트를 문자열로 반환한다.
        """
        started_at = time.perf_counter()
        audio_buffer = self._build_wav_buffer(audio)
        result = self.client.audio.transcriptions.create(
            model=self.model_name,
            file=audio_buffer,
            language=self.language,
            prompt=self.prompt,
            response_format="text",
        )
        self.last_duration_sec = time.perf_counter() - started_at
        self.last_result = result
        self.last_text = str(result).strip()
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
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0

    def _build_wav_buffer(self, audio):
        """
        기능:
        - float32 mono 오디오 배열을 API 업로드용 wav 버퍼로 변환한다.

        입력:
        - `audio`: float32 mono 16kHz numpy 배열.

        반환:
        - wav 형식이 들어간 메모리 버퍼를 반환한다.
        """
        pcm16 = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm16 * 32767.0).astype(np.int16)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(pcm16.tobytes())
        buffer.name = "audio.wav"
        buffer.seek(0)
        return buffer
