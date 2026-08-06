"""The examiner agent: the loop that actually conducts a spoken interview.

Ties together four things that already exist and own their own rules:

* `core.interview` decides what the examiner says and when the exam moves on.
* `core.turn_taking` decides when the candidate has finished speaking.
* `ai.voice` synthesises the examiner and transcribes the candidate.
* A `RoomTransport` moves audio in and out.

The transport is an interface rather than LiveKit directly, and that is the
whole design. Joining a LiveKit room means WebRTC -- ICE, DTLS, SRTP, Opus --
which is a native dependency and cannot be exercised in a test. Everything
interesting about an examiner, though, is sequencing and timing, and that is
testable against a fake transport in milliseconds. So the untestable part is
pushed to the edge and kept as thin as it can be.

The loop is written so that a failure in any one turn does not end the exam. A
candidate twelve minutes into a speaking test should not lose it because one
synthesis call timed out.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ai.voice import SpeechToText, TextToSpeech
from core.interview import Action, ActionKind, Interview, Phase
from core.turn_taking import (
    Decision,
    Observation,
    TurnDetector,
    policy_for_phase,
)

#: How often the loop re-checks whether a silent candidate has finished. The
#: end of a turn is the absence of speech, which produces no event, so
#: something has to look.
TICK_MS = 100

#: A turn is abandoned after this long with the transport producing nothing at
#: all. Distinct from the turn-taking timeout: that one means "they stopped
#: talking", this one means "the audio pipeline is dead".
TRANSPORT_STALL_MS = 30_000


@runtime_checkable
class RoomTransport(Protocol):
    """Moves audio between the agent and the candidate.

    Narrow on purpose. A LiveKit implementation, a WebSocket one and the test
    fake all satisfy this, and none of the exam logic knows which it has.
    """

    async def play(self, audio: bytes, mime_type: str) -> None:
        """Play audio to the candidate. Returns when playback has finished."""

    async def stop_playback(self) -> None:
        """Cut playback immediately. Called on barge-in, so it must be fast."""

    def observations(self) -> AsyncIterator[Observation]:
        """Turn-taking events, as they happen."""

    async def transcript_so_far(self) -> str:
        """Everything the candidate has said in the current turn."""

    async def begin_turn(self) -> None:
        """Start listening. Resets whatever per-turn state the transport holds."""

    async def send_state(self, payload: dict) -> None:
        """Push exam state to the client -- phase, countdowns, progress."""


@dataclass
class TurnResult:
    text: str
    interrupted_examiner: bool
    ended_by: str


@dataclass
class ExaminerAgent:
    """Conducts one interview over one transport."""

    interview: Interview
    transport: RoomTransport
    tts: TextToSpeech
    #: Used only when the transport cannot transcribe for itself. A streaming
    #: transport does its own; a chunked one hands audio back here.
    stt: SpeechToText | None = None
    tick_ms: int = TICK_MS

    #: Turns that failed for a technical reason, so a session can be reviewed
    #: rather than silently containing gaps.
    failures: list[str] = field(default_factory=list)

    async def run(self) -> Interview:
        """Conduct the exam to completion.

        Returns the interview so the caller can score it. Errors in a single
        turn are recorded and the exam continues: losing a twelve-minute
        speaking test to one timed-out synthesis call would be worse than
        losing one answer.
        """
        while not self.interview.is_complete:
            action = self.interview.current_action()
            await self._announce(action)

            if action.kind is ActionKind.FINISH:
                break

            try:
                await self._speak(action)
            except Exception as exc:  # noqa: BLE001 - one turn, not the exam
                self.failures.append(f"{action.phase.value}: speak failed ({exc})")

            if action.kind is ActionKind.SAY:
                # Nothing is expected back; move on without opening a turn.
                self.interview.answer("")
                continue

            if action.kind is ActionKind.PREPARE:
                await self._wait_out_preparation(action)
                self.interview.answer("")
                continue

            try:
                result = await self._listen(action)
                self.interview.answer(result.text)
            except Exception as exc:  # noqa: BLE001
                self.failures.append(f"{action.phase.value}: listen failed ({exc})")
                # Advance anyway. A candidate stuck on one question of a timed
                # exam with no way forward is worse than one lost answer.
                self.interview.answer("")

        await self._announce(self.interview.current_action())
        return self.interview

    # ---------- Steps ----------
    async def _announce(self, action: Action) -> None:
        """Tell the client what is happening, so the UI can render it.

        Sent before the audio, so the cue card is on screen while the examiner
        is still introducing it rather than appearing after.
        """
        try:
            await self.transport.send_state(
                {
                    "action": action.to_dict(),
                    "progress": self.interview.progress(),
                    "isComplete": self.interview.is_complete,
                }
            )
        except Exception as exc:  # noqa: BLE001 - never fatal
            self.failures.append(f"state push failed ({exc})")

    async def _speak(self, action: Action) -> None:
        if not action.text.strip():
            return
        speech = await self.tts.synthesize(action.text)
        if speech.audio:
            await self.transport.play(speech.audio, speech.mime_type)

    async def _wait_out_preparation(self, action: Action) -> None:
        """The Part 2 minute. Silence is the point, so nothing is recorded."""
        seconds = action.duration_seconds or 60
        await asyncio.sleep(seconds)

    async def _listen(self, action: Action) -> TurnResult:
        """Listen until the candidate has finished, then return what they said."""
        detector = TurnDetector(policy=policy_for_phase(action.phase.value))
        await self.transport.begin_turn()

        elapsed = 0
        stalled = 0
        ended_by = "silence"

        events = self.transport.observations()
        pending: asyncio.Task | None = None

        try:
            while not detector.has_ended:
                if pending is None:
                    pending = asyncio.create_task(_next(events))

                done, _ = await asyncio.wait(
                    {pending}, timeout=self.tick_ms / 1000.0
                )
                elapsed += self.tick_ms

                if pending in done:
                    observation = pending.result()
                    pending = None
                    if observation is None:
                        # The transport closed. Whatever was said is what there
                        # is; treating it as an error would discard a real answer.
                        ended_by = "transport_closed"
                        break
                    stalled = 0
                    decision = detector.observe(observation)
                else:
                    stalled += self.tick_ms
                    decision = detector.tick(elapsed)

                if decision is Decision.STOP_EXAMINER:
                    # Immediately, and before anything else: the whole point of
                    # barge-in is that the examiner stops mid-word.
                    await self.transport.stop_playback()
                elif decision is Decision.END_TURN:
                    ended_by = "detector"
                    break

                if stalled >= TRANSPORT_STALL_MS:
                    # Distinct from a silent candidate: nothing at all is
                    # arriving, which means the pipeline is broken rather than
                    # the person being quiet.
                    ended_by = "transport_stalled"
                    self.failures.append(f"{action.phase.value}: transport stalled")
                    break
        finally:
            if pending is not None:
                pending.cancel()

        text = detector.transcript
        if not text and self.stt is None:
            # A streaming transport builds the transcript as it goes; if it has
            # nothing, ask it directly before giving up on the turn.
            text = await self.transport.transcript_so_far()

        return TurnResult(
            text=text,
            interrupted_examiner=detector.examiner_was_interrupted,
            ended_by=ended_by,
        )


async def _next(iterator: AsyncIterator[Observation]) -> Observation | None:
    """One observation, or None when the stream is done."""
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        return None


def transcripts_by_part(interview: Interview) -> dict[int, str]:
    """What the scorer needs, per part."""
    return {part: interview.transcript_for(part) for part in (1, 2, 3)}


def is_scorable(interview: Interview) -> bool:
    """Whether the exam produced anything worth sending to the scorer.

    An interview where every turn failed technically must not be scored: a band
    computed from silence would be reported to the learner as their ability.
    """
    return bool(interview.full_transcript().strip()) and interview.phase in (
        Phase.SCORING,
        Phase.COMPLETE,
    )
