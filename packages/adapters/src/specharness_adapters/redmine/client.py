"""Redmine API client behind the tracker ports (SPEC-007).

httpx lives here and nowhere else in this adapter. The `fetch` callable is
injectable so contract tests drive canned pages — pagination, auth, rate limit
and missing fields — with no network and no key. The API key is read at the edge
and sent as the `X-Redmine-API-Key` header; it never touches a value object.

Rate limit (métrica 1) is respected: a 429 is retried after a bounded backoff
(the `sleep` is injectable so tests wait for nothing), and only surfaces as
`TrackerRateLimited` if it persists.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx
from specharness_core.ports.tracker import (
    InvalidTrackerConfig,
    TrackerError,
    WorkItem,
)

from .errors import classify
from .mapping import ORIGIN, work_item_from_issue, work_item_from_version

#: (method, path, params, json_body) -> response
FetchFn = Callable[[str, str, "dict[str, Any] | None", "dict[str, Any] | None"], "httpx.Response"]

DEFAULT_TIMEOUT_S = 30.0
_DEFAULT_PAGE_SIZE = 100
_DEFAULT_MAX_RETRIES = 2


class RedmineClient:
    """Implements the `WorkItemReader` and `StatusWriter` ports over Redmine's REST API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        project: str,
        *,
        fetch: FetchFn | None = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        sleep: Callable[[float], None] | None = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._project = project
        self._page_size = page_size
        self._sleep = sleep or time.sleep
        self._max_retries = max_retries
        self._fetch = fetch or self._httpx_fetch

    def _httpx_fetch(
        self, method: str, path: str, params: dict[str, Any] | None, json: dict[str, Any] | None
    ) -> httpx.Response:
        headers = {"X-Redmine-API-Key": self._api_key, "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
                return client.request(
                    method, f"{self._base}{path}", headers=headers, params=params, json=json
                )
        except httpx.HTTPError as exc:
            raise TrackerError.for_tracker(
                self._base, f"falha de rede ({type(exc).__name__})"
            ) from exc

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            response = self._fetch("GET", path, params, None)
            if response.status_code == 429 and attempt < self._max_retries:
                self._sleep(_retry_after(response.headers))
                continue
            if response.status_code != 200:
                raise classify(response.status_code, self._base)
            return response.json()
        # A última iteração nunca faz `continue` (attempt < max_retries é falso),
        # então o loop sempre sai por return/raise acima. Rede de segurança:
        raise classify(429, self._base)  # pragma: no cover

    # --- WorkItemReader ----------------------------------------------------

    def work_items(self) -> Iterator[WorkItem]:
        yield from self._issues()
        yield from self._versions()

    def _issues(self) -> Iterator[WorkItem]:
        offset = 0
        while True:
            data = self._get(
                "/issues.json",
                {
                    "project_id": self._project,
                    "status_id": "*",  # inclui fechadas (import brownfield)
                    "offset": offset,
                    "limit": self._page_size,
                },
            )
            issues = data.get("issues", [])
            for issue in issues:
                yield work_item_from_issue(issue, self._base)
            offset += self._page_size
            if not issues or offset >= int(data.get("total_count", 0)):
                return

    def _versions(self) -> Iterator[WorkItem]:
        data = self._get(f"/projects/{self._project}/versions.json", {})
        for version in data.get("versions", []):
            yield work_item_from_version(version, self._base)

    # --- StatusWriter ------------------------------------------------------

    def update_status(self, external_id: str, status_name: str) -> None:
        status_id = self._resolve_status_id(status_name)
        response = self._fetch(
            "PUT", f"/issues/{external_id}.json", None, {"issue": {"status_id": status_id}}
        )
        if response.status_code not in (200, 204):
            raise classify(response.status_code, self._base)

    def _resolve_status_id(self, status_name: str) -> int:
        data = self._get("/issue_statuses.json", {})
        for status in data.get("issue_statuses", []):
            if status.get("name") == status_name:
                return int(status["id"])
        raise InvalidTrackerConfig.because(
            f"o status '{status_name}' não existe no Redmine deste projeto"
        )

    @property
    def origin(self) -> str:
        return ORIGIN


def _retry_after(headers: Any) -> float:
    try:
        return float(headers.get("Retry-After", 1.0))
    except (TypeError, ValueError):
        return 1.0
