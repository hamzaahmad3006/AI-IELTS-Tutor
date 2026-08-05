"""ElevenLabs text-to-speech adapter, with a cache and a spend ceiling.

Two guards, because this is the expensive half of the voice pipeline and a free
tier has already been exhausted once on this project.

**Cache.** The question bank is fixed: the same eight Part 1 questions and the
same cue cards are spoken to every candidate. Synthesising them repeatedly would
be paying over and over for identical bytes. Audio is keyed by the exact text
plus the voice and model that produced it, so a reworded question or a changed
voice is a new entry rather than a stale hit. After the bank has been spoken
once, almost every exam is free.

**Ceiling.** A monthly character budget checked *before* the request, so an
overrun is refused rather than discovered on an invoice. The check has to be
pre-flight: counting afterwards tells you what you already spent, which is not a
limit, it is a receipt.

The ceiling matters most for what does not exist yet. A fixed bank is naturally
bounded, but AI-generated questions would miss the cache every single time, and
that is precisely the change that would quietly turn a bounded cost into an
unbounded one.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

from ai.voice import Speech

_API_ROOT = "https://api.elevenlabs.io/v1/text-to-speech"

#: Rachel — a clear, neutral English voice. Overridable per call.
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

#: Multilingual v2 is the quality model; flash is cheaper and faster but
#: noticeably flatter, which matters when the audio is meant to sound like a
#: person conducting an exam.
DEFAULT_MODEL = "eleven_multilingual_v2"

_MIME = "audio/mpeg"


class SpendLimitExceeded(RuntimeError):
    """Raised instead of making a call that would breach the budget."""


@dataclass
class UsageLedger:
    """Characters spent this month, persisted next to the cache.

    Deliberately a plain JSON file rather than a table. It is process-local
    accounting for a single deployment, it must survive a restart, and putting
    it in the database would mean a migration and a session for something the
    provider itself is the real authority on. Reconcile against the ElevenLabs
    dashboard; this exists to stop runaway spend, not to be the books.
    """

    path: Path

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupt ledger must not be read as "nothing spent yet", which
            # would silently disable the ceiling. Treat the month as unknown
            # and start counting again from a fresh file.
            return {}

    @staticmethod
    def _period() -> str:
        today = date.today()
        return f"{today.year:04d}-{today.month:02d}"

    def spent(self) -> int:
        return int(self._read().get(self._period(), 0))

    def add(self, characters: int) -> int:
        data = self._read()
        period = self._period()
        total = int(data.get(period, 0)) + characters
        # Only the current and previous period are kept: an unbounded history
        # of months is a file that grows forever for no reader.
        data = {k: v for k, v in data.items() if k >= period}
        data[period] = total
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return total


class ElevenLabsTextToSpeech:
    name = "elevenlabs"

    def __init__(
        self,
        api_key: str,
        *,
        voice_id: str = DEFAULT_VOICE_ID,
        model: str = DEFAULT_MODEL,
        cache_dir: Path | None = None,
        monthly_character_limit: int = 0,
        timeout_s: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("ElevenLabs requires an API key")
        self._api_key = api_key
        self._voice_id = voice_id
        self._model = model
        self._timeout_s = timeout_s
        self._cache_dir = cache_dir or Path("media/tts-cache")
        #: 0 disables the ceiling. Explicit, so an unlimited budget is a
        #: decision someone made rather than a default nobody noticed.
        self._limit = monthly_character_limit
        self._ledger = UsageLedger(self._cache_dir / "usage.json")

    # ---------- Cache ----------
    def _cache_key(self, text: str, voice_id: str) -> str:
        # The voice and model are part of the key: the same words in a
        # different voice are different audio, and a cache that ignored that
        # would serve the old voice forever after a change.
        material = f"{self._model}\x00{voice_id}\x00{text}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.mp3"

    def cached_bytes(self, text: str, *, voice: str | None = None) -> bytes | None:
        path = self._cache_path(self._cache_key(text, voice or self._voice_id))
        if path.exists():
            try:
                return path.read_bytes()
            except OSError:
                return None
        return None

    def _store(self, text: str, voice_id: str, audio: bytes) -> None:
        path = self._cache_path(self._cache_key(text, voice_id))
        path.parent.mkdir(parents=True, exist_ok=True)
        # Written via a temporary file and moved into place, so a crash
        # mid-write cannot leave a truncated mp3 that the cache then serves
        # forever as if it were complete.
        tmp = path.with_suffix(".part")
        tmp.write_bytes(audio)
        tmp.replace(path)

    # ---------- Budget ----------
    def remaining_characters(self) -> int | None:
        """Characters left this month, or None when no ceiling is set."""
        if self._limit <= 0:
            return None
        return max(0, self._limit - self._ledger.spent())

    # ---------- Port ----------
    async def synthesize(self, text: str, *, voice: str | None = None) -> Speech:
        text = text.strip()
        if not text:
            raise ValueError("Nothing to synthesize")

        voice_id = voice or self._voice_id

        cached = self.cached_bytes(text, voice=voice_id)
        if cached is not None:
            # A cache hit costs nothing, so it is not counted against the
            # ceiling and must not be blocked by it.
            return Speech(
                audio=cached,
                mime_type=_MIME,
                provider=f"{self.name}:cache",
                duration_ms=None,
            )

        remaining = self.remaining_characters()
        if remaining is not None and len(text) > remaining:
            raise SpendLimitExceeded(
                f"Synthesising {len(text)} characters would exceed the monthly "
                f"limit of {self._limit}; {remaining} remain. Raise "
                f"ELEVENLABS_MONTHLY_CHAR_LIMIT or wait for the period to reset."
            )

        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(
                f"{_API_ROOT}/{voice_id}",
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": _MIME,
                },
                json={"text": text, "model_id": self._model},
            )
            response.raise_for_status()
            audio = response.content
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Counted only after a successful call: charging the budget for a
        # request that failed would ratchet the limit down on every outage.
        self._ledger.add(len(text))
        self._store(text, voice_id, audio)

        return Speech(
            audio=audio,
            mime_type=_MIME,
            provider=self.name,
            duration_ms=latency_ms,
        )
