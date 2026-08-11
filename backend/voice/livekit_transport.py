"""LiveKit implementation of `RoomTransport`.

The agent's port was written so this file could stay thin, and it is: joining a
room means WebRTC -- ICE, DTLS, SRTP, Opus -- which is native code that cannot
be exercised in a unit test. So everything that can be decided without a
network lives in the pure functions at the top, is tested directly, and the
class below is left as glue.

Two things are worth knowing before reading it.

**WebRTC carries PCM, not files.** `RoomTransport.play` receives whatever the
TTS produced, and the two providers disagree: the streaming ElevenLabs path
emits `pcm_16000`, which is exactly right, while the batch path emits MP3,
which cannot be decoded here without pulling in a native decoder. So WAV and
raw PCM are handled and MP3 is refused loudly. Refusing is the point -- an MP3
pushed into an audio source as though it were PCM does not error, it plays a
burst of noise into a candidate's ear during their exam.

**Frames are fixed-size.** An `AudioSource` expects a steady 10 ms cadence.
Handing it whatever length the synthesiser happened to return produces
stuttering that sounds like a bad connection, so audio is re-chunked here and
the tail is padded with silence rather than sent short.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import re
import sys
import wave
from array import array
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field

from core.turn_taking import Observation

logger = logging.getLogger("voice.livekit")

#: WebRTC's native cadence. Anything else is re-chunked to it.
FRAME_MS = 10

#: What the agent publishes as. One track, mono, matching the streaming TTS
#: rate so the common path needs no resampling at all.
PUBLISH_SAMPLE_RATE = 16_000
PUBLISH_CHANNELS = 1

TRACK_NAME = "examiner"
#: Data-channel topic for exam state. Named so a client can filter rather than
#: parsing every message to find out whether it cared.
STATE_TOPIC = "exam-state"


class AudioFormatError(ValueError):
    """The audio cannot be published as PCM."""


def parse_rate(mime_type: str, default: int = PUBLISH_SAMPLE_RATE) -> int:
    """Pull the sample rate out of a mime type like `audio/pcm;rate=16000`.

    Raw PCM carries no header, so the rate has to travel beside it. Guessing
    wrong does not fail -- it plays the examiner back at the wrong pitch and
    speed, which is the kind of bug that gets described as "it sounds weird".
    """
    match = re.search(r"rate=(\d+)", mime_type or "")
    return int(match.group(1)) if match else default


def to_pcm(audio: bytes, mime_type: str) -> tuple[bytes, int, int]:
    """Normalise synthesised audio to (pcm_s16le, sample_rate, channels).

    Only formats that can be decoded with the standard library are accepted.
    Anything else raises rather than being passed through, because passing
    compressed bytes to an audio source is silent corruption: it plays as
    noise, at full volume, into somebody's headphones.
    """
    kind = (mime_type or "").split(";")[0].strip().lower()

    if kind in ("audio/pcm", "audio/l16", "audio/x-pcm", ""):
        return audio, parse_rate(mime_type), PUBLISH_CHANNELS

    if kind in ("audio/wav", "audio/x-wav", "audio/wave"):
        if not audio:
            # The mock TTS returns an empty body with a duration. Legitimate,
            # and `wave` would raise on it.
            return b"", PUBLISH_SAMPLE_RATE, PUBLISH_CHANNELS
        try:
            with contextlib.closing(wave.open(io.BytesIO(audio), "rb")) as handle:
                if handle.getsampwidth() != 2:
                    raise AudioFormatError(
                        f"WAV must be 16-bit PCM, got {handle.getsampwidth() * 8}-bit"
                    )
                frames = handle.readframes(handle.getnframes())
                return frames, handle.getframerate(), handle.getnchannels()
        except wave.Error as error:
            raise AudioFormatError(f"Unreadable WAV: {error}") from error

    raise AudioFormatError(
        f"Cannot publish {kind!r} over WebRTC without a native decoder. "
        "Configure the streaming TTS path, which emits pcm_16000."
    )


def to_mono(pcm: bytes, channels: int) -> bytes:
    """Average interleaved channels down to one.

    Publishing stereo as if it were mono without mixing plays back at double
    speed, which is a strange enough symptom to lose an afternoon to.

    Done by hand rather than with `audioop`, which was removed in Python 3.13
    and would have been an import error on this interpreter rather than a
    fallback.
    """
    if channels <= 1 or not pcm:
        return pcm

    samples = array("h")
    # A trailing odd byte would make frombytes raise; drop it rather than fail
    # on audio that is merely truncated.
    samples.frombytes(pcm[: len(pcm) - (len(pcm) % (2 * channels))])
    if sys.byteorder == "big":
        # PCM on the wire is little-endian; array uses native order.
        samples.byteswap()

    mixed = array(
        "h",
        [
            # Summed as Python ints before dividing, so the intermediate
            # cannot overflow the 16-bit range the way it would in place.
            sum(samples[index : index + channels]) // channels
            for index in range(0, len(samples), channels)
        ],
    )
    if sys.byteorder == "big":
        mixed.byteswap()
    return mixed.tobytes()


def frame_chunks(
    pcm: bytes, *, sample_rate: int, channels: int = 1, frame_ms: int = FRAME_MS
) -> Iterator[bytes]:
    """Split PCM into fixed frames, padding the tail with silence.

    Padded rather than truncated: dropping the tail clips the last syllable of
    every utterance, and a partial frame is rejected by the source outright.
    """
    if not pcm:
        return
    bytes_per_frame = int(sample_rate * frame_ms / 1000) * channels * 2
    if bytes_per_frame <= 0:
        raise AudioFormatError(f"Nonsensical sample rate: {sample_rate}")

    for start in range(0, len(pcm), bytes_per_frame):
        chunk = pcm[start : start + bytes_per_frame]
        if len(chunk) < bytes_per_frame:
            chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))
        yield chunk


def samples_per_frame(sample_rate: int, frame_ms: int = FRAME_MS) -> int:
    return int(sample_rate * frame_ms / 1000)


@dataclass
class LiveKitRoomTransport:
    """Moves audio between the examiner agent and a LiveKit room.

    Constructed with the room and the pieces it needs rather than building
    them, so the agent's tests keep using their fake and this stays glue.
    """

    room: object
    audio_source: object
    #: Feeds turn-taking. Owned by whoever wired up the STT stream, because
    #: transcription is not this class's job.
    observation_queue: "asyncio.Queue[Observation]" = field(
        default_factory=asyncio.Queue
    )

    sample_rate: int = PUBLISH_SAMPLE_RATE
    channels: int = PUBLISH_CHANNELS

    _transcript: list[str] = field(default_factory=list, init=False)
    _playing: asyncio.Task | None = field(default=None, init=False)
    _stopped: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    # -- outbound ----------------------------------------------------------

    async def play(self, audio: bytes, mime_type: str) -> None:
        """Publish audio, returning when it has finished or been cut."""
        pcm, rate, channels = to_pcm(audio, mime_type)
        pcm = to_mono(pcm, channels)
        if not pcm:
            return

        self._stopped.clear()
        self._playing = asyncio.current_task()
        try:
            await self._capture(pcm, rate)
        finally:
            self._playing = None

    async def _capture(self, pcm: bytes, rate: int) -> None:
        from livekit import rtc  # noqa: PLC0415 - native import, kept off module load

        per_frame = samples_per_frame(rate)
        for chunk in frame_chunks(pcm, sample_rate=rate, channels=1):
            if self._stopped.is_set():
                # Barge-in. Stopping mid-utterance is the whole point of
                # interruptible playback; finishing the buffer would talk over
                # the candidate for as long as the queue is deep.
                return

            # Yield before capturing, every frame. `capture_frame` only awaits
            # once the source's queue is full -- a second of audio by default --
            # so a whole second of frames can be pushed without the event loop
            # ever getting a turn, and `stop_playback` cannot be processed in
            # that window. For an examiner that is supposed to stop the moment
            # the candidate speaks, a second is the difference between
            # interruptible and not.
            await asyncio.sleep(0)

            await self.audio_source.capture_frame(
                rtc.AudioFrame(
                    data=chunk,
                    sample_rate=rate,
                    num_channels=1,
                    samples_per_channel=per_frame,
                )
            )

    async def stop_playback(self) -> None:
        """Cut playback now. Called on barge-in, so it must not block."""
        self._stopped.set()
        # The source buffers up to a second by default; without clearing it the
        # examiner keeps talking after the flag is set.
        clear = getattr(self.audio_source, "clear_queue", None)
        if clear is not None:
            result = clear()
            if asyncio.iscoroutine(result):
                await result

    async def send_state(self, payload: dict) -> None:
        """Push exam state to the client over the data channel.

        Failures are logged, never raised: a dropped progress update must not
        end an exam that is otherwise working.
        """
        try:
            await self.room.local_participant.publish_data(
                json.dumps(payload).encode("utf-8"),
                reliable=True,
                topic=STATE_TOPIC,
            )
        except Exception:  # noqa: BLE001 - see docstring
            logger.warning("could not publish exam state", exc_info=True)

    # -- inbound -----------------------------------------------------------

    async def begin_turn(self) -> None:
        self._transcript.clear()
        self._stopped.clear()
        # Anything queued during the examiner's own turn is stale: it is the
        # tail of the previous answer, or echo. Carried forward it lands at the
        # front of the next answer's transcript.
        while not self.observation_queue.empty():
            self.observation_queue.get_nowait()

    async def observations(self) -> AsyncIterator[Observation]:
        while True:
            yield await self.observation_queue.get()

    async def transcript_so_far(self) -> str:
        return " ".join(part for part in self._transcript if part).strip()

    def add_transcript(self, text: str) -> None:
        """Append a finalised STT segment. Called by whatever drives the STT."""
        if text and text.strip():
            self._transcript.append(text.strip())


async def build_transport(
    url: str, token: str, *, room: object | None = None
) -> LiveKitRoomTransport:
    """Connect to a room and publish the examiner's track.

    Separated from the class so the class needs no network to construct, which
    is what lets the tests cover it at all.
    """
    from livekit import rtc  # noqa: PLC0415 - native import

    room = room or rtc.Room()
    await room.connect(url, token)

    source = rtc.AudioSource(PUBLISH_SAMPLE_RATE, PUBLISH_CHANNELS)
    track = rtc.LocalAudioTrack.create_audio_track(TRACK_NAME, source)
    await room.local_participant.publish_track(track)

    return LiveKitRoomTransport(room=room, audio_source=source)
