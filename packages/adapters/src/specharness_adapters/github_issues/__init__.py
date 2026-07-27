"""GitHub Issues tracker adapter (SPEC-008, ADR-007).

Reuses the SPEC-006 GitHub connection but produces canonical WorkItems, proving
the ADR-007 model works for a second taxonomy. HTTP I/O is confined to
`client.py`; the core never sees a GitHub-shaped type.
"""

from .client import GitHubIssuesClient
from .errors import classify
from .mapping import work_item_from_issue

__all__ = ["GitHubIssuesClient", "classify", "work_item_from_issue"]
