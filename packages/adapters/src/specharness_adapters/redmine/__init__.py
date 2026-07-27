"""Redmine tracker adapter (SPEC-007, ADR-007).

This is where HTTP I/O to Redmine is allowed. The core knows only the canonical
`WorkItem`; this package imports issues and versions into it, writes status back,
and never leaks the API key or a Redmine-shaped type past its boundary.
"""

from .client import RedmineClient
from .errors import classify
from .mapping import work_item_from_issue, work_item_from_version

__all__ = [
    "RedmineClient",
    "classify",
    "work_item_from_issue",
    "work_item_from_version",
]
