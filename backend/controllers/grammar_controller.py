"""Grammar controller: lesson library + weakness-targeted recommendations."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.grammar import GrammarLesson
from models.user import User

from .base import CamelModel
from .weakness_controller import WeaknessService


# ---------- Schemas ----------
class GrammarLessonSummary(CamelModel):
    id: str
    title: str
    concept_tag: str
    summary: str
    level: str
    minutes: int
    recommended: bool = False


class GrammarLessonDetail(CamelModel):
    id: str
    title: str
    concept_tag: str
    summary: str
    body: str
    examples: list[dict[str, str]]
    level: str
    minutes: int


class GrammarLessonList(CamelModel):
    items: list[GrammarLessonSummary]
    recommended_count: int


# ---------- Seeding (dev/demo content) ----------
_SEED_LESSONS: list[dict[str, object]] = [
    {
        "title": "Articles: a, an and the",
        "concept_tag": "articles",
        "level": "beginner",
        "minutes": 5,
        "summary": "When to use a/an, the, or no article at all.",
        "body": (
            "Use 'a' or 'an' when a noun is singular, countable and mentioned for "
            "the first time. Use 'the' when the listener already knows which thing "
            "you mean, or when it is unique. Use no article for plural or "
            "uncountable nouns talking about things in general."
        ),
        "examples": [
            {
                "incorrect": "I saw a accident on the road.",
                "correct": "I saw an accident on the road.",
                "note": "Use 'an' before a vowel sound.",
            },
            {
                "incorrect": "Technology has changed the society.",
                "correct": "Technology has changed society.",
                "note": "No article when speaking generally.",
            },
        ],
        "weakness_tags": ["articles", "grammatical_range"],
    },
    {
        "title": "Subject-verb agreement",
        "concept_tag": "subject_verb_agreement",
        "level": "beginner",
        "minutes": 6,
        "summary": "Making the verb match its subject, even at a distance.",
        "body": (
            "A singular subject takes a singular verb, and a plural subject takes "
            "a plural verb. Watch for phrases between the subject and verb: the "
            "verb agrees with the subject, not with the nearest noun."
        ),
        "examples": [
            {
                "incorrect": "The number of students are increasing.",
                "correct": "The number of students is increasing.",
                "note": "The subject is 'the number', which is singular.",
            },
            {
                "incorrect": "It make life easier.",
                "correct": "It makes life easier.",
                "note": "Third-person singular takes -s.",
            },
        ],
        "weakness_tags": ["subject_verb_agreement", "grammatical_range"],
    },
    {
        "title": "Complex sentences for a higher band",
        "concept_tag": "sentence_complexity",
        "level": "intermediate",
        "minutes": 8,
        "summary": "Combine ideas with subordinate clauses instead of short sentences.",
        "body": (
            "Band 7+ writing shows a range of structures. Join related ideas with "
            "subordinating conjunctions (although, whereas, because, while) and "
            "relative clauses (which, who, that) rather than writing a series of "
            "short simple sentences."
        ),
        "examples": [
            {
                "incorrect": "Technology is useful. It also creates problems.",
                "correct": "Although technology is useful, it also creates problems.",
                "note": "One complex sentence shows more range than two simple ones.",
            },
            {
                "incorrect": "Cities are growing. This causes pollution.",
                "correct": "Cities are growing rapidly, which causes severe pollution.",
                "note": "A relative clause links the cause and effect.",
            },
        ],
        "weakness_tags": ["grammatical_range", "sentence_complexity"],
    },
    {
        "title": "Cohesive devices that raise your band",
        "concept_tag": "cohesion",
        "level": "intermediate",
        "minutes": 6,
        "summary": "Linking ideas without overusing 'firstly, secondly, finally'.",
        "body": (
            "Cohesion is judged on how naturally ideas connect. Vary your linkers "
            "(furthermore, consequently, in contrast, by comparison) and use "
            "referencing (this trend, such measures) so paragraphs flow instead of "
            "reading as a list."
        ),
        "examples": [
            {
                "incorrect": "Firstly, it is cheap. Secondly, it is fast. Thirdly, it is easy.",
                "correct": "It is cheap and, more importantly, considerably faster than the alternatives.",
                "note": "Mechanical listing limits the Coherence & Cohesion score.",
            },
        ],
        "weakness_tags": ["coherence_cohesion", "cohesion_connectors"],
    },
    {
        "title": "Precise vocabulary instead of vague words",
        "concept_tag": "lexical_precision",
        "level": "intermediate",
        "minutes": 7,
        "summary": "Replacing 'good', 'bad' and 'thing' with topic-specific words.",
        "body": (
            "Lexical Resource rewards precision, not rare words for their own sake. "
            "Replace vague adjectives with specific ones and use collocations that "
            "native speakers actually use."
        ),
        "examples": [
            {
                "incorrect": "Pollution is a very bad thing for the environment.",
                "correct": "Pollution is detrimental to the environment.",
                "note": "One precise word replaces a vague phrase.",
            },
            {
                "incorrect": "The graph shows a big rise.",
                "correct": "The graph shows a substantial increase.",
                "note": "'Substantial increase' is a natural collocation.",
            },
        ],
        "weakness_tags": ["lexical_resource", "lexical_repetition"],
    },
    {
        "title": "Fully answering the task",
        "concept_tag": "task_response",
        "level": "intermediate",
        "minutes": 6,
        "summary": "Addressing every part of the prompt with developed ideas.",
        "body": (
            "Task Response falls when a prompt asks two things and only one is "
            "answered, or when a position is stated but never developed. Identify "
            "each part of the question, take a clear position, and support every "
            "main idea with a reason and an example."
        ),
        "examples": [
            {
                "incorrect": "Discuss both views and give your opinion. -> only one view discussed.",
                "correct": "Both views are covered in separate paragraphs, then a clear opinion is given.",
                "note": "Missing a part of the prompt caps Task Response.",
            },
        ],
        "weakness_tags": ["task_response", "task2_development"],
    },
    {
        "title": "Reducing hesitation and fillers",
        "concept_tag": "fluency",
        "level": "intermediate",
        "minutes": 5,
        "summary": "Speaking with fewer 'um's and smoother self-correction.",
        "body": (
            "Fluency is about sustaining speech, not speed. Buy thinking time with "
            "natural phrases ('That's an interesting question', 'Let me think') "
            "rather than filled pauses, and avoid restarting sentences repeatedly."
        ),
        "examples": [
            {
                "incorrect": "Um... I think... um... it is, uh, good.",
                "correct": "That's an interesting question. I'd say it's genuinely beneficial, because...",
                "note": "A stalling phrase sounds far more fluent than filler.",
            },
        ],
        "weakness_tags": ["fluency_coherence", "filler_words"],
    },
    {
        "title": "Pronunciation: word and sentence stress",
        "concept_tag": "pronunciation",
        "level": "intermediate",
        "minutes": 6,
        "summary": "Stressing the right syllables and key words.",
        "body": (
            "Intelligibility depends more on stress and intonation than on having "
            "a particular accent. Stress the correct syllable in long words, and "
            "emphasise the content words that carry your meaning."
        ),
        "examples": [
            {
                "incorrect": "PHO-to-graph / pho-TO-graph-er said with the same stress.",
                "correct": "PHO-to-graph but pho-TO-gra-pher.",
                "note": "Stress moves when the word form changes.",
            },
        ],
        "weakness_tags": ["pronunciation", "pron_word_stress"],
    },
]


async def _ensure_seeded(session: AsyncSession) -> None:
    count = await session.scalar(select(func.count()).select_from(GrammarLesson))
    if count and count > 0:
        return
    for row in _SEED_LESSONS:
        session.add(GrammarLesson(**row, source="seed"))
    await session.flush()


class GrammarController:
    @staticmethod
    async def list_lessons(
        session: AsyncSession, user: User, tag: str | None
    ) -> GrammarLessonList:
        """List lessons, flagging those that target the learner's weaknesses."""
        await _ensure_seeded(session)

        query = select(GrammarLesson)
        if tag:
            query = query.where(GrammarLesson.concept_tag == tag)
        lessons = list(await session.scalars(query))

        weaknesses = (await WeaknessService.list_for_user(session, user.id)).items
        weak_tags = {item.tag for item in weaknesses}

        items = [
            GrammarLessonSummary(
                id=lesson.id,
                title=lesson.title,
                concept_tag=lesson.concept_tag,
                summary=lesson.summary,
                level=lesson.level,
                minutes=lesson.minutes,
                recommended=bool(weak_tags & set(lesson.weakness_tags or [])),
            )
            for lesson in lessons
        ]
        # Recommended lessons first so the most useful work is at the top.
        items.sort(key=lambda item: (not item.recommended, item.title))
        return GrammarLessonList(
            items=items,
            recommended_count=sum(1 for item in items if item.recommended),
        )

    @staticmethod
    async def get_lesson(session: AsyncSession, lesson_id: str) -> GrammarLessonDetail:
        await _ensure_seeded(session)
        lesson = await session.get(GrammarLesson, lesson_id)
        if lesson is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
            )
        return GrammarLessonDetail(
            id=lesson.id,
            title=lesson.title,
            concept_tag=lesson.concept_tag,
            summary=lesson.summary,
            body=lesson.body,
            examples=list(lesson.examples or []),
            level=lesson.level,
            minutes=lesson.minutes,
        )
