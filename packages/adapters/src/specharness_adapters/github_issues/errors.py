"""GitHub HTTP status -> actionable TrackerError (SPEC-008).

GitHub Issues is a tracker (produces WorkItems), so failures are `TrackerError`,
not repository errors — but auth guidance still names GITHUB_TOKEN. Only the
status code reaches the message, never the body.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from specharness_core.ports.repository import GITHUB_TOKEN_ENV
from specharness_core.ports.tracker import (
    TrackerAuthenticationFailed,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimited,
)


def classify(
    status_code: int, tracker: str, headers: Mapping[str, Any] | None = None
) -> TrackerError:
    """Translate a non-2xx GitHub response into a `TrackerError`."""
    header_map = headers or {}
    if status_code == 401:
        return TrackerAuthenticationFailed.for_tracker(
            tracker, detail="HTTP 401", key_env=GITHUB_TOKEN_ENV
        )
    if status_code == 403:
        remaining = str(header_map.get("X-RateLimit-Remaining", "")).strip()
        if remaining == "0":
            return TrackerRateLimited.for_tracker(tracker, detail="HTTP 403")
        return TrackerAuthenticationFailed.for_tracker(
            tracker, detail="HTTP 403", key_env=GITHUB_TOKEN_ENV
        )
    if status_code == 404:
        return TrackerNotFound.for_tracker(tracker, detail="HTTP 404")
    return TrackerError.for_tracker(tracker, detail=f"HTTP {status_code}")
