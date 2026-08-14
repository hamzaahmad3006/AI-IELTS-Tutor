"""The conversational examiner: decides what to ask next, from what was said.

The existing `core.interview` machine plays a fixed script -- Part 1 questions,
a cue card, Part 3 discussion -- which is right for a rehearsal of the real
exam, where the examiner's lines are standardised. It cannot follow up on an
answer, because it never sees one.

A live interview needs the opposite. If a candidate says they build mobile
apps, the next question has to be about that, or the whole thing reads as a
recording. So this asks the model for one question at a time, given the
conversation so far.

Kept separate from `core.interview` rather than bolted onto it: the two have
genuinely different jobs, and making the scripted machine occasionally
improvise would leave neither behaviour clear.

Two rules the prompt enforces, because a general-purpose model breaks both by
default:

  - **One question per turn.** Models like to acknowledge, summarise, and then
    ask two things. Spoken aloud that is twenty seconds of examiner and a
    candidate who has forgotten the first half.
  - **No feedback during the interview.** An examiner does not say "great
    answer". It biases the candidate and it is not what the real test sounds
    like.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ai.provider import LLMProvider, Message

#: Spoken, not read. Anything longer than this stops sounding like a question
#: and starts sounding like a monologue.
MAX_QUESTION_CHARS = 220

OPENING_QUESTION = "Hello, and welcome to your speaking interview. To begin, could you tell me a little about yourself?"

SYSTEM_PROMPT = """You are conducting a spoken English speaking-test interview, in the style of an IELTS examiner.

Rules you must follow exactly:
- Ask EXACTLY ONE question per turn. Never two.
- Keep every question under 30 words. It is spoken aloud, not read.
- Base each question on what the candidate just said. Follow up on specifics they mentioned.
- Do NOT give feedback, praise, corrections or scores. Never say "great answer" or similar.
- Do NOT explain yourself, apologise, or mention that you are an AI.
- Move to a new topic only after two or three exchanges on the current one.
- Use plain spoken English. No lists, no markdown, no stage directions.

Return ONLY the question text. Nothing else."""


@dataclass
class Turn:
    """One exchange. `question` was asked; `answer` is what came back."""

    question: str
    answer: str = ""


def clean_question(raw: str) -> str:
    """Reduce a model's reply to a single speakable question.

    Models wrap questions in quotes, prefix them with "Examiner:", add a
    preamble, or ask two things at once. All of that is inaudible in text and
    obvious the moment it is spoken, so it is stripped here rather than hoped
    away in the prompt.
    """
    text = (raw or "").strip()
    if not text:
        return ""

    # Drop a speaker label the model added to be helpful.
    text = re.sub(r"^\s*(examiner|interviewer|ai|assistant)\s*[:\-]\s*", "", text, flags=re.I)
    # Drop surrounding quotes, straight or curly.
    text = text.strip().strip('"“”‘’\'').strip()
    # Markdown emphasis reads as literal asterisks when spoken.
    text = re.sub(r"[*_`#]+", "", text)
    # Collapse newlines: a model that returned a list would otherwise be read
    # out complete with its line breaks.
    text = " ".join(text.split())

    # Keep only the first question, and only the question -- models prefix
    # them with an acknowledgement ("Sure!", "Great answer!") that the prompt
    # forbids and they produce anyway. Spoken, that praise biases the candidate
    # and does not sound like an examiner.
    if "?" in text:
        text = text.split("?")[0] + "?"
        # Back up to the start of the sentence the question is actually in,
        # dropping whatever preamble came before it.
        start = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        if start != -1:
            text = text[start + 2 :]
        # A numbered list item keeps its number otherwise, and "one. what do
        # you do" is what gets read out.
        text = re.sub(r"^\s*\d+[.)]\s*", "", text)
        text = text.strip()

    if len(text) > MAX_QUESTION_CHARS:
        # Cut at a sentence boundary if there is one, so it does not end
        # mid-word in the candidate's ear.
        clipped = text[:MAX_QUESTION_CHARS]
        cut = max(clipped.rfind("."), clipped.rfind(","))
        text = (clipped[:cut] if cut > 60 else clipped).strip().rstrip(",.") + "?"

    return text


def build_messages(history: list[Turn]) -> list[Message]:
    """Turn the exchange history into a chat transcript for the model."""
    messages: list[Message] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        if turn.question:
            messages.append({"role": "assistant", "content": turn.question})
        if turn.answer:
            messages.append({"role": "user", "content": turn.answer})
    messages.append(
        {
            "role": "user",
            "content": (
                "Ask your next question now. One question only, under 30 words, "
                "following up on what I just said."
            ),
        }
    )
    return messages


@dataclass
class LiveInterviewer:
    """Holds the conversation and produces the next question."""

    provider: LLMProvider
    history: list[Turn] = field(default_factory=list)
    #: After this many exchanges the interview wraps up. A demo and a real
    #: rehearsal both need an end.
    max_turns: int = 12

    @property
    def is_finished(self) -> bool:
        return len(self.history) >= self.max_turns

    def opening(self) -> str:
        """The first question, fixed so the interview always starts cleanly.

        Not generated: an empty history gives the model nothing to follow up
        on, and a cold-start call is latency before the candidate has heard
        anything at all.
        """
        self.history.append(Turn(question=OPENING_QUESTION))
        return OPENING_QUESTION

    def record_answer(self, text: str) -> None:
        if not self.history:
            self.history.append(Turn(question=OPENING_QUESTION))
        self.history[-1].answer = (text or "").strip()

    async def next_question(self) -> str:
        """Ask the model what to say next, given everything so far."""
        result = await self.provider.complete(
            messages=build_messages(self.history),
            json_object=False,
            # Warmer than scoring: identical phrasing every interview is the
            # thing that makes a demo look scripted.
            temperature=0.8,
            max_tokens=120,
        )
        question = clean_question(result.content)
        if not question:
            # The model returned nothing usable. A generic prompt keeps the
            # conversation alive, which matters more mid-interview than an
            # elegant follow-up.
            question = "Could you tell me a little more about that?"
        self.history.append(Turn(question=question))
        return question

    def closing(self) -> str:
        return "Thank you, that is the end of the interview. You did well to keep going."
