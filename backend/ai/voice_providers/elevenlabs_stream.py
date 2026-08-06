"""ElevenLabs streaming synthesis over WebSocket.

The batch adapter waits for the whole sentence to be rendered before anything
plays. For a question like "Now I'm going to give you a topic, and I'd like you
to talk about it for one to two minutes..." that is a second or more of silence
before the examiner opens their mouth, which is exactly the dead air that makes
a voice agent feel like a form submission.

Streaming plays the first chunk as soon as it arrives, so the perceived latency
is the time to the first audio frame rather than to the last.

The trade-off, stated plainly: streamed audio is not cached. The batch adapter's
cache is what makes a fixed question bank cost almost nothing, and chunks
arriving over time cannot be keyed and stored the same way without buffering the
whole thing -- which would give back the latency this exists to remove. So the
two are used for different jobs:

* **Batch, cached** for the question bank. Fixed text, spoken to everyone,
  latency hidden by pre-fetching while the candidate is still answering.
* **Streaming, uncached** for anything generated on the fly, where there is
  nothing to pre-fetch and the first-chunk latency is what the candidate feels.

Because streaming bypasses the cache it also bypasses the saving, so it is
counted against the same monthly ledger. A streaming path that quietly did not
count would make the ceiling meaningless.
"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

import websockets

from .elevenlabs_tts import DEFAULT_MODEL, DEFAULT_VOICE_ID, SpendLimitExceeded, UsageLedger

_WS_ROOT = "wss://api.elevenlabs.io/v1/text-to-speech"

#: PCM at 16 kHz: what WebRTC wants, and no client-side decode step.
DEFAULT_OUTPUT_FORMAT = "pcm_16000"


@dataclass(frozen=True)
class StreamConfig:
    voice_id: str = DEFAULT_VOICE_ID
    model: str = DEFAULT_MODEL
    output_format: str = DEFAULT_OUTPUT_FORMAT
    #: How much text ElevenLabs buffers before it starts generating. Low values
    #: start sooner; very low ones cost prosody, because the model has less
    #: context for where the sentence is going.
    chunk_length_schedule: tuple[int, ...] = (120, 160, 250, 290)


def build_url(config: StreamConfig) -> str:
    params = urlencode(
        {"model_id": config.model, "output_format": config.output_format}
    )
    return f"{_WS_ROOT}/{config.voice_id}/stream-input?{params}"


def opening_message(text: str, config: StreamConfig) -> str:
    """The first frame, which carries settings as well as text."""
    return json.dumps(
        {
            "text": f"{text} ",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
            "generation_config": {
                "chunk_length_schedule": list(config.chunk_length_schedule)
            },
        }
    )


#: Sent to flush and close. An empty string is ElevenLabs' end-of-input marker;
#: without it the final chunk is never generated and the last words are lost.
CLOSING_MESSAGE = json.dumps({"text": ""})


def parse_chunk(raw: str | bytes) -> bytes | None:
    """Decode one audio frame, or None for a message carrying no audio.

    Alignment and metadata frames arrive interleaved with audio and must not be
    fed to the speaker.
    """
    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    audio = message.get("audio")
    if not audio:
        return None
    try:
        return base64.b64decode(audio)
    except (ValueError, TypeError):
        # A frame we cannot decode is dropped rather than raised: one corrupt
        # chunk should cost a moment of audio, not the whole question.
        return None


class ElevenLabsStream:
    """Streaming synthesis for one utterance."""

    name = "elevenlabs-stream"

    def __init__(
        self,
        api_key: str,
        *,
        config: StreamConfig | None = None,
        cache_dir: Path | None = None,
        monthly_character_limit: int = 0,
    ) -> None:
        if not api_key:
            raise ValueError("ElevenLabs streaming requires an API key")
        self._api_key = api_key
        self._config = config or StreamConfig()
        self._limit = monthly_character_limit
        self._ledger = UsageLedger(
            (cache_dir or Path("media/tts-cache")) / "usage.json"
        )

    def remaining_characters(self) -> int | None:
        if self._limit <= 0:
            return None
        return max(0, self._limit - self._ledger.spent())

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield audio chunks as they are generated."""
        text = text.strip()
        if not text:
            raise ValueError("Nothing to synthesize")

        # Checked before connecting. Streaming skips the cache, so it skips the
        # saving too, and a streaming path that did not count against the
        # ledger would make the ceiling meaningless.
        remaining = self.remaining_characters()
        if remaining is not None and len(text) > remaining:
            raise SpendLimitExceeded(
                f"Streaming {len(text)} characters would exceed the monthly "
                f"limit of {self._limit}; {remaining} remain."
            )

        async with websockets.connect(
            build_url(self._config),
            additional_headers={"xi-api-key": self._api_key},
        ) as socket:
            await socket.send(opening_message(text, self._config))
            await socket.send(CLOSING_MESSAGE)

            charged = False
            async for raw in socket:
                chunk = parse_chunk(raw)
                if chunk:
                    if not charged:
                        # Charged on first audio, not on connect: a request
                        # that produced nothing was not a synthesis, and
                        # billing for it would ratchet the budget down on
                        # every failure.
                        self._ledger.add(len(text))
                        charged = True
                    yield chunk
