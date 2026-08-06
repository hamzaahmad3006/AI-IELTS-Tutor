"""Smoke test: the examiner agent loop.

Run against a fake transport, which is the point of having one. A whole
interview -- greeting, eight Part 1 questions, the cue card, a silent
preparation minute, the long turn, Part 3 -- executes in milliseconds and every
timing and failure path is reachable.

The assertions that matter are about resilience and about not speaking over the
candidate. A twelve-minute exam must not be lost to one failed synthesis call.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_agent.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.voice import MockTextToSpeech, Speech  # noqa: E402
from core.interview import CueCard, Interview, InterviewScript, Phase  # noqa: E402
from core.turn_taking import Event, Observation  # noqa: E402
from voice.agent import (  # noqa: E402
    ExaminerAgent,
    RoomTransport,
    is_scorable,
    transcripts_by_part,
)

SCRIPT = InterviewScript(
    part1=("Where do you live?", "Do you work or study?"),
    cue_card=CueCard(
        topic="a teacher",
        prompt="Describe a teacher who influenced you.",
        bullets=("who they were", "what they taught"),
    ),
    part2_followup="Do you still keep in touch?",
    part3=("How has teaching changed?",),
)


class FakeTransport:
    """Scripted answers, and a record of everything the agent did."""

    def __init__(self, answers: list[str], barge_in_on: int | None = None) -> None:
        self._answers = list(answers)
        self._barge_in_on = barge_in_on
        self.turn = 0
        self.played: list[bytes] = []
        self.stopped_playback = 0
        self.states: list[dict] = []
        self._current = ""

    async def play(self, audio: bytes, mime_type: str) -> None:
        self.played.append(audio)

    async def stop_playback(self) -> None:
        self.stopped_playback += 1

    async def begin_turn(self) -> None:
        self.turn += 1
        self._current = self._answers.pop(0) if self._answers else ""

    def observations(self) -> AsyncIterator[Observation]:
        text = self._current
        barge = self._barge_in_on == self.turn

        async def gen() -> AsyncIterator[Observation]:
            if barge:
                yield Observation(Event.SPEECH_STARTED, at_ms=0)
                await asyncio.sleep(0)
                yield Observation(Event.INTERIM_TRANSCRIPT, at_ms=400, text=text)
            if text:
                yield Observation(Event.FINAL_TRANSCRIPT, at_ms=500, text=text)
            yield Observation(Event.SPEECH_ENDED, at_ms=600)

        return gen()

    async def transcript_so_far(self) -> str:
        return self._current

    async def send_state(self, payload: dict) -> None:
        self.states.append(payload)


def _agent(transport: FakeTransport, **kwargs) -> ExaminerAgent:
    return ExaminerAgent(
        interview=Interview(script=SCRIPT),
        transport=transport,
        tts=MockTextToSpeech(),
        # Fast ticks: the detector's thresholds are in exam time, which the
        # fake transport supplies, so real sleeping would only slow the test.
        tick_ms=1,
        **kwargs,
    )


class InstantSpeech(MockTextToSpeech):
    """Mock TTS that returns real bytes, so playback is observable."""

    async def synthesize(self, text: str, *, voice: str | None = None) -> Speech:
        return Speech(audio=b"audio:" + text[:20].encode(), mime_type="audio/wav")


async def check_full_interview() -> None:
    answers = [
        "My name is Sara.",
        "I live in Lahore.",
        "I study engineering.",
        "I want to talk about my physics teacher.",
        "Yes, we still email.",
        "Teaching is more digital now.",
    ]
    transport = FakeTransport(answers)
    agent = _agent(transport)
    agent.tts = InstantSpeech()

    # Preparation is a real minute in the exam; patched so the test does not
    # actually wait one.
    agent._wait_out_preparation = lambda action: asyncio.sleep(0)  # type: ignore[assignment]

    interview = await asyncio.wait_for(agent.run(), timeout=30)

    assert interview.is_complete or interview.phase is Phase.SCORING, interview.phase
    assert not agent.failures, agent.failures

    # The examiner actually spoke, and the client was told what was happening
    # before each turn.
    assert transport.played, "the examiner never said anything"
    assert transport.states, "the client was never told the exam state"
    assert transport.states[0]["action"]["kind"] == "ask"

    parts = transcripts_by_part(interview)
    assert "Lahore" in parts[1]
    assert "physics teacher" in parts[2]
    assert "digital" in parts[3]
    # Part boundaries hold: an answer must not leak into the wrong part.
    assert "physics" not in parts[1] and "Lahore" not in parts[2]

    assert is_scorable(interview)


async def check_barge_in_stops_the_examiner() -> None:
    """The examiner stops mid-word, not at the end of the turn."""
    transport = FakeTransport(["Sara.", "Actually, I live in Karachi."], barge_in_on=2)
    agent = _agent(transport)
    agent.tts = InstantSpeech()
    agent._wait_out_preparation = lambda action: asyncio.sleep(0)  # type: ignore[assignment]

    await asyncio.wait_for(agent.run(), timeout=30)
    assert transport.stopped_playback >= 1, "the examiner talked over the candidate"


async def check_one_failure_does_not_end_the_exam() -> None:
    """A twelve-minute test must survive one bad synthesis call."""

    class FlakyTTS(InstantSpeech):
        def __init__(self) -> None:
            self.calls = 0

        async def synthesize(self, text: str, *, voice: str | None = None) -> Speech:
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("provider timed out")
            return await super().synthesize(text, voice=voice)

    transport = FakeTransport(["Sara.", "I live in Lahore.", "I study.", "Teacher.", "Yes.", "Digital."])
    agent = _agent(transport)
    agent.tts = FlakyTTS()
    agent._wait_out_preparation = lambda action: asyncio.sleep(0)  # type: ignore[assignment]

    interview = await asyncio.wait_for(agent.run(), timeout=30)

    assert interview.is_complete or interview.phase is Phase.SCORING
    # The failure is recorded rather than swallowed: a session with gaps must
    # be reviewable, not silently incomplete.
    assert any("speak failed" in f for f in agent.failures), agent.failures
    assert is_scorable(interview), "one failed question lost the whole exam"


async def check_silent_candidate_still_finishes() -> None:
    """Saying nothing is an answer, and the exam still ends."""
    transport = FakeTransport([""] * 10)
    agent = _agent(transport)
    agent._wait_out_preparation = lambda action: asyncio.sleep(0)  # type: ignore[assignment]

    interview = await asyncio.wait_for(agent.run(), timeout=30)
    assert interview.is_complete or interview.phase is Phase.SCORING

    # ...but there is nothing to score, and a band computed from silence must
    # never be reported to a learner as their ability.
    assert not is_scorable(interview)


async def check_state_pushes_precede_audio() -> None:
    """The cue card is on screen while the examiner introduces it."""
    transport = FakeTransport(["Sara.", "Lahore.", "Engineering.", "Teacher.", "Yes.", "Digital."])
    agent = _agent(transport)
    agent.tts = InstantSpeech()
    agent._wait_out_preparation = lambda action: asyncio.sleep(0)  # type: ignore[assignment]

    await asyncio.wait_for(agent.run(), timeout=30)

    phases = [s["action"]["phase"] for s in transport.states]
    assert "part2_cue" in phases
    cue = next(s for s in transport.states if s["action"]["phase"] == "part2_cue")
    assert cue["action"]["bullets"], "the cue card was pushed without its bullets"

    prep = next(s for s in transport.states if s["action"]["phase"] == "part2_prep")
    assert prep["action"]["durationSeconds"] == 60


def check_transport_protocol() -> None:
    assert isinstance(FakeTransport([]), RoomTransport)


def run() -> None:
    check_transport_protocol()
    asyncio.run(check_full_interview())
    asyncio.run(check_barge_in_stops_the_examiner())
    asyncio.run(check_one_failure_does_not_end_the_exam())
    asyncio.run(check_silent_candidate_still_finishes())
    asyncio.run(check_state_pushes_precede_audio())

    print("AGENT SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
