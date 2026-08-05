"""Deepgram speech-to-text adapter (pre-recorded audio).

Batch transcription rather than streaming: the phone records one answer, uploads
it, and gets text back. That matches the exam -- a candidate answers a question
and stops -- and it costs per second of audio rather than per connected minute,
which for a test taken a few times a week is a very different bill.

Streaming will be a separate adapter when barge-in arrives. It is genuinely a
different protocol, not a flag on this one, which is why the port does not
pretend otherwise.

Uses httpx directly, like the Groq adapter, so there is no SDK dependency to
keep in step with the rest of the stack.
"""

from __future__ import annotations

import time

import httpx

from ai.voice import Transcript

_DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"

#: Nova-2 is Deepgram's general-purpose model. `smart_format` restores
#: punctuation and capitalisation, which matters here beyond readability: the
#: scorer reads sentence structure, and an unpunctuated wall of words reads as
#: far worse grammar than the candidate actually produced.
_DEFAULT_MODEL = "nova-2"

_PARAMS = {
    "model": _DEFAULT_MODEL,
    "smart_format": "true",
    "punctuate": "true",
    # Filler words are kept on purpose. "Um" and "er" are evidence for the
    # Fluency and Coherence band, so stripping them would quietly inflate the
    # score for exactly the candidates who need to hear about hesitation.
    "filler_words": "true",
    "language": "en",
}


class DeepgramSpeechToText:
    name = "deepgram"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = _DEFAULT_MODEL,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Deepgram requires an API key")
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    async def transcribe(self, audio: bytes, *, mime_type: str) -> Transcript:
        if not audio:
            # Refused locally rather than sent. An empty upload is always a
            # client bug, and paying an API to confirm that is silly.
            raise ValueError("No audio to transcribe")

        params = {**_PARAMS, "model": self._model}
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                _DEEPGRAM_URL,
                params=params,
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": mime_type,
                },
                content=audio,
            )
            response.raise_for_status()
            body = response.json()
        latency_ms = int((time.perf_counter() - started) * 1000)

        return _parse(body, latency_ms=latency_ms)


def _parse(body: dict, *, latency_ms: int) -> Transcript:
    """Pull the transcript out of a Deepgram response.

    Split out and given its own tests because the shape is deeply nested and
    every level is optional. A response with no alternatives means "nothing was
    recognised", which is a real outcome for a silent recording and must come
    back as empty text rather than a KeyError.
    """
    channels = (body.get("results") or {}).get("channels") or []
    alternatives = (channels[0].get("alternatives") or []) if channels else []
    best = alternatives[0] if alternatives else {}

    duration = (body.get("metadata") or {}).get("duration")

    return Transcript(
        text=(best.get("transcript") or "").strip(),
        # Deepgram reports 0.0 for silence, which is meaningfully different
        # from not reporting confidence at all -- so only absence becomes None.
        confidence=best.get("confidence"),
        provider="deepgram",
        duration_ms=int(float(duration) * 1000) if duration is not None else latency_ms,
        is_partial=False,
    )
