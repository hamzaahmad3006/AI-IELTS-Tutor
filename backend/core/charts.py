"""SVG charts for Academic Writing Task 1.

Task 1 asks a candidate to describe visual data. Ours stated its figures in
prose instead -- "the chart shows 45 per cent in 2000, rising to 50 per cent" --
which is not the task. Reading numbers out of a sentence and reading them off a
graph are different skills, and only one of them is being examined.

SVG rather than raster: it is text, so it diffs, it scales to any screen without
a second asset, and generating it needs no image library.

Deliberately plain. A Task 1 chart is a stimulus, not a data-visualisation
exercise: gridlines, axis labels and honest proportions matter, and styling does
not. Anything decorative competes with the thing the candidate is meant to be
reading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import escape as _escape_text


def _escape_attr(value: str) -> str:
    """Escape for an attribute value.

    saxutils.escape handles &, < and > but leaves quotes alone, which is fine
    in element text and breaks the document in an attribute: a title
    containing a double quote closes aria-label early and the rest of the tag
    becomes garbage. Titles are data, so this has to hold for any of them.
    """
    return _escape_text(value, {'"': "&quot;", "'": "&apos;"})


def escape(value: str) -> str:
    """Escape for element text."""
    return _escape_text(value)

WIDTH = 720
HEIGHT = 420
PADDING_LEFT = 70
PADDING_BOTTOM = 60
PADDING_TOP = 50
PADDING_RIGHT = 30

#: Distinguishable in greyscale and to the common forms of colour blindness.
#: A chart whose series are told apart only by hue excludes the candidates
#: least able to ask for an alternative.
SERIES_COLOURS = ("#4F46E5", "#0D9488", "#B45309", "#9333EA")

#: Dash patterns carry the same information as colour, so a printed or
#: greyscale copy is still readable.
SERIES_DASHES = ("", "6 4", "2 3", "10 3 2 3")


@dataclass
class Series:
    label: str
    values: list[float]


@dataclass
class ChartSpec:
    title: str
    #: X-axis categories: years, months, groups.
    categories: list[str]
    series: list[Series]
    y_label: str = ""
    #: "line" or "bar". Line for change over time, bar for comparison between
    #: groups -- the choice is part of what makes a Task 1 chart readable.
    kind: str = "line"
    unit: str = ""
    notes: list[str] = field(default_factory=list)

    def validated(self) -> ChartSpec:
        if not self.categories:
            raise ValueError("A chart needs at least one category")
        if not self.series:
            raise ValueError("A chart needs at least one series")
        for item in self.series:
            if len(item.values) != len(self.categories):
                raise ValueError(
                    f"Series '{item.label}' has {len(item.values)} values for "
                    f"{len(self.categories)} categories. A chart drawn from "
                    f"mismatched data is a chart the candidate cannot describe "
                    f"correctly, and they would be marked down for our bug."
                )
        if self.kind not in ("line", "bar"):
            raise ValueError(f"Unknown chart kind: {self.kind}")
        return self


def _nice_ceiling(value: float) -> float:
    """Round an axis maximum up to something a human would choose.

    An axis topping out at 63.7 is technically correct and unreadable. Task 1
    candidates quote figures off the gridlines, so the gridlines have to land
    on numbers worth quoting.
    """
    if value <= 0:
        return 10
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if value <= step:
            return float(step)
    return float(int(value / 1000 + 1) * 1000)


def render(spec: ChartSpec) -> str:
    """Draw the chart as a standalone SVG document."""
    spec = spec.validated()

    highest = max(max(s.values) for s in spec.series)
    top = _nice_ceiling(highest)

    plot_width = WIDTH - PADDING_LEFT - PADDING_RIGHT
    plot_height = HEIGHT - PADDING_TOP - PADDING_BOTTOM

    def y_for(value: float) -> float:
        return PADDING_TOP + plot_height * (1 - value / top)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" '
        f'aria-label="{_escape_attr(spec.title)}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{WIDTH / 2}" y="28" text-anchor="middle" font-family="sans-serif" '
        f'font-size="17" font-weight="600" fill="#131B2E">{escape(spec.title)}</text>',
    ]

    # Gridlines and y-axis labels. Five intervals: enough to read a value
    # against, few enough not to clutter.
    for index in range(6):
        value = top * index / 5
        y = y_for(value)
        parts.append(
            f'<line x1="{PADDING_LEFT}" y1="{y:.1f}" x2="{WIDTH - PADDING_RIGHT}" '
            f'y2="{y:.1f}" stroke="#E2E7FF" stroke-width="1"/>'
        )
        label = f"{value:g}{spec.unit}"
        parts.append(
            f'<text x="{PADDING_LEFT - 10}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-family="sans-serif" font-size="12" fill="#464555">{label}</text>'
        )

    if spec.y_label:
        parts.append(
            f'<text x="18" y="{PADDING_TOP + plot_height / 2}" '
            f'transform="rotate(-90 18 {PADDING_TOP + plot_height / 2})" '
            f'text-anchor="middle" font-family="sans-serif" font-size="12" '
            f'fill="#464555">{escape(spec.y_label)}</text>'
        )

    count = len(spec.categories)
    if spec.kind == "line":
        step = plot_width / max(1, count - 1)
        x_for = lambda i: PADDING_LEFT + step * i  # noqa: E731
    else:
        step = plot_width / count
        x_for = lambda i: PADDING_LEFT + step * (i + 0.5)  # noqa: E731

    for index, category in enumerate(spec.categories):
        parts.append(
            f'<text x="{x_for(index):.1f}" y="{HEIGHT - PADDING_BOTTOM + 22}" '
            f'text-anchor="middle" font-family="sans-serif" font-size="12" '
            f'fill="#464555">{escape(category)}</text>'
        )

    # Axes drawn last of the furniture, so they sit on top of the gridlines.
    parts.append(
        f'<line x1="{PADDING_LEFT}" y1="{PADDING_TOP}" x2="{PADDING_LEFT}" '
        f'y2="{HEIGHT - PADDING_BOTTOM}" stroke="#464555" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{PADDING_LEFT}" y1="{HEIGHT - PADDING_BOTTOM}" '
        f'x2="{WIDTH - PADDING_RIGHT}" y2="{HEIGHT - PADDING_BOTTOM}" '
        f'stroke="#464555" stroke-width="1.5"/>'
    )

    for series_index, series in enumerate(spec.series):
        colour = SERIES_COLOURS[series_index % len(SERIES_COLOURS)]
        dash = SERIES_DASHES[series_index % len(SERIES_DASHES)]

        if spec.kind == "line":
            points = " ".join(
                f"{x_for(i):.1f},{y_for(v):.1f}" for i, v in enumerate(series.values)
            )
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(
                f'<polyline points="{points}" fill="none" stroke="{colour}" '
                f'stroke-width="2.5"{dash_attr}/>'
            )
            for i, value in enumerate(series.values):
                parts.append(
                    f'<circle cx="{x_for(i):.1f}" cy="{y_for(value):.1f}" r="3.5" '
                    f'fill="{colour}"/>'
                )
        else:
            group_width = step * 0.8
            bar_width = group_width / len(spec.series)
            for i, value in enumerate(series.values):
                x = x_for(i) - group_width / 2 + bar_width * series_index
                y = y_for(value)
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                    f'height="{HEIGHT - PADDING_BOTTOM - y:.1f}" fill="{colour}"/>'
                )

    # Legend, only when there is more than one series. A legend for a single
    # line is furniture that explains nothing.
    if len(spec.series) > 1:
        x = PADDING_LEFT
        for series_index, series in enumerate(spec.series):
            colour = SERIES_COLOURS[series_index % len(SERIES_COLOURS)]
            parts.append(
                f'<rect x="{x}" y="{HEIGHT - 22}" width="14" height="10" fill="{colour}"/>'
            )
            parts.append(
                f'<text x="{x + 20}" y="{HEIGHT - 13}" font-family="sans-serif" '
                f'font-size="12" fill="#464555">{escape(series.label)}</text>'
            )
            x += 34 + len(series.label) * 7

    parts.append("</svg>")
    return "\n".join(parts)


def describe(spec: ChartSpec) -> str:
    """A text description of the same data.

    Not a replacement for the chart -- reading figures off a graph is the skill
    being examined. This is the accessible alternative, for a candidate using a
    screen reader, and it is generated from the same numbers so the two cannot
    disagree.
    """
    lines = [f"{spec.title}."]
    if spec.y_label:
        lines.append(f"Vertical axis: {spec.y_label}.")
    for series in spec.series:
        pairs = ", ".join(
            f"{category} {value:g}{spec.unit}"
            for category, value in zip(spec.categories, series.values)
        )
        lines.append(f"{series.label}: {pairs}.")
    lines.extend(spec.notes)
    return " ".join(lines)
