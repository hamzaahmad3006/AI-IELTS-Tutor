"""Examiner state machine for the IELTS Speaking test.

This is the backbone of the voice module, and it is deliberately pure: no audio,
no network, no database. Given the current phase and what the candidate just
did, it decides what happens next. That makes the exam's rules testable in
milliseconds instead of only being observable by talking to a phone for twelve
minutes.

It is also the reason the audio transport can be swapped later. On-device
Android speech recognition and a server-side LiveKit agent disagree about
almost everything, but they agree on this: something asks a question, someone
answers, and the exam moves on. Both drive the same machine.

The structure follows the real test rather than a simplification of it:

* **Part 1** — introduction and familiar topics, 4-5 minutes. Several short
  questions across a few topics.
* **Part 2** — the long turn. A task card, exactly one minute to prepare, then
  1-2 minutes of uninterrupted speech, then a short rounding-off question.
* **Part 3** — two-way discussion, 4-5 minutes, abstract questions tied to the
  Part 2 topic.

The timings are exam rules, not interface decoration. A candidate who practises
with ninety seconds of preparation is practising for an exam that does not
exist, so the machine enforces them and the client renders them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# ---------- Exam constants ----------

#: Preparation time for the Part 2 long turn. Exactly one minute in the real
#: test, and the single most commonly mis-implemented rule in practice apps.
PART2_PREP_SECONDS = 60

#: The candidate should speak for 1-2 minutes. The examiner stops them at two.
PART2_MIN_SPEAK_SECONDS = 60
PART2_MAX_SPEAK_SECONDS = 120

#: Target question counts. The real examiner varies these; these are the
#: midpoints of the published ranges.
PART1_QUESTIONS = 8
PART3_QUESTIONS = 5


class Phase(str, Enum):
    """Where the exam currently is.

    Part 2 is three phases rather than one because the candidate can do
    completely different things in each: listen, prepare in silence, then
    speak uninterrupted. Collapsing them loses the prep timer, which is the
    part candidates most need to rehearse.
    """

    GREETING = "greeting"
    PART1 = "part1"
    PART2_CUE = "part2_cue"
    PART2_PREP = "part2_prep"
    PART2_SPEAKING = "part2_speaking"
    PART2_FOLLOWUP = "part2_followup"
    PART3 = "part3"
    SCORING = "scoring"
    COMPLETE = "complete"


class Speaker(str, Enum):
    EXAMINER = "examiner"
    CANDIDATE = "candidate"


class ActionKind(str, Enum):
    """What the client should do next."""

    #: Speak this text, then wait for an answer.
    ASK = "ask"
    #: Speak this text; no answer expected.
    SAY = "say"
    #: Show the cue card and run a silent countdown.
    PREPARE = "prepare"
    #: Listen for a long uninterrupted turn.
    LONG_TURN = "long_turn"
    #: The exam is over; submit for scoring.
    FINISH = "finish"


@dataclass(frozen=True)
class Action:
    """One instruction for whatever is driving the audio."""

    kind: ActionKind
    phase: Phase
    text: str = ""
    #: Present for timed phases. The client counts down; the machine decides.
    duration_seconds: int | None = None
    #: Cue card bullet points, Part 2 only.
    bullets: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "phase": self.phase.value,
            "text": self.text,
            "durationSeconds": self.duration_seconds,
            "bullets": list(self.bullets),
        }


@dataclass(frozen=True)
class Turn:
    """One thing that was said."""

    speaker: Speaker
    text: str
    phase: Phase


@dataclass(frozen=True)
class CueCard:
    topic: str
    prompt: str
    bullets: tuple[str, ...]


@dataclass
class InterviewScript:
    """The questions this particular exam will ask.

    Supplied by the caller from the question bank rather than generated here,
    so the machine stays pure and the same script can be replayed in a test.
    """

    part1: tuple[str, ...]
    cue_card: CueCard
    part2_followup: str
    part3: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.part1:
            raise ValueError("Part 1 needs at least one question")
        if not self.part3:
            raise ValueError("Part 3 needs at least one question")
        if not self.cue_card.bullets:
            raise ValueError("A cue card without bullets is not a cue card")


GREETING = (
    "Good morning. My name is your examiner for today. "
    "Can you tell me your full name, please?"
)

PART2_INTRO = (
    "Now I'm going to give you a topic, and I'd like you to talk about it for "
    "one to two minutes. Before you talk, you'll have one minute to think "
    "about what you're going to say. You can make some notes if you wish."
)

PART3_INTRO = (
    "We've been talking about that topic, and I'd like to discuss with you "
    "one or two more general questions related to this."
)

CLOSING = "Thank you. That is the end of the speaking test."


@dataclass
class Interview:
    """A speaking test in progress.

    Advanced by `answer()`, which is the only way state changes. Everything the
    client needs to render is returned as an `Action`, so the client holds no
    exam rules of its own and cannot drift from them.
    """

    script: InterviewScript
    phase: Phase = Phase.GREETING
    turns: list[Turn] = field(default_factory=list)
    #: Index of the next question within the current part.
    _cursor: int = 0

    # ---------- Queries ----------

    @property
    def is_complete(self) -> bool:
        return self.phase is Phase.COMPLETE

    @property
    def candidate_turns(self) -> list[Turn]:
        return [t for t in self.turns if t.speaker is Speaker.CANDIDATE]

    def transcript_for(self, part: int) -> str:
        """The candidate's words for one part, as the scorer expects them.

        Only the candidate's speech: feeding the examiner's questions into a
        fluency score would measure the script, not the learner.
        """
        phases = {
            1: {Phase.PART1},
            2: {Phase.PART2_SPEAKING, Phase.PART2_FOLLOWUP},
            3: {Phase.PART3},
        }[part]
        return " ".join(
            t.text.strip()
            for t in self.turns
            if t.speaker is Speaker.CANDIDATE and t.phase in phases and t.text.strip()
        )

    def full_transcript(self) -> str:
        return " ".join(
            t.text.strip() for t in self.candidate_turns if t.text.strip()
        )

    # ---------- Progression ----------

    def current_action(self) -> Action:
        """What the client should do right now, without changing anything.

        Separate from `answer()` so a reconnecting client can ask "where were
        we?" and get the same instruction it lost, rather than skipping a
        question because it had to re-request one.
        """
        if self.phase is Phase.GREETING:
            return Action(ActionKind.ASK, Phase.GREETING, GREETING)

        if self.phase is Phase.PART1:
            return Action(
                ActionKind.ASK, Phase.PART1, self.script.part1[self._cursor]
            )

        if self.phase is Phase.PART2_CUE:
            return Action(
                ActionKind.SAY,
                Phase.PART2_CUE,
                PART2_INTRO,
                bullets=self.script.cue_card.bullets,
            )

        if self.phase is Phase.PART2_PREP:
            return Action(
                ActionKind.PREPARE,
                Phase.PART2_PREP,
                self.script.cue_card.prompt,
                duration_seconds=PART2_PREP_SECONDS,
                bullets=self.script.cue_card.bullets,
            )

        if self.phase is Phase.PART2_SPEAKING:
            return Action(
                ActionKind.LONG_TURN,
                Phase.PART2_SPEAKING,
                self.script.cue_card.prompt,
                # The maximum, not the minimum: the client must not stop the
                # candidate at sixty seconds when the exam allows a hundred
                # and twenty.
                duration_seconds=PART2_MAX_SPEAK_SECONDS,
                bullets=self.script.cue_card.bullets,
            )

        if self.phase is Phase.PART2_FOLLOWUP:
            return Action(
                ActionKind.ASK, Phase.PART2_FOLLOWUP, self.script.part2_followup
            )

        if self.phase is Phase.PART3:
            return Action(
                ActionKind.ASK, Phase.PART3, self.script.part3[self._cursor]
            )

        if self.phase is Phase.SCORING:
            return Action(ActionKind.FINISH, Phase.SCORING, CLOSING)

        return Action(ActionKind.FINISH, Phase.COMPLETE, CLOSING)

    def answer(self, text: str) -> Action:
        """Record the candidate's answer and advance.

        An empty answer still advances. A candidate who says nothing has given
        an answer -- a bad one, which the scorer should see -- and a machine
        that waits for something better would simply hang.
        """
        if self.is_complete:
            raise ValueError("The test is over; no further answers are accepted")

        action = self.current_action()

        # The cue card intro expects no answer, so recording one would insert a
        # phantom candidate turn into the Part 2 transcript.
        if action.kind is not ActionKind.SAY:
            self.turns.append(
                Turn(speaker=Speaker.CANDIDATE, text=text, phase=self.phase)
            )

        self._advance()
        return self.current_action()

    def _advance(self) -> None:
        if self.phase is Phase.GREETING:
            self.phase, self._cursor = Phase.PART1, 0
            return

        if self.phase is Phase.PART1:
            self._cursor += 1
            if self._cursor >= len(self.script.part1):
                self.phase, self._cursor = Phase.PART2_CUE, 0
            return

        if self.phase is Phase.PART2_CUE:
            self.phase = Phase.PART2_PREP
            return

        if self.phase is Phase.PART2_PREP:
            self.phase = Phase.PART2_SPEAKING
            return

        if self.phase is Phase.PART2_SPEAKING:
            self.phase = Phase.PART2_FOLLOWUP
            return

        if self.phase is Phase.PART2_FOLLOWUP:
            self.phase, self._cursor = Phase.PART3, 0
            return

        if self.phase is Phase.PART3:
            self._cursor += 1
            if self._cursor >= len(self.script.part3):
                self.phase = Phase.SCORING
            return

        if self.phase is Phase.SCORING:
            self.phase = Phase.COMPLETE

    def skip_preparation(self) -> Action:
        """Let a candidate start early. The prep minute is a maximum, not a wait.

        Only valid during preparation: allowing it anywhere else would be a way
        to skip questions.
        """
        if self.phase is not Phase.PART2_PREP:
            raise ValueError("There is no preparation to skip in this phase")
        self.phase = Phase.PART2_SPEAKING
        return self.current_action()

    def progress(self) -> dict[str, object]:
        """Coarse progress, for a client that wants to show how far along we are."""
        order = [
            Phase.GREETING,
            Phase.PART1,
            Phase.PART2_CUE,
            Phase.PART2_PREP,
            Phase.PART2_SPEAKING,
            Phase.PART2_FOLLOWUP,
            Phase.PART3,
            Phase.SCORING,
            Phase.COMPLETE,
        ]
        return {
            "phase": self.phase.value,
            "phaseIndex": order.index(self.phase),
            "phaseCount": len(order),
            "questionIndex": self._cursor,
            "answered": len(self.candidate_turns),
        }
