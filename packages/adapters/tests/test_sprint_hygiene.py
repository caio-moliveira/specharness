"""Sprint test-hygiene signals from the git range (SPEC-013, ADR-016)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from specharness_adapters.metrics import SprintHygieneReader


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), *args], check=True, capture_output=True, text=True
    ).stdout


def _init(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True, text=True)
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "Tester")


def _commit(path: Path, message: str) -> str:
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", message)
    return _git(path, "rev-parse", "HEAD").strip()


def test_signals_attribute_tampering_to_the_commits_spec(tmp_path):
    repo = tmp_path
    _init(repo)
    test_file = repo / "packages" / "core" / "tests" / "test_x.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_x():\n    assert foo() == 1\n    bar()\n")
    base = _commit(repo, "feat: seed\n\nSpec: SPEC-013")

    # a later commit removes the assert, carrying SPEC-013's trailer
    test_file.write_text("def test_x():\n    bar()\n")
    _commit(repo, "test: drop assert\n\nSpec: SPEC-013")

    signals = SprintHygieneReader(repo).signals(base)

    assert len(signals) == 1
    assert signals[0].spec_id == "SPEC-013"
    assert signals[0].kind == "assert-removed"


def test_commits_without_a_spec_trailer_are_ignored(tmp_path):
    repo = tmp_path
    _init(repo)
    test_file = repo / "packages" / "core" / "tests" / "test_y.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_y():\n    assert a() == 1\n")
    base = _commit(repo, "feat: seed\n\nSpec: SPEC-013")

    test_file.write_text("def test_y():\n    pass\n")
    _commit(repo, "test: drop assert without trailer")  # no Spec: trailer

    assert SprintHygieneReader(repo).signals(base) == []


def test_no_signals_when_no_tampering(tmp_path):
    repo = tmp_path
    _init(repo)
    (repo / "readme.md").write_text("hi\n")
    base = _commit(repo, "docs: seed\n\nSpec: SPEC-013")
    (repo / "readme.md").write_text("hi there\n")
    _commit(repo, "docs: more\n\nSpec: SPEC-013")

    assert SprintHygieneReader(repo).signals(base) == []
