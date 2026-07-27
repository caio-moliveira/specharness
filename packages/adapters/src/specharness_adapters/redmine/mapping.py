"""Redmine JSON -> canonical WorkItem (SPEC-007, ADR-007, critério 3).

Every Redmine field without a canonical home is preserved in `extras` — nothing
is discarded silently (métrica 2). The canonical fields are always filled from
real data or left explicitly null, never invented.
"""

from __future__ import annotations

from typing import Any

from specharness_core.ports.tracker import WorkItem

ORIGIN = "redmine"

# Fields that map onto a canonical WorkItem field — everything else goes to extras.
_ISSUE_CANONICAL = frozenset({"id", "subject", "status", "fixed_version"})
_VERSION_CANONICAL = frozenset({"id", "name", "status"})


def work_item_from_issue(issue: dict[str, Any], base_url: str) -> WorkItem:
    status = issue.get("status") or {}
    version = issue.get("fixed_version") or {}
    external_id = str(issue["id"])
    return WorkItem(
        origin=ORIGIN,
        external_id=external_id,
        kind="issue",
        title=issue.get("subject") or "",
        state=status.get("name") or "",
        sprint=version.get("name") or None,
        url=f"{base_url}/issues/{external_id}",
        extras={k: v for k, v in issue.items() if k not in _ISSUE_CANONICAL},
    )


def work_item_from_version(version: dict[str, Any], base_url: str) -> WorkItem:
    external_id = str(version["id"])
    status = version.get("status")
    return WorkItem(
        origin=ORIGIN,
        external_id=external_id,
        kind="version",
        title=version.get("name") or "",
        state=status if isinstance(status, str) else "",
        sprint=None,
        url=f"{base_url}/versions/{external_id}",
        extras={k: v for k, v in version.items() if k not in _VERSION_CANONICAL},
    )
