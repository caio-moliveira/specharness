"""Dashboard live do TL: dia-um do usuário e trava de anti-vigilância (SPEC-024)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from specharness_adapters.db import gateway_from_env
from specharness_core.ports.database import DATABASE_URL_ENV
from specharness_core.scaffold import render_spec_template
from specharness_server.app import app


@pytest.fixture
def live_client(monkeypatch, tmp_path):
    # Dia-um: banco VAZIO (sem seed) e só a spec-semente do `init` em specs/.
    monkeypatch.setenv(DATABASE_URL_ENV, "")
    monkeypatch.delenv("SPECHARNESS_DEMO", raising=False)
    monkeypatch.chdir(tmp_path)
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "SPEC-000-exemplo.md").write_text(render_spec_template(), encoding="utf-8")
    monkeypatch.setenv("SPECHARNESS_SPECS_DIR", str(specs))
    gateway_from_env().migrate()  # cria as tabelas no SQLite vazio, como o `up` faz
    return TestClient(app)


def test_day_one_empty_db_shows_seed_spec_without_error(live_client):
    body = live_client.get("/api/big-picture").json()
    assert body["data_source"] == "live"  # dados reais do usuário, não demo
    statuses = {row["status"]: row["count"] for row in body["specs_by_status"]}
    assert statuses == {"draft": 1}  # o funil mostra a spec-semente
    assert body["metrics"] == []  # banco vazio: métricas vazias, sem erro
    assert body["hygiene"]["orphan_commits"] == 0
    assert body["perception"]["n_samples"] == 0


def test_seed_spec_pipeline_is_available_on_day_one(live_client):
    pipeline = live_client.get("/api/specs/SPEC-000/pipeline").json()
    assert pipeline["spec_id"] == "SPEC-000"
    assert pipeline["stages"]  # o pipeline responde mesmo sem dados ingeridos


_INDIVIDUAL_HINTS = ("author", "respondent", "assignee", "committer", "email", "@")


def test_no_dashboard_endpoint_exposes_individual_data(live_client):
    # ADR-008: agregados, nunca o indivíduo — em NENHUM endpoint do dashboard.
    for path in ("/api/big-picture", "/api/specs/SPEC-000/pipeline"):
        raw = live_client.get(path).text.lower()
        for hint in _INDIVIDUAL_HINTS:
            assert hint not in raw, f"{hint!r} vazou em {path}"
