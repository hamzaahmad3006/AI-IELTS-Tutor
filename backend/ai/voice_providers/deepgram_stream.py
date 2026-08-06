"""Deepgram streaming transcription over WebSocket.

The batch adapter waits for a finished recording. This one transcribes while
the candidate is still talking, which is what makes barge-in and instant
turn-taking possible: the agent knows someone started speaking within a couple
of hundred milliseconds instead of after the upload.

Deliberately thin. It speaks Deepgram's protocol and translates each message
into a transport-neutral `Observation`; every decision about what those
observations *mean* lives in core.turn_taking, where it can be tested without a
socket. A streaming client that also decided when turns ended would be
untestable and would hide the exam rules inside a network adapter.

The parameters matter more than the plumbing:

* `interim_results` is on, because barge-in needs to know about speech before
  it is finalised.
* `vad_events` gives an explicit SpeechStarted, which is faster and more
  reliable than inferring speech from a first partial transcript.
* `utterance_end_ms` is set high and treated as advisory. Deepgram's
  endpointing is tuned for conversation; this exam assesses people who pause to
  think, and following its advice directly would cut them off.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlencode

import websockets

from core.turn_taking import Event, Observation

_DEEPGRAM_WS = "wss://api.deepgram.com/v1/listen"

#: Deepgram's minimum is 1000ms. This is the largest useful value: it is only a
#: hint, and core.turn_taking applies the real threshold.
UTTERANCE_END_MS = 2_000


@dataclass(frozen=True)
class StreamConfig:
    model: str = "nova-2"
    #: Raw PCM is what WebRTC gives us; no container, no re-encoding.
    encoding: str = "linear16"
    sample_rate: int = 16_000
    channels: int = 1
    language: str = "en"

    def as_params(self) -> dict[str, str]:
        return {
            "model": self.model,
            "encoding": self.encoding,
            "sample_rate": str(self.sample_rate),
            "channels": str(self.channels),
            "language": self.language,
            "punctuate": "true",
            "smart_format": "true",
            # Hesitation is evidence for Fluency and Coherence, so it is
            # transcribed rather than tidied away.
            "filler_words": "true",
            # Needed for barge-in: waiting for a finalised result would let the
            # examiner talk over the candidate for a second or more.
            "interim_results": "true",
            "vad_events": "true",
            "utterance_end_ms": str(UTTERANCE_END_MS),
        }


def build_url(config: StreamConfig) -> str:
    return f"{_DEEPGRAM_WS}?{urlencode(config.as_params())}"


def parse_message(raw: str | bytes, *, at_ms: int) -> Observation | None:
    """Translate one Deepgram message into an Observation.

    Returns None for messages that carry no turn-taking signal -- metadata,
    keepalives, and empty interim results, which Deepgram emits steadily during
    silence and which would otherwise look like continuous speech.
    """
    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    kind = message.get("type")

    if kind == "SpeechStarted":
        return Observation(event=Event.SPEECH_STARTED, at_ms=at_ms)

    if kind == "UtteranceEnd":
        return Observation(event=Event.UTTERANCE_END, at_ms=at_ms)

    if kind != "Results":
        # Metadata, Finalize acknowledgements, anything Deepgram adds later.
        return None

    channel = message.get("channel") or {}
    alternatives = channel.get("alternatives") or []
    text = (alternatives[0].get("transcript") or "") if alternatives else ""

    if not text.strip():
        # An empty result is silence, not speech. Treating it as speech would
        # keep resetting the silence timer and the turn would never end.
        return None

    is_final = bool(message.get("is_final"))
    return Observation(
        event=Event.FINAL_TRANSCRIPT if is_final else Event.INTERIM_TRANSCRIPT,
        at_ms=at_ms,
        text=text,
    )


class DeepgramStream:
    """An open streaming transcription session."""

    name = "deepgram-stream"

    def __init__(self, api_key: str, config: StreamConfig | None = None) -> None:
        if not api_key:
            raise ValueError("Deepgram streaming requires an API key")
        self._api_key = api_key
        self._config = config or StreamConfig()
        self._socket: websockets.ClientConnection | None = None

    async def __aenter__(self) -> DeepgramStream:
        self._socket = await websockets.connect(
            build_url(self._config),
            additional_headers={"Authorization": f"Token {self._api_key}"},
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def send_audio(self, chunk: bytes) -> None:
        if self._socket is None:
            raise RuntimeError("Stream is not open")
        await self._socket.send(chunk)

    async def finish(self) -> None:
        """Ask Deepgram to flush and finalise.

        Sent instead of simply closing, so the last partial result is finalised
        rather than discarded -- otherwise the end of every answer is lost.
        """
        if self._socket is not None:
            await self._socket.send(json.dumps({"type": "Finalize"}))

    async def close(self) -> None:
        if self._socket is not None:
            await self._socket.close()
            self._socket = None

    async def observations(self, clock) -> AsyncIterator[Observation]:
        """Yield turn-taking observations as they arrive.

        `clock` returns milliseconds since the turn began. Injected rather than
        read here so timing is the caller's, and so tests are deterministic.
        """
        if self._socket is None:
            raise RuntimeError("Stream is not open")
        async for raw in self._socket:
            observation = parse_message(raw, at_ms=clock())
            if observation is not None:
                yield observation
