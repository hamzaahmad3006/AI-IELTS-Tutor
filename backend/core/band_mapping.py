"""Raw-score -> IELTS band mapping tables (SRS Appendix B).

Representative, configurable thresholds for 40-question sets. Reading differs by
exam type; Listening is shared. Real thresholds are calibrated per test set."""

from __future__ import annotations

# Each row: (min_raw, max_raw, band)
BandRow = tuple[int, int, float]

READING_ACADEMIC: tuple[BandRow, ...] = (
    (39, 40, 9.0),
    (37, 38, 8.5),
    (35, 36, 8.0),
    (33, 34, 7.5),
    (30, 32, 7.0),
    (27, 29, 6.5),
    (23, 26, 6.0),
    (19, 22, 5.5),
    (15, 18, 5.0),
    (13, 14, 4.5),
    (10, 12, 4.0),
    (8, 9, 3.5),
    (6, 7, 3.0),
    (4, 5, 2.5),
)

READING_GENERAL: tuple[BandRow, ...] = (
    (40, 40, 9.0),
    (39, 39, 8.5),
    (37, 38, 8.0),
    (36, 36, 7.5),
    (34, 35, 7.0),
    (32, 33, 6.5),
    (30, 31, 6.0),
    (27, 29, 5.5),
    (23, 26, 5.0),
    (19, 22, 4.5),
    (15, 18, 4.0),
    (12, 14, 3.5),
    (9, 11, 3.0),
)

LISTENING: tuple[BandRow, ...] = (
    (39, 40, 9.0),
    (37, 38, 8.5),
    (35, 36, 8.0),
    (32, 34, 7.5),
    (30, 31, 7.0),
    (26, 29, 6.5),
    (23, 25, 6.0),
    (18, 22, 5.5),
    (16, 17, 5.0),
    (13, 15, 4.5),
    (10, 12, 4.0),
    (8, 9, 3.5),
    (6, 7, 3.0),
)


def raw_to_band(raw: int, total: int, table: tuple[BandRow, ...]) -> float:
    """Scale the raw score to a 40-question basis, then map to a band."""
    if total <= 0:
        return 0.0
    scaled = round(raw / total * 40)
    for lo, hi, band in table:
        if lo <= scaled <= hi:
            return band
    # Below the lowest defined threshold.
    return 2.5 if scaled >= 3 else 0.0


def reading_band(raw: int, total: int, exam_type: str) -> float:
    table = READING_GENERAL if exam_type == "general" else READING_ACADEMIC
    return raw_to_band(raw, total, table)


def listening_band(raw: int, total: int) -> float:
    return raw_to_band(raw, total, LISTENING)
