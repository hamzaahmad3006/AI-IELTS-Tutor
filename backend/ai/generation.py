"""Generating practice content.

The seeded banks are small -- eight writing prompts, five passages, twenty-one
speaking questions. A learner practising daily exhausts them in a fortnight and
then re-answers questions they have memorised, which measures recall rather than
English.

Generated content is therefore about variety, not about replacing the seeds. The
seeds are known-good and stay; generation fills in around them.

Two constraints shape this.

Generated items are never served unreviewed. They land as drafts for an admin to
approve, because a model asked for an IELTS passage will occasionally produce
something subtly off -- a question with two defensible answers, a passage whose
"Not Given" is arguably "False" -- and a learner marked wrong by a broken
question learns the wrong lesson and distrusts the app.

Generation is a billed call per item, and unlike scoring it has no natural
ceiling: nothing stops someone requesting a thousand passages. So the batch size
is capped and the endpoint is admin-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from ai.prompts.registry import PromptTemplate, register
from ai.provider import Message

#: Most items one request may generate. Each is a billed call, and a caller who
#: wants fifty can ask five times and notice the cost.
MAX_BATCH = 10

_DIFFICULTIES = ("easy", "medium", "hard")


class GeneratedQuestion(BaseModel):
    question: str
    #: Present for multiple choice; absent for short answer.
    options: list[str] = Field(default_factory=list)
    answer: str
    #: Where in the passage the answer comes from. Reviewed by a human, so it
    #: has to be checkable rather than merely plausible.
    evidence: str = ""


class GeneratedPassage(BaseModel):
    title: str
    body: str
    questions: list[GeneratedQuestion]


class GeneratedWritingPrompt(BaseModel):
    task_type: int = Field(ge=1, le=2)
    prompt: str
    #: Academic or general training. A Task 1 prompt for the wrong exam type is
    #: the single most common way generated writing content goes wrong: a chart
    #: description handed to someone sitting General Training, who will be
    #: asked for a letter.
    exam_type: str = "academic"


class GeneratedSpeakingQuestions(BaseModel):
    part: int = Field(ge=1, le=3)
    topic: str
    questions: list[str]


@dataclass(frozen=True)
class GenerationRequest:
    kind: str
    count: int = 1
    difficulty: str = "medium"
    topic: str = ""
    exam_type: str = "academic"
    part: int = 1
    task_type: int = 2

    def validated(self) -> GenerationRequest:
        if self.count < 1 or self.count > MAX_BATCH:
            raise ValueError(f"count must be between 1 and {MAX_BATCH}")
        if self.difficulty not in _DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {_DIFFICULTIES}")
        return self


_SHARED_RULES = (
    "Write content suitable for an IELTS practice app. Follow the official "
    "test format exactly. Do not reuse well-known published passages or "
    "questions. Every question must have exactly one defensible answer that a "
    "careful reader can locate in the text; if you cannot write such a "
    "question, write a different one. Return ONLY a JSON object."
)


def build_passage_messages(
    topic: str = "", difficulty: str = "medium", count: int = 4
) -> list[Message]:
    subject = f" about {topic}" if topic else ""
    return [
        {
            "role": "system",
            "content": (
                f"You are an IELTS Reading item writer. {_SHARED_RULES} "
                "The passage must be 250-350 words of continuous prose at "
                f"{difficulty} difficulty. Return keys: title, body, questions. "
                "Each question has: question, options (empty list for short "
                "answer), answer, evidence. `evidence` must be a verbatim "
                "sentence from the passage that establishes the answer -- a "
                "reviewer uses it to check the question is answerable, so a "
                "paraphrase is useless."
            ),
        },
        {
            "role": "user",
            "content": f"Write one reading passage{subject} with {count} questions.",
        },
    ]


def build_writing_prompt_messages(
    task_type: int = 2, exam_type: str = "academic", topic: str = ""
) -> list[Message]:
    if task_type == 1 and exam_type == "general":
        shape = "a letter-writing task (formal, semi-formal or informal)"
    elif task_type == 1:
        shape = (
            "a data-description task. State the data IN WORDS, since the app "
            "has no chart images: describe the figures precisely enough that a "
            "candidate can write about them without seeing a graph"
        )
    else:
        shape = "an opinion, discussion or problem-solution essay question"

    subject = f" on the theme of {topic}" if topic else ""
    return [
        {
            "role": "system",
            "content": (
                f"You are an IELTS Writing item writer. {_SHARED_RULES} "
                f"Produce {shape} for {exam_type} Task {task_type}"
                f"{subject}. Return keys: task_type, prompt, exam_type."
            ),
        },
        {"role": "user", "content": "Write one task prompt."},
    ]


def build_speaking_questions_messages(
    part: int = 1, topic: str = "", count: int = 4
) -> list[Message]:
    guidance = {
        1: "short, familiar questions about the candidate's own life",
        2: "a cue card topic with three or four bullet points to cover",
        3: "abstract, analytical questions inviting a justified opinion",
    }[part]

    subject = f" about {topic}" if topic else ""
    return [
        {
            "role": "system",
            "content": (
                f"You are an IELTS Speaking examiner writing questions. "
                f"{_SHARED_RULES} Part {part} calls for {guidance}. "
                "Return keys: part, topic, questions."
            ),
        },
        {
            "role": "user",
            "content": f"Write {count} Part {part} questions{subject}.",
        },
    ]


PASSAGE_PROMPT = register(
    PromptTemplate(
        id="generate.passage",
        version="1.0.0",
        description="Generate an IELTS Reading passage with questions.",
        build=build_passage_messages,
    )
)

WRITING_PROMPT_PROMPT = register(
    PromptTemplate(
        id="generate.writing_prompt",
        version="1.0.0",
        description="Generate an IELTS Writing task prompt.",
        build=build_writing_prompt_messages,
    )
)

SPEAKING_QUESTIONS_PROMPT = register(
    PromptTemplate(
        id="generate.speaking_questions",
        version="1.0.0",
        description="Generate IELTS Speaking questions for one part.",
        build=build_speaking_questions_messages,
    )
)


#: What each kind returns, so a caller validates against the right shape.
SCHEMAS: dict[str, type[BaseModel]] = {
    "passage": GeneratedPassage,
    "writing_prompt": GeneratedWritingPrompt,
    "speaking_questions": GeneratedSpeakingQuestions,
}

PROMPT_IDS = {
    "passage": "generate.passage",
    "writing_prompt": "generate.writing_prompt",
    "speaking_questions": "generate.speaking_questions",
}


def prompt_kwargs(request: GenerationRequest) -> dict[str, Any]:
    """Arguments for the template this request needs."""
    if request.kind == "passage":
        return {"topic": request.topic, "difficulty": request.difficulty}
    if request.kind == "writing_prompt":
        return {
            "task_type": request.task_type,
            "exam_type": request.exam_type,
            "topic": request.topic,
        }
    if request.kind == "speaking_questions":
        return {"part": request.part, "topic": request.topic}
    raise ValueError(f"Unknown generation kind: {request.kind}")
