"""Smoke test: the live interviewer and the worker's turn detection.

The demo this supports is a spoken conversation, so the failures that matter
are the ones you only hear: an examiner that reads a markdown list aloud,
praises the candidate mid-test, asks two questions at once, or cuts them off
while they are still thinking.

None of those are errors. They all "work". So each is pinned here.

The LiveKit round trip is not covered -- it needs a server, and there is a
separate honest note about that. What is covered is everything that decides
*what the examiner says* and *when it decides the candidate has finished*.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_live_interviewer.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from ai.provider import LLMResult  # noqa: E402
from voice.interviewer import (  # noqa: E402
    MAX_QUESTION_CHARS,
    OPENING_QUESTION,
    LiveInterviewer,
    Turn,
    build_messages,
    clean_question,
)
from voice.live_worker import _peak, _wav  # noqa: E402


class ScriptedProvider:
    """Returns queued replies, and records what it was asked."""

    name = "scripted"

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.seen: list[list[dict]] = []

    async def complete(self, *, messages, json_object=False, temperature=0.2, max_tokens=1024):
        self.seen.append(messages)
        text = self.replies.pop(0) if self.replies else ""
        return LLMResult(content=text, provider=self.name)


def check_questions_are_speakable() -> None:
    """Everything here is read aloud, so formatting is not cosmetic."""
    # A speaker label the model added to be helpful.
    assert clean_question('Examiner: "What is your name?"') == "What is your name?"

    # Two questions in one turn: the second is the one that gets forgotten.
    assert clean_question("Where do you live? And why?") == "Where do you live?"

    # Praise the prompt forbids and the model produces anyway. Spoken, it
    # biases the candidate and is not what a real examiner sounds like.
    assert (
        clean_question("**Great answer!** Can you tell me about your job?")
        == "Can you tell me about your job?"
    )

    # A numbered list, read out complete with its numbering.
    assert clean_question("Sure!\n\n1. What do you do?\n2. Why?") == "What do you do?"

    # Markdown emphasis is pronounced as literal asterisks by most voices.
    assert "*" not in clean_question("Tell me about *your* work?")

    assert clean_question("") == ""
    assert clean_question("   \n  ") == ""


def check_long_answers_are_trimmed() -> None:
    """A question that runs on stops sounding like a question."""
    rambling = (
        "I would like to know, if you do not mind me asking, and please do "
        "take your time with this, about the various different things that "
        "you personally tend to enjoy doing whenever you happen to find that "
        "you have some free time available to you on an ordinary weekday "
        "evening after your work has finished for the day"
    )
    assert len(rambling) > MAX_QUESTION_CHARS, "the test input is not long enough"
    trimmed = clean_question(rambling)
    assert len(trimmed) <= MAX_QUESTION_CHARS + 1
    assert trimmed.endswith("?")


def check_the_interview_opens_without_a_model_call() -> None:
    """An empty history gives the model nothing to follow up on.

    Generating the greeting would also be latency before the candidate has
    heard anything at all, which is exactly when silence feels broken.
    """
    provider = ScriptedProvider([])
    interviewer = LiveInterviewer(provider=provider)

    assert interviewer.opening() == OPENING_QUESTION
    assert provider.seen == [], "the opening question cost an LLM call"
    assert interviewer.history[0].question == OPENING_QUESTION


async def check_follow_ups_use_what_was_said() -> None:
    """The whole point: the next question depends on the last answer."""
    provider = ScriptedProvider(
        [
            "That sounds demanding. Which part of building mobile apps do you find hardest?",
            "Can you describe a project that went wrong?",
        ]
    )
    interviewer = LiveInterviewer(provider=provider)
    interviewer.opening()

    interviewer.record_answer("I am a React Native developer building mobile apps.")
    first = await interviewer.next_question()
    assert "mobile apps" in first

    # The transcript the model saw must contain the candidate's actual words,
    # or it is improvising rather than following up.
    sent = provider.seen[0]
    assert any("React Native developer" in m["content"] for m in sent)
    # And the examiner's own previous turn, so it does not repeat itself.
    assert any(m["content"] == OPENING_QUESTION for m in sent)

    interviewer.record_answer("Mostly the native module work.")
    await interviewer.next_question()
    assert len(provider.seen[1]) > len(provider.seen[0]), "history did not grow"


async def check_a_useless_reply_does_not_end_the_interview() -> None:
    """Mid-interview, keeping the conversation alive beats an elegant question."""
    interviewer = LiveInterviewer(provider=ScriptedProvider(["", "   "]))
    interviewer.opening()
    interviewer.record_answer("Something.")

    question = await interviewer.next_question()
    assert question, "an empty model reply produced silence"
    assert question.endswith("?")


def check_message_shape() -> None:
    history = [Turn("Tell me about yourself?", "I am a developer."), Turn("Where?", "")]
    messages = build_messages(history)

    assert messages[0]["role"] == "system"
    # The examiner's turns are assistant turns and the candidate's are user
    # turns; swapped, the model answers its own questions.
    assert messages[1] == {"role": "assistant", "content": "Tell me about yourself?"}
    assert messages[2] == {"role": "user", "content": "I am a developer."}
    assert messages[-1]["role"] == "user"


def check_the_interview_ends() -> None:
    interviewer = LiveInterviewer(provider=ScriptedProvider([]), max_turns=2)
    interviewer.opening()
    assert not interviewer.is_finished
    interviewer.history.append(Turn("Second?"))
    assert interviewer.is_finished
    assert interviewer.closing()


def check_turn_detection_helpers() -> None:
    """Silence versus speech, and the header the recogniser needs."""
    quiet = b"\x00\x00" * 400
    loud = b"\x00\x40" * 400  # 0x4000 = 16384

    assert _peak(quiet) == 0
    assert _peak(loud) > 900
    assert _peak(b"") == 0
    assert _peak(b"\x01") == 0

    # Raw PCM has no header, so the recogniser guesses the sample rate and
    # transcribes a chipmunk. The WAV wrapper is what stops that.
    wav = _wav(quiet)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    # 16 kHz, mono, 16-bit little-endian in the fmt chunk.
    assert int.from_bytes(wav[24:28], "little") == 16_000
    assert int.from_bytes(wav[22:24], "little") == 1
    assert len(wav) == len(quiet) + 44


def run() -> None:
    check_questions_are_speakable()
    check_long_answers_are_trimmed()
    check_the_interview_opens_without_a_model_call()
    check_message_shape()
    check_the_interview_ends()
    check_turn_detection_helpers()

    asyncio.run(check_follow_ups_use_what_was_said())
    asyncio.run(check_a_useless_reply_does_not_end_the_interview())

    print("LIVE INTERVIEWER SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
