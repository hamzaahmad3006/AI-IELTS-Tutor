"""Seed every content bank, explicitly.

    python scripts/seed_content.py            # report what is present
    python scripts/seed_content.py --apply    # seed anything missing

Seeding happens lazily today: each controller has its own `_ensure_seeded` that
fires on the first request to reach it. That works right up until one feature
needs another's content before anyone has asked for it -- which already
happened, when the spoken interview asked for a cue card and cue cards were only
ever created by the cue-card endpoint. The first interview on a fresh database
failed with "No cue cards available".

Lazy seeding also makes provisioning non-deterministic: what a fresh deployment
contains depends on which endpoint a user happens to hit first, so two
environments meant to be identical are not.

This runs them all, in one place, on purpose. The individual `_ensure_seeded`
calls stay where they are -- they are a safety net for a database seeded by
something other than this script, and removing them would trade one failure mode
for another.

Idempotent: every seeder checks before inserting, so running twice is a no-op
and running against a partly-seeded database fills only the gaps.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from controllers.grammar_controller import _ensure_seeded as seed_grammar  # noqa: E402
from controllers.listening_controller import (  # noqa: E402
    _ensure_seeded as seed_listening,
)
from controllers.reading_controller import _ensure_seeded as seed_reading  # noqa: E402
from controllers.speaking_controller import (  # noqa: E402
    _ensure_cue_cards_seeded as seed_cue_cards,
)
from controllers.speaking_questions import (  # noqa: E402
    ensure_seeded as seed_speaking_questions,
)
from controllers.vocabulary_controller import (  # noqa: E402
    _ensure_seeded as seed_vocabulary,
)
from controllers.writing_controller import (  # noqa: E402
    _ensure_prompts_seeded as seed_writing_prompts,
)
from db.session import SessionLocal  # noqa: E402
from models.content import (  # noqa: E402
    AudioClip,
    ListeningQuestion,
    Passage,
    Question,
)
from models.cue_card import CueCard  # noqa: E402
from models.grammar import GrammarLesson  # noqa: E402
from models.speaking_question import SpeakingQuestion  # noqa: E402
from models.vocabulary import VocabItem  # noqa: E402
from models.writing_prompt import WritingPrompt  # noqa: E402

#: (label, seeder, model to count). Ordered as a learner meets them, which is
#: also the order that reads sensibly in the output.
SEEDERS = [
    ("writing prompts", seed_writing_prompts, WritingPrompt),
    ("reading passages", seed_reading, Passage),
    ("reading questions", None, Question),
    ("listening clips", seed_listening, AudioClip),
    ("listening questions", None, ListeningQuestion),
    ("speaking questions", seed_speaking_questions, SpeakingQuestion),
    ("cue cards", seed_cue_cards, CueCard),
    ("vocabulary items", seed_vocabulary, VocabItem),
    ("grammar lessons", seed_grammar, GrammarLesson),
]


async def _count(session: AsyncSession, model: type) -> int:
    return await session.scalar(select(func.count()).select_from(model)) or 0


async def report(session: AsyncSession) -> dict[str, int]:
    return {label: await _count(session, model) for label, _, model in SEEDERS}


async def seed_all(session: AsyncSession) -> dict[str, int]:
    """Run every seeder. Returns the row counts afterwards."""
    for label, seeder, _ in SEEDERS:
        if seeder is None:
            # Reading questions are created by the passage seeder; counting
            # them separately is still worth it, because a passage with no
            # questions is a practice screen with nothing to answer.
            continue
        await seeder(session)
    await session.commit()
    return await report(session)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="seed anything missing (default: report only)",
    )
    args = parser.parse_args(argv)

    async with SessionLocal() as session:
        before = await report(session)
        counts = await seed_all(session) if args.apply else before

    width = max(len(label) for label in counts)
    print("Content banks:" if args.apply else "Content banks (no changes made):")
    empty = []
    for label, count in counts.items():
        delta = count - before[label]
        suffix = f"  (+{delta})" if delta else ""
        print(f"  {label:<{width}}  {count:>4}{suffix}")
        if count == 0:
            empty.append(label)

    if empty:
        # Non-zero exit, so this is usable as a deployment gate. An empty bank
        # is a feature that will fail the first time someone opens it.
        print(f"\nEmpty: {', '.join(empty)}")
        if not args.apply:
            print("Run with --apply to seed them.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
