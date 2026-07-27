"""Redmine HTTP status -> actionable TrackerError (SPEC-007, critério auth).

Only the status code reaches the message — never the response body, which can
echo the request and the API key. Auth failures name the env var.
"""

from __future__ import annotations

from specharness_core.ports.tracker import (
    TrackerAuthenticationFailed,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimited,
)


def classify(status_code: int, tracker: str) -> TrackerError:
    """Translate a non-2xx Redmine response into a `TrackerError`."""
    if status_code in (401, 403):
        return TrackerAuthenticationFailed.for_tracker(tracker, detail=f"HTTP {status_code}")
    if status_code == 404:
        return TrackerNotFound.for_tracker(tracker, detail="HTTP 404")
    if status_code == 429:
        return TrackerRateLimited.for_tracker(tracker, detail="HTTP 429")
    return TrackerError.for_tracker(tracker, detail=f"HTTP {status_code}")
