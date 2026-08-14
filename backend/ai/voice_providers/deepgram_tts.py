"""Deepgram Aura text-to-speech.

Added because the examiner needs a voice for the real-time interview, and the
alternative required a second vendor account. Aura runs on the same Deepgram
key as transcription, so a deployment that can already hear the candidate can
already speak back.

The important property is the output format. Aura will return raw `linear16`
at a requested sample rate, which is precisely what `LiveKitRoomTransport`
publishes -- 16 kHz, mono, signed 16-bit. So the audio goes from here into a
WebRTC frame with no decoding step at all.

That matters more than it sounds. The batch ElevenLabs adapter returns MP3,
and MP3 cannot be turned into PCM without a native decoder; the transport
refuses it loudly for exactly that reason. Choosing a synthesiser that emits
PCM removes the problem rather than working around it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx

from ai.voice import Speech

SPEAK_URL = "https://api.deepgram.com/v1/speak"

#: Matches LiveKitRoomTransport.PUBLISH_SAMPLE_RATE. Changing one without the
#: other plays the examiner at the wrong pitch, which sounds like a bad
#: connection rather than a configuration mistake.
SAMPLE_RATE = 16_000

#: Raw PCM, carried with its rate so the transport does not have to guess.
MIME_TYPE = f"audio/pcm;rate={SAMPLE_RATE}"

#: A measured, articulate English voice. Aura's voices are named rather than
#: numbered, and this one reads as an examiner rather than an assistant.
DEFAULT_VOICE = "aura-2-thalia-en"


@dataclass
class DeepgramTextToSpeech:
    """Synthesise the examiner's turns as PCM ready for WebRTC."""

    api_key: str
    voice: str = DEFAULT_VOICE
    timeout_s: float = 30.0

    name: str = field(default="deepgram", init=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("Deepgram TTS requires an API key")

    async def synthesize(self, text: str, *, voice: str | None = None) -> Speech:
        spoken = (text or "").strip()
        if not spoken:
            # Nothing to say is not an error: the agent asks for silence
            # between phases, and an exception here would end the exam.
            return Speech(
                audio=b"", mime_type=MIME_TYPE, provider=self.name, duration_ms=0
            )

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                SPEAK_URL,
                params={
                    "model": voice or self.voice,
                    # Raw PCM rather than a container: the transport wants
                    # frames, and a WAV header would be published as audio.
                    "encoding": "linear16",
                    "sample_rate": str(SAMPLE_RATE),
                },
                headers={
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"text": spoken},
            )
            response.raise_for_status()
            audio = response.content

        _ = started  # latency is visible in the request log; not part of Speech
        return Speech(
            audio=audio,
            mime_type=MIME_TYPE,
            provider=self.name,
            # Derived from the byte count rather than read from a header,
            # because raw PCM has none. Two bytes per mono sample.
            duration_ms=int(len(audio) / 2 / SAMPLE_RATE * 1000),
        )
