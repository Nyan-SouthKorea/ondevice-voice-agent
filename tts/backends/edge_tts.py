"""
Edge TTS backend.
"""

import asyncio
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from .base import BaseTTSModel


class EdgeTTSModel(BaseTTSModel):
    def __init__(
        self,
        voice="ko-KR-SunHiNeural",
        rate=None,
        pitch=None,
        speed=1.0,
    ):
        """
        기능:
        - Edge TTS backend를 초기화한다.

        입력:
        - `voice`: Edge TTS 음성 이름.
        - `rate`: Edge TTS 속도 문자열. 예: `+8%`
        - `pitch`: Edge TTS 음높이 문자열. 예: `+5Hz`
        - `speed`: 공통 인터페이스 속도 배율. `rate`가 없을 때만 사용한다.

        반환:
        - 없음.
        """
        try:
            import edge_tts
        except Exception as exc:
            raise ImportError(
                "Edge TTS를 사용하려면 전용 env에 `edge-tts`를 설치해야 합니다."
            ) from exc

        super().__init__()
        self._edge_tts = edge_tts
        self.voice = voice or "ko-KR-SunHiNeural"
        self.rate = self._normalize_rate(rate, speed)
        self.pitch = str(pitch or "+0Hz")
        self.ffmpeg_path = shutil.which("ffmpeg")

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 Edge TTS로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        suffix = output_path.suffix.lower()
        if suffix not in {"", ".wav", ".mp3"}:
            raise ValueError("Edge TTS backend는 현재 `.wav`와 `.mp3` 출력만 지원합니다.")

        self.last_text = str(text).strip()
        started_at = time.perf_counter()

        try:
            with tempfile.TemporaryDirectory(prefix="edge_tts_") as tmp_dir:
                temp_mp3 = Path(tmp_dir) / "speech.mp3"
                self._run_async(self._save_mp3(self.last_text, temp_mp3))

                if suffix == ".mp3":
                    shutil.copy2(temp_mp3, output_path)
                else:
                    final_path = output_path if suffix == ".wav" else output_path.with_suffix(".wav")
                    self._convert_mp3_to_wav(temp_mp3, final_path)
                    output_path = final_path
        except Exception as exc:
            self.last_duration_sec = time.perf_counter() - started_at
            self.last_output_path = None
            self.last_error = str(exc)
            raise

        self.last_duration_sec = time.perf_counter() - started_at
        self.last_output_path = output_path
        self.last_error = ""
        return output_path

    async def _save_mp3(self, text, output_path):
        communicate = self._edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )
        await communicate.save(str(output_path))

    def _convert_mp3_to_wav(self, input_path, output_path):
        if not self.ffmpeg_path:
            raise RuntimeError(
                "Edge TTS `.wav` 출력에는 ffmpeg가 필요합니다. `.mp3`를 사용하거나 ffmpeg를 설치하세요."
            )

        subprocess.run(
            [
                self.ffmpeg_path,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                str(output_path),
            ],
            check=True,
        )

    def _normalize_rate(self, rate, speed):
        if rate is not None:
            return str(rate)

        speed = float(speed)
        offset_percent = round((speed - 1.0) * 100.0)
        offset_percent = max(-100, min(100, offset_percent))
        return f"{offset_percent:+d}%"

    def _run_async(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError(
            "Edge TTS backend는 현재 동기 실행 경로만 지원합니다. 이미 실행 중인 event loop 안에서는 직접 await 경로를 사용하세요."
        )
