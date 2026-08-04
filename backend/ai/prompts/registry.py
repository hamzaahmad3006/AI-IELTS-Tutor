"""Versioned prompt registry.

Scores are only comparable if the prompt that produced them is known. Change a
rubric's wording and every band it produces shifts slightly — without a recorded
version, last month's band 6.5 and today's band 6.5 are quietly different
measurements, and a trend chart built from both is misleading.

Every prompt therefore carries an id and a version, and the version is written
onto the `ai_interactions` row for each call. Bumping the version is a
deliberate act: it marks the point after which scores are on a new basis.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ai.provider import Message


@dataclass(frozen=True)
class PromptTemplate:
    """One registered prompt, identified by id and version."""

    id: str
    version: str
    #: What this prompt is for, in one line — shown in the admin listing.
    description: str
    build: Callable[..., list[Message]]

    @property
    def label(self) -> str:
        return f"{self.id}@{self.version}"


_REGISTRY: dict[str, PromptTemplate] = {}


def register(template: PromptTemplate) -> PromptTemplate:
    """Add a template. Registering the same id twice is a programming error."""
    if template.id in _REGISTRY:
        raise ValueError(f"Prompt '{template.id}' is already registered")
    _REGISTRY[template.id] = template
    return template


def get(prompt_id: str) -> PromptTemplate:
    if prompt_id not in _REGISTRY:
        raise KeyError(f"No prompt registered as '{prompt_id}'")
    return _REGISTRY[prompt_id]


def build(prompt_id: str, **kwargs: Any) -> tuple[list[Message], PromptTemplate]:
    """Build the messages and hand back the template that produced them.

    Returned together so a caller cannot record a version it did not actually
    use — the pairing is the point.
    """
    template = get(prompt_id)
    return template.build(**kwargs), template


def all_templates() -> list[PromptTemplate]:
    return sorted(_REGISTRY.values(), key=lambda t: t.id)


def reset_for_tests() -> None:
    """Clear the registry. Only for tests that register throwaway prompts."""
    _REGISTRY.clear()
