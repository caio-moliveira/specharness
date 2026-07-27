"""GitHub API client behind the core `PullRequestReader` port (SPEC-006).

httpx lives here and nowhere else in this adapter. The `fetch` callable is
injectable so the contract test drives canned pages — pagination, rate limit and
invalid auth (métrica 3) — with no network and no token. The token is read at
the edge and sent as a bearer header; it is never stored on any value object.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx
from specharness_core.ports.repository import (
    GITHUB_API_ROOT,
    PullRequest,
    RepoRef,
    RepositoryError,
)

from .errors import classify
from .mapping import pull_request_from_payload

#: A response the client understands: status, JSON body, headers.
FetchFn = Callable[[str, dict[str, Any]], "httpx.Response"]

DEFAULT_TIMEOUT_S = 30.0
_PER_PAGE = 100


class GitHubClient:
    """Implements the core `PullRequestReader` port over the GitHub REST API."""

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
            # A network failure must read as a message, not a traceback. The token
            # lives in a header, never in the URL, so the class name is safe.
            raise RepositoryError.for_repo(
                self._ref.slug, f"falha de rede ao acessar o GitHub ({type(exc).__name__})"
            ) from exc

    def pull_requests(self) -> Iterator[PullRequest]:
        base = f"/repos/{self._ref.slug}/pulls"
        for payload in self._paginate(base, {"state": "all"}):
            shas = self._commit_shas(int(payload["number"]))
            yield pull_request_from_payload(payload, shas)

    def _commit_shas(self, number: int) -> tuple[str, ...]:
        path = f"/repos/{self._ref.slug}/pulls/{number}/commits"
        return tuple(commit["sha"] for commit in self._paginate(path, {}))

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
