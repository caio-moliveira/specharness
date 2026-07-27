"""GitHub issue JSON -> canonical WorkItem (SPEC-008, ADR-007).

The milestone becomes the candidate sprint; labels and assignees are normalised
into `extras` (mapped, critério 1), alongside every other field without a
canonical home — nothing is discarded. Missing fields are explicitly null, never
invented.
"""

from __future__ import annotations

from typing import Any

from specharness_core.ports.tracker import WorkItem

ORIGIN = "github"

# Fields that map onto a canonical WorkItem field — everything else goes to extras.
_CANONICAL = frozenset({"number", "title", "state", "milestone", "html_url"})


def work_item_from_issue(issue: dict[str, Any]) -> WorkItem:
    milestone = issue.get("milestone") or {}
    extras = {k: v for k, v in issue.items() if k not in _CANONICAL}
    extras["labels"] = _label_names(issue.get("labels", []))
    extras["assignees"] = _assignee_logins(issue.get("assignees", []))
    return WorkItem(
        origin=ORIGIN,
        external_id=str(issue["number"]),
        kind="issue",
        title=issue.get("title") or "",
        state=issue.get("state") or "",
        sprint=milestone.get("title") or None,
        url=issue.get("html_url"),
        extras=extras,
    )


def _label_names(labels: list[Any]) -> list[str]:
    return [label["name"] if isinstance(label, dict) else label for label in labels]


def _assignee_logins(assignees: list[Any]) -> list[str]:
    return [a["login"] for a in assignees if isinstance(a, dict) and "login" in a]
