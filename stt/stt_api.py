"""
API 기반 STT 백엔드.
"""

from datetime import datetime
import io
from pathlib import Path
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
        usage_purpose=None,
    ):
        """
        기능:
        - OpenAI Audio Transcriptions API를 사용하는 STT 백엔드를 초기화한다.

        입력:
        - `model_name`: 사용할 OpenAI STT 모델 이름.
        - `language`: 기본 언어 코드.
        - `api_key`: OpenAI API 키.
        - `prompt`: 전사 힌트 프롬프트.
        - `usage_purpose`: API 사용 목적 기록용 문자열.

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
        self.usage_purpose = usage_purpose or "stt_api_unspecified"
        self.secrets_dir = Path(__file__).resolve().parents[1] / "secrets"
        self.usage_log_path = self.secrets_dir / "api_usage_log.md"
        resolved_api_key = api_key or self._read_local_api_key()
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0
        self.last_usage = None
        self.last_usage_unit = ""
        self.last_usage_amount = 0.0
        self.last_error = ""

        if not resolved_api_key:
            raise RuntimeError("OpenAI API 키를 찾을 수 없습니다. secrets/api_key.txt를 확인하세요.")

        self.client = OpenAI(api_key=resolved_api_key)

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
        audio_sec = float(len(audio)) / 16000.0

        try:
            result = self.client.audio.transcriptions.create(
                model=self.model_name,
                file=audio_buffer,
                language=self.language,
                prompt=self.prompt,
            )
        except Exception as exc:
            self.last_duration_sec = time.perf_counter() - started_at
            self.last_result = None
            self.last_text = ""
            self.last_usage = None
            self.last_usage_unit = ""
            self.last_usage_amount = 0.0
            self.last_error = str(exc)
            self._append_usage_log(
                audio_sec=audio_sec,
                request_sec=self.last_duration_sec,
                success=False,
                error_text=self.last_error,
            )
            raise

        self.last_duration_sec = time.perf_counter() - started_at
        self.last_result = result
        self.last_text = self._extract_text(result)
        self.last_usage = self._extract_usage(result)
        self.last_usage_unit = self.last_usage["unit"]
        self.last_usage_amount = self.last_usage["amount"]
        self.last_error = ""
        self._append_usage_log(
            audio_sec=audio_sec,
            request_sec=self.last_duration_sec,
            success=True,
            error_text="",
        )
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
        self.last_usage = None
        self.last_usage_unit = ""
        self.last_usage_amount = 0.0
        self.last_error = ""

    def close(self):
        """
        기능:
        - API 백엔드가 잡고 있는 클라이언트 참조를 정리한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.client = None

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

    def _read_local_api_key(self):
        """
        기능:
        - 로컬 secrets 디렉토리의 api_key.txt에서 OpenAI API 키를 읽는다.

        입력:
        - 없음.

        반환:
        - API 키 문자열을 반환한다.
        """
        key_path = self.secrets_dir / "api_key.txt"
        if not key_path.exists():
            return None
        api_key = key_path.read_text(encoding="utf-8").strip()
        return api_key or None

    def _extract_text(self, result):
        """
        기능:
        - OpenAI 전사 응답에서 텍스트를 안정적으로 추출한다.

        입력:
        - `result`: OpenAI 전사 응답 객체.

        반환:
        - 전사 텍스트 문자열을 반환한다.
        """
        if hasattr(result, "text"):
            return str(result.text).strip()
        return str(result).strip()

    def _extract_usage(self, result):
        """
        기능:
        - OpenAI 전사 응답에서 과금 기준 usage 정보를 추출한다.

        입력:
        - `result`: OpenAI 전사 응답 객체.

        반환:
        - 단위와 값을 담은 usage 사전을 반환한다.
        """
        usage = getattr(result, "usage", None)
        if usage is None:
            return {"unit": "", "amount": 0.0}

        usage_type = getattr(usage, "type", "") or ""
        if usage_type == "duration":
            usage_seconds = float(getattr(usage, "seconds", 0.0) or 0.0)
            return {"unit": usage_type, "amount": usage_seconds}
        if usage_type == "tokens":
            total_tokens = float(getattr(usage, "total_tokens", 0.0) or 0.0)
            return {"unit": usage_type, "amount": total_tokens}
        return {"unit": usage_type, "amount": 0.0}

    def _append_usage_log(self, audio_sec, request_sec, success, error_text):
        """
        기능:
        - API 사용 이력을 로컬 secrets 문서에 한 줄씩 추가한다.

        입력:
        - `audio_sec`: 업로드한 오디오 길이.
        - `request_sec`: 실제 요청 처리 시간.
        - `success`: 성공 여부.
        - `error_text`: 실패 시 오류 문자열.

        반환:
        - 없음.
        """
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        if not self.usage_log_path.exists():
            self.usage_log_path.write_text(
                "# API Usage Log\n\n"
                "이 문서는 로컬 전용 API 사용 기록이다.\n\n",
                encoding="utf-8",
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status_text = "success" if success else "failed"
        usage_text = "-"
        if self.last_usage_unit:
            usage_text = f"{self.last_usage_unit}={self.last_usage_amount:.3f}"

        lines = [
            f"## {timestamp}",
            f"- purpose: {self.usage_purpose}",
            f"- model: {self.model_name}",
            f"- language: {self.language}",
            f"- status: {status_text}",
            f"- audio_sec: {audio_sec:.3f}",
            f"- request_sec: {request_sec:.3f}",
            f"- usage: {usage_text}",
        ]

        if success and self.last_text:
            preview = self.last_text.replace("\n", " ").strip()
            preview = preview[:120]
            lines.append(f"- text_preview: {preview}")
        if error_text:
            lines.append(f"- error: {error_text}")

        lines.append("")
        with self.usage_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write("\n".join(lines) + "\n")
