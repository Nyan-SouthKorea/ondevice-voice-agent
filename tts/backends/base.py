"""
TTS backend 공통 기반 클래스.
"""

from abc import ABC, abstractmethod
from pathlib import Path
import tempfile


class BaseTTSModel(ABC):
    def __init__(self):
        """
        기능:
        - 모든 TTS backend가 공통으로 가지는 상태 변수를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_text = ""
        self.last_error = ""
        self.model_load_sec = 0.0

    @abstractmethod
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

    def synthesize_bytes(self, text):
        """
        기능:
        - 입력 텍스트를 음성으로 합성하고 파일 바이트를 반환한다.

        입력:
        - `text`: 음성으로 변환할 문자열.

        반환:
        - 생성 오디오 파일의 바이트 데이터를 반환한다.
        """
        with tempfile.TemporaryDirectory(prefix="tts_backend_") as tmp_dir:
            temp_path = Path(tmp_dir) / "speech.wav"
            self.synthesize_to_file(text, temp_path)
            return temp_path.read_bytes()

    def reset(self):
        """
        기능:
        - 마지막 합성 상태를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_text = ""
        self.last_error = ""
