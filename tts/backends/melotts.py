"""
MeloTTS backend.
"""

from pathlib import Path
import time

from .base import BaseTTSModel


class MeloTTSModel(BaseTTSModel):
    def __init__(
        self,
        language_code="KR",
        voice=None,
        speed=1.0,
        device=None,
        use_hf=True,
        config_path=None,
        ckpt_path=None,
        sdp_ratio=0.2,
        noise_scale=0.6,
        noise_scale_w=0.8,
    ):
        """
        기능:
        - MeloTTS 한국어 backend를 초기화한다.

        입력:
        - `language_code`: MeloTTS 언어 코드.
        - `voice`: speaker key 또는 speaker id.
        - `speed`: 합성 속도 배율.
        - `device`: `cuda:0` 같은 실행 장치 문자열.
        - `use_hf`: Hugging Face 체크포인트 사용 여부.
        - `config_path`: 로컬 config 경로.
        - `ckpt_path`: 로컬 checkpoint 경로.
        - `sdp_ratio`: MeloTTS 추론 파라미터.
        - `noise_scale`: MeloTTS 추론 파라미터.
        - `noise_scale_w`: MeloTTS 추론 파라미터.

        반환:
        - 없음.
        """
        try:
            from melo.api import TTS
        except Exception as exc:
            raise ImportError(
                "MeloTTS를 사용하려면 전용 env에 `melotts`를 설치해야 합니다."
            ) from exc

        super().__init__()
        self.language_code = language_code or "KR"
        self.voice = voice
        self.speed = float(speed)
        self.device = device or "cuda:0"
        self.use_hf = bool(use_hf)
        self.config_path = config_path
        self.ckpt_path = ckpt_path
        self.sdp_ratio = float(sdp_ratio)
        self.noise_scale = float(noise_scale)
        self.noise_scale_w = float(noise_scale_w)
        self.model_load_sec = 0.0

        started_at = time.perf_counter()
        self.model = TTS(
            language=self.language_code,
            device=self.device,
            use_hf=self.use_hf,
            config_path=self.config_path,
            ckpt_path=self.ckpt_path,
        )
        self.model_load_sec = time.perf_counter() - started_at
        self.speaker_ids = dict(getattr(self.model.hps.data, "spk2id", {}))
        self.default_speaker_key = next(iter(self.speaker_ids), self.language_code)

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 MeloTTS로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() not in {"", ".wav"}:
            raise ValueError("MeloTTS backend는 현재 `.wav` 출력만 지원합니다.")

        started_at = time.perf_counter()
        self.last_text = str(text).strip()
        speaker_id = self._resolve_speaker_id(self.voice)

        try:
            self.model.tts_to_file(
                text=self.last_text,
                speaker_id=speaker_id,
                output_path=str(output_path),
                speed=self.speed,
                sdp_ratio=self.sdp_ratio,
                noise_scale=self.noise_scale,
                noise_scale_w=self.noise_scale_w,
                quiet=True,
            )
        except Exception as exc:
            self.last_duration_sec = time.perf_counter() - started_at
            self.last_output_path = None
            self.last_error = str(exc)
            raise

        self.last_duration_sec = time.perf_counter() - started_at
        self.last_output_path = output_path
        self.last_error = ""
        return output_path

    def _resolve_speaker_id(self, voice):
        """
        기능:
        - 전달된 voice 값을 MeloTTS speaker id 정수로 변환한다.

        입력:
        - `voice`: speaker key 또는 speaker id.

        반환:
        - speaker id 정수를 반환한다.
        """
        if voice is None:
            return int(self.speaker_ids[self.default_speaker_key])
        if isinstance(voice, int):
            return int(voice)
        voice_text = str(voice).strip()
        if voice_text in self.speaker_ids:
            return int(self.speaker_ids[voice_text])
        if voice_text.isdigit():
            return int(voice_text)
        raise ValueError(
            f"지원하지 않는 MeloTTS voice입니다: {voice_text}. "
            f"사용 가능 key: {sorted(self.speaker_ids.keys())}"
        )
