"""
Kokoro backend.
"""

from pathlib import Path
import time

from .base import BaseTTSModel


class KokoroTTSModel(BaseTTSModel):
    DEFAULT_VOICES = {
        "a": "af_heart",
        "b": "bf_emma",
        "e": "ef_dora",
        "f": "ff_siwis",
        "h": "hf_alpha",
        "i": "if_sara",
        "j": "jf_alpha",
        "p": "pf_dora",
        "z": "zf_xiaobei",
    }

    LANGUAGE_ALIASES = {
        "a": "a",
        "en-us": "a",
        "american-english": "a",
        "b": "b",
        "en-gb": "b",
        "british-english": "b",
        "e": "e",
        "es": "e",
        "espanol": "e",
        "f": "f",
        "fr-fr": "f",
        "french": "f",
        "h": "h",
        "hi": "h",
        "hindi": "h",
        "i": "i",
        "it": "i",
        "italian": "i",
        "j": "j",
        "ja": "j",
        "japanese": "j",
        "p": "p",
        "pt-br": "p",
        "brazilian-portuguese": "p",
        "portuguese": "p",
        "z": "z",
        "zh": "z",
        "mandarin": "z",
        "mandarin-chinese": "z",
    }

    def __init__(
        self,
        language_code="a",
        voice=None,
        speed=1.0,
        device=None,
        repo_id="hexgrad/Kokoro-82M",
    ):
        """
        기능:
        - Kokoro backend를 초기화한다.

        입력:
        - `language_code`: Kokoro language code 또는 alias.
        - `voice`: Kokoro voice 이름.
        - `speed`: 합성 속도 배율.
        - `device`: `cuda`, `cuda:0`, `cpu` 같은 실행 장치 문자열.
        - `repo_id`: Hugging Face model repo id.

        반환:
        - 없음.
        """
        try:
            import soundfile as sf
            from kokoro import KPipeline
        except Exception as exc:
            raise ImportError(
                "Kokoro를 사용하려면 전용 env에 `kokoro`, `soundfile`가 설치되어 있어야 합니다."
            ) from exc

        super().__init__()
        self._sf = sf
        self._KPipeline = KPipeline
        self.language_code = self._normalize_language_code(language_code or "a")
        self.voice = voice or self.DEFAULT_VOICES[self.language_code]
        self.speed = float(speed)
        self.device = device or "cuda"
        self.repo_id = repo_id or "hexgrad/Kokoro-82M"

        started_at = time.perf_counter()
        self.pipeline = self._KPipeline(
            lang_code=self.language_code,
            repo_id=self.repo_id,
            device=self.device,
        )
        self.model_load_sec = time.perf_counter() - started_at

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 Kokoro로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() not in {"", ".wav"}:
            raise ValueError("Kokoro backend는 현재 `.wav` 출력만 지원합니다.")

        self.last_text = str(text).strip()
        started_at = time.perf_counter()

        try:
            result = next(
                self.pipeline(
                    self.last_text,
                    voice=self.voice,
                    speed=self.speed,
                )
            )
            _, _, audio = result
            self._sf.write(output_path, audio, 24000)
        except Exception as exc:
            self.last_duration_sec = time.perf_counter() - started_at
            self.last_output_path = None
            self.last_error = str(exc)
            raise

        self.last_duration_sec = time.perf_counter() - started_at
        self.last_output_path = output_path
        self.last_error = ""
        return output_path

    def _normalize_language_code(self, language_code):
        """
        기능:
        - 입력 language code를 Kokoro 공식 single-letter code로 정규화한다.

        입력:
        - `language_code`: 사용자 입력 language code.

        반환:
        - Kokoro single-letter language code를 반환한다.
        """
        normalized = str(language_code).strip().lower()
        if normalized in {"ko", "ko-kr", "korean"}:
            raise ValueError(
                "Kokoro 공식 경로는 현재 한국어를 지원하지 않습니다. "
                "공식 지원 언어는 en-us, en-gb, es, fr-fr, hi, it, pt-br, ja, zh 입니다."
            )

        if normalized not in self.LANGUAGE_ALIASES:
            raise ValueError(
                f"지원하지 않는 Kokoro language code입니다: {language_code}"
            )
        return self.LANGUAGE_ALIASES[normalized]
