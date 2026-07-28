"""Jira JSON -> canonical WorkItem (SPEC-019, ADR-007, ADR-020).

Every Jira field without a canonical home is preserved in `extras` — nothing
preenchido is discarded (métrica 3). The canonical fields are filled from real
data or left explicitly null, never invented: `state` is the raw `status.name`
(the `status_map` belongs to write-back only), and the candidate sprint follows
the spec's disambiguation rule (first active, else highest-id future, else
null).
"""

from __future__ import annotations

from typing import Any

from specharness_core.ports.tracker import WorkItem

ORIGIN = "jira"

#: issuetype.name -> canonical kind (SPEC-019 mapping table, case-insensitive).
#: Anything else falls back to the lowercased native name — fidelity, never an
#: invented taxonomy.
_KIND_MAP = {
    "epic": "epic",
    "story": "story",
    "task": "task",
    "bug": "bug",
    "sub-task": "subtask",
    "subtask": "subtask",
}

#: Payload fields with a canonical home; everything else non-empty -> extras.
_CANONICAL = frozenset({"summary", "issuetype", "status"})


def kind_from_issuetype(name: str | None) -> str:
    normalized = (name or "").strip().lower()
    return _KIND_MAP.get(normalized, normalized)


def candidate_sprint(value: Any) -> str | None:
    """The spec's rule: first active sprint, else highest-id future, else null."""
    if not isinstance(value, list):
        return None
    sprints = [s for s in value if isinstance(s, dict)]
    for sprint in sprints:
        if sprint.get("state") == "active":
            name = sprint.get("name")
            return str(name) if name else None
    future = [s for s in sprints if s.get("state") == "future"]
    if future:
        name = max(future, key=lambda s: int(s.get("id", 0))).get("name")
        return str(name) if name else None
    return None


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def work_item_from_issue(
    issue: dict[str, Any], base_url: str, sprint_field: str | None
) -> WorkItem:
    fields: dict[str, Any] = issue.get("fields") or {}
    key = str(issue["key"])
    issuetype = fields.get("issuetype") or {}
    status = fields.get("status") or {}
    skipped = _CANONICAL | ({sprint_field} if sprint_field else set())
    return WorkItem(
        origin=ORIGIN,
        external_id=key,
        kind=kind_from_issuetype(issuetype.get("name")),
        title=fields.get("summary") or "",
        state=status.get("name") or "",
        sprint=candidate_sprint(fields.get(sprint_field)) if sprint_field else None,
        url=f"{base_url.rstrip('/')}/browse/{key}",
        extras={k: v for k, v in fields.items() if k not in skipped and not _is_empty(v)},
    )
