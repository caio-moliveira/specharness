"""The repository store's idempotent persistence (SPEC-006, métrica 2, critério 3).

Runs against a real (virgin, tmp) SQLite database migrated to head — the same
contract the database gateway keeps. Idempotency is measured here: a second sync
over unchanged input inserts nothing.
"""

from __future__ import annotations

import time
from datetime import datetime

import pytest
from specharness_adapters.db import RepositoryStore, SqlAlchemyDatabaseGateway
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.repository import Commit, PullRequest
from sqlalchemy import create_engine, text

SYNC_BUDGET_SECONDS = 60.0  # SPEC-006, métrica 1


@pytest.fixture
def store_and_target(tmp_path):
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()  # applies 0001 + 0002
    return RepositoryStore(target), target


def _commit(sha, trailers=()):
    return Commit(
        sha=sha,
        author="Ana",
        authored_at=datetime(2026, 7, 27),
        message="m",
        spec_trailers=trailers,
    )


def _pr(number, shas=()):
    return PullRequest(
        number=number,
        title="t",
        state="open",
        head_branch="feat",
        base_branch="main",
        commit_shas=shas,
    )


def test_first_sync_inserts_everything(store_and_target):
    store, _ = store_and_target

    result = store.sync("acme/tool", [_commit("a"), _commit("b")], [_pr(1, ("a",))])

    assert result.new_commits == 2
    assert result.new_pull_requests == 1
    assert result.total_commits == 2
    assert result.total_pull_requests == 1
    assert result.was_noop is False


def test_second_sync_over_unchanged_input_is_a_noop(store_and_target):
    store, _ = store_and_target
    args = ("acme/tool", [_commit("a"), _commit("b")], [_pr(1, ("a",))])
    store.sync(*args)

    second = store.sync(*args)

    assert second.new_commits == 0
    assert second.new_pull_requests == 0
    assert second.total_commits == 2
    assert second.total_pull_requests == 1
    assert second.was_noop is True


def test_new_commits_on_a_later_sync_are_added(store_and_target):
    store, _ = store_and_target
    store.sync("acme/tool", [_commit("a")], [])

    result = store.sync("acme/tool", [_commit("a"), _commit("b")], [])

    assert result.new_commits == 1
    assert result.total_commits == 2


def test_trailers_and_pr_commit_links_are_persisted(store_and_target):
    store, target = store_and_target

    store.sync("acme/tool", [_commit("a", ("SPEC-006",))], [_pr(7, ("a", "b"))])

    engine = create_engine(target.sync_url, future=True)
    try:
        with engine.connect() as conn:
            trailers = conn.execute(
                text("SELECT spec_trailers FROM commits WHERE sha = 'a'")
            ).scalar()
            links = conn.execute(
                text("SELECT count(*) FROM pull_request_commits WHERE number = 7")
            ).scalar()
    finally:
        engine.dispose()

    assert "SPEC-006" in str(trailers)
    assert links == 2


def test_the_same_sha_in_two_repos_is_two_rows(store_and_target):
    store, _ = store_and_target
    store.sync("acme/one", [_commit("a")], [])

    result = store.sync("acme/two", [_commit("a")], [])

    assert result.new_commits == 1
    assert result.total_commits == 1  # por repo


def test_duplicate_shas_within_one_batch_insert_once(store_and_target):
    store, _ = store_and_target

    result = store.sync("acme/tool", [_commit("a"), _commit("a")], [])

    assert result.new_commits == 1
    assert result.total_commits == 1


def test_all_commits_reads_back_what_was_ingested(store_and_target):
    store, _ = store_and_target
    store.sync("acme/tool", [_commit("a", ("SPEC-006",)), _commit("b")], [])

    commits = store.all_commits()

    by_sha = {c.sha: c for c in commits}
    assert set(by_sha) == {"a", "b"}
    assert by_sha["a"].spec_trailers == ("SPEC-006",)
    assert by_sha["b"].spec_trailers == ()


def test_syncing_five_thousand_commits_stays_under_the_budget(store_and_target):
    """Métrica 1: medida com perf_counter, não afirmada (lado da persistência)."""
    store, _ = store_and_target
    commits = [_commit(f"{i:040x}") for i in range(5000)]

    started = time.perf_counter()
    result = store.sync("acme/tool", commits, [])
    elapsed = time.perf_counter() - started

    assert result.new_commits == 5000
    assert elapsed < SYNC_BUDGET_SECONDS, f"sync de 5000 commits levou {elapsed:.2f}s"
