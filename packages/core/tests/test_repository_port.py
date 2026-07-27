"""The repository port's pure decisions (SPEC-006, critérios 3, 4, métrica 2)."""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_core.ports.repository import (
    GITHUB_TOKEN_ENV,
    AuthenticationFailed,
    Commit,
    InvalidRepositoryConfig,
    PullRequest,
    RepoRef,
    SyncResult,
    parse_github_remote,
)

# --- parse_github_remote (as três formas que o git entrega) ----------------


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:caio-moliveira/specharness.git",
        "https://github.com/caio-moliveira/specharness.git",
        "https://github.com/caio-moliveira/specharness",
        "ssh://git@github.com/caio-moliveira/specharness.git",
    ],
)
def test_parses_every_remote_form_to_the_same_ref(url):
    ref = parse_github_remote(url)

    assert ref == RepoRef(owner="caio-moliveira", name="specharness")
    assert ref.slug == "caio-moliveira/specharness"


def test_a_repo_name_with_a_dot_keeps_it():
    ref = parse_github_remote("git@github.com:acme/my.tool.git")

    assert ref.name == "my.tool"


def test_a_non_github_remote_is_rejected():
    with pytest.raises(InvalidRepositoryConfig):
        parse_github_remote("git@gitlab.com:acme/tool.git")


# --- mensagem de auth cita o token e o escopo (critério 4, cenário 3) ------


def test_auth_error_names_the_token_env_and_minimum_scope():
    error = AuthenticationFailed.for_repo("acme/tool", detail="HTTP 403")

    text = str(error)
    assert GITHUB_TOKEN_ENV in text
    assert "escopo" in text.lower()
    assert "acme/tool" in text


# --- SyncResult idempotência (métrica 2) -----------------------------------


def test_sync_result_is_a_noop_only_when_nothing_new():
    assert SyncResult(0, 0, 10, 3).was_noop is True
    assert SyncResult(1, 0, 10, 3).was_noop is False
    assert SyncResult(0, 2, 10, 3).was_noop is False


# --- value objects ---------------------------------------------------------


def test_commit_subject_is_the_first_line():
    commit = Commit(
        sha="abc",
        author="Ana",
        authored_at=datetime(2026, 7, 27),
        message="feat: algo\n\ncorpo\n\nSpec: SPEC-006",
        spec_trailers=("SPEC-006",),
    )

    assert commit.subject == "feat: algo"
    assert commit.spec_trailers == ("SPEC-006",)


def test_pull_request_carries_its_commit_links():
    pr = PullRequest(
        number=7,
        title="t",
        state="open",
        head_branch="feat/x",
        base_branch="main",
        commit_shas=("a", "b"),
    )

    assert pr.commit_shas == ("a", "b")
