"""GitHub JSON -> canonical PullRequest (SPEC-006, ADR-001).

The adapter never leaks GitHub's payload shape past this boundary: callers get
the core's `PullRequest`, nothing more.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from specharness_core.ports.repository import PullRequest


def pull_request_from_payload(payload: dict[str, Any], commit_shas: Sequence[str]) -> PullRequest:
    head = payload.get("head") or {}
    base = payload.get("base") or {}
    return PullRequest(
        number=int(payload["number"]),
        title=payload.get("title") or "",
        state=payload.get("state") or "",
        head_branch=head.get("ref") or "",
        base_branch=base.get("ref") or "",
        commit_shas=tuple(commit_shas),
    )
