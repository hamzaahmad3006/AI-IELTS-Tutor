"""Smoke test: the examiner state machine and the voice ports.

The exam's rules are the thing under test. A speaking test that gives ninety
seconds of preparation, or lets the candidate talk for six minutes, or feeds the
examiner's own questions into a fluency score, is training the learner for an
exam that does not exist -- and every one of those is invisible unless something
checks it.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_interview.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.voice import (  # noqa: E402
    MockSpeechToText,
    MockTextToSpeech,
    SpeechToText,
    TextToSpeech,
)
from core.interview import (  # noqa: E402
    PART2_MAX_SPEAK_SECONDS,
    PART2_PREP_SECONDS,
    ActionKind,
    CueCard,
    Interview,
    InterviewScript,
    Phase,
    Speaker,
)

SCRIPT = InterviewScript(
    part1=("Where do you live?", "Do you work or study?", "What do you do at weekends?"),
    cue_card=CueCard(
        topic="a teacher",
        prompt="Describe a teacher who influenced you.",
        bullets=("who they were", "what they taught", "why they influenced you"),
    ),
    part2_followup="Do you still keep in touch with them?",
    part3=("How has teaching changed?", "Should teachers be paid more?"),
)


def _fresh() -> Interview:
    return Interview(script=SCRIPT)


def check_full_run() -> None:
    """A whole exam, in order, ending in a scorable transcript."""
    exam = _fresh()

    assert exam.phase is Phase.GREETING
    action = exam.current_action()
    assert action.kind is ActionKind.ASK and "name" in action.text

    # Asking twice must not skip a question -- a client that reconnects has to
    # be able to re-request the instruction it lost.
    assert exam.current_action() == action

    seen: list[Phase] = []
    answers = 0
    while not exam.is_complete:
        seen.append(exam.phase)
        exam.answer(f"answer {answers}")
        answers += 1
        assert answers < 50, "the machine is not terminating"

    assert seen == [
        Phase.GREETING,
        Phase.PART1,
        Phase.PART1,
        Phase.PART1,
        Phase.PART2_CUE,
        Phase.PART2_PREP,
        Phase.PART2_SPEAKING,
        Phase.PART2_FOLLOWUP,
        Phase.PART3,
        Phase.PART3,
        Phase.SCORING,
    ], seen

    # The cue-card intro expects no answer, so it must not have produced a
    # candidate turn -- otherwise "answer 4" lands in the Part 2 transcript.
    assert len(exam.candidate_turns) == len(seen) - 1

    try:
        exam.answer("one more")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a finished test accepted another answer")


def check_exam_timings() -> None:
    """Preparation is one minute and the long turn allows two."""
    exam = _fresh()
    while exam.phase is not Phase.PART2_PREP:
        exam.answer("x")

    prep = exam.current_action()
    assert prep.kind is ActionKind.PREPARE
    assert prep.duration_seconds == PART2_PREP_SECONDS == 60
    assert prep.bullets == SCRIPT.cue_card.bullets

    exam.answer("")
    turn = exam.current_action()
    assert turn.kind is ActionKind.LONG_TURN
    # The maximum, not the minimum. Cutting the candidate off at sixty seconds
    # would fail them for using time the real exam gives them.
    assert turn.duration_seconds == PART2_MAX_SPEAK_SECONDS == 120


def check_skip_preparation() -> None:
    """The prep minute is a ceiling, not a wait."""
    exam = _fresh()
    while exam.phase is not Phase.PART2_PREP:
        exam.answer("x")

    action = exam.skip_preparation()
    assert exam.phase is Phase.PART2_SPEAKING
    assert action.kind is ActionKind.LONG_TURN

    # ...but it must not be a way to skip questions elsewhere.
    other = _fresh()
    try:
        other.skip_preparation()
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("preparation was skippable outside Part 2")


def check_transcripts() -> None:
    """Only the candidate's words, split by part, are scorable."""
    exam = _fresh()
    exam.answer("My name is Sara.")  # greeting
    exam.answer("I live in Lahore.")
    exam.answer("I study engineering.")
    exam.answer("I play cricket.")
    exam.answer("")  # cue card intro: no answer expected
    exam.answer("")  # preparation
    exam.answer("I want to talk about my physics teacher.")
    exam.answer("Yes, we still email.")
    exam.answer("Teaching has become more digital.")
    exam.answer("Yes, they should.")

    part1 = exam.transcript_for(1)
    assert "Lahore" in part1 and "cricket" in part1
    assert "physics" not in part1, "Part 2 speech leaked into Part 1"

    part2 = exam.transcript_for(2)
    assert "physics teacher" in part2
    assert "still email" in part2, "the rounding-off answer belongs to Part 2"
    assert "Lahore" not in part2

    part3 = exam.transcript_for(3)
    assert "digital" in part3 and "physics" not in part3

    # The examiner's own questions must never reach the scorer: they would
    # measure the script's vocabulary, not the learner's.
    full = exam.full_transcript()
    for question in SCRIPT.part1 + SCRIPT.part3 + (SCRIPT.part2_followup,):
        assert question not in full, question
    assert SCRIPT.cue_card.prompt not in full


