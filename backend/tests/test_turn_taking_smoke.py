"""Smoke test: turn-taking and Deepgram's streaming message shapes.

The assertions here are mostly about *not* acting: not ending a turn because
someone paused to think, not stopping the examiner because a chair creaked, not
treating an empty interim result as speech. Each of those is a plausible
implementation that would feel broken to a candidate in a specific way.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_turn_taking.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.voice_providers.deepgram_stream import (  # noqa: E402
    StreamConfig,
    build_url,
    parse_message,
)
from core.turn_taking import (  # noqa: E402
    DEFAULT_END_OF_TURN_SILENCE_MS,
    Decision,
    Event,
    Observation,
    TurnDetector,
    TurnPolicy,
    policy_for_phase,
)


def _speak(detector: TurnDetector, at: int, text: str = "", final: bool = False):
    return detector.observe(
        Observation(
            event=Event.FINAL_TRANSCRIPT if final else Event.INTERIM_TRANSCRIPT,
            at_ms=at,
            text=text,
        )
    )


def check_thinking_pause_does_not_end_turn() -> None:
    """The assertion this module exists for.

    A candidate pausing mid-answer is producing the behaviour Fluency and
    Coherence assesses. A chat app's 800ms threshold would cut them off and
    then mark them down for the disfluency it caused.
    """
    d = TurnDetector()
    _speak(d, 0, "I would like to talk about", final=True)
    d.observe(Observation(Event.SPEECH_ENDED, at_ms=1_000))

    # Two seconds of thinking. Long for a chat assistant; normal here.
    assert d.tick(2_000) is Decision.NONE
    assert d.tick(3_000) is Decision.NONE
    assert not d.has_ended

    # They resume, and the turn continues.
    _speak(d, 3_200, "my physics teacher.", final=True)
    assert d.tick(4_000) is Decision.NONE
    assert "physics teacher" in d.transcript
    assert "I would like to talk about" in d.transcript

    # Only sustained silence ends it.
    d.observe(Observation(Event.SPEECH_ENDED, at_ms=4_100))
    assert d.tick(4_100 + DEFAULT_END_OF_TURN_SILENCE_MS - 1) is Decision.NONE
    assert d.tick(4_100 + DEFAULT_END_OF_TURN_SILENCE_MS) is Decision.END_TURN
    assert d.has_ended


def check_silence_before_speaking_never_ends_turn() -> None:
    """A candidate who has not started yet is still thinking about the question."""
    d = TurnDetector()
    for t in range(0, 60_000, 5_000):
        assert d.tick(t) is Decision.NONE, t
    assert not d.has_ended
    assert d.transcript == ""


def check_barge_in() -> None:
    d = TurnDetector(policy=TurnPolicy(barge_in_min_speech_ms=300))

    # A brief noise must not interrupt the examiner.
    assert d.observe(Observation(Event.SPEECH_STARTED, at_ms=0)) is Decision.NONE
    assert d.observe(Observation(Event.SPEECH_ENDED, at_ms=120)) is Decision.NONE
    assert not d.examiner_was_interrupted

    # Sustained speech does.
    d2 = TurnDetector(policy=TurnPolicy(barge_in_min_speech_ms=300))
    d2.observe(Observation(Event.SPEECH_STARTED, at_ms=0))
    assert _speak(d2, 350, "actually I think") is Decision.STOP_EXAMINER
    assert d2.examiner_was_interrupted

    # Only once -- the examiner cannot be stopped twice.
    assert _speak(d2, 400, "that") is Decision.NONE

    # And not at all where the exam forbids it.
    d3 = TurnDetector(policy=TurnPolicy(allow_barge_in=False))
    d3.observe(Observation(Event.SPEECH_STARTED, at_ms=0))
    assert _speak(d3, 5_000, "talking") is Decision.NONE
    assert not d3.examiner_was_interrupted


def check_part2_hard_stop() -> None:
    """Two minutes is the exam, not a timeout to be lenient about."""
    policy = policy_for_phase("part2_speaking")
    assert policy.hard_stop_ms == 120_000
    assert policy.allow_barge_in is False
    # More generous silence: this is the phase where ending early costs most.
    assert policy.end_of_turn_silence_ms > DEFAULT_END_OF_TURN_SILENCE_MS

    d = TurnDetector(policy=policy)
    _speak(d, 1_000, "I want to describe my teacher.", final=True)
    assert d.tick(119_000) is Decision.NONE

    # Still mid-sentence at two minutes, and stopped anyway.
    _speak(d, 119_500, "and another thing", final=True)
    assert d.tick(120_000) is Decision.END_TURN
    assert d.has_ended


def check_prep_phase_is_silent() -> None:
    """Nothing said during preparation is an answer."""
    policy = policy_for_phase("part2_prep")
    assert policy.allow_barge_in is False
    d = TurnDetector(policy=policy)
    d.observe(Observation(Event.SPEECH_STARTED, at_ms=0))
    _speak(d, 5_000, "thinking out loud", final=True)
    assert d.tick(59_000) is Decision.NONE
    assert not d.has_ended


def check_interims_are_never_scored() -> None:
    """Interim results are guesses and must not reach the transcript."""
    d = TurnDetector()
    _speak(d, 0, "I live in la whore")  # interim, misheard
    _speak(d, 500, "I live in Lahore.", final=True)
    assert d.transcript == "I live in Lahore."
    assert "la whore" not in d.transcript


def check_runaway_turn_is_closed() -> None:
    """A stuck recogniser must not hang the exam."""
    d = TurnDetector(policy=TurnPolicy(max_turn_ms=10_000))
    for t in range(0, 10_000, 500):
        _speak(d, t, "still going", final=True)
    assert d.tick(10_000) is Decision.END_TURN


def check_utterance_end_is_advisory() -> None:
    """Deepgram endpoints for conversation; this exam is not a conversation."""
    d = TurnDetector()
    _speak(d, 0, "I think", final=True)
    # The provider says the utterance is over...
    assert d.observe(Observation(Event.UTTERANCE_END, at_ms=1_000)) is Decision.NONE
    # ...and we keep listening, because the candidate is probably thinking.
    assert not d.has_ended
    _speak(d, 1_500, "that education matters.", final=True)
    assert "education matters" in d.transcript


def check_policy_validation() -> None:
    base = {"end_of_turn_silence_ms": 2500, "barge_in_min_speech_ms": 300, "max_turn_ms": 60_000}
    TurnPolicy(**base)
    for label, override in [
        ("zero silence", {"end_of_turn_silence_ms": 0}),
        ("negative barge-in", {"barge_in_min_speech_ms": -1}),
        ("zero max turn", {"max_turn_ms": 0}),
        ("zero hard stop", {"hard_stop_ms": 0}),
    ]:
        try:
            TurnPolicy(**{**base, **override})  # type: ignore[arg-type]
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{label} should have been rejected")


def check_deepgram_messages() -> None:
    url = build_url(StreamConfig())
    # Barge-in is impossible without interims, and inferring speech from a
    # first partial is slower and less reliable than an explicit event.
    assert "interim_results=true" in url
    assert "vad_events=true" in url
    assert "filler_words=true" in url
    assert "encoding=linear16" in url

    started = parse_message(json.dumps({"type": "SpeechStarted"}), at_ms=10)
    assert started is not None and started.event is Event.SPEECH_STARTED

    ended = parse_message(json.dumps({"type": "UtteranceEnd"}), at_ms=20)
    assert ended is not None and ended.event is Event.UTTERANCE_END

    def results(text: str, is_final: bool) -> str:
        return json.dumps(
            {
                "type": "Results",
                "is_final": is_final,
                "channel": {"alternatives": [{"transcript": text}]},
            }
        )

    interim = parse_message(results("I live in", False), at_ms=30)
    assert interim is not None and interim.event is Event.INTERIM_TRANSCRIPT

    final = parse_message(results("I live in Lahore.", True), at_ms=40)
    assert final is not None and final.event is Event.FINAL_TRANSCRIPT
    assert final.text == "I live in Lahore."

    # Deepgram emits empty results steadily through silence. Treating those as
    # speech would keep resetting the silence timer and the turn would never
    # end -- the candidate would sit there having finished, waiting.
    assert parse_message(results("", False), at_ms=50) is None
    assert parse_message(results("   ", True), at_ms=50) is None

    # Anything unrecognised is ignored rather than crashing the session.
    assert parse_message(json.dumps({"type": "Metadata"}), at_ms=60) is None
    assert parse_message("not json", at_ms=60) is None
    assert parse_message(b"\x00\x01", at_ms=60) is None
    assert parse_message(json.dumps({"type": "Results"}), at_ms=60) is None


def run() -> None:
    check_thinking_pause_does_not_end_turn()
    check_silence_before_speaking_never_ends_turn()
    check_barge_in()
    check_part2_hard_stop()
    check_prep_phase_is_silent()
    check_interims_are_never_scored()
    check_runaway_turn_is_closed()
    check_utterance_end_is_advisory()
    check_policy_validation()
    check_deepgram_messages()

    print("TURN TAKING SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
