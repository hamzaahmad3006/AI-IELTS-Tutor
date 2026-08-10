"""Smoke test: practice content generation.

Runs against the mock provider, so this proves the prompts, the validation and
the batching -- not that any model writes good IELTS questions. That judgement
is why generated items are drafts for a human rather than content served to
learners, and no test can substitute for it.

The assertions that matter are about cost and about refusal: an uncapped batch
is an unbounded bill, and an item that fails to parse must be reported rather
than silently dropped from something the caller paid for.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_generation.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

from fastapi.testclient import TestClient  # noqa: E402

from ai.generation import (  # noqa: E402
    MAX_BATCH,
    GenerationRequest,
    build_passage_messages,
    build_speaking_questions_messages,
    build_writing_prompt_messages,
    prompt_kwargs,
)
from ai.prompts import all_templates  # noqa: E402
from core.config import get_settings  # noqa: E402
from main import app  # noqa: E402


def check_prompts_are_registered() -> None:
    ids = {t.id for t in all_templates()}
    assert {
        "generate.passage",
        "generate.writing_prompt",
        "generate.speaking_questions",
    } <= ids, ids

    # Versioned like the scoring prompts, so generated content can be traced to
    # the prompt revision that produced it when a batch turns out to be bad.
    for template in all_templates():
        if template.id.startswith("generate."):
            assert template.version and template.description


def check_prompt_content() -> None:
    """The instructions that keep generated items usable."""
    passage = build_passage_messages(topic="urbanisation", difficulty="hard")
    system = passage[0]["content"]

    # One defensible answer, or write a different question. A question with two
    # arguable answers marks a correct learner wrong.
    assert "exactly one defensible answer" in system
    # Verbatim evidence, because a reviewer uses it to check the question is
    # answerable at all and a paraphrase proves nothing.
    assert "verbatim" in system
    # Not a published passage: reusing one is both a copyright problem and
    # useless practice for anyone who has seen it.
    assert "well-known published" in system
    assert "hard" in system
    assert "urbanisation" in passage[1]["content"]

    # Task 1 differs by exam type, and getting it wrong is the most common
    # failure: a chart description handed to someone sitting General Training,
    # who will be asked for a letter.
    academic = build_writing_prompt_messages(task_type=1, exam_type="academic")
    general = build_writing_prompt_messages(task_type=1, exam_type="general")
    assert "letter" in general[0]["content"]
    assert "letter" not in academic[0]["content"]
    # The app has no chart images, so Task 1 data has to be stated in words.
    assert "IN WORDS" in academic[0]["content"]

    # Each speaking part wants a different kind of question.
    part1 = build_speaking_questions_messages(part=1)[0]["content"]
    part3 = build_speaking_questions_messages(part=3)[0]["content"]
    assert "familiar" in part1 and "abstract" in part3


def check_request_validation() -> None:
    GenerationRequest(kind="passage", count=1).validated()
    GenerationRequest(kind="passage", count=MAX_BATCH).validated()

    for bad in (0, -1, MAX_BATCH + 1, 1000):
        try:
            GenerationRequest(kind="passage", count=bad).validated()
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"count {bad} was accepted")

    try:
        GenerationRequest(kind="passage", difficulty="impossible").validated()
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an unknown difficulty was accepted")

    # Each kind gets only the arguments its template takes; passing a part to a
    # passage template would be a TypeError at build time.
    assert set(prompt_kwargs(GenerationRequest(kind="passage"))) == {
        "topic",
        "difficulty",
    }
    assert "part" in prompt_kwargs(GenerationRequest(kind="speaking_questions"))

    try:
        prompt_kwargs(GenerationRequest(kind="nonsense"))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("an unknown kind was accepted")


def run() -> None:
    check_prompts_are_registered()
    check_prompt_content()
    check_request_validation()

    settings = get_settings()
    with TestClient(app) as client:
        admin = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={
                    "email": settings.seed_admin_email,
                    "password": settings.seed_admin_password,
                },
            ).json()["tokens"]["accessToken"]
        }

        r = client.post(
            "/v1/admin/generate",
            headers=admin,
            json={"kind": "passage", "count": 2, "difficulty": "medium"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["requested"] == 2
        # The mock provider returns a scoring shape, not a passage, so items
        # legitimately fail to validate. What matters is that the failure is
        # reported rather than silently dropped from something that was paid for.
        assert len(body["generated"]) + len(body["failures"]) == 2, body

        for item in body["generated"]:
            assert item["kind"] == "passage"
            assert item["item"]
            # Stamped, so a bad batch can be traced to the prompt revision.
            assert item["promptId"] == "generate.passage"
            assert item["promptVersion"]

        # An over-sized batch is refused rather than clamped: silently
        # generating ten when fifty were asked for hides a cost decision the
        # caller thought they had made.
        over = client.post(
            "/v1/admin/generate",
            headers=admin,
            json={"kind": "passage", "count": 500},
        )
        assert over.status_code in (400, 422), over.text

        # A learner cannot spend the platform's money.
        client.post(
            "/v1/auth/register",
            json={
                "fullName": "Curious Learner",
                "email": "generate@example.com",
                "password": "StrongPass123",
            },
        )
        learner = {
            "Authorization": "Bearer "
            + client.post(
                "/v1/auth/login",
                json={"email": "generate@example.com", "password": "StrongPass123"},
            ).json()["tokens"]["accessToken"]
        }
        assert (
            client.post(
                "/v1/admin/generate",
                headers=learner,
                json={"kind": "passage", "count": 1},
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/v1/admin/generate", json={"kind": "passage", "count": 1}
            ).status_code
            in (401, 403)
        )

    print("GENERATION SMOKE TEST PASSED")


if __name__ == "__main__":
    run()
