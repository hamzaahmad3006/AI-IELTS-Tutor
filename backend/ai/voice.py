"""Ports for speech-to-text and text-to-speech.

Two implementations are planned and they are very different animals:

* **On-device (Android)** — the phone's own recogniser and synthesiser. Free,
  private, no account, works offline. The server never sees audio at all; the
  client posts a finished transcript. Quality is below a dedicated model and
  there is no real barge-in.
* **Server-side (LiveKit + a streaming provider)** — real duplex audio, the
  examiner can be interrupted, recordings can be kept. Costs money per minute
  and needs infrastructure.

They agree on very little, which is exactly why the contract is drawn narrowly:
audio in, text out; text in, audio out. Anything wider would end up shaped like
whichever one was written first, and the second would not fit.

Note what is *not* here. There is no "start streaming session" method, because
on-device recognition has no session to start. The streaming case will add its
own interface for the parts that genuinely differ, rather than forcing a
lowest-common-denominator abstraction that suits neither.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Transcript:
    """A recognised utterance."""

    text: str
    #: 0..1 where the provider reports one. None means "not offered" -- which
    #: is different from zero, and must not be rendered as low confidence.
    confidence: float | None = None
    #: Provider identifier, recorded so a transcript can be traced to what
    #: produced it when scores look wrong.
    provider: str = "unknown"
    #: Wall-clock length of the audio, where known.
    duration_ms: int | None = None
    #: True when the speaker was still talking -- streaming providers emit
    #: these continuously and they must never be scored.
    is_partial: bool = False


@dataclass(frozen=True)
class Speech:
    """Synthesised audio."""

    audio: bytes
    mime_type: str
    provider: str = "unknown"
    duration_ms: int | None = None


@runtime_checkable
class SpeechToText(Protocol):
    """Turns recorded audio into text."""

    name: str

    async def transcribe(self, audio: bytes, *, mime_type: str) -> Transcript: ...


@runtime_checkable
class TextToSpeech(Protocol):
    """Turns text into audio."""

    name: str

    async def synthesize(self, text: str, *, voice: str | None = None) -> Speech: ...


class DeviceSpeechToText:
    """Stand-in for recognition that happened on the phone.

    The Android recogniser runs client-side, so by the time the server is
    involved the work is done and there is no audio to process. This exists so
    the server-side path has something to hold that satisfies the port, and so
    a transcript's origin is recorded rather than assumed.
    """

    name = "android-device"

    async def transcribe(self, audio: bytes, *, mime_type: str) -> Transcript:
        raise NotImplementedError(
            "On-device recognition produces its transcript on the client. "
            "Post the text to the interview endpoint instead of audio."
        )


@dataclass
class MockSpeechToText:
    """Returns queued transcripts. For tests and for the offline eval path."""

    name: str = "mock"
    queued: list[str] = field(default_factory=list)

    async def transcribe(self, audio: bytes, *, mime_type: str) -> Transcript:
        text = self.queued.pop(0) if self.queued else ""
        return Transcript(
            text=text,
            confidence=1.0 if text else 0.0,
            provider=self.name,
            duration_ms=len(audio),
        )


@dataclass
class MockTextToSpeech:
    """Produces silent audio of a plausible length.

    Length scales with the text so a client that sequences on playback duration
    behaves roughly as it would with real speech, rather than racing through
    because every clip is zero bytes.
    """

    name: str = "mock"
    #: Roughly conversational pace.
    words_per_minute: int = 150

    async def synthesize(self, text: str, *, voice: str | None = None) -> Speech:
        words = max(1, len(text.split()))
        duration_ms = int(words / self.words_per_minute * 60_000)
        return Speech(
            audio=b"",
            mime_type="audio/wav",
            provider=self.name,
            duration_ms=duration_ms,
        )
