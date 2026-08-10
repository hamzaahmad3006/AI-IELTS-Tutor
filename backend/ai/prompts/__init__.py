"""Versioned prompt registry and the templates registered into it."""

from ai.prompts.registry import (
    PromptTemplate,
    all_templates,
    build,
    get,
    register,
)

# Importing the rubrics registers their templates as a side effect, so the
# registry is fully populated by the time anything asks it for a prompt.
from ai.rubrics import speaking_rubric, writing_rubric  # noqa: F401
from ai import generation  # noqa: F401,E402  (registers the generation prompts)

__all__ = ["PromptTemplate", "all_templates", "build", "get", "register"]
