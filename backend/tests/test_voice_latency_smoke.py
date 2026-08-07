"""Smoke test: the voice pipeline's latency budget.

Turn-taking and barge-in are covered by test_turn_taking_smoke and
test_agent_smoke. What those do not check is *how long* the parts take, and
latency is the thing that decides whether a spoken exam feels like a
conversation or like a form submission.

The budget is asserted against the pieces this machine can actually run: the
state machine, turn detection, cache lookups and the agent loop. Network time
to Deepgram and ElevenLabs is deliberately not simulated — a made-up number
would be worse than no number, because it would look like evidence.

What this does catch is our own code becoming the bottleneck. If deciding what
the examiner says next ever costs tens of milliseconds, no amount of provider
speed will rescue the experience.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_voice_latency.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.voice_providers.deepgram_stream import parse_message  # noqa: E402
from ai.voice_providers.elevenlabs_tts import ElevenLabsTextToSpeech  # noqa: E402
from core.interview import (  # noqa: E402
    CueCard,
    Interview,
    InterviewScript,
)
from core.turn_taking import (  # noqa: E402
    Event,
    Observation,
    TurnDetector,
)

#: Our own code's share of the budget. A spoken turn has roughly a second of
#: headroom before it stops feeling like a conversation, and essentially all of
#: it belongs to the network and the models. Anything of ours that costs more
#: than a millisecond per decision is spending someone else's budget.
DECISION_BUDGET_MS = 1.0

#: A cached question must play immediately. The cache exists so the fixed
#: question bank is free *and* instant; a slow cache is only half of that.
CACHE_HIT_BUDGET_MS = 5.0

SCRIPT = InterviewScript(
    part1=("Where do you live?",) * 8,
    cue_card=CueCard(
        topic="a teacher",
        prompt="Describe a teacher who influenced you.",
        bullets=("who", "what"),
    ),
    part2_followup="Do you still keep in touch?",
    part3=("How has teaching changed?",) * 5,
)


def _median_ms(fn, iterations: int = 200) -> float:
    """Median, not mean: one scheduler hiccup should not fail the build."""
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def check_examiner_decision_is_instant() -> None:
    """Deciding what to say next must not cost measurable time."""
    exam = Interview(script=SCRIPT)
    elapsed = _median_ms(exam.current_action)
    assert elapsed < DECISION_BUDGET_MS, f"current_action took {elapsed:.3f}ms"


def check_turn_detection_is_instant() -> None:
    """Called on every audio event, so a slow one compounds."""
    detector = TurnDetector()
    counter = {"t": 0}

    def observe() -> None:
        counter["t"] += 10
        detector.observe(
            Observation(Event.INTERIM_TRANSCRIPT, at_ms=counter["t"], text="word")
        )

    elapsed = _median_ms(observe)
    assert elapsed < DECISION_BUDGET_MS, f"observe took {elapsed:.3f}ms"


def check_transcript_parsing_is_instant() -> None:
    """Deepgram sends interim results continuously while someone speaks."""
    message = (
        '{"type":"Results","is_final":false,'
        '"channel":{"alternatives":[{"transcript":"I live in Lahore"}]}}'
    )
    elapsed = _median_ms(lambda: parse_message(message, at_ms=100))
    assert elapsed < DECISION_BUDGET_MS, f"parse_message took {elapsed:.3f}ms"


def check_whole_exam_is_decided_quickly() -> None:
    """Every decision in a full twelve-minute exam, end to end.

    Sixteen turns of pure sequencing. If that takes longer than a blink, the
    latency is ours rather than the network's.
    """
    started = time.perf_counter()
    for _ in range(20):
        exam = Interview(script=SCRIPT)
        while not exam.is_complete:
            exam.current_action()
            exam.answer("an answer of reasonable length")
    elapsed = (time.perf_counter() - started) * 1000

    per_exam = elapsed / 20
    assert per_exam < 20, f"a whole exam cost {per_exam:.1f}ms of decisions"


def check_cached_speech_is_immediate() -> None:
    """A cache hit is the difference between instant and a billed round trip."""
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp) / "cache"
        tts = ElevenLabsTextToSpeech(
            api_key="test-key", cache_dir=cache, monthly_character_limit=0
        )
        text = "Where do you live?"

        # Seed the cache directly rather than calling the provider: this test
        # measures the read, and a network call would measure the network.
        key = tts._cache_key(text, tts._voice_id)  # noqa: SLF001
        path = tts._cache_path(key)  # noqa: SLF001
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x00" * 32_000)

        elapsed = _median_ms(lambda: tts.cached_bytes(text), iterations=50)
        assert elapsed < CACHE_HIT_BUDGET_MS, f"cache read took {elapsed:.3f}ms"

        # And a miss must be cheap too: it is checked before every synthesis.
        miss = _median_ms(lambda: tts.cached_bytes("never synthesised"), iterations=50)
        assert miss < CACHE_HIT_BUDGET_MS, f"cache miss took {miss:.3f}ms"


async def check_barge_in_reaction_is_immediate() -> None:
    """The examiner must stop mid-word, not at the end of the sentence.

    Measured from the observation that crosses the barge-in threshold to the
    decision being returned. Playback stopping is the transport's job; this is
    the part we own.
    """
    from core.turn_taking import Decision, TurnPolicy

    detector = TurnDetector(policy=TurnPolicy(barge_in_min_speech_ms=300))
    detector.observe(Observation(Event.SPEECH_STARTED, at_ms=0))

    started = time.perf_counter()
    decision = detector.observe(
        Observation(Event.INTERIM_TRANSCRIPT, at_ms=350, text="actually")
    )
    elapsed = (time.perf_counter() - started) * 1000

    assert decision is Decision.STOP_EXAMINER
    assert elapsed < DECISION_BUDGET_MS, f"barge-in decision took {elapsed:.3f}ms"


def run() -> None:
    check_examiner_decision_is_instant()
    check_turn_detection_is_instant()
    check_transcript_parsing_is_instant()
    check_whole_exam_is_decided_quickly()
    check_cached_speech_is_immediate()
    asyncio.run(check_barge_in_reaction_is_immediate())

    print("VOICE LATENCY SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
