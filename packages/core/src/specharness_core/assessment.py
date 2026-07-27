"""The LLM Readiness Gate's domain (SPEC-011, ADR-006).

Pure domain (ADR-001): the *shape* of a semantic assessment and the *decisions*
around it — the schema the model must return, the score→block rule, the audited
override, and the content hash that keys the cache. The litellm call, the prompt
text and the persistence live in adapters.

Testabilidade, ambiguidade, contradição and completude are semantic judgments —
that is what justifies the LLM layer (ADR-006). The score informs; a human
decides via an audited override.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

#: The issue taxonomy the model must use (SPEC-011, critério 1; evals rubric).
IssueCategory = Literal["testabilidade", "ambiguidade", "contradição", "completude"]
ISSUE_CATEGORIES: tuple[str, ...] = ("testabilidade", "ambiguidade", "contradição", "completude")

#: Below this the LLM layer blocks approved -> ready (rubric: <70 não-ready).
DEFAULT_THRESHOLD = 70


class ReadinessIssue(BaseModel):
    """One actionable semantic issue (SPEC-011, critério 1)."""

    category: IssueCategory
    description: str
    suggestion: str


class ReadinessAssessment(BaseModel):
    """The structured output the model MUST return (SPEC-011, métrica 2).

    A response that does not validate against this schema triggers a retry in
    the adapter — never free-text parsing.
    """

    score: int = Field(ge=0, le=100)
    issues: list[ReadinessIssue] = Field(default_factory=list)


@dataclass(frozen=True)
class Evaluation:
    """The gate's verdict on a spec: the assessment plus how it was produced."""

    score: int
    issues: tuple[ReadinessIssue, ...]
    model: str
    cost_usd: float | None
    cached: bool = False

    def blocks(self, threshold: int = DEFAULT_THRESHOLD) -> bool:
        """Whether this score blocks the approved -> ready transition (critério 2)."""
        return self.score < threshold

    @property
    def cost_label(self) -> str:
        return "n/d" if self.cost_usd is None else f"US$ {self.cost_usd:.6f}"


@dataclass(frozen=True)
class Override:
    """An audited Tech Lead override of the gate (SPEC-011, critério 3)."""

    spec_id: str
    author: str
    justification: str
    at: date


def content_hash(text: str, salt: str = "") -> str:
    """A stable cache key for a spec's content (SPEC-011, critério 5, métrica 3).

    The `salt` folds the prompt version in, so a prompt change re-evaluates
    instead of serving a stale cached score.
    """
    payload = f"{salt}\n{text}" if salt else text
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
