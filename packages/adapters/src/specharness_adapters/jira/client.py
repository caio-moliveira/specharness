"""Jira Cloud (REST v3) client behind the tracker ports (SPEC-019).

httpx lives here and nowhere else in this adapter. The `fetch` callable is
injectable so contract tests drive recorded cassettes — pagination, auth, rate
limit and missing fields — with no network and no credential. Auth is Basic
e-mail+token, read at the edge; the credential never touches a value object.

Rate limit is respected: a 429 is retried after a bounded backoff (the `sleep`
is injectable so tests wait for nothing), and only surfaces as
`TrackerRateLimited` if it persists. A network failure interrupts the import
before anything reaches the store (SPEC-019, cenário "falha de rede").
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
from .mapping import ORIGIN, work_item_from_issue

#: (method, path, params, json_body) -> response
FetchFn = Callable[[str, str, "dict[str, Any] | None", "dict[str, Any] | None"], "httpx.Response"]

DEFAULT_TIMEOUT_S = 30.0
_DEFAULT_PAGE_SIZE = 100
_DEFAULT_MAX_RETRIES = 2

#: How Jira marks the agile sprint custom field (its id varies per instance).
_SPRINT_FIELD_SCHEMA = "com.pyxis.greenhopper.jira:gh-sprint"


class JiraClient:
    """Implements the `WorkItemReader` and `StatusWriter` ports over Jira Cloud REST v3."""

    def __init__(
        self,
        base_url: str,
        email: str,
        token: str,
        project: str,
        *,
        fetch: FetchFn | None = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
        sleep: Callable[[float], None] | None = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._email = email
        self._token = token
        self._project = project
        self._page_size = page_size
        self._sleep = sleep or time.sleep
        self._max_retries = max_retries
        self._fetch = fetch or self._httpx_fetch

    def _httpx_fetch(
        self, method: str, path: str, params: dict[str, Any] | None, json: dict[str, Any] | None
    ) -> httpx.Response:
        try:
            with httpx.Client(
                timeout=DEFAULT_TIMEOUT_S, auth=httpx.BasicAuth(self._email, self._token)
            ) as client:
                return client.request(method, f"{self._base}{path}", params=params, json=json)
        except httpx.HTTPError as exc:
            raise TrackerError.for_tracker(
                self._base,
                f"falha de rede ({type(exc).__name__}). Verifique a rede e tente de novo",
            ) from exc

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
        expected: tuple[int, ...],
    ) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            response = self._fetch(method, path, params, json)
            if response.status_code == 429 and attempt < self._max_retries:
                self._sleep(_retry_after(response.headers))
                continue
            if response.status_code not in expected:
                raise classify(response.status_code, self._base)
            return response
        # A última iteração nunca faz `continue` (attempt < max_retries é falso),
        # então o loop sempre sai por return/raise acima. Rede de segurança:
        raise classify(429, self._base)  # pragma: no cover

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | list[Any]:
        return self._request("GET", path, params, None, expected=(200,)).json()

    # --- WorkItemReader ----------------------------------------------------

    def work_items(self) -> Iterator[WorkItem]:
        sprint_field = self._sprint_field()
        params: dict[str, Any] = {
            "jql": f'project = "{self._project}" ORDER BY created ASC',
            "maxResults": self._page_size,
            "fields": "*all",
        }
        while True:
            data = self._get("/rest/api/3/search/jql", params)
            assert isinstance(data, dict)
            issues = data.get("issues", [])
            for issue in issues:
                yield work_item_from_issue(issue, self._base, sprint_field)
            token = data.get("nextPageToken")
            if not token or not issues:
                return
            params["nextPageToken"] = token

    def _sprint_field(self) -> str | None:
        """The instance-specific id of the agile sprint field; None sem agile."""
        data = self._get("/rest/api/3/field", {})
        assert isinstance(data, list)
        for field in data:
            if (field.get("schema") or {}).get("custom") == _SPRINT_FIELD_SCHEMA:
                return str(field["id"])
        return None

    # --- StatusWriter ------------------------------------------------------

    def update_status(self, external_id: str, status_name: str) -> None:
        """Write back ONLY the status via a workflow transition (ADR-020).

        The request body carries a transition id and nothing else — summary
        and description are untouchable by construction.
        """
        transition_id = self._resolve_transition(external_id, status_name)
        self._request(
            "POST",
            f"/rest/api/3/issue/{external_id}/transitions",
            None,
            {"transition": {"id": transition_id}},
            expected=(204,),
        )

    def _resolve_transition(self, external_id: str, status_name: str) -> str:
        data = self._get(f"/rest/api/3/issue/{external_id}/transitions", {})
        assert isinstance(data, dict)
        for transition in data.get("transitions", []):
            if (transition.get("to") or {}).get("name", "").casefold() == status_name.casefold():
                return str(transition["id"])
        raise InvalidTrackerConfig.because(
            f"o status '{status_name}' não é alcançável pelo workflow do Jira "
            f"para a issue {external_id}; confira jira.status_map"
        )

    @property
    def origin(self) -> str:
        return ORIGIN


def _retry_after(headers: Any) -> float:
    try:
        return float(headers.get("Retry-After", 1.0))
    except (TypeError, ValueError):
        return 1.0
