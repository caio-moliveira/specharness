"""`specharness survey` e `perception` — micro-survey de percepção (SPEC-014)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from specharness_adapters.db import (
    MetricSnapshotStore,
    PerceptionStore,
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
    # link PR #7 to SPEC-042 via a commit trailer (SPEC-009)
    RepositoryStore(target).sync(
        "acme/tool",
        [Commit("a", "Ana", datetime(2026, 7, 27), "m", ("SPEC-042",))],
        [PullRequest(7, "t", "merged", "feat", "main", ("a",))],
    )
    return tmp_path


def test_records_a_sample_anchored_to_the_triple(env):
    result = runner.invoke(
        app,
        [
            "survey",
            "acme/tool#7",
            "--runtime",
            "Claude Code",
            "--model",
            "claude-opus",
            "--aproveitamento",
            "5",
            "--retrabalho",
            "leve",
            "--tempo",
            "economizou",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "SPEC-042" in result.output and "Claude Code" in result.output


def test_spec_is_derived_from_the_pr_link(env):
    # no --spec: derived from PR #7 -> SPEC-042
    result = runner.invoke(
        app,
        ["survey", "acme/tool#7", "--runtime", "R", "--model", "M", "--skip"],
    )
    assert result.exit_code == 0, result.output
    assert "pulado" in result.output.lower()


def test_a_pr_without_a_linked_spec_is_refused(env):
    result = runner.invoke(
        app,
        ["survey", "acme/tool#999", "--runtime", "R", "--model", "M", "--skip"],
    )
    assert result.exit_code == 1
    assert "sem spec" in result.output.lower()
    # nada é persistido na recusa
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=env)
    assert PerceptionStore(target).has_response("acme/tool#999") is False


def test_a_skip_is_not_re_prompted(env):
    args = ["survey", "acme/tool#7", "--runtime", "R", "--model", "M"]
    first = runner.invoke(app, [*args, "--skip"])
    assert first.exit_code == 0

    # a later attempt to answer the same PR must not create a sample
    second = runner.invoke(
        app,
        [*args, "--aproveitamento", "5", "--retrabalho", "leve", "--tempo", "economizou"],
    )
    assert second.exit_code == 0
    assert "já registrado" in second.output.lower()


def test_an_out_of_range_answer_is_rejected(env):
    result = runner.invoke(
        app,
        [
            "survey",
            "acme/tool#7",
            "--runtime",
            "R",
            "--model",
            "M",
            "--aproveitamento",
            "9",
            "--retrabalho",
            "leve",
            "--tempo",
            "economizou",
        ],
    )
    assert result.exit_code == 1
    assert "entre 1 e 5" in result.output
    # item inválido não persiste amostra
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=env)
    assert PerceptionStore(target).has_response("acme/tool#7") is False


def test_perception_aggregate_exposes_only_aggregates(env):
    # two answers on the same sprint
    runner.invoke(
        app,
        [
            "survey",
            "acme/tool#7",
            "--runtime",
            "R",
            "--model",
            "M",
            "--aproveitamento",
            "5",
            "--retrabalho",
            "leve",
            "--tempo",
            "economizou",
        ],
    )
    result = runner.invoke(app, ["perception", "2026-A4", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["sprint"] == "2026-A4"
    assert payload["n_samples"] == 1
    assert payload["tempo_dist"] == {"economizou": 1, "neutro": 0, "custou": 0}
    # no respondent identity anywhere in the output
    assert "author" not in result.output and "respond" not in result.output.lower()


def test_perception_gap_crosses_cycle_time(env):
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=env)
    # metrics snapshot gives SPEC-042 a cycle time; perceived "custou" but the only
    # spec sits at the median -> measured 0, perceived +1 -> divergent -> gap 1.0
    MetricSnapshotStore(target).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-042", 100.0, None, None, None, None, None, None, 1),),
        ),
        datetime(2026, 7, 27),
    )
    runner.invoke(
        app,
        [
            "survey",
            "acme/tool#7",
            "--runtime",
            "R",
            "--model",
            "M",
            "--aproveitamento",
            "3",
            "--retrabalho",
            "leve",
            "--tempo",
            "custou",
        ],
    )
    result = runner.invoke(app, ["perception", "2026-A4", "--json"])
    assert json.loads(result.output)["perception_gap"] == 1.0


def test_survey_and_perception_are_discoverable(env):
    out = runner.invoke(app, ["--help"]).output
    assert "survey" in out and "perception" in out
