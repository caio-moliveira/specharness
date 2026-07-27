"""Commit <-> spec linking (SPEC-009, ADR-011).

Pure domain (ADR-001): given the commits (with their `Spec:` trailers already
extracted) and the spec registry, decide the links, the invalid links (a trailer
pointing at a spec that does not exist) and the two hygiene metrics — orphan
commits (no trailer) and orphan specs (in_progress with nothing linked).

The trailer is the source of truth (SPEC-001 §7.3). Orphans are a hygiene metric,
never a fatal error.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .ports.repository import Commit
from .specschema import SPEC_ID_PATTERN, SpecStatus


@dataclass(frozen=True)
class SpecInfo:
    """The registry's view of a spec, for linking (SPEC-003)."""

    spec_id: str
    status: str
    sprint: str | None = None

    @property
    def is_in_progress(self) -> bool:
        return self.status == SpecStatus.IN_PROGRESS


@dataclass(frozen=True)
class Link:
    """A commit's reference to a spec via a `Spec:` trailer."""

    commit_sha: str
    spec_id: str
    valid: bool  # o trailer tem formato SPEC-NNN E a spec existe


@dataclass(frozen=True)
class LinkingResult:
    """The full picture computed on each `track` run (métrica 3)."""

    links: tuple[Link, ...]
    orphan_commits: tuple[str, ...]
    orphan_specs: tuple[str, ...]

    @property
    def valid_links(self) -> tuple[Link, ...]:
        return tuple(link for link in self.links if link.valid)

    @property
    def invalid_links(self) -> tuple[Link, ...]:
        return tuple(link for link in self.links if not link.valid)

    @property
    def is_clean(self) -> bool:
        return not self.invalid_links and not self.orphan_commits and not self.orphan_specs


def link_commits(commits: Iterable[Commit], specs: Iterable[SpecInfo]) -> LinkingResult:
    """Link commits to specs by trailer, flagging invalid links and orphans.

    - A trailer that is well-formed (SPEC-NNN) *and* names an existing spec is a
      valid link.
    - A trailer that is malformed or names a spec that does not exist is an
      invalid link — flagged for the hygiene report, never silently dropped
      (critério 2).
    - A commit with no trailer is an orphan commit (critério 3).
    - An in_progress spec with no valid link is an orphan spec (critério 4).
    """
    spec_list = list(specs)
    known_ids = {spec.spec_id for spec in spec_list}

    links: list[Link] = []
    orphan_commits: list[str] = []
    linked_ids: set[str] = set()

    for commit in commits:
        if not commit.spec_trailers:
            orphan_commits.append(commit.sha)
            continue
        for trailer in commit.spec_trailers:
            valid = bool(SPEC_ID_PATTERN.match(trailer)) and trailer in known_ids
            links.append(Link(commit_sha=commit.sha, spec_id=trailer, valid=valid))
            if valid:
                linked_ids.add(trailer)

    orphan_specs = [
        spec.spec_id for spec in spec_list if spec.is_in_progress and spec.spec_id not in linked_ids
    ]

    return LinkingResult(
        links=tuple(links),
        orphan_commits=tuple(orphan_commits),
        orphan_specs=tuple(orphan_specs),
    )
