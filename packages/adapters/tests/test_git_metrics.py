"""Git-derived camada-2 signals (SPEC-013): status transitions and blame-based
turnover. The arithmetic is pinned against real temporary repositories; a couple
of edge branches are driven with an injected `run` callable."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from specharness_adapters.metrics import StatusHistoryReader, TurnoverReader
from specharness_core.metrics import cycle_time_seconds
from specharness_core.ports.repository import RepositoryError
from specharness_core.specschema import SpecStatus


def _git(path: Path, *args: str, when: datetime | None = None) -> None:
    env = None
    if when is not None:
        stamp = when.isoformat()
        import os

        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
    subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True, env=env
    )


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True, text=True)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "Tester")


def _spec_body(status: str) -> str:
    return f"---\nspec: SPEC-999\nstatus: {status}\n---\n\n## Contexto\n"


def _commit_spec(repo: Path, relpath: str, status: str, when: datetime) -> None:
    target = repo / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_spec_body(status))
    _git(repo, "add", relpath)
    _git(repo, "commit", "-q", "-m", f"chore: SPEC-999 → {status}", when=when)


# --- StatusHistoryReader ----------------------------------------------------


def test_transitions_track_frontmatter_status_changes(tmp_path):
    repo = tmp_path
    _init(repo)
    rel = "specs/SPEC-999-x.md"
    _commit_spec(repo, rel, "ready", datetime(2026, 7, 1, tzinfo=UTC))
    _commit_spec(repo, rel, "in_progress", datetime(2026, 7, 2, tzinfo=UTC))
    _commit_spec(repo, rel, "verifying", datetime(2026, 7, 3, tzinfo=UTC))
    _commit_spec(repo, rel, "done", datetime(2026, 7, 5, tzinfo=UTC))

    transitions = StatusHistoryReader(repo, rel).transitions("SPEC-999")

    assert [t.to_status for t in transitions] == [
        SpecStatus.READY,
        SpecStatus.IN_PROGRESS,
        SpecStatus.VERIFYING,
        SpecStatus.DONE,
    ]
    # cycle time flows straight from these raw git timestamps (4 days).
    assert cycle_time_seconds(transitions) == 4 * 24 * 3600


def test_a_commit_that_does_not_change_status_adds_no_transition(tmp_path):
    repo = tmp_path
    _init(repo)
    rel = "specs/SPEC-999-x.md"
    _commit_spec(repo, rel, "ready", datetime(2026, 7, 1, tzinfo=UTC))
    # touch the file without changing status
    (repo / rel).write_text(_spec_body("ready") + "\nmais contexto\n")
    _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", "docs: contexto", when=datetime(2026, 7, 2, tzinfo=UTC))
    _commit_spec(repo, rel, "in_progress", datetime(2026, 7, 3, tzinfo=UTC))

    transitions = StatusHistoryReader(repo, rel).transitions("SPEC-999")

    assert [t.to_status for t in transitions] == [SpecStatus.READY, SpecStatus.IN_PROGRESS]


def test_a_file_version_without_a_status_line_is_skipped():
    # first version has no frontmatter status; second introduces it.
    def run(args):
        if args[0] == "log":
            return "aaa\x1f2026-07-01T00:00:00+00:00\nbbb\x1f2026-07-02T00:00:00+00:00\n"
        # git show <sha>:path
        return "no status here\n" if "aaa:" in args[1] else _spec_body("ready")

    transitions = StatusHistoryReader("/repo", "specs/x.md", run=run).transitions("SPEC-999")

    assert [t.to_status for t in transitions] == [SpecStatus.READY]


def test_an_unknown_status_value_is_ignored():
    def run(args):
        if args[0] == "log":
            return "aaa\x1f2026-07-01T00:00:00+00:00\n"
        return _spec_body("bogus")

    assert StatusHistoryReader("/repo", "specs/x.md", run=run).transitions("SPEC-999") == []


# --- TurnoverReader ---------------------------------------------------------


def _write_lines(path: Path, n: int, tag: str) -> None:
    path.write_text("".join(f"{tag}-line-{i}\n" for i in range(n)))


def test_turnover_measures_the_fraction_of_spec_lines_rewritten(tmp_path):
    repo = tmp_path
    _init(repo)
    data = repo / "data.txt"
    _write_lines(data, 10, "orig")
    _git(repo, "add", "data.txt")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        "feat: seed\n\nSpec: SPEC-777",
        when=datetime(2026, 7, 1, tzinfo=UTC),
    )

    # rewrite 6 of the 10 lines in a later commit (not the spec's)
    lines = data.read_text().splitlines()
    for i in range(6):
        lines[i] = f"rewritten-line-{i}"
    data.write_text("\n".join(lines) + "\n")
    _git(repo, "add", "data.txt")
    _git(repo, "commit", "-q", "-m", "refactor: rewrite", when=datetime(2026, 7, 10, tzinfo=UTC))

    reader = TurnoverReader(repo)
    as_of = datetime(2026, 7, 20, tzinfo=UTC)

    turnover = reader.turnover("SPEC-777", window_days=30, as_of=as_of)
    assert turnover == pytest.approx(0.6)  # 6 of 10 spec lines gone

    baseline = reader.repo_baseline(window_days=30, as_of=as_of)
    # added across both commits = 10 + 6 = 16, surviving = 10 -> 1 - 10/16
    assert baseline == pytest.approx(0.375)


def test_turnover_is_none_for_a_spec_with_no_commits(tmp_path):
    repo = tmp_path
    _init(repo)
    (repo / "f.txt").write_text("x\n")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "chore: no trailer", when=datetime(2026, 7, 1, tzinfo=UTC))

    reader = TurnoverReader(repo)
    assert (
        reader.turnover("SPEC-777", window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)) is None
    )


def test_commits_outside_the_window_do_not_count(tmp_path):
    repo = tmp_path
    _init(repo)
    data = repo / "data.txt"
    _write_lines(data, 5, "old")
    _git(repo, "add", "data.txt")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        "feat: old\n\nSpec: SPEC-777",
        when=datetime(2026, 1, 1, tzinfo=UTC),  # 6+ months before as_of
    )

    reader = TurnoverReader(repo)
    # window of 30 days ending in July excludes the January commit
    assert (
        reader.turnover("SPEC-777", window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)) is None
    )


_SHA = "a" * 40


def test_added_lines_skips_binary_numstat_rows():
    # numstat prints '-\t-\tpath' for binary changes; those must not crash.
    def run(args):
        if args[0] == "log":
            return f"{_SHA}\x1ffeat: x\n\nSpec: SPEC-777\x1e"
        if args[0] == "show":
            return "5\t0\tsrc.txt\n-\t-\timage.png\n"
        if args[0] == "blame":
            return f"{_SHA} 1 1\n\tcontent\n"
        return ""

    reader = TurnoverReader("/repo", run=run)
    # 5 lines added, 1 surviving -> 1 - 1/5
    assert reader.turnover(
        "SPEC-777", window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)
    ) == pytest.approx(0.8)


def test_a_removed_file_contributes_no_surviving_lines():
    def run(args):
        if args[0] == "log":
            return f"{_SHA}\x1ffeat: x\n\nSpec: SPEC-777\x1e"
        if args[0] == "show":
            return "4\t0\tgone.txt\n"
        if args[0] == "blame":
            raise RepositoryError.for_repo("/repo", "no such path gone.txt in HEAD")
        return ""

    reader = TurnoverReader("/repo", run=run)
    # 4 added, blame fails (file removed) -> 0 surviving -> turnover 1.0
    assert reader.turnover(
        "SPEC-777", window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)
    ) == pytest.approx(1.0)


def test_turnover_is_none_when_spec_commits_added_no_lines():
    def run(args):
        if args[0] == "log":
            return f"{_SHA}\x1ffeat: x\n\nSpec: SPEC-777\x1e"
        if args[0] == "show":
            return "0\t3\tdeleted_only.txt\n"  # pure deletion: 0 added
        return ""

    reader = TurnoverReader("/repo", run=run)
    assert (
        reader.turnover("SPEC-777", window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)) is None
    )


def test_blank_log_lines_are_ignored():
    def run(args):
        if args[0] == "log":
            return "\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\x1f2026-07-01T00:00:00+00:00\n\n"
        return _spec_body("ready")

    transitions = StatusHistoryReader("/repo", "specs/x.md", run=run).transitions("SPEC-999")
    assert [t.to_status for t in transitions] == [SpecStatus.READY]


def test_a_non_repository_path_raises_repository_error(tmp_path):
    with pytest.raises(RepositoryError):
        StatusHistoryReader(tmp_path, "specs/x.md").transitions("SPEC-999")


def test_missing_git_binary_raises_repository_error(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr("specharness_adapters.metrics.git_metrics.subprocess.run", boom)
    with pytest.raises(RepositoryError) as excinfo:
        TurnoverReader(tmp_path).repo_baseline(
            window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC)
        )
    assert "git" in str(excinfo.value).lower()


def test_git_metrics_decode_output_as_utf8(monkeypatch, tmp_path):
    # Mesma regressão de Windows no reader de turnover/blame (cp1252 → stdout None).
    captured: dict = {}

    class _Proc:
        stdout = ""

    def fake_run(*args, **kwargs):
        captured.update(kwargs)
        return _Proc()

    monkeypatch.setattr("specharness_adapters.metrics.git_metrics.subprocess.run", fake_run)

    TurnoverReader(tmp_path).repo_baseline(window_days=30, as_of=datetime(2026, 7, 20, tzinfo=UTC))

    assert captured["encoding"] == "utf-8"
    assert captured["errors"] == "replace"
