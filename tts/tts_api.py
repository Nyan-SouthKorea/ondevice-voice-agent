"""
API 기반 TTS 백엔드.
"""

from datetime import datetime
from pathlib import Path
import tempfile
import time


def _resolve_secrets_dir():
    """기능: 로컬 secrets 디렉토리 위치를 결정한다.
    입력: 없음.
    반환: Path
    """

    repo_root = Path(__file__).resolve().parents[1]
    project_root = repo_root.parent
    outer_secrets_dir = project_root / "secrets"
    repo_secrets_dir = repo_root / "secrets"
    if outer_secrets_dir.exists():
        return outer_secrets_dir
    return repo_secrets_dir


class OpenAIAPITTSModel:
    def __init__(
        self,
        model_name="gpt-4o-mini-tts",
        voice="alloy",
        instructions=None,
        response_format="wav",
        speed=1.0,
        api_key=None,
        usage_purpose=None,
    ):
        """
        기능:
        - OpenAI Audio Speech API를 사용하는 TTS 백엔드를 초기화한다.

        입력:
        - `model_name`: 사용할 OpenAI TTS 모델 이름.
        - `voice`: 사용할 음성 이름.
        - `instructions`: 말투 제어용 추가 지시 문자열.
        - `response_format`: 출력 오디오 포맷.
        - `speed`: 합성 속도 배율.
        - `api_key`: OpenAI API 키.
        - `usage_purpose`: API 사용 목적 기록용 문자열.

        반환:
        - 없음.
        """
        try:
            from openai import OpenAI
        except Exception as exc:
            raise ImportError(
                "API TTS를 사용하려면 `openai` 패키지가 필요합니다."
            ) from exc

        self.model_name = model_name
        self.voice = voice
        self.instructions = instructions
        self.response_format = response_format
        self.speed = float(speed)
        self.usage_purpose = usage_purpose or "tts_api_unspecified"
        self.secrets_dir = _resolve_secrets_dir()
        self.usage_log_path = self.secrets_dir / "api_usage_log.md"
        resolved_api_key = api_key or self._read_local_api_key()

        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_text = ""
        self.last_error = ""

        if not resolved_api_key:
            raise RuntimeError(
                "OpenAI API 키를 찾을 수 없습니다. ../secrets/api_key.txt를 확인하세요."
            )

        self.client = OpenAI(api_key=resolved_api_key)

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 음성으로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        started_at = time.perf_counter()
        self.last_text = str(text).strip()

        try:
            with self.client.audio.speech.with_streaming_response.create(
                model=self.model_name,
                voice=self.voice,
                input=self.last_text,
                instructions=self.instructions,
                response_format=self.response_format,
                speed=self.speed,
            ) as response:
                response.stream_to_file(output_path)
        except Exception as exc:
            self.last_duration_sec = time.perf_counter() - started_at
            self.last_output_path = None
            self.last_error = str(exc)
            self._append_usage_log(success=False, error_text=self.last_error)
            raise

        self.last_duration_sec = time.perf_counter() - started_at
        self.last_output_path = output_path
        self.last_error = ""
        self._append_usage_log(success=True, error_text="")
        return output_path

    def synthesize_bytes(self, text):
        """
        기능:
        - 입력 텍스트를 음성으로 합성하고 파일 바이트를 메모리로 반환한다.

        입력:
        - `text`: 음성으로 변환할 문자열.

        반환:
        - 생성 오디오 파일의 바이트 데이터를 반환한다.
        """
        suffix = f".{self.response_format}"
        with tempfile.TemporaryDirectory(prefix="tts_api_") as tmp_dir:
            temp_path = Path(tmp_dir) / f"speech{suffix}"
            self.synthesize_to_file(text, temp_path)
            return temp_path.read_bytes()

    def reset(self):
        """
        기능:
        - 마지막 TTS 실행 상태를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_text = ""
        self.last_error = ""

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

    def _append_usage_log(self, success, error_text):
        """
        기능:
        - TTS API 사용 이력을 로컬 usage log 문서에 기록한다.

        입력:
        - `success`: 요청 성공 여부.
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
        preview = self.last_text.replace("\n", " ").strip()[:120]

        lines = [
            f"## {timestamp}",
            f"- purpose: {self.usage_purpose}",
            f"- api_kind: tts",
            f"- model: {self.model_name}",
            f"- voice: {self.voice}",
            f"- response_format: {self.response_format}",
            f"- speed: {self.speed:.2f}",
            f"- status: {status_text}",
            f"- request_sec: {self.last_duration_sec:.3f}",
            f"- text_preview: {preview or '-'}",
        ]
        if self.instructions:
            lines.append(f"- instructions: {self.instructions[:120]}")
        if error_text:
            lines.append(f"- error: {error_text}")

        lines.append("")
        with self.usage_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write("\n".join(lines) + "\n")
