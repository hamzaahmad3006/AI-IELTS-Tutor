"""IELTS band to CEFR level mapping.

Uses the alignment published by the IELTS partners. The boundaries are wide
because the two scales measure different things — a CEFR level is a description
of what someone can do, not a score — so this is reported as an indication
rather than a precise equivalence.
"""

from __future__ import annotations

#: (minimum overall band, CEFR level). Checked from the top down.
_BANDS: tuple[tuple[float, str], ...] = (
    (8.5, "C2"),
    (7.0, "C1"),
    (5.5, "B2"),
    (4.0, "B1"),
    (3.0, "A2"),
)

_DESCRIPTIONS = {
    "C2": "Fully operational command; handles complex, subtle language with ease.",
    "C1": "Operational command; handles complex language and detailed argument.",
    "B2": "Generally effective command; copes with complex language in familiar areas.",
    "B1": "Partial command; handles overall meaning in most situations.",
    "A2": "Basic competence limited to familiar situations.",
    "A1": "Occasional command; understands only very basic, familiar language.",
}


def band_to_cefr(overall_band: float | None) -> str | None:
    """CEFR level for an overall band, or None when nothing was measured."""
    if overall_band is None:
        return None
    for minimum, level in _BANDS:
        if overall_band >= minimum:
            return level
    return "A1"


def cefr_description(level: str | None) -> str:
    if level is None:
        return "Not enough evidence yet to estimate a CEFR level."
    return _DESCRIPTIONS.get(level, "")
