"""
TTS backend 패키지 공개 진입점.
"""

from importlib import import_module

from .base import BaseTTSModel

_LAZY_EXPORTS = {
    "EdgeTTSModel": (".edge_tts", "EdgeTTSModel"),
    "OpenAIAPITTSModel": (".openai_api", "OpenAIAPITTSModel"),
    "KokoroTTSModel": (".kokoro", "KokoroTTSModel"),
    "MeloTTSModel": (".melotts", "MeloTTSModel"),
    "OpenVoiceV2Model": (".openvoice_v2", "OpenVoiceV2Model"),
    "PiperTTSModel": (".piper", "PiperTTSModel"),
}


def __getattr__(name):
    """
    기능:
    - backend 클래스를 실제 접근 시점에만 지연 import한다.

    입력:
    - `name`: 조회할 export 이름.

    반환:
    - 요청한 backend 클래스 객체를 반환한다.
    """
    if name == "BaseTTSModel":
        return BaseTTSModel
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)

    module_name, attr_name = _LAZY_EXPORTS[name]
    module = import_module(module_name, package=__name__)
    return getattr(module, attr_name)


__all__ = [
    "BaseTTSModel",
    "EdgeTTSModel",
    "OpenAIAPITTSModel",
    "KokoroTTSModel",
    "MeloTTSModel",
    "OpenVoiceV2Model",
    "PiperTTSModel",
]
