"""`specharness ready <spec>` — deterministic floor + LLM layer + override (SPEC-010/011)."""

from __future__ import annotations

import json

import pytest
from specharness_cli.main import app
from specharness_core import Evaluation
from specharness_core.ports.llm import LLMError
from typer.testing import CliRunner

runner = CliRunner()


def _good_spec(spec_id: str, deps: str = "[SPEC-003]", status: str = "approved") -> str:
    return (
        "---\n"
        f"spec: {spec_id}\n"
        f'title: "T {spec_id}"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        "sprint: 2026-A2\n"
        "tracker_refs: []\n"
        f"depends_on: {deps}\n"
        "adrs: []\n"
        "success_metrics:\n"
        '  - "linking em < 500ms"\n'
        "acceptance:\n"
        '  - "Commit com trailer válido é vinculado à spec"\n'
        "---\n\n"
        "## Cenários\n\n"
        "```gherkin\n"
        "# language: pt\n"
        "Funcionalidade: linking\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        "    Então o commit é vinculado à spec\n"
        "```\n"
    )


@pytest.fixture(autouse=True)
def in_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "SPEC-003-x.md").write_text(_good_spec("SPEC-003", deps="[]"), "utf-8")
    (tmp_path / "specs" / "SPEC-042-y.md").write_text(_good_spec("SPEC-042"), "utf-8")
    return tmp_path


