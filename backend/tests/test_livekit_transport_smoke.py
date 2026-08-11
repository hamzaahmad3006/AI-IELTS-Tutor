"""Smoke test: the LiveKit implementation of RoomTransport.

WebRTC itself cannot be tested here -- ICE, DTLS and Opus need a network and a
peer. What can be tested is everything that decides *what bytes go into* the
audio source, and that is where the failures that reach a candidate's ears
live:

  - compressed audio published as though it were PCM plays as a burst of noise
    at full volume, and does not raise;
  - stereo published as mono plays at double speed;
  - a wrong sample rate plays the examiner at the wrong pitch;
  - a short final frame is rejected, clipping the last syllable of every
    utterance.

None of those announce themselves as errors, so each is pinned below. The
transport class is exercised against a fake source and room, which is the same
trick the agent's own tests use.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import sys
import wave
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_livekit_transport.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from core.turn_taking import Event, Observation  # noqa: E402
from voice.agent import RoomTransport  # noqa: E402
from voice.livekit_transport import (  # noqa: E402
    FRAME_MS,
    PUBLISH_SAMPLE_RATE,
    STATE_TOPIC,
    AudioFormatError,
    LiveKitRoomTransport,
    frame_chunks,
    parse_rate,
    samples_per_frame,
    to_mono,
    to_pcm,
)


def _wav(pcm: bytes, *, rate: int = 16_000, channels: int = 1, width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    return buffer.getvalue()


def check_rate_is_read_from_the_mime_type() -> None:
    """Raw PCM has no header, so the rate travels beside it or is guessed."""
    assert parse_rate("audio/pcm;rate=24000") == 24_000
    assert parse_rate("audio/pcm; rate=8000") == 8_000
    # No rate given falls back to what we publish at, rather than to zero --
    # which would be a division by zero when framing.
    assert parse_rate("audio/pcm") == PUBLISH_SAMPLE_RATE
    assert parse_rate("") == PUBLISH_SAMPLE_RATE


def check_supported_formats() -> None:
    pcm = b"\x01\x02" * 100

    # Raw PCM passes through with the rate from the mime type.
    assert to_pcm(pcm, "audio/pcm;rate=24000") == (pcm, 24_000, 1)

    # WAV is unwrapped by the standard library, rate read from the header.
    data, rate, channels = to_pcm(_wav(pcm, rate=22_050), "audio/wav")
    assert data == pcm
    assert rate == 22_050
    assert channels == 1

    # The mock TTS returns an empty body with a duration. Legitimate, and
    # `wave` would raise on it.
    assert to_pcm(b"", "audio/wav") == (b"", PUBLISH_SAMPLE_RATE, 1)


def check_undecodable_audio_is_refused_loudly() -> None:
    """The most dangerous case, because passing it through does not raise.

    MP3 bytes handed to an audio source are played as though they were PCM:
    full-volume noise, into a candidate's headphones, mid-exam.
    """
    for mime in ("audio/mpeg", "audio/mp3", "audio/ogg", "audio/aac"):
        try:
            to_pcm(b"\xff\xfb\x90\x00" * 50, mime)
        except AudioFormatError as error:
            # The message has to say what to do about it, not just that it
            # failed -- the fix is a configuration change.
            assert "pcm_16000" in str(error), mime
        else:  # pragma: no cover
            raise AssertionError(f"accepted undecodable {mime}")

    # 8-bit WAV would play as noise for the same reason.
    try:
        to_pcm(_wav(b"\x01" * 100, width=1), "audio/wav")
    except AudioFormatError as error:
        assert "16-bit" in str(error)
    else:  # pragma: no cover
        raise AssertionError("accepted 8-bit WAV")

    try:
        to_pcm(b"not a wav at all", "audio/wav")
    except AudioFormatError:
        pass
    else:  # pragma: no cover
        raise AssertionError("accepted a corrupt WAV")


def check_stereo_is_mixed_not_reinterpreted() -> None:
    """Stereo taken as mono plays at double speed."""
    # Left = 100, right = 200 for two frames.
    stereo = b"".join(
        value.to_bytes(2, "little", signed=True) for value in (100, 200, 300, 400)
    )
    mono = to_mono(stereo, 2)

    assert len(mono) == len(stereo) // 2
    values = [
        int.from_bytes(mono[i : i + 2], "little", signed=True)
        for i in range(0, len(mono), 2)
    ]
    assert values == [150, 350]

    # Mono passes straight through, and an odd trailing byte does not raise on
    # audio that is merely truncated.
    assert to_mono(b"\x01\x02", 1) == b"\x01\x02"
    assert to_mono(b"", 2) == b""
    assert to_mono(b"\x01\x02\x03", 2) == b""


def check_framing_is_exact_and_padded() -> None:
    """A short final frame is rejected by the source, clipping every utterance."""
    rate = 16_000
    bytes_per_frame = int(rate * FRAME_MS / 1000) * 2  # 320 bytes at 16 kHz
    assert samples_per_frame(rate) == 160

    # Two and a bit frames.
    pcm = b"\x00\x01" * (160 + 160 + 40)
    chunks = list(frame_chunks(pcm, sample_rate=rate))

    assert len(chunks) == 3
    assert all(len(chunk) == bytes_per_frame for chunk in chunks), [
        len(c) for c in chunks
    ]
    # The tail is padded with silence rather than dropped: truncating clips the
    # last syllable of everything the examiner says.
    assert chunks[2].endswith(b"\x00" * 100)
    # And no audio is lost in the process.
    assert b"".join(chunks)[: len(pcm)] == pcm

    assert list(frame_chunks(b"", sample_rate=rate)) == []

    try:
        list(frame_chunks(b"\x00" * 10, sample_rate=0))
    except AudioFormatError:
        pass
    else:  # pragma: no cover
        raise AssertionError("accepted a zero sample rate")


# --------------------------------------------------------------------------
# The transport, against fakes
# --------------------------------------------------------------------------


class FakeSource:
    def __init__(self) -> None:
        self.frames: list[object] = []
        self.cleared = 0

    async def capture_frame(self, frame: object) -> None:
        self.frames.append(frame)

    def clear_queue(self) -> None:
        self.cleared += 1


class FakeParticipant:
    def __init__(self) -> None:
        self.published: list[tuple[bytes, str]] = []
        self.fail = False

    async def publish_data(self, payload: bytes, *, reliable: bool = True, topic: str = "") -> None:
        if self.fail:
            raise ConnectionError("data channel closed")
        self.published.append((payload, topic))


class FakeRoom:
    def __init__(self) -> None:
        self.local_participant = FakeParticipant()


def _transport() -> tuple[LiveKitRoomTransport, FakeSource, FakeRoom]:
    source = FakeSource()
    room = FakeRoom()
    return LiveKitRoomTransport(room=room, audio_source=source), source, room


async def check_playback_emits_steady_frames() -> None:
    transport, source, _ = _transport()

    # 100 ms of 16 kHz mono = 10 frames.
    pcm = b"\x00\x01" * (160 * 10)
    await transport.play(pcm, "audio/pcm;rate=16000")

    assert len(source.frames) == 10
    for frame in source.frames:
        assert frame.sample_rate == 16_000
        assert frame.num_channels == 1
        assert frame.samples_per_channel == 160

    # Empty audio is a no-op rather than an error: the mock TTS produces it.
    await transport.play(b"", "audio/wav")
    assert len(source.frames) == 10


async def check_barge_in_stops_mid_utterance() -> None:
    """Finishing the buffer would talk over the candidate."""
    transport, source, _ = _transport()
    pcm = b"\x00\x01" * (160 * 200)  # 2 seconds

    async def interrupt() -> None:
        while len(source.frames) < 5:
            await asyncio.sleep(0)
        await transport.stop_playback()

    await asyncio.gather(transport.play(pcm, "audio/pcm;rate=16000"), interrupt())

    assert len(source.frames) < 200, "playback ran to completion despite barge-in"
    # The source buffers ahead, so the flag alone is not enough -- the queue
    # has to be dropped or the examiner keeps talking.
    assert source.cleared == 1


async def check_state_is_published_and_failures_are_swallowed() -> None:
    transport, _, room = _transport()

    await transport.send_state({"phase": "part2", "remainingMs": 90_000})
    assert len(room.local_participant.published) == 1
    payload, topic = room.local_participant.published[0]
    assert json.loads(payload) == {"phase": "part2", "remainingMs": 90_000}
    # Topic-tagged so a client can filter rather than parse every message to
    # find out whether it cared.
    assert topic == STATE_TOPIC

    # A dropped progress update must not end an exam that is otherwise fine.
    room.local_participant.fail = True
    await transport.send_state({"phase": "part3"})


async def check_turn_boundaries_discard_stale_audio() -> None:
    transport, _, _ = _transport()

    transport.add_transcript("I think that")
    transport.add_transcript("  cities are  ")
    assert await transport.transcript_so_far() == "I think that cities are"

    # Observations queued while the examiner was speaking are echo or the tail
    # of the previous answer. Carried forward they land at the front of the
    # next answer.
    transport.observation_queue.put_nowait(
        Observation(event=Event.SPEECH_STARTED, at_ms=10)
    )
    transport.observation_queue.put_nowait(
        Observation(event=Event.FINAL_TRANSCRIPT, at_ms=90, text="stale echo")
    )

    await transport.begin_turn()

    assert transport.observation_queue.empty()
    assert await transport.transcript_so_far() == ""

    # Blank segments are dropped rather than joined into double spaces.
    transport.add_transcript("   ")
    transport.add_transcript("")
    assert await transport.transcript_so_far() == ""


async def check_observations_stream() -> None:
    transport, _, _ = _transport()
    transport.observation_queue.put_nowait(
        Observation(event=Event.SPEECH_STARTED, at_ms=0)
    )
    transport.observation_queue.put_nowait(
        Observation(event=Event.SPEECH_ENDED, at_ms=800)
    )

    stream = transport.observations()
    first = await asyncio.wait_for(stream.__anext__(), timeout=1)
    second = await asyncio.wait_for(stream.__anext__(), timeout=1)
    assert first.event is Event.SPEECH_STARTED
    assert second.event is Event.SPEECH_ENDED
    assert second.at_ms == 800


def check_it_satisfies_the_port() -> None:
    """Interchangeable with the agent's fake, or the agent cannot use it."""
    transport, _, _ = _transport()
    assert isinstance(transport, RoomTransport)


def run() -> None:
    check_rate_is_read_from_the_mime_type()
    check_supported_formats()
    check_undecodable_audio_is_refused_loudly()
    check_stereo_is_mixed_not_reinterpreted()
    check_framing_is_exact_and_padded()
    check_it_satisfies_the_port()

    asyncio.run(check_playback_emits_steady_frames())
    asyncio.run(check_barge_in_stops_mid_utterance())
    asyncio.run(check_state_is_published_and_failures_are_swallowed())
    asyncio.run(check_turn_boundaries_discard_stale_audio())
    asyncio.run(check_observations_stream())

    print("LIVEKIT TRANSPORT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
