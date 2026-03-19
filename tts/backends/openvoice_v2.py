"""
OpenVoice V2 backend.
"""

import sys
import types
from pathlib import Path
import tempfile
import time

from .base import BaseTTSModel
from .melotts import MeloTTSModel


def _install_wavmark_stub_if_needed():
    """
    기능:
    - OpenVoice constructor가 `wavmark` import만 요구할 때 최소 stub를 주입한다.

    입력:
    - 없음.

    반환:
    - 없음.
    """
    try:
        import wavmark  # noqa: F401
        return
    except Exception:
        pass

    class _DummyWatermarkModel:
        def to(self, device):
            return self

        def encode(self, signal, message_tensor):
            return signal

        def decode(self, signal):
            import torch

            batch = signal.shape[0] if hasattr(signal, "shape") else 1
            return torch.zeros((batch, 32), device=getattr(signal, "device", "cpu"))

    stub = types.ModuleType("wavmark")
    stub.load_model = lambda: _DummyWatermarkModel()
    sys.modules["wavmark"] = stub


class OpenVoiceV2Model(BaseTTSModel):
    def __init__(
        self,
        language_code="KR",
        voice=None,
        reference_audio_path=None,
        speed=1.0,
        device=None,
        checkpoint_root=None,
        processed_dir=None,
        tau=0.3,
        use_hf=True,
        config_path=None,
        ckpt_path=None,
        sdp_ratio=0.2,
        noise_scale=0.6,
        noise_scale_w=0.8,
    ):
        """
        기능:
        - OpenVoice V2 한국어 backend를 초기화한다.

        입력:
        - `language_code`: MeloTTS base speaker 언어 코드.
        - `voice`: MeloTTS base speaker key.
        - `reference_audio_path`: 음색을 추출할 참조 음성 경로.
        - `speed`: base TTS 합성 속도 배율.
        - `device`: `cuda:0` 같은 실행 장치 문자열.
        - `checkpoint_root`: `checkpoints_v2` 루트 경로.
        - `processed_dir`: 참조 화자 embedding cache 경로.
        - `tau`: OpenVoice tone conversion 강도 파라미터.
        - `use_hf`: MeloTTS Hugging Face 체크포인트 사용 여부.
        - `config_path`: MeloTTS 로컬 config 경로.
        - `ckpt_path`: MeloTTS 로컬 checkpoint 경로.
        - `sdp_ratio`: MeloTTS 추론 파라미터.
        - `noise_scale`: MeloTTS 추론 파라미터.
        - `noise_scale_w`: MeloTTS 추론 파라미터.

        반환:
        - 없음.
        """
        try:
            import torch
            from openvoice import se_extractor
            from openvoice.api import ToneColorConverter
        except Exception as exc:
            raise ImportError(
                "OpenVoice V2를 사용하려면 전용 env에 `openvoice`, `melotts`, "
                "`faster-whisper`, `whisper-timestamped` 등을 설치해야 합니다."
            ) from exc

        super().__init__()
        self._torch = torch
        self._se_extractor = se_extractor
        self.language_code = language_code or "KR"
        self.voice = voice or self.language_code
        self.speed = float(speed)
        self.device = device or "cuda:0"
        self.reference_audio_path = (
            Path(reference_audio_path).expanduser().resolve()
            if reference_audio_path
            else None
        )
        self.workspace_root = Path(__file__).resolve().parents[3]
        self.checkpoint_root = (
            Path(checkpoint_root).expanduser().resolve()
            if checkpoint_root
            else self.workspace_root
            / "results"
            / "tts_assets"
            / "openvoice_v2"
            / "checkpoints_v2"
        )
        self.processed_dir = (
            Path(processed_dir).expanduser().resolve()
            if processed_dir
            else self.workspace_root
            / "results"
            / "tts_assets"
            / "openvoice_v2"
            / "processed"
        )
        self.tau = float(tau)

        converter_config_path = self.checkpoint_root / "converter" / "config.json"
        converter_ckpt_path = self.checkpoint_root / "converter" / "checkpoint.pth"
        if not converter_config_path.is_file() or not converter_ckpt_path.is_file():
            raise FileNotFoundError(
                "OpenVoice V2 converter checkpoint를 찾지 못했습니다. "
                f"기대 경로: {self.checkpoint_root}"
            )
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        started_at = time.perf_counter()
        self.base_tts = MeloTTSModel(
            language_code=self.language_code,
            voice=self.voice,
            speed=self.speed,
            device=self.device,
            use_hf=use_hf,
            config_path=config_path,
            ckpt_path=ckpt_path,
            sdp_ratio=sdp_ratio,
            noise_scale=noise_scale,
            noise_scale_w=noise_scale_w,
        )
        _install_wavmark_stub_if_needed()
        self.converter = ToneColorConverter(
            str(converter_config_path),
            device=self.device,
        )
        self.converter.load_ckpt(str(converter_ckpt_path))
        if hasattr(self.converter, "watermark_model"):
            self.converter.watermark_model = None
        self.source_speaker_key = self._resolve_source_speaker_key(self.voice)
        self.src_se = self._load_source_speaker_embedding(self.source_speaker_key)
        self.model_load_sec = time.perf_counter() - started_at
        self._target_se_cache = {}

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 OpenVoice V2로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() not in {"", ".wav"}:
            raise ValueError("OpenVoice V2 backend는 현재 `.wav` 출력만 지원합니다.")

        reference_audio_path = self._resolve_reference_audio_path()
        started_at = time.perf_counter()
        self.last_text = str(text).strip()

        try:
            target_se = self._get_target_speaker_embedding(reference_audio_path)
            with tempfile.TemporaryDirectory(prefix="openvoice_v2_") as tmp_dir:
                base_audio_path = Path(tmp_dir) / "base_tts.wav"
                self.base_tts.synthesize_to_file(self.last_text, base_audio_path)
                self.converter.convert(
                    audio_src_path=str(base_audio_path),
                    src_se=self.src_se,
                    tgt_se=target_se,
                    output_path=str(output_path),
                    tau=self.tau,
                    message="openvoice_v2",
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

    def _resolve_reference_audio_path(self):
        """
        기능:
        - OpenVoice V2가 사용할 참조 음성 경로를 검증한다.

        입력:
        - 없음.

        반환:
        - 검증된 참조 음성 경로를 반환한다.
        """
        if self.reference_audio_path is None:
            raise ValueError(
                "OpenVoice V2는 `reference_audio_path`가 반드시 필요합니다."
            )
        if not self.reference_audio_path.is_file():
            raise FileNotFoundError(
                f"참조 음성 파일을 찾지 못했습니다: {self.reference_audio_path}"
            )
        return self.reference_audio_path

    def _get_target_speaker_embedding(self, reference_audio_path):
        """
        기능:
        - 참조 음성에서 추출한 target speaker embedding을 캐시와 함께 반환한다.

        입력:
        - `reference_audio_path`: 참조 음성 경로.

        반환:
        - OpenVoice target speaker embedding tensor를 반환한다.
        """
        cache_key = str(reference_audio_path)
        if cache_key in self._target_se_cache:
            return self._target_se_cache[cache_key]

        audio_name = (
            f"{reference_audio_path.stem}_{self.converter.version}_"
            f"{self._se_extractor.hash_numpy_array(str(reference_audio_path))}"
        )
        se_path = self.processed_dir / audio_name / "se.pth"
        if se_path.is_file():
            target_se = self._torch.load(str(se_path), map_location=self.device).to(
                self.device
            )
            self._target_se_cache[cache_key] = target_se
            return target_se

        target_se, _ = self._se_extractor.get_se(
            audio_path=str(reference_audio_path),
            vc_model=self.converter,
            target_dir=str(self.processed_dir),
            vad=True,
        )
        target_se = target_se.to(self.device)
        self._target_se_cache[cache_key] = target_se
        return target_se

    def _load_source_speaker_embedding(self, speaker_key):
        """
        기능:
        - OpenVoice V2 base speaker embedding을 로드한다.

        입력:
        - `speaker_key`: base speaker 파일 key.

        반환:
        - source speaker embedding tensor를 반환한다.
        """
        speaker_path = (
            self.checkpoint_root / "base_speakers" / "ses" / f"{speaker_key}.pth"
        )
        if not speaker_path.is_file():
            raise FileNotFoundError(
                "OpenVoice V2 base speaker embedding을 찾지 못했습니다. "
                f"기대 경로: {speaker_path}"
            )
        return self._torch.load(str(speaker_path), map_location=self.device).to(
            self.device
        )

    def _resolve_source_speaker_key(self, voice):
        """
        기능:
        - 전달된 voice/language 값을 OpenVoice base speaker key로 변환한다.

        입력:
        - `voice`: speaker key 또는 언어 식별자.

        반환:
        - base speaker 파일 key를 반환한다.
        """
        normalized = str(voice or self.language_code).strip().lower().replace("_", "-")
        alias_map = {
            "kr": "kr",
            "ko": "kr",
            "ko-kr": "kr",
            "korean": "kr",
            "jp": "jp",
            "ja": "jp",
            "ja-jp": "jp",
            "japanese": "jp",
            "zh": "zh",
            "chinese": "zh",
            "es": "es",
            "spanish": "es",
            "fr": "fr",
            "french": "fr",
            "en": "en-default",
            "en-default": "en-default",
            "en-us": "en-us",
            "en-au": "en-au",
            "en-br": "en-br",
            "en-india": "en-india",
            "en-newest": "en-newest",
        }
        if normalized in alias_map:
            return alias_map[normalized]
        raise ValueError(
            f"지원하지 않는 OpenVoice V2 base speaker입니다: {voice}. "
            "예: KR, EN-US, EN-DEFAULT, JP, ZH, ES, FR"
        )