@pytest.fixture
def with_provider(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.detect_providers", lambda env: ["anthropic"])


@pytest.fixture
def no_provider(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.detect_providers", lambda env: [])


def _fake_llm(monkeypatch, score, counter=None):
    def fake(text, client):
        if counter is not None:
            counter.append(1)
        return Evaluation(
            score=score, issues=(), model="ollama/qwen3:8b", cost_usd=0.001, cached=False
        )

    monkeypatch.setattr("specharness_cli.main.evaluate_spec", fake)


# --- piso determinístico (SPEC-010) ----------------------------------------


def test_floor_block_stops_before_the_llm_layer(monkeypatch, in_repo, with_provider):
    called: list = []
    _fake_llm(monkeypatch, 90, called)
    bad = _good_spec("SPEC-042").replace(
        '  - "Commit com trailer válido é vinculado à spec"\n',
        '  - "Commit com trailer válido é vinculado à spec"\n  - "Exporta relatório em PDF"\n',
    )
    (in_repo / "specs" / "SPEC-042-y.md").write_text(bad, "utf-8")

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "sem cenário que o cubra" in result.output
    assert called == []  # a camada LLM não roda quando o piso bloqueia


# --- camada semântica pendente (ADR-006) -----------------------------------


def test_floor_passes_but_no_provider_is_semantic_pending(no_provider):
    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "semântica pendente" in result.output.lower()


# --- camada LLM (SPEC-011) --------------------------------------------------


def test_a_high_score_passes_the_llm_layer(monkeypatch, with_provider):
    _fake_llm(monkeypatch, 92)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 0, result.output
    assert "passa na camada LLM" in result.output
    assert "92/100" in result.output


def test_a_low_score_blocks_with_override_guidance(monkeypatch, with_provider):
    _fake_llm(monkeypatch, 50)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "bloqueada pela camada LLM" in result.output
    assert "--override" in result.output


def test_unchanged_spec_uses_the_cache_on_the_second_run(monkeypatch, with_provider):
    calls: list = []
    _fake_llm(monkeypatch, 92, calls)

    first = runner.invoke(app, ["ready", "SPEC-042"])
    second = runner.invoke(app, ["ready", "SPEC-042"])

    assert first.exit_code == 0 and second.exit_code == 0
    assert len(calls) == 1  # a 2ª execução veio do cache
    assert "cache" in second.output


# --- override auditado (critério 3) ----------------------------------------


def test_override_is_audited_and_unblocks(monkeypatch):
    result = runner.invoke(
        app, ["ready", "SPEC-042", "--override", "--author", "Ana", "--reason", "release urgente"]
    )

    assert result.exit_code == 0, result.output
    assert "Override registrado por Ana" in result.output
    assert "release urgente" in result.output


def test_override_requires_author_and_reason():
    result = runner.invoke(app, ["ready", "SPEC-042", "--override", "--author", "Ana"])

    assert result.exit_code == 1
    assert "author" in result.output and "reason" in result.output


# --- resolução / erros ------------------------------------------------------


def test_a_missing_spec_is_reported():
    result = runner.invoke(app, ["ready", "SPEC-999"])

    assert result.exit_code == 1
    assert "não encontrada" in result.output


def test_ready_is_discoverable_from_help():
    result = runner.invoke(app, ["--help"])

    assert "ready" in result.output


# --- veredito consolidado (SPEC-017) ----------------------------------------


def test_floor_block_ends_with_a_verdict(monkeypatch, in_repo, with_provider):
    _fake_llm(monkeypatch, 90)
    bad = _good_spec("SPEC-042").replace(
        '  - "Commit com trailer válido é vinculado à spec"\n',
        '  - "Commit com trailer válido é vinculado à spec"\n  - "Exporta relatório em PDF"\n',
    )
    (in_repo / "specs" / "SPEC-042-y.md").write_text(bad, "utf-8")

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "Veredito: BLOQUEADA" in result.output
    assert "piso determinístico" in result.output


def test_no_provider_ends_with_a_blocked_verdict(no_provider):
    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "Veredito: BLOQUEADA" in result.output
    assert "semântica pendente" in result.output.lower()


def test_a_pass_ends_with_verdict_pronta(monkeypatch, with_provider):
    _fake_llm(monkeypatch, 92)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 0, result.output
    assert "Veredito: PRONTA" in result.output


def test_a_low_score_verdict_names_score_and_threshold(monkeypatch, with_provider):
    _fake_llm(monkeypatch, 50)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "Veredito: BLOQUEADA" in result.output
    assert "score 50" in result.output and "limiar" in result.output


def test_override_ends_with_a_verdict(monkeypatch):
    result = runner.invoke(
        app, ["ready", "SPEC-042", "--override", "--author", "Ana", "--reason", "release urgente"]
    )

    assert result.exit_code == 0, result.output
    assert "Veredito: PRONTA" in result.output
    assert "override" in result.output.lower()


def _fake_llm_error(monkeypatch):
    def fake(text, client):
        raise LLMError("provedor caiu no meio da avaliação")

    monkeypatch.setattr("specharness_cli.main.evaluate_spec", fake)


def test_an_llm_error_ends_with_a_blocked_verdict(monkeypatch, with_provider):
    _fake_llm_error(monkeypatch)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "provedor caiu" in result.output
    assert "Veredito: BLOQUEADA" in result.output
    assert "erro na camada LLM" in result.output


def test_ready_json_reports_an_llm_error(monkeypatch, with_provider):
    _fake_llm_error(monkeypatch)

    result = runner.invoke(app, ["ready", "SPEC-042", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "blocked"
    assert payload["reason"] == "erro na camada LLM"
    assert payload["llm"] is None


def test_ready_json_emits_the_verdict(monkeypatch, with_provider):
    _fake_llm(monkeypatch, 92)

    result = runner.invoke(app, ["ready", "SPEC-042", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "ready"
    assert payload["floor"]["passed"] is True
    assert payload["llm"]["score"] == 92


def test_ready_json_blocked_names_the_reason(no_provider):
    result = runner.invoke(app, ["ready", "SPEC-042", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "blocked"
    assert "semântica" in payload["reason"]


# --- SPEC-033: veredito PRONTA grava a transição -----------------------------


def test_approval_promotes_the_spec_to_ready(monkeypatch, in_repo, with_provider):
    _fake_llm(monkeypatch, 90)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 0, result.output
    text = (in_repo / "specs" / "SPEC-042-y.md").read_text("utf-8")
    assert "status: ready" in text
    assert "status: ready gravado" in result.output


def test_override_also_promotes(in_repo):
    result = runner.invoke(
        app, ["ready", "SPEC-042", "--override", "--author", "tl", "--reason", "prazo"]
    )

    assert result.exit_code == 0, result.output
    assert "status: ready" in (in_repo / "specs" / "SPEC-042-y.md").read_text("utf-8")


def test_draft_is_not_promoted_and_gets_guidance(monkeypatch, in_repo, with_provider):
    path = in_repo / "specs" / "SPEC-042-y.md"
    path.write_text(path.read_text("utf-8").replace("status: approved", "status: draft"), "utf-8")
    _fake_llm(monkeypatch, 90)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 0, result.output
    assert "status: draft" in path.read_text("utf-8")  # arquivo intocado
    assert "aprove" in result.output.lower()


def test_blocked_verdict_leaves_the_file_untouched(monkeypatch, in_repo, with_provider):
    path = in_repo / "specs" / "SPEC-042-y.md"
    before = path.read_text("utf-8")
    _fake_llm(monkeypatch, 10)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert path.read_text("utf-8") == before


def test_json_reports_the_promotion(monkeypatch, in_repo, with_provider):
    _fake_llm(monkeypatch, 90)

    result = runner.invoke(app, ["ready", "SPEC-042", "--json"])

    payload = json.loads([line for line in result.output.splitlines() if line.strip()][-1])
    assert payload["promoted"] is True
