"""
TTS 모듈 공개 진입점.
"""

from importlib import import_module

from .tts import TTSSynthesizer

_LAZY_EXPORTS = {
    "EdgeTTSModel": ("tts.backends", "EdgeTTSModel"),
    "OpenAIAPITTSModel": ("tts.backends", "OpenAIAPITTSModel"),
    "KokoroTTSModel": ("tts.backends", "KokoroTTSModel"),
    "MeloTTSModel": ("tts.backends", "MeloTTSModel"),
    "OpenVoiceV2Model": ("tts.backends", "OpenVoiceV2Model"),
    "PiperTTSModel": ("tts.backends", "PiperTTSModel"),
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
    if name == "TTSSynthesizer":
        return TTSSynthesizer
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)

    module_name, attr_name = _LAZY_EXPORTS[name]
    module = import_module(module_name)
    return getattr(module, attr_name)


__all__ = [
    "TTSSynthesizer",
    "EdgeTTSModel",
    "OpenAIAPITTSModel",
    "KokoroTTSModel",
    "MeloTTSModel",
    "OpenVoiceV2Model",
    "PiperTTSModel",
]
