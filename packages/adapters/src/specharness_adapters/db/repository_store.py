"""Idempotent persistence of commits and pull requests (SPEC-006, métrica 2).

The sync inserts only what is missing: keyed by (repo, sha) and (repo, number),
a second run over an unchanged repo adds nothing. This is where the "0 registros
novos na 2ª execução" promise is kept — measured by the store's contract test,
not asserted.
"""

from __future__ import annotations

from specharness_core.ports.database import DatabaseTarget
from specharness_core.ports.repository import Commit, PullRequest, SyncResult
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import CommitRow, PullRequestCommitRow, PullRequestRow


class RepositoryStore:
    """Implements the core `RepositoryStore` port over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def all_commits(self) -> list[Commit]:
        """Read every ingested commit back as a core `Commit` (SPEC-009 linking)."""
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(select(CommitRow).order_by(CommitRow.authored_at.desc()))
                return [
                    Commit(
                        sha=row.sha,
                        author=row.author,
                        authored_at=row.authored_at,
                        message=row.message,
                        spec_trailers=tuple(row.spec_trailers),
                    )
                    for row in rows
                ]
        finally:
            engine.dispose()

    def spec_ids_for_pr(self, repo: str, number: int) -> set[str]:
        """The distinct spec ids linked to a PR via its commits' trailers (SPEC-009).

        This is how the perception survey anchors to a spec without asking the dev
        to retype it (SPEC-014, acceptance[3]).
        """
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(
                    select(CommitRow)
                    .join(
                        PullRequestCommitRow,
                        (PullRequestCommitRow.repo == CommitRow.repo)
                        & (PullRequestCommitRow.sha == CommitRow.sha),
                    )
                    .where(
                        PullRequestCommitRow.repo == repo,
                        PullRequestCommitRow.number == number,
                    )
                )
                return {spec for row in rows for spec in row.spec_trailers}
        finally:
            engine.dispose()

    def sync(
        self, repo: str, commits: list[Commit], pull_requests: list[PullRequest]
    ) -> SyncResult:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                new_commits = self._insert_new_commits(session, repo, commits)
                new_prs = self._insert_new_pull_requests(session, repo, pull_requests)
                session.flush()
                total_commits = session.scalar(
                    select(func.count()).select_from(CommitRow).where(CommitRow.repo == repo)
                )
                total_prs = session.scalar(
                    select(func.count())
                    .select_from(PullRequestRow)
                    .where(PullRequestRow.repo == repo)
                )
                session.commit()
            return SyncResult(
                new_commits=new_commits,
                new_pull_requests=new_prs,
                total_commits=total_commits or 0,
                total_pull_requests=total_prs or 0,
            )
        finally:
            engine.dispose()

    @staticmethod
    def _insert_new_commits(session: Session, repo: str, commits: list[Commit]) -> int:
        existing = set(session.scalars(select(CommitRow.sha).where(CommitRow.repo == repo)))
        seen: set[str] = set()
        inserted = 0
        for commit in commits:
            if commit.sha in existing or commit.sha in seen:
                continue
            seen.add(commit.sha)
            session.add(
                CommitRow(
                    repo=repo,
                    sha=commit.sha,
                    author=commit.author,
                    authored_at=commit.authored_at,
                    message=commit.message,
                    spec_trailers=list(commit.spec_trailers),
                )
            )
            inserted += 1
        return inserted

    @staticmethod
    def _insert_new_pull_requests(
        session: Session, repo: str, pull_requests: list[PullRequest]
    ) -> int:
        existing = set(
            session.scalars(select(PullRequestRow.number).where(PullRequestRow.repo == repo))
        )
        seen: set[int] = set()
        inserted = 0
        for pr in pull_requests:
            if pr.number in existing or pr.number in seen:
                continue
            seen.add(pr.number)
            session.add(
                PullRequestRow(
                    repo=repo,
                    number=pr.number,
                    title=pr.title,
                    state=pr.state,
                    head_branch=pr.head_branch,
                    base_branch=pr.base_branch,
                )
            )
            for sha in dict.fromkeys(pr.commit_shas):  # dedupe links, preserve order
                session.add(PullRequestCommitRow(repo=repo, number=pr.number, sha=sha))
            inserted += 1
        return inserted
