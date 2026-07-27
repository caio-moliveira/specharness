"""GitHub Issues client behind the `WorkItemReader` port (SPEC-008).

Reuses the SPEC-006 GitHub connection conventions — same httpx bearer auth, same
pagination — but produces canonical WorkItems, not repository types. The `fetch`
callable is injectable so contract tests run with no network and no token. The
`/issues` endpoint also returns pull requests; those are skipped.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
from specharness_core.ports.repository import GITHUB_API_ROOT, RepoRef
from specharness_core.ports.tracker import TrackerError, WorkItem

from .errors import classify
from .mapping import ORIGIN, work_item_from_issue

FetchFn = Callable[[str, dict[str, Any]], "httpx.Response"]

DEFAULT_TIMEOUT_S = 30.0
_PER_PAGE = 100


class GitHubIssuesClient:
    """Implements the `WorkItemReader` port over the GitHub Issues REST API."""

    def __init__(
        self,
        ref: RepoRef,
        token: str | None,
        *,
        fetch: FetchFn | None = None,
        api_root: str = GITHUB_API_ROOT,
        per_page: int = _PER_PAGE,
    ) -> None:
        self._ref = ref
        self._token = token
        self._api_root = api_root
        self._per_page = per_page
        self._fetch = fetch or self._httpx_fetch

    def _httpx_fetch(self, path: str, params: dict[str, Any]) -> httpx.Response:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            with httpx.Client(timeout=DEFAULT_TIMEOUT_S) as client:
                return client.get(f"{self._api_root}{path}", headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise TrackerError.for_tracker(
                self._ref.slug, f"falha de rede ao acessar o GitHub ({type(exc).__name__})"
            ) from exc

    def work_items(self) -> Iterator[WorkItem]:
        base = f"/repos/{self._ref.slug}/issues"
        for payload in self._paginate(base, {"state": "all"}):
            if "pull_request" in payload:  # o endpoint /issues devolve PRs também
                continue
            yield work_item_from_issue(payload)

    @property
    def origin(self) -> str:
        return ORIGIN

    def _paginate(self, path: str, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            response = self._fetch(path, {**params, "per_page": self._per_page, "page": page})
            if response.status_code != 200:
                raise classify(response.status_code, self._ref.slug, response.headers)
            batch = response.json()
            if not batch:
                return
            yield from batch
            if len(batch) < self._per_page:
                return
            page += 1
