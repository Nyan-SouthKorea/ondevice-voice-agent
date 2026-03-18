"""
TTS 공통 진입점.

동일한 `synthesize_to_file(text, output_path)` 사용법으로
여러 TTS 백엔드를 갈아끼울 수 있게 한다.
"""

from importlib import import_module
from pathlib import Path

IMPLEMENTED_TTS_MODELS = (
    "api",
    "openai_api",
    "chatgpt_api",
    "edge_tts",
    "melotts",
    "openvoice_v2",
    "piper",
    "kokoro",
)
PLANNED_TTS_MODELS = ()

_BACKEND_SPECS = {
    "api": ("tts.backends.openai_api", "OpenAIAPITTSModel"),
    "openai_api": ("tts.backends.openai_api", "OpenAIAPITTSModel"),
    "chatgpt_api": ("tts.backends.openai_api", "OpenAIAPITTSModel"),
    "edge_tts": ("tts.backends.edge_tts", "EdgeTTSModel"),
    "melotts": ("tts.backends.melotts", "MeloTTSModel"),
    "openvoice_v2": ("tts.backends.openvoice_v2", "OpenVoiceV2Model"),
    "piper": ("tts.backends.piper", "PiperTTSModel"),
    "kokoro": ("tts.backends.kokoro", "KokoroTTSModel"),
}


def _load_backend_class(model_name):
    """
    기능:
    - 선택한 backend 클래스만 지연 import한다.

    입력:
    - `model_name`: backend key 문자열.

    반환:
    - 해당 backend 클래스 객체를 반환한다.
    """
    if model_name not in _BACKEND_SPECS:
        raise ValueError(f"지원하지 않는 TTS 모델입니다: {model_name}")

    module_name, class_name = _BACKEND_SPECS[model_name]
    module = import_module(module_name)
    return getattr(module, class_name)


class TTSSynthesizer:
    def __init__(
        self,
        model="api",
        model_name=None,
        voice=None,
        instructions=None,
        response_format="wav",
        speed=1.0,
        rate=None,
        pitch=None,
        device=None,
        reference_audio_path=None,
        checkpoint_root=None,
        api_key=None,
        usage_purpose=None,
    ):
        """
        기능:
        - 선택한 백엔드에 맞는 TTS 모델을 초기화하고 공통 인터페이스를 제공한다.

        입력:
        - `model`: 사용할 TTS 백엔드 이름.
        - `model_name`: 백엔드별 실제 모델 이름.
        - `voice`: 사용할 음성 이름.
        - `instructions`: 말투 제어용 추가 지시 문자열.
        - `response_format`: 출력 오디오 포맷.
        - `speed`: 합성 속도 배율.
        - `rate`: backend별 속도 문자열. 현재 `edge_tts`에서 사용.
        - `pitch`: backend별 음높이 문자열. 현재 `edge_tts`에서 사용.
        - `device`: backend별 실행 장치 문자열.
        - `reference_audio_path`: voice cloning 계열 backend의 참조 음성 경로.
        - `checkpoint_root`: backend별 외부 자산 루트 경로.
        - `api_key`: API TTS용 키.
        - `usage_purpose`: API 사용 목적 기록용 문자열.

        반환:
        - 없음.
        """
        self.model = model
        if model in {"api", "openai_api", "chatgpt_api"}:
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                model_name=model_name or "gpt-4o-mini-tts",
                voice=voice or "alloy",
                instructions=instructions,
                response_format=response_format,
                speed=speed,
                api_key=api_key,
                usage_purpose=usage_purpose,
            )
        elif model == "edge_tts":
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                voice=voice or "ko-KR-SunHiNeural",
                rate=rate,
                pitch=pitch,
                speed=speed,
            )
        elif model == "melotts":
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                language_code=model_name or "KR",
                voice=voice or "KR",
                speed=speed,
                device=device or "cuda:0",
            )
        elif model == "openvoice_v2":
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                language_code=model_name or "KR",
                voice=voice or "KR",
                reference_audio_path=reference_audio_path,
                speed=speed,
                device=device or "cuda:0",
                checkpoint_root=checkpoint_root,
            )
        elif model == "piper":
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                model_name=model_name or "en_US-lessac-medium",
                voice=voice,
                speed=speed,
                device=device or "cuda:0",
                checkpoint_root=checkpoint_root,
            )
        elif model == "kokoro":
            backend_cls = _load_backend_class(model)
            self.backend = backend_cls(
                language_code=model_name or "a",
                voice=voice or "af_heart",
                speed=speed,
                device=device or "cuda",
            )
        else:
            raise ValueError(f"지원하지 않는 TTS 모델입니다: {model}")

        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_error = ""
        self.model_load_sec = float(getattr(self.backend, "model_load_sec", 0.0))

    @staticmethod
    def available_models():
        """
        기능:
        - 현재 코드에서 바로 사용할 수 있는 TTS backend 목록을 반환한다.

        입력:
        - 없음.

        반환:
        - backend 이름 목록을 반환한다.
        """
        return list(IMPLEMENTED_TTS_MODELS)

    @staticmethod
    def planned_models():
        """
        기능:
        - 현재 비교 대상으로 계획된 TTS 후보 목록을 반환한다.

        입력:
        - 없음.

        반환:
        - 계획된 backend 이름 목록을 반환한다.
        """
        return list(PLANNED_TTS_MODELS)

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
        saved_path = self.backend.synthesize_to_file(text, output_path)
        self.last_duration_sec = float(self.backend.last_duration_sec)
        self.last_output_path = Path(saved_path)
        self.last_error = str(getattr(self.backend, "last_error", ""))
        return self.last_output_path

    def synthesize_bytes(self, text):
        """
        기능:
        - 입력 텍스트를 음성으로 합성하고 결과 바이트를 반환한다.

        입력:
        - `text`: 음성으로 변환할 문자열.

        반환:
        - 생성 오디오의 바이트 데이터를 반환한다.
        """
        payload = self.backend.synthesize_bytes(text)
        self.last_duration_sec = float(self.backend.last_duration_sec)
        self.last_output_path = getattr(self.backend, "last_output_path", None)
        self.last_error = str(getattr(self.backend, "last_error", ""))
        return payload

    def reset(self):
        """
        기능:
        - 마지막 TTS 실행 상태를 초기화한다.

        입력:
        - 없음.

        반환:
        - 없음.
        """
        self.backend.reset()
        self.last_duration_sec = 0.0
        self.last_output_path = None
        self.last_error = ""