def check_silence_is_an_answer() -> None:
    """Saying nothing advances the exam.

    It is a bad answer, which the scorer should see, but a machine that waits
    for something better simply hangs -- and on a phone that looks like a crash.
    """
    exam = _fresh()
    for _ in range(12):
        if exam.is_complete:
            break
        exam.answer("")
    assert exam.is_complete
    assert exam.full_transcript() == ""


def check_script_validation() -> None:
    """A script that cannot produce a valid exam is rejected on construction.

    Built by overriding a complete kwargs dict rather than passing both the
    base value and an override: doing the latter raises TypeError for duplicate
    keyword arguments, which a broad `except` happily mistakes for the
    validation firing. That version of this test passed without ever reaching
    __post_init__.
    """
    base = {
        "part1": SCRIPT.part1,
        "cue_card": SCRIPT.cue_card,
        "part2_followup": SCRIPT.part2_followup,
        "part3": SCRIPT.part3,
    }
    InterviewScript(**base)  # the baseline must be valid, or nothing below means anything

    bad = [
        ("no Part 1 questions", {"part1": ()}),
        ("no Part 3 questions", {"part3": ()}),
        (
            "cue card with no bullets",
            {"cue_card": CueCard(topic="t", prompt="p", bullets=())},
        ),
    ]
    for label, override in bad:
        try:
            InterviewScript(**{**base, **override})  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{label} should have been rejected")


def check_progress() -> None:
    exam = _fresh()
    start = exam.progress()
    assert start["answered"] == 0 and start["phaseIndex"] == 0

    exam.answer("hello")
    later = exam.progress()
    assert later["answered"] == 1
    assert later["phaseIndex"] > start["phaseIndex"]

    while not exam.is_complete:
        exam.answer("x")
    done = exam.progress()
    assert done["phaseIndex"] == done["phaseCount"] - 1


def check_serialisation() -> None:
    """Actions cross the wire, so they must serialise to camelCase."""
    exam = _fresh()
    while exam.phase is not Phase.PART2_PREP:
        exam.answer("x")
    payload = exam.current_action().to_dict()
    assert payload["kind"] == "prepare"
    assert payload["phase"] == "part2_prep"
    assert payload["durationSeconds"] == 60
    assert payload["bullets"] == list(SCRIPT.cue_card.bullets)


async def check_voice_ports() -> None:
    stt = MockSpeechToText(queued=["I live in Lahore."])
    assert isinstance(stt, SpeechToText)

    first = await stt.transcribe(b"\x00" * 100, mime_type="audio/wav")
    assert first.text == "I live in Lahore."
    assert first.provider == "mock" and first.is_partial is False

    # An exhausted queue yields empty text, not a crash: silence is a valid
    # recognition result and the exam must survive it.
    empty = await stt.transcribe(b"", mime_type="audio/wav")
    assert empty.text == "" and empty.confidence == 0.0

    tts = MockTextToSpeech()
    assert isinstance(tts, TextToSpeech)
    short = await tts.synthesize("Hello.")
    long = await tts.synthesize(" ".join(["word"] * 150))
    # Duration scales with length, so a client that sequences on playback time
    # behaves as it would with real speech instead of racing ahead.
    assert long.duration_ms > short.duration_ms
    assert abs(long.duration_ms - 60_000) < 1_000, long.duration_ms


def run() -> None:
    check_full_run()
    check_exam_timings()
    check_skip_preparation()
    check_transcripts()
    check_silence_is_an_answer()
    check_script_validation()
    check_progress()
    check_serialisation()
    asyncio.run(check_voice_ports())

    print("INTERVIEW SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
