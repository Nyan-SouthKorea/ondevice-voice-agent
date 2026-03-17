"""
온디바이스 Whisper STT 백엔드.
"""

import time
import gc


class WhisperSTTModel:
    def __init__(
        self,
        model_name="tiny",
        language="ko",
        device=None,
        download_root=None,
        prompt=None,
    ):
        """
        기능:
        - OpenAI Whisper 기반 온디바이스 STT 모델을 초기화한다.

        입력:
        - `model_name`: 사용할 Whisper 모델 이름.
        - `language`: 기본 언어 코드.
        - `device`: 실행 장치.
        - `download_root`: 모델 다운로드 경로.
        - `prompt`: 전사 힌트 프롬프트.

        반환:
        - 없음.
        """
        try:
            import torch
            import whisper
        except Exception as exc:
            raise ImportError(
                "Whisper STT를 사용하려면 `openai-whisper`와 `torch`가 필요합니다."
            ) from exc

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model_name = model_name
        self.language = language
        self.device = device
        self.prompt = prompt
        self._torch = torch
        self._whisper = whisper
        self.model = whisper.load_model(
            model_name,
            device=device,
            download_root=download_root,
        )
        self.last_text = ""
        self.last_result = None
        self.last_duration_sec = 0.0

    def transcribe(self, audio):
        """
        기능:
        - float32 mono 오디오를 Whisper로 전사한다.

        입력:
        - `audio`: float32 mono 16kHz numpy 배열.

        반환:
        - 전사된 텍스트를 문자열로 반환한다.
        """
        started_at = time.perf_counter()
        result = self.model.transcribe(
            audio,
            language=self.language,
            task="transcribe",
            prompt=self.prompt,
            fp16=self.device == "cuda",
            verbose=False,
            condition_on_previous_text=False,
            temperature=0.0,
        )
        self.last_duration_sec = time.perf_counter() - started_at
        self.last_result = result
        self.last_text = str(result.get("text", "")).strip()
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

    def close(self):
        """
        기능:
        - Whisper 모델을 정리하고 CUDA 캐시를 비운다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.model = None
        gc.collect()
        if self.device == "cuda":
            self._torch.cuda.empty_cache()
