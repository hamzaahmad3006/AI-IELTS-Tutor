"""Turn-taking: when to stop the examiner, and when the candidate has finished.

This is the part of real-time voice that is specific to IELTS rather than to
conversation in general, and getting it wrong is worse here than in a chat
assistant.

**Hesitation is not the end of a turn.** A candidate pausing to think is
producing exactly the behaviour the Fluency and Coherence band is written
about. A chat assistant treats 800ms of silence as "your turn is over"; doing
that here would cut people off mid-sentence and then mark them down for the
disfluency it caused. The silence threshold is therefore measured in seconds,
not hundreds of milliseconds.

**Barge-in must survive a cough.** The examiner should stop talking when the
candidate genuinely starts, not when a chair creaks. So a barge-in needs a
minimum run of speech before it counts, which costs a little latency and buys
not being interrupted by background noise.

**Part 2 has a hard ceiling.** The real examiner stops you at two minutes. That
is not a timeout to be lenient about; it is the exam.

All pure: events in, decisions out. The transport feeds it, and can be swapped
without touching any of this.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

#: Silence that ends a turn. Deliberately long. Deepgram's own default
#: endpointing is measured in tens of milliseconds and a chat app might use
#: 800ms; for a test where thinking aloud is being assessed, that would
#: repeatedly cut candidates off mid-thought.
DEFAULT_END_OF_TURN_SILENCE_MS = 2_500

#: A candidate must speak for at least this long before the examiner stops.
#: Below this, a cough or a chair scrape would interrupt the question.
DEFAULT_BARGE_IN_MIN_SPEECH_MS = 300

#: No answer runs forever. Beyond this the turn is closed regardless, so a
#: stuck recogniser cannot hang the exam.
DEFAULT_MAX_TURN_MS = 5 * 60 * 1_000


class Event(str, Enum):
    """What the transport observed."""

    SPEECH_STARTED = "speech_started"
    SPEECH_ENDED = "speech_ended"
    #: A recognised fragment; the speaker may still be going.
    INTERIM_TRANSCRIPT = "interim_transcript"
    #: A finalised fragment. Several make up one turn.
    FINAL_TRANSCRIPT = "final_transcript"
    #: The provider believes the utterance is over. Advisory, not obeyed
    #: blindly -- providers endpoint far more eagerly than this exam wants.
    UTTERANCE_END = "utterance_end"


class Decision(str, Enum):
    """What the agent should do about it."""

    NONE = "none"
    #: The candidate has started; stop the examiner's audio immediately.
    STOP_EXAMINER = "stop_examiner"
    #: The turn is over; submit what was said and move on.
    END_TURN = "end_turn"


@dataclass(frozen=True)
class Observation:
    event: Event
    #: Milliseconds since the turn began. Supplied by the caller rather than
    #: read from a clock, so the whole thing is deterministic under test.
    at_ms: int
    text: str = ""


@dataclass
class TurnPolicy:
    end_of_turn_silence_ms: int = DEFAULT_END_OF_TURN_SILENCE_MS
    barge_in_min_speech_ms: int = DEFAULT_BARGE_IN_MIN_SPEECH_MS
    max_turn_ms: int = DEFAULT_MAX_TURN_MS
    #: Set for the Part 2 long turn. The real examiner stops the candidate at
    #: two minutes, so this is the exam rather than a timeout.
    hard_stop_ms: int | None = None
    #: Whether the examiner is currently speaking and can be interrupted.
    allow_barge_in: bool = True

    def __post_init__(self) -> None:
        if self.end_of_turn_silence_ms <= 0:
            raise ValueError("end_of_turn_silence_ms must be positive")
        if self.barge_in_min_speech_ms < 0:
            raise ValueError("barge_in_min_speech_ms must not be negative")
        if self.max_turn_ms <= 0:
            raise ValueError("max_turn_ms must be positive")
        if self.hard_stop_ms is not None and self.hard_stop_ms <= 0:
            raise ValueError("hard_stop_ms must be positive when set")


@dataclass
class TurnDetector:
    """Tracks one candidate turn and decides when it is over."""

    policy: TurnPolicy = field(default_factory=TurnPolicy)

    #: Finalised fragments, in order. Interims are never kept: they are
    #: guesses, and a guess that made it into a scored transcript would be
    #: words the candidate did not say.
    _finals: list[str] = field(default_factory=list)
    _speaking: bool = False
    _speech_started_at: int | None = None
    _last_voice_at: int | None = None
    _examiner_stopped: bool = False
    _ended: bool = False

    @property
    def transcript(self) -> str:
        return " ".join(part.strip() for part in self._finals if part.strip())

    @property
    def has_ended(self) -> bool:
        return self._ended

    @property
    def examiner_was_interrupted(self) -> bool:
        return self._examiner_stopped

    def observe(self, observation: Observation) -> Decision:
        """Feed one event; get back what to do."""
        if self._ended:
            return Decision.NONE

        event, at = observation.event, observation.at_ms

        if event is Event.SPEECH_STARTED:
            self._speaking = True
            if self._speech_started_at is None:
                self._speech_started_at = at
            self._last_voice_at = at

        elif event in (Event.INTERIM_TRANSCRIPT, Event.FINAL_TRANSCRIPT):
            self._speaking = True
            if self._speech_started_at is None:
                self._speech_started_at = at
            self._last_voice_at = at
            if event is Event.FINAL_TRANSCRIPT and observation.text.strip():
                self._finals.append(observation.text)

        elif event is Event.SPEECH_ENDED:
            self._speaking = False
            self._last_voice_at = at

        elif event is Event.UTTERANCE_END:
            # Advisory only. Providers endpoint far more eagerly than this exam
            # wants, and obeying it directly is what cuts off a thinking
            # candidate. It records silence; the silence threshold decides.
            self._speaking = False
            if self._last_voice_at is None:
                self._last_voice_at = at

        # Stopping the examiner comes first: it must happen the moment the
        # candidate is genuinely speaking, not after the turn has ended.
        if (
            self.policy.allow_barge_in
            and not self._examiner_stopped
            and self._speech_started_at is not None
            and at - self._speech_started_at >= self.policy.barge_in_min_speech_ms
            and self._speaking
        ):
            self._examiner_stopped = True
            return Decision.STOP_EXAMINER

        return self._maybe_end(at)

    def tick(self, at_ms: int) -> Decision:
        """Advance time with no event.

        Needed because the end of a turn is the *absence* of speech, and
        absence produces no event to react to.
        """
        if self._ended:
            return Decision.NONE
        return self._maybe_end(at_ms)

    def _maybe_end(self, at_ms: int) -> Decision:
        # The Part 2 ceiling. Applies whether or not the candidate is still
        # talking -- being stopped mid-sentence at two minutes is the exam
        # working correctly.
        if self.policy.hard_stop_ms is not None and at_ms >= self.policy.hard_stop_ms:
            self._ended = True
            return Decision.END_TURN

        if at_ms >= self.policy.max_turn_ms:
            self._ended = True
            return Decision.END_TURN

        # Silence only counts once something has been said. Before that, the
        # candidate is still thinking about the question, and ending the turn
        # would answer it for them with nothing.
        if (
            not self._speaking
            and self._last_voice_at is not None
            and at_ms - self._last_voice_at >= self.policy.end_of_turn_silence_ms
        ):
            self._ended = True
            return Decision.END_TURN

        return Decision.NONE


def policy_for_phase(phase: str) -> TurnPolicy:
    """Turn-taking rules per exam phase.

    They genuinely differ. Part 1 answers are short exchanges; the Part 2 long
    turn is uninterrupted by definition and ends on the clock.
    """
    if phase == "part2_speaking":
        return TurnPolicy(
            # Two minutes, as the real examiner enforces.
            hard_stop_ms=120_000,
            # The long turn is meant to be uninterrupted, so the examiner is
            # not speaking and there is nothing to barge into.
            allow_barge_in=False,
            # More generous still: a candidate collecting their thoughts
            # mid-long-turn has not finished, and this is the one phase where
            # ending early costs them the most.
            end_of_turn_silence_ms=4_000,
        )

    if phase == "part2_prep":
        # Silence is the point. Nothing the candidate says here is an answer.
        return TurnPolicy(allow_barge_in=False, end_of_turn_silence_ms=10 ** 9)

    return TurnPolicy()
