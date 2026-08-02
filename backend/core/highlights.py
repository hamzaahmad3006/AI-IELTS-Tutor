"""Locate AI-flagged quotes inside the learner's own text.

The model is asked to quote verbatim, but models paraphrase, fix typos and
re-punctuate. Rather than trusting the quote, every one is located in the source
text and anything that cannot be found is dropped. A highlight over the wrong
words is worse than no highlight: it tells the learner they made a mistake they
did not make.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Highlight:
    start: int
    end: int
    quote: str
    tag: str
    note: str


def _normalise(text: str) -> str:
    """Lowercase and collapse whitespace, preserving length mapping separately."""
    return re.sub(r"\s+", " ", text).strip().lower()


def _find_span(source: str, quote: str) -> tuple[int, int] | None:
    """Character span of `quote` in `source`, or None if it is not really there.

    Tries an exact match first, then a whitespace-insensitive match, which is
    what rescues quotes that differ only by line breaks or double spaces.
    """
    if not quote.strip():
        return None

    index = source.find(quote)
    if index != -1:
        return index, index + len(quote)

    # Whitespace-insensitive: build a regex from the quote's words so any run of
    # whitespace in the source can match.
    words = [re.escape(word) for word in quote.split()]
    if not words:
        return None
    pattern = re.compile(r"\s+".join(words), re.IGNORECASE)
    match = pattern.search(source)
    if match:
        return match.start(), match.end()
    return None


def resolve_highlights(
    source: str,
    issues: list[dict[str, str]],
    *,
    max_highlights: int = 4,
) -> list[Highlight]:
    """Turn model-reported issues into spans that genuinely exist in `source`.

    Overlapping spans are dropped so the UI never has to render nested
    highlights, and the result is ordered by position for straightforward
    rendering and jump-to-next behaviour.
    """
    resolved: list[Highlight] = []
    for issue in issues:
        quote = str(issue.get("quote", "") or "")
        span = _find_span(source, quote)
        if span is None:
            continue
        start, end = span
        if any(start < existing.end and existing.start < end for existing in resolved):
            continue
        resolved.append(
            Highlight(
                start=start,
                end=end,
                quote=source[start:end],
                tag=str(issue.get("tag", "") or "general"),
                note=str(issue.get("note", "") or ""),
            )
        )
        if len(resolved) >= max_highlights:
            break

    resolved.sort(key=lambda h: h.start)
    return resolved
