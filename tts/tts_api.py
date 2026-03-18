"""
기존 API TTS backend 호환 import 경로.
"""

from .backends.openai_api import OpenAIAPITTSModel

__all__ = ["OpenAIAPITTSModel"]
