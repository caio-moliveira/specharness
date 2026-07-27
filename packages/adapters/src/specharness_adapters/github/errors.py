"""GitHub HTTP status -> actionable RepositoryError (SPEC-006, critério 4).

The user never reads a raw API body — it can echo the request, token and all.
Only the status code reaches the message, and auth failures name the env var and
the minimum token scope (cenário 3).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specharness_core.ports.repository import (
    AuthenticationFailed,
    RateLimited,
    RepositoryError,
    RepositoryNotFound,
)


def classify(
    status_code: int, repo: str, headers: Mapping[str, Any] | None = None
) -> RepositoryError:
    """Translate a non-2xx GitHub response into a `RepositoryError`."""
    header_map = headers or {}
    if status_code == 401:
        return AuthenticationFailed.for_repo(repo, detail="HTTP 401")
    if status_code == 403:
        remaining = str(header_map.get("X-RateLimit-Remaining", "")).strip()
        if remaining == "0":
            return RateLimited.for_repo(repo, detail="HTTP 403")
        # A 403 with quota left is almost always a token missing the scope.
        return AuthenticationFailed.for_repo(repo, detail="HTTP 403")
    if status_code == 404:
        return RepositoryNotFound.for_repo(repo, detail="HTTP 404")
    return RepositoryError.for_repo(repo, detail=f"HTTP {status_code}")
