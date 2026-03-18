"""
Piper backend.
"""

import json
from pathlib import Path
import time
import types
import wave

from .base import BaseTTSModel


class PiperTTSModel(BaseTTSModel):
    def __init__(
        self,
        model_name="en_US-lessac-medium",
        voice=None,
        speed=1.0,
        device=None,
        checkpoint_root=None,
    ):
        """
        기능:
        - Piper backend를 초기화한다.

        입력:
        - `model_name`: Piper voice code 또는 `.onnx` 모델 경로.
        - `voice`: multi-speaker voice용 speaker id.
        - `speed`: 합성 속도 배율.
        - `device`: `cuda:0` 같은 실행 장치 문자열.
        - `checkpoint_root`: voice 모델 다운로드/탐색 루트 경로.

        반환:
        - 없음.
        """
        try:
            import onnxruntime as ort
            from piper.download_voices import download_voice
            from piper.config import PiperConfig
            from piper.voice import PiperVoice
            from piper.config import SynthesisConfig
        except Exception as exc:
            raise ImportError(
                "Piper를 사용하려면 전용 env에 `piper-tts`와 "
                "`onnxruntime-gpu`를 설치해야 합니다."
            ) from exc

        super().__init__()
        self._ort = ort
        self._download_voice = download_voice
        self._PiperConfig = PiperConfig
        self._PiperVoice = PiperVoice
        self._SynthesisConfig = SynthesisConfig
        self.model_name = str(model_name or "en_US-lessac-medium").strip()
        self.voice = voice
        self.speed = float(speed)
        self.device = str(device or "cuda:0").strip()
        self.use_cuda = "cuda" in self.device.lower()
        self.workspace_root = Path(__file__).resolve().parents[3]
        self.checkpoint_root = (
            Path(checkpoint_root).expanduser().resolve()
            if checkpoint_root
            else self.workspace_root / "results" / "tts_assets" / "piper"
        )
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)

        model_path, config_path = self._resolve_model_paths(self.model_name)
        self._raw_config = self._load_config_dict(config_path)
        started_at = time.perf_counter()
        self.model = self._load_model(model_path, config_path, self._raw_config)
        self.model_load_sec = time.perf_counter() - started_at
        self.model_path = Path(model_path)
        self.config_path = Path(config_path)
        self.session_providers = list(self.model.session.get_providers())
        self.raw_phoneme_type = str(self._raw_config.get("phoneme_type", "")).strip()
        self.pygoruut_language = str(
            getattr(self.model, "_pygoruut_language", "")
        ).strip()
        self.pygoruut_version = str(
            getattr(self.model, "_pygoruut_version", "")
        ).strip()

    def synthesize_to_file(self, text, output_path):
        """
        기능:
        - 입력 텍스트를 Piper로 합성해 지정한 파일로 저장한다.

        입력:
        - `text`: 음성으로 변환할 문자열.
        - `output_path`: 생성 오디오를 저장할 파일 경로.

        반환:
        - 저장한 파일 경로를 반환한다.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix.lower() not in {"", ".wav"}:
            raise ValueError("Piper backend는 현재 `.wav` 출력만 지원합니다.")

        started_at = time.perf_counter()
        self.last_text = str(text).strip()
        syn_config = self._build_synthesis_config()

        try:
            with wave.open(str(output_path), "wb") as wav_file:
                self.model.synthesize_wav(
                    self.last_text,
                    wav_file,
                    syn_config=syn_config,
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

    def _build_synthesis_config(self):
        """
        기능:
        - Piper 합성에 사용할 설정을 구성한다.

        입력:
        - 없음.

        반환:
        - `SynthesisConfig` 객체를 반환한다.
        """
        speaker_id = self._resolve_speaker_id(self.voice)
        length_scale = None
        if self.speed > 0:
            length_scale = 1.0 / self.speed
        return self._SynthesisConfig(
            speaker_id=speaker_id,
            length_scale=length_scale,
        )

    def _resolve_model_paths(self, model_name):
        """
        기능:
        - Piper model_name을 실제 `.onnx`와 `.onnx.json` 경로로 변환한다.

        입력:
        - `model_name`: Piper voice code 또는 `.onnx` 경로.

        반환:
        - `(model_path, config_path)` 튜플을 반환한다.
        """
        candidate = Path(model_name).expanduser()
        if candidate.suffix == ".onnx":
            model_path = candidate.resolve()
            config_path = Path(f"{model_path}.json")
            if not model_path.is_file():
                raise FileNotFoundError(f"Piper 모델을 찾지 못했습니다: {model_path}")
            if not config_path.is_file():
                raise FileNotFoundError(
                    f"Piper config를 찾지 못했습니다: {config_path}"
                )
            return model_path, config_path

        model_path = self.checkpoint_root / f"{model_name}.onnx"
        config_path = self.checkpoint_root / f"{model_name}.onnx.json"
        if not model_path.is_file() or not config_path.is_file():
            self._download_voice(model_name, self.checkpoint_root)
        return model_path, config_path

    def _resolve_speaker_id(self, voice):
        """
        기능:
        - 전달된 voice 값을 Piper speaker id 정수로 변환한다.

        입력:
        - `voice`: speaker id 문자열 또는 정수.

        반환:
        - speaker id 정수 또는 `None`을 반환한다.
        """
        if voice is None:
            return None
        if isinstance(voice, int):
            return int(voice)
        voice_text = str(voice).strip()
        if voice_text.isdigit():
            return int(voice_text)
        raise ValueError(
            "Piper backend의 `voice`는 현재 speaker id 정수만 지원합니다."
        )

    def _load_model(self, model_path, config_path, config_dict):
        """
        기능:
        - 일반 Piper voice 또는 `pygoruut` 기반 custom voice를 로드한다.

        입력:
        - `model_path`: `.onnx` 모델 경로.
        - `config_path`: `.onnx.json` config 경로.
        - `config_dict`: config JSON dict.

        반환:
        - 초기화된 Piper voice 객체를 반환한다.
        """
        if self.use_cuda:
            # onnxruntime-gpu can use NVIDIA wheel libraries when preloaded first.
            self._ort.preload_dlls(directory="")

        raw_phoneme_type = str(config_dict.get("phoneme_type", "")).strip().lower()
        if raw_phoneme_type != "pygoruut":
            return self._PiperVoice.load(
                model_path=model_path,
                config_path=config_path,
                use_cuda=self.use_cuda,
                download_dir=self.checkpoint_root,
            )

        try:
            from pygoruut.pygoruut import Pygoruut
        except Exception as exc:
            raise ImportError(
                "이 Piper custom model은 `phoneme_type=pygoruut`를 사용합니다. "
                "전용 env에 `pip install pygoruut`를 추가해야 합니다."
            ) from exc

        providers = ["CPUExecutionProvider"]
        if self.use_cuda:
            providers = [
                (
                    "CUDAExecutionProvider",
                    {"cudnn_conv_algo_search": "HEURISTIC"},
                )
            ]

        patched_config = dict(config_dict)
        patched_config["phoneme_type"] = "text"
        model = self._PiperVoice(
            config=self._PiperConfig.from_dict(patched_config),
            session=self._ort.InferenceSession(
                str(model_path),
                sess_options=self._ort.SessionOptions(),
                providers=providers,
            ),
            download_dir=self.checkpoint_root,
        )

        language = self._resolve_pygoruut_language(config_dict)
        version = self._resolve_pygoruut_version(config_dict)
        phoneme_id_map = dict(model.config.phoneme_id_map)
        pygoruut = Pygoruut(version=version, writeable_bin_dir="")

        def _phonemize_with_pygoruut(inner_self, text):
            response = pygoruut.phonemize(language=language, sentence=text)
            raw_phonemes = self._build_pygoruut_raw_phonemes(response)
            normalized = self._normalize_pygoruut_phonemes(raw_phonemes)
            phonemes = [char for char in normalized if char in phoneme_id_map]
            if not phonemes:
                raise ValueError(
                    "pygoruut phonemizer 결과를 현재 Piper phoneme_id_map으로 "
                    "변환하지 못했습니다."
                )
            return [phonemes]

        model.phonemize = types.MethodType(_phonemize_with_pygoruut, model)
        model._pygoruut_language = language
        model._pygoruut_version = version
        return model

    def _load_config_dict(self, config_path):
        """
        기능:
        - Piper config JSON을 dict로 읽는다.

        입력:
        - `config_path`: `.onnx.json` 경로.

        반환:
        - config dict를 반환한다.
        """
        with Path(config_path).open("r", encoding="utf-8") as config_file:
            return json.load(config_file)

    def _resolve_pygoruut_language(self, config_dict):
        """
        기능:
        - `pygoruut` phonemizer에 넘길 언어 이름을 정한다.

        입력:
        - `config_dict`: Piper config JSON dict.

        반환:
        - `pygoruut` 언어 문자열을 반환한다.
        """
        language = config_dict.get("language", {}).get("code")
        if language:
            return str(language).strip()

        espeak_voice = config_dict.get("espeak", {}).get("voice")
        if espeak_voice:
            return str(espeak_voice).strip()

        return "Korean"

    def _resolve_pygoruut_version(self, config_dict):
        """
        기능:
        - `pygoruut` custom model에 사용할 goruut 버전을 결정한다.

        입력:
        - `config_dict`: Piper config JSON dict.

        반환:
        - goruut version 문자열 또는 `None`을 반환한다.
        """
        explicit_version = config_dict.get("pygoruut_version")
        if explicit_version:
            return str(explicit_version).strip()

        language = self._resolve_pygoruut_language(config_dict)
        if language in {"Korean", "ko"}:
            # 0.7.0 기준 한국어 분절이 `안녕하세요 -> 녕 + 안하세요`처럼 깨져
            # 같은 모델에서도 품질이 크게 흔들린다. 현재는 v0.6.2가 더 안정적이다.
            return "v0.6.2"
        return None

    def _build_pygoruut_raw_phonemes(self, response):
        """
        기능:
        - `pygoruut` 응답 객체에서 실제 phonetic 본문만 추려 Piper 입력 문자열을 만든다.

        입력:
        - `response`: `pygoruut` phonemize 응답 객체.

        반환:
        - phonetic 문자열을 반환한다.
        """
        words = getattr(response, "Words", None)
        if not words:
            return str(response)

        parts = []
        for word in words:
            phonetic = str(getattr(word, "Phonetic", "")).strip()
            if phonetic:
                parts.append(phonetic)

            post_punct = str(getattr(word, "PostPunct", "")).strip()
            if post_punct:
                parts.append(post_punct)

            parts.append(" ")

        return "".join(parts).strip()

    def _normalize_pygoruut_phonemes(self, phoneme_text):
        """
        기능:
        - `pygoruut` 출력 중 현재 Python Piper runtime이 바로 못 쓰는 일부 기호를
          보수적으로 정리한다.

        입력:
        - `phoneme_text`: `pygoruut`가 반환한 문자열.

        반환:
        - 정리된 phoneme 문자열을 반환한다.
        """
        replacements = {
            "ʰ": "h",
        }
        drops = {
            "̠",
            "̞",
            "̹",
        }

        normalized = []
        for char in phoneme_text:
            if char in drops:
                continue
            normalized.append(replacements.get(char, char))
        return "".join(normalized)
