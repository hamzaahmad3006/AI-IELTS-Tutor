"""Smoke test: Deepgram and ElevenLabs adapters.

Run against a stubbed HTTP transport rather than the real services. That is not
a compromise: it lets the tests assert things a live call cannot, such as "the
second synthesis of the same text sends no request at all", and it means the
suite never spends anyone's quota — which on this project has already happened
twice with a different provider.

What these cannot prove is that the request shape is the one the provider
actually accepts. That needs one live call each, documented in the PR.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_voice.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import httpx  # noqa: E402

from ai.voice import SpeechToText, TextToSpeech  # noqa: E402
from ai.voice_providers.deepgram_stt import (  # noqa: E402
    DeepgramSpeechToText,
    _parse,
)
from ai.voice_providers.elevenlabs_tts import (  # noqa: E402
    ElevenLabsTextToSpeech,
    SpendLimitExceeded,
    UsageLedger,
)

DEEPGRAM_OK = {
    "metadata": {"duration": 6.5},
    "results": {
        "channels": [
            {
                "alternatives": [
                    {
                        "transcript": "I live in Lahore, um, in the north of the city.",
                        "confidence": 0.97,
                    }
                ]
            }
        ]
    },
}

MP3 = b"ID3\x04\x00\x00\x00fake-mp3-bytes"


def _stub(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


def _patch_client(monkeypatched_transport):
    """Force httpx.AsyncClient to use our transport, whatever the adapter passes."""
    original = httpx.AsyncClient.__init__

    def patched(self, *args, **kwargs):
        kwargs["transport"] = monkeypatched_transport
        original(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = patched
    return original


def _restore(original) -> None:
    httpx.AsyncClient.__init__ = original


# ---------- Deepgram ----------
def check_deepgram_parsing() -> None:
    """The response shape is deeply nested and every level is optional."""
    ok = _parse(DEEPGRAM_OK, latency_ms=100)
    assert ok.text == "I live in Lahore, um, in the north of the city."
    assert ok.confidence == 0.97
    assert ok.provider == "deepgram"
    assert ok.duration_ms == 6500  # from metadata, not the request latency
    assert ok.is_partial is False

    # Filler words survive. They are evidence for Fluency and Coherence, so
    # stripping them would inflate the score for exactly the candidates who
    # need to hear about hesitation.
    assert "um" in ok.text

    # A silent recording recognises nothing. That is a real outcome and must
    # come back as empty text, not a KeyError.
    for empty in (
        {},
        {"results": {}},
        {"results": {"channels": []}},
        {"results": {"channels": [{"alternatives": []}]}},
        {"results": {"channels": [{"alternatives": [{}]}]}},
    ):
        parsed = _parse(empty, latency_ms=50)
        assert parsed.text == "", empty
        assert parsed.duration_ms == 50, "fell back to latency when duration absent"

    # Absent confidence is None, not zero: "not reported" and "reported as
    # certainly nothing" must not render the same way.
    assert _parse({"results": {"channels": [{"alternatives": [{}]}]}}, latency_ms=1).confidence is None
    silent = {"results": {"channels": [{"alternatives": [{"transcript": "", "confidence": 0.0}]}]}}
    assert _parse(silent, latency_ms=1).confidence == 0.0


async def check_deepgram_request() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("Authorization")
        seen["content_type"] = request.headers.get("Content-Type")
        seen["body"] = request.content
        return httpx.Response(200, json=DEEPGRAM_OK)

    original = _patch_client(_stub(handler))
    try:
        stt = DeepgramSpeechToText(api_key="dg-test-key")
        assert isinstance(stt, SpeechToText)

        result = await stt.transcribe(b"RIFFfake-wav", mime_type="audio/wav")
        assert result.text.startswith("I live in Lahore")

        assert "api.deepgram.com" in str(seen["url"])
        assert seen["auth"] == "Token dg-test-key"
        # The audio's own type, not a hardcoded one: the recorder decides the
        # container and Deepgram needs to be told which it is.
        assert seen["content_type"] == "audio/wav"
        assert seen["body"] == b"RIFFfake-wav"
        # Punctuation matters beyond readability -- the scorer reads sentence
        # structure, and an unpunctuated wall of words reads as worse grammar.
        assert "smart_format=true" in str(seen["url"])
        assert "filler_words=true" in str(seen["url"])
    finally:
        _restore(original)

    # An empty upload is a client bug; paying an API to confirm that is silly.
    stt = DeepgramSpeechToText(api_key="k")
    try:
        await stt.transcribe(b"", mime_type="audio/wav")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("empty audio was sent to the provider")

    try:
        DeepgramSpeechToText(api_key="")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a keyless provider was constructed")


# ---------- ElevenLabs ----------
async def check_elevenlabs_cache(cache_dir: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=MP3)

    original = _patch_client(_stub(handler))
    try:
        tts = ElevenLabsTextToSpeech(
            api_key="el-test-key", cache_dir=cache_dir, monthly_character_limit=0
        )
        assert isinstance(tts, TextToSpeech)

        first = await tts.synthesize("Where do you live?")
        assert first.audio == MP3
        assert first.provider == "elevenlabs"
        assert calls["n"] == 1

        # The whole point: the question bank is fixed, so the same question is
        # paid for once and every later exam gets it free.
        second = await tts.synthesize("Where do you live?")
        assert second.audio == MP3
        assert second.provider == "elevenlabs:cache"
        assert calls["n"] == 1, "a cached question was re-synthesised"

        # Different text is a different entry.
        await tts.synthesize("Do you work or study?")
        assert calls["n"] == 2

        # A different voice is different audio, so it must not hit the cache
        # of the old one -- otherwise changing voice would appear to do nothing.
        await tts.synthesize("Where do you live?", voice="other-voice-id")
        assert calls["n"] == 3
    finally:
        _restore(original)


async def check_elevenlabs_ceiling(cache_dir: Path) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        payload = json.loads(request.content)
        assert payload["text"], "empty text reached the provider"
        assert request.headers.get("xi-api-key") == "el-test-key"
        return httpx.Response(200, content=MP3)

    original = _patch_client(_stub(handler))
    try:
        tts = ElevenLabsTextToSpeech(
            api_key="el-test-key", cache_dir=cache_dir, monthly_character_limit=30
        )
        assert tts.remaining_characters() == 30

        await tts.synthesize("a" * 20)
        assert calls["n"] == 1
        assert tts.remaining_characters() == 10

        # Refused before the request, not after. Counting afterwards is a
        # receipt, not a limit.
        try:
            await tts.synthesize("b" * 20)
        except SpendLimitExceeded as exc:
            assert "monthly limit" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("the ceiling did not stop the call")
        assert calls["n"] == 1, "a request was sent despite the ceiling"

        # A cache hit costs nothing, so the ceiling must not block it.
        cached = await tts.synthesize("a" * 20)
        assert cached.provider == "elevenlabs:cache"
        assert calls["n"] == 1

        # The ledger survives a restart, or the limit resets on every deploy.
        reopened = ElevenLabsTextToSpeech(
            api_key="el-test-key", cache_dir=cache_dir, monthly_character_limit=30
        )
        assert reopened.remaining_characters() == 10
    finally:
        _restore(original)

    # A failed call must not be charged, or an outage ratchets the limit down.
    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="upstream on fire")

    original = _patch_client(_stub(failing))
    try:
        tts = ElevenLabsTextToSpeech(
            api_key="el-test-key", cache_dir=cache_dir, monthly_character_limit=30
        )
        before = tts.remaining_characters()
        try:
            await tts.synthesize("c" * 5)
        except httpx.HTTPStatusError:
            pass
        assert tts.remaining_characters() == before, "a failed call was billed"
    finally:
        _restore(original)


def check_ledger(tmp: Path) -> None:
    ledger = UsageLedger(tmp / "usage.json")
    assert ledger.spent() == 0
    ledger.add(100)
    assert ledger.spent() == 100
    ledger.add(50)
    assert ledger.spent() == 150

    # A corrupt ledger must not read as "nothing spent", which would silently
    # switch the ceiling off.
    (tmp / "usage.json").write_text("{not json", encoding="utf-8")
    assert ledger.spent() == 0
    ledger.add(10)
    assert ledger.spent() == 10


def check_no_key_means_mock() -> None:
    """Without a key, the factory hands back mocks rather than failing later.

    This is the guard that keeps a misconfigured deployment from billing, and
    keeps every other test suite offline.
    """
    from ai.voice_providers import build_stt, build_tts

    assert build_stt().name == "mock"
    assert build_tts().name == "mock"

    try:
        ElevenLabsTextToSpeech(api_key="", cache_dir=Path("."))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a keyless TTS provider was constructed")


def run() -> None:
    check_deepgram_parsing()
    asyncio.run(check_deepgram_request())

    with tempfile.TemporaryDirectory() as tmp:
        asyncio.run(check_elevenlabs_cache(Path(tmp) / "cache"))
    with tempfile.TemporaryDirectory() as tmp:
        asyncio.run(check_elevenlabs_ceiling(Path(tmp) / "cache"))
    with tempfile.TemporaryDirectory() as tmp:
        check_ledger(Path(tmp))

    check_no_key_means_mock()

    print("VOICE PROVIDERS SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
