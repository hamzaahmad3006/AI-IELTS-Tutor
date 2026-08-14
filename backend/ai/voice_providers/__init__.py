"""Voice provider factory.

Both default to the mock. A voice provider is only built when it has been
explicitly selected *and* given a key, so a missing key degrades to silent
offline behaviour rather than failing at request time — and, more to the point,
so nothing bills anybody by accident.
"""

from __future__ import annotations

from pathlib import Path

from ai.voice import (
    MockSpeechToText,
    MockTextToSpeech,
    SpeechToText,
    TextToSpeech,
)
from core.config import get_settings

from .deepgram_stt import DeepgramSpeechToText
from .deepgram_tts import DeepgramTextToSpeech
from .elevenlabs_tts import ElevenLabsTextToSpeech, SpendLimitExceeded


def build_stt() -> SpeechToText:
    settings = get_settings()
    if settings.stt_provider == "deepgram" and settings.deepgram_api_key:
        return DeepgramSpeechToText(
            api_key=settings.deepgram_api_key, model=settings.deepgram_model
        )
    return MockSpeechToText()


def build_tts() -> TextToSpeech:
    settings = get_settings()
    # Checked first: Aura runs on the same key as transcription and emits raw
    # PCM, so a real-time deployment needs one vendor rather than two and the
    # transport needs no decoder.
    if settings.tts_provider == "deepgram" and settings.deepgram_api_key:
        return DeepgramTextToSpeech(
            api_key=settings.deepgram_api_key, voice=settings.deepgram_voice
        )
    if settings.tts_provider == "elevenlabs" and settings.elevenlabs_api_key:
        return ElevenLabsTextToSpeech(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model=settings.elevenlabs_model,
            cache_dir=Path(settings.tts_cache_dir),
            monthly_character_limit=settings.elevenlabs_monthly_char_limit,
        )
    return MockTextToSpeech()


__all__ = [
    "build_stt",
    "DeepgramTextToSpeech",
    "build_tts",
    "DeepgramSpeechToText",
    "ElevenLabsTextToSpeech",
    "SpendLimitExceeded",
]
