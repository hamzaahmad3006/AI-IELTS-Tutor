"""The agent worker: what actually holds a live interview.

This is the piece that was missing. Every part of the pipeline existed and was
tested -- the room transport, the turn detector, the STT and TTS adapters, the
LLM port -- and nothing joined them up, so no audio ever moved. `build_transport`
was called only from tests and `ExaminerAgent.run()` was never called at all.

The loop:

    candidate's microphone
      -> LiveKit audio track (WebRTC)
      -> AudioStream frames, resampled to 16 kHz mono
      -> Deepgram streaming STT
      -> turn detector decides they have finished speaking
      -> LLM writes the next question from the transcript
      -> Deepgram Aura synthesises it as PCM
      -> published on the agent's own LiveKit track
      -> candidate's speaker

Run as a separate process rather than inside a request handler. A request that
lasts the length of an interview holds a worker for ten minutes, and an API
process that restarts mid-deploy would cut the candidate off mid-sentence.

    python -m voice.live_worker --room interview-abc123

Needs a LiveKit server: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import sys

from ai.providers import build_provider
from ai.voice_providers import build_stt, build_tts
from core.config import get_settings
from core.livekit import VideoGrant, mint_access_token
from voice.interviewer import LiveInterviewer
from voice.livekit_transport import (
    PUBLISH_CHANNELS,
    PUBLISH_SAMPLE_RATE,
    LiveKitRoomTransport,
)

logger = logging.getLogger("voice.worker")


END_OF_TURN_SILENCE_S = 2.0

MIN_ANSWER_CHARS = 2

IDENTITY = "ai-examiner"


async def _publish_state(transport: LiveKitRoomTransport, **payload: object) -> None:
    """Tell the client what is happening, so the UI is not a silent box."""
    await transport.send_state(payload)


async def _speak(transport: LiveKitRoomTransport, tts, text: str) -> None:
    """Synthesise and play one examiner turn."""
    await _publish_state(transport, speaking=True, text=text)
    speech = await tts.synthesize(text)
    if speech.audio:
        await transport.play(speech.audio, speech.mime_type)
    await _publish_state(transport, speaking=False, text=text)


async def run_interview(room_name: str) -> None:
    settings = get_settings()
    if not settings.livekit_enabled:
        raise SystemExit(
            "LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY and "
            "LIVEKIT_API_SECRET in backend/.env."
        )

    from livekit import rtc  # noqa: PLC0415 - native import, kept out of module load

    stt = build_stt()
    tts = build_tts()
    interviewer = LiveInterviewer(provider=build_provider())

    logger.info(
        "starting worker", extra={"room": room_name, "stt": stt.name, "tts": tts.name}
    )

    access = mint_access_token(
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        url=settings.livekit_url,
        room=room_name,
        identity=IDENTITY,
        name="AI Examiner",
        grant=VideoGrant(room=room_name, room_join=True, can_publish=True, can_subscribe=True),
    )

    room = rtc.Room()
    audio_source = rtc.AudioSource(PUBLISH_SAMPLE_RATE, PUBLISH_CHANNELS)
    transport = LiveKitRoomTransport(room=room, audio_source=audio_source)

    # The candidate's audio arrives on a track we have to wait for; this is
    # how the loop below knows there is someone to talk to.
    candidate_audio: asyncio.Queue = asyncio.Queue()

    @room.on("track_subscribed")
    def _on_track(track, publication, participant) -> None:  # noqa: ANN001
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("candidate audio subscribed", extra={"participant": participant.identity})
            candidate_audio.put_nowait(track)

    await room.connect(settings.livekit_url, access.token)
    track = rtc.LocalAudioTrack.create_audio_track("examiner", audio_source)
    await room.local_participant.publish_track(track)
    logger.info("worker joined", extra={"room": room_name})

    try:
        # Wait for the candidate before speaking, or the greeting is played to
        # an empty room and they join to silence.
        candidate_track = await asyncio.wait_for(candidate_audio.get(), timeout=120)

        await _speak(transport, tts, interviewer.opening())

        stream = rtc.AudioStream(
            candidate_track, sample_rate=PUBLISH_SAMPLE_RATE, num_channels=1
        )

        while not interviewer.is_finished:
            answer = await _listen(stream, stt, transport)
            if answer is None:
                break  # the candidate left

            interviewer.record_answer(answer)
            await _publish_state(transport, thinking=True, transcript=answer)

            question = await interviewer.next_question()
            await _speak(transport, tts, question)

        await _speak(transport, tts, interviewer.closing())
        await _publish_state(transport, finished=True)
    finally:
        with contextlib.suppress(Exception):
            await room.disconnect()
        logger.info("worker left", extra={"room": room_name})


async def _listen(stream, stt, transport: LiveKitRoomTransport) -> str | None:
    """Collect the candidate's next answer, ending on a pause.

    Buffered and transcribed in one call at the end of the turn rather than
    streamed word by word. Streaming STT would cut latency further, but the
    turn cannot end before they stop talking anyway, so the saving is smaller
    than it looks and a batch call is far easier to reason about when it fails.
    """
    await transport.begin_turn()
    await _publish_state(transport, listening=True)

    pcm = bytearray()
    silence_s = 0.0
    heard_anything = False

    async for event in stream:
        frame = event.frame
        data = bytes(frame.data)
        pcm.extend(data)

        # Frames are 16-bit mono here, so amplitude is a cheap proxy for
        # "someone is talking" and costs nothing next to a VAD model.
        loud = _peak(data) > 900
        seconds = len(data) / 2 / PUBLISH_SAMPLE_RATE

        if loud:
            heard_anything = True
            silence_s = 0.0
        else:
            silence_s += seconds

        if heard_anything and silence_s >= END_OF_TURN_SILENCE_S:
            break
        # A candidate who never speaks at all should not hang the interview.
        if not heard_anything and len(pcm) > PUBLISH_SAMPLE_RATE * 2 * 45:
            return ""

    if not pcm:
        return None

    await _publish_state(transport, listening=False, thinking=True)
    transcript = await stt.transcribe(
        _wav(bytes(pcm)), mime_type="audio/wav"
    )
    text = (transcript.text or "").strip()
    return text if len(text) >= MIN_ANSWER_CHARS else ""


def _peak(pcm: bytes) -> int:
    """Loudest sample in a frame, for the crude end-of-turn check."""
    if len(pcm) < 2:
        return 0
    peak = 0
    # Every 8th sample: enough to spot speech, an eighth of the work on a hot
    # path that runs every 10 ms.
    for index in range(0, len(pcm) - 1, 16):
        value = int.from_bytes(pcm[index : index + 2], "little", signed=True)
        peak = max(peak, abs(value))
    return peak


def _wav(pcm: bytes, rate: int = PUBLISH_SAMPLE_RATE) -> bytes:
    """Wrap raw PCM in a WAV header.

    The batch STT endpoint infers the format from the container. Raw PCM has
    no header, so without this the provider guesses the sample rate and
    transcribes a chipmunk.
    """
    import io  # noqa: PLC0415
    import wave  # noqa: PLC0415

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    return buffer.getvalue()


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    parser = argparse.ArgumentParser(description="Run the live AI examiner in a room.")
    parser.add_argument("--room", required=True, help="LiveKit room name to join")
    args = parser.parse_args()

    try:
        asyncio.run(run_interview(args.room))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
