"""Unit tests for the pure pieces: rounding, error mapping, validators.

Separate from the smoke suites, which drive the whole app over HTTP. These
cover the small functions where a wrong answer is silent — a band rounded the
wrong way is still a plausible band, and an error mapped to the wrong code is
still an error.

Run with `pytest tests/unit`. The smoke suites stay as they are: they are
integration tests and pytest would add nothing to them.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_units.db")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import tests._env  # noqa: E402,F401  (pins AI_PROVIDER=mock before settings load)

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from ai.rubrics.writing_rubric import round_ielts  # noqa: E402
from controllers.speaking_controller import SpeakingSubmitRequest  # noqa: E402
from controllers.writing_controller import WritingSubmitRequest  # noqa: E402
from core.errors import code_for_status, type_for_code  # noqa: E402


class TestRoundIelts:
    """IELTS bands come in half steps, and the edges are where this goes wrong."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (6.0, 6.0),
            (6.24, 6.0),
            # Half UP, not half-to-even. Python's round(12.5) is 12, which
            # made every .25 average round down and quietly took half a band
            # off the learner. Official IELTS rounds .25 up.
            (6.25, 6.5),
            (5.25, 5.5),
            (7.25, 7.5),
            (6.26, 6.5),
            (6.74, 6.5),
            (6.75, 7.0),
            (6.5, 6.5),
        ],
    )
    def test_rounds_to_half_bands(self, raw: float, expected: float) -> None:
        assert round_ielts(raw) == expected

    @pytest.mark.parametrize("raw", [-1.0, -0.1, 0.0])
    def test_clamps_the_floor(self, raw: float) -> None:
        # A negative band is not a low score, it is a bug, and showing one
        # would tell a learner something impossible about their work.
        assert round_ielts(raw) == 0.0

    @pytest.mark.parametrize("raw", [9.0, 9.4, 100.0])
    def test_clamps_the_ceiling(self, raw: float) -> None:
        assert round_ielts(raw) == 9.0

    def test_output_is_always_a_valid_band(self) -> None:
        for step in range(-20, 220):
            value = round_ielts(step / 20)
            assert 0.0 <= value <= 9.0
            # Every result must land on a half step: 6.3 is not a band anyone
            # can be awarded.
            assert (value * 2) % 1 == 0


class TestErrorCodes:
    @pytest.mark.parametrize(
        ("status", "code"),
        [(401, "unauthenticated"), (403, "forbidden"), (404, "not_found")],
    )
    def test_known_statuses_map_to_named_codes(self, status: int, code: str) -> None:
        assert code_for_status(status) == code

    def test_unknown_client_and_server_errors_are_distinguished(self) -> None:
        # A client sending something wrong and a server falling over need
        # different responses from the caller; collapsing both to one code
        # tells them to retry a request that will never work.
        assert code_for_status(418) == "client_error"
        assert code_for_status(451) == "client_error"
        # 502 has its own code: an upstream failing is not this service
        # failing, and the two want different alerts.
        assert code_for_status(502) == "upstream_error"
        assert code_for_status(500) in ("internal_error", "server_error")

    def test_type_is_a_real_uri(self) -> None:
        # `about:blank` is RFC 7807's default and carries no information; a
        # real URI gives the code somewhere to be documented.
        uri = type_for_code("not_found")
        assert uri.startswith("http")
        assert uri.endswith("not_found")


class TestWritingValidator:
    ESSAY = "Urbanisation has reshaped how populations live. " * 10

    def test_accepts_a_normal_submission(self) -> None:
        payload = WritingSubmitRequest(essayText=self.ESSAY, taskType=2)
        assert payload.task_type == 2

    def test_rejects_an_empty_essay(self) -> None:
        # Not a validation nicety: an empty essay would be sent to the scorer
        # and billed for, to be told there was nothing there.
        with pytest.raises(ValidationError):
            WritingSubmitRequest(essayText="", taskType=2)

    @pytest.mark.parametrize("task_type", [0, 3, -1, 99])
    def test_rejects_a_task_that_does_not_exist(self, task_type: int) -> None:
        with pytest.raises(ValidationError):
            WritingSubmitRequest(essayText=self.ESSAY, taskType=task_type)

    def test_rejects_an_essay_beyond_the_ceiling(self) -> None:
        # The cap is a cost control as much as a validation: tokens are billed
        # per request and nobody writes an 8,000-character IELTS essay.
        with pytest.raises(ValidationError):
            WritingSubmitRequest(essayText="x" * 8_001, taskType=2)

    def test_defaults_to_task_two(self) -> None:
        assert WritingSubmitRequest(essayText=self.ESSAY).task_type == 2


class TestSpeakingValidator:
    TRANSCRIPT = "I would like to talk about my hometown in some detail."

    def test_accepts_a_normal_submission(self) -> None:
        payload = SpeakingSubmitRequest(transcript=self.TRANSCRIPT, part=2)
        assert payload.part == 2

    def test_part_is_optional(self) -> None:
        # Not every transcript comes from a numbered part; freeform practice
        # has no part and must not be forced to invent one.
        assert SpeakingSubmitRequest(transcript=self.TRANSCRIPT).part is None

    @pytest.mark.parametrize("part", [0, 4, -1])
    def test_rejects_a_part_that_does_not_exist(self, part: int) -> None:
        with pytest.raises(ValidationError):
            SpeakingSubmitRequest(transcript=self.TRANSCRIPT, part=part)

    def test_rejects_negative_duration(self) -> None:
        with pytest.raises(ValidationError):
            SpeakingSubmitRequest(
                transcript=self.TRANSCRIPT, part=1, durationSec=-1
            )

    def test_accepts_camel_case_from_the_wire(self) -> None:
        # The client sends camelCase; a validator that only accepted snake_case
        # would reject every real request while passing every test written in
        # Python.
        payload = SpeakingSubmitRequest(transcript=self.TRANSCRIPT, durationSec=42)
        assert payload.duration_sec == 42
