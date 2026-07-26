"""Spec schema and parser — the central contract of specharness (SPEC-001 §7).

A spec is a markdown file with YAML frontmatter. This module is pure domain:
no I/O, no framework imports (ADR-001). Everything here must stay importable
by CLI, server, hooks and adapters alike.
"""

from __future__ import annotations

import re
from datetime import date
from enum import StrEnum

import yaml
from pydantic import BaseModel, Field, field_validator

SPEC_ID_PATTERN = re.compile(r"^SPEC-\d{3,}$")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


class SpecStatus(StrEnum):
    """Lifecycle states (SPEC-001 §7.2). Order matters for transition rules."""

    DRAFT = "draft"
    APPROVED = "approved"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    DONE = "done"
    ARCHIVED = "archived"


class SpecType(StrEnum):
    PRODUCT = "product"
    FEATURE = "feature"
    ARCHITECTURE = "architecture"
    HARNESS = "harness"


#: Allowed forward transitions. Gate rules (Readiness, BDD) are enforced by
#: the services that call `can_transition`, not here — the domain only knows
#: the shape of the lifecycle.
ALLOWED_TRANSITIONS: dict[SpecStatus, frozenset[SpecStatus]] = {
    SpecStatus.DRAFT: frozenset({SpecStatus.APPROVED}),
    SpecStatus.APPROVED: frozenset({SpecStatus.READY, SpecStatus.DRAFT}),
    SpecStatus.READY: frozenset({SpecStatus.IN_PROGRESS, SpecStatus.APPROVED}),
    SpecStatus.IN_PROGRESS: frozenset({SpecStatus.VERIFYING, SpecStatus.READY}),
    SpecStatus.VERIFYING: frozenset({SpecStatus.DONE, SpecStatus.IN_PROGRESS}),
    SpecStatus.DONE: frozenset({SpecStatus.ARCHIVED}),
    SpecStatus.ARCHIVED: frozenset(),
}


class SpecParseError(ValueError):
    """Raised when a document cannot be parsed as a valid spec."""


class SpecFrontmatter(BaseModel):
    """The YAML frontmatter contract of every spec file."""

    spec: str
    title: str
    status: SpecStatus = SpecStatus.DRAFT
    type: SpecType = SpecType.FEATURE
    owner: str | None = None
    created: date | None = None
    updated: date | None = None
    version: float | str | None = None
    sprint: str | None = None
    tracker_refs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    adrs: list[str] = Field(default_factory=list)
    success_metrics: list[str] = Field(default_factory=list)
    acceptance: list[str] = Field(default_factory=list)

    @field_validator("spec")
    @classmethod
    def _valid_spec_id(cls, value: str) -> str:
        if not SPEC_ID_PATTERN.match(value):
            raise ValueError(f"invalid spec id {value!r}; expected e.g. 'SPEC-042'")
        return value

    @field_validator("depends_on")
    @classmethod
    def _valid_dependency_ids(cls, value: list[str]) -> list[str]:
        for dep in value:
            if not SPEC_ID_PATTERN.match(dep):
                raise ValueError(f"invalid dependency id {dep!r} in depends_on")
        return value


class ParsedSpec(BaseModel):
    """A parsed spec: validated frontmatter + raw markdown body."""

    frontmatter: SpecFrontmatter
    body: str

    @property
    def spec_id(self) -> str:
        return self.frontmatter.spec

    @property
    def gherkin_blocks(self) -> list[str]:
        """Extract fenced ```gherkin blocks from the body (used by the gate)."""
        return re.findall(r"```gherkin\s*\n(.*?)```", self.body, re.DOTALL)


def parse_spec(text: str) -> ParsedSpec:
    """Parse a spec document (frontmatter + body) or raise SpecParseError."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise SpecParseError("document has no YAML frontmatter block ('---' fences)")
    try:
        raw = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SpecParseError(f"invalid YAML in frontmatter: {exc}") from exc
    if not isinstance(raw, dict):
        raise SpecParseError("frontmatter must be a YAML mapping")
    try:
        frontmatter = SpecFrontmatter.model_validate(raw)
    except ValueError as exc:
        raise SpecParseError(str(exc)) from exc
    return ParsedSpec(frontmatter=frontmatter, body=text[match.end() :])


def can_transition(current: SpecStatus, target: SpecStatus) -> bool:
    """Whether the lifecycle allows moving from `current` to `target`."""
    return target in ALLOWED_TRANSITIONS[current]
