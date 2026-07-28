"""Spaced-repetition scheduling (SM-2).

Pure functions so the algorithm can be unit-tested without a database.
Grades follow the SM-2 convention: 0-2 = failed recall, 3-5 = successful.
"""

from __future__ import annotations

from dataclasses import dataclass

MIN_EASE = 1.3
DEFAULT_EASE = 2.5
PASS_THRESHOLD = 3


@dataclass(frozen=True)
class ScheduleState:
    repetitions: int
    interval_days: int
    ease_factor: float


def next_state(state: ScheduleState, grade: int) -> ScheduleState:
    """Return the next scheduling state for a review graded 0-5."""
    if not 0 <= grade <= 5:
        raise ValueError("grade must be between 0 and 5")

    # A failed recall resets the streak; the item comes back the next day.
    if grade < PASS_THRESHOLD:
        return ScheduleState(
            repetitions=0,
            interval_days=1,
            ease_factor=max(MIN_EASE, state.ease_factor - 0.20),
        )

    repetitions = state.repetitions + 1
    if repetitions == 1:
        interval = 1
    elif repetitions == 2:
        interval = 6
    else:
        interval = max(1, round(state.interval_days * state.ease_factor))

    # Standard SM-2 ease update: harder recalls shrink the factor.
    ease = state.ease_factor + (0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))
    return ScheduleState(
        repetitions=repetitions,
        interval_days=interval,
        ease_factor=max(MIN_EASE, round(ease, 3)),
    )
