"""GitHub REST API adapter (SPEC-006).

This is where HTTP I/O to GitHub is allowed. The core decides *what* a pull
request is; this package knows how to read it, page through it and translate its
failures — never leaking the token or the raw payload.
"""

from .client import GitHubClient
from .errors import classify
from .mapping import pull_request_from_payload

__all__ = ["GitHubClient", "classify", "pull_request_from_payload"]
