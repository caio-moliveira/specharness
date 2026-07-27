"""Diagnóstico causal do gap de percepção indisponível (SPEC-017).

O gap é None em quatro situações distintas; a dica antiga ("rode metrics")
só resolvia uma delas. Cada teste fixa uma causa e assere que a dica aponta
a ação que de fato resolve — precedência: sem amostras → sem snapshot →
sem cycle time → sem amostra comparável.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_adapters.db import (
    MetricSnapshotStore,
    RepositoryStore,
    SqlAlchemyDatabaseGateway,
)
from specharness_cli.main import app
from specharness_core import SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.repository import Commit, PullRequest
from typer.testing import CliRunner

runner = CliRunner()


def _spec(sprint: str = "2026-A4") -> str:
    return (
        "---\n"
        "spec: SPEC-042\n"
        'title: "P"\n'
        "status: verifying\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        f"sprint: {sprint}\n"
        'success_metrics: ["m < 1s"]\n'
        'acceptance: ["a"]\n'
        "---\n\n## Contexto\n"
    )


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "SPEC-042-x.md").write_text(_spec(), "utf-8")
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()
    # link PR #7 -> SPEC-042 via trailer (SPEC-009), para o survey ancorar a amostra
    RepositoryStore(target).sync(
        "acme/tool",
        [Commit("a", "Ana", datetime(2026, 7, 27), "m", ("SPEC-042",))],
        [PullRequest(7, "t", "merged", "feat", "main", ("a",))],
    )
    return target


def _survey(pr: str = "acme/tool#7") -> None:
    args = ["survey", pr, "--runtime", "R", "--model", "M"]
    args += ["--aproveitamento", "4", "--retrabalho", "leve", "--tempo", "custou"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def test_without_samples_the_hint_points_to_survey(env):
    result = runner.invoke(app, ["perception", "2026-A4"])

    assert result.exit_code == 0, result.output
    assert "Gap indisponível" in result.output
    assert "specharness survey" in result.output


def test_without_a_snapshot_the_hint_points_to_metrics(env):
    _survey()

    result = runner.invoke(app, ["perception", "2026-A4"])

    assert "Gap indisponível" in result.output
    assert "specharness metrics" in result.output


def test_without_cycle_times_the_hint_names_the_real_cause(env):
    _survey()
    MetricSnapshotStore(env).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-042", None, None, None, None, None, None, None, 1),),
        ),
        datetime(2026, 7, 27),
    )

    result = runner.invoke(app, ["perception", "2026-A4"])

    assert "Gap indisponível" in result.output
    assert "cycle time" in result.output
    assert "não muda isso" in result.output
    assert "specharness metrics" not in result.output  # a dica antiga mandava para cá


def test_without_comparable_samples_the_hint_says_so(env):
    _survey()
    MetricSnapshotStore(env).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-777", 100.0, None, None, None, None, None, None, 1),),
        ),
        datetime(2026, 7, 27),
    )

    result = runner.invoke(app, ["perception", "2026-A4"])

    assert "Gap indisponível" in result.output
    assert "nenhuma amostra é de spec com cycle time conhecido" in result.output
