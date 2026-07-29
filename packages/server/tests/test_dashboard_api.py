"""Dashboard API: big picture + pipeline, over seeded data (SPEC-016, SPEC-018)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_server.app import app
from specharness_server.seed import SEED_SPRINT, demo_target, seed


@pytest.fixture
def client(monkeypatch, tmp_path):
    # isolate the DB and the specs dir so the API reads a known world
    monkeypatch.setenv(DATABASE_URL_ENV, "")
    monkeypatch.delenv("SPECHARNESS_DEMO", raising=False)
    monkeypatch.chdir(tmp_path)
    specs = tmp_path / "specs"
    specs.mkdir()
    _write_spec(specs, "SPEC-013", "verifying")
    _write_spec(specs, "SPEC-014", "done")
    _write_spec(specs, "SPEC-015", "approved")
    (specs / "SPEC-999-bad.md").write_text("not a valid spec", encoding="utf-8")  # skipped
    monkeypatch.setenv("SPECHARNESS_SPECS_DIR", str(specs))

    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    seed(target)
    return TestClient(app)


def _write_spec(specs_dir, spec_id: str, status: str, sprint: str = SEED_SPRINT) -> None:
    (specs_dir / f"{spec_id}-x.md").write_text(
        "---\n"
        f"spec: {spec_id}\n"
        'title: "T"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        f"sprint: {sprint}\n"
        'success_metrics: ["m < 1s"]\n'
        'acceptance: ["a"]\n'
        "---\n\n## Contexto\n",
        encoding="utf-8",
    )


def test_big_picture_with_seed_data(client):
    body = client.get("/api/big-picture").json()

    assert body["phase"] is None  # sem fase interna do specharness vazando (SPEC-025)
    assert body["sprint"] == SEED_SPRINT
    statuses = {row["status"]: row["count"] for row in body["specs_by_status"]}
    assert statuses == {"approved": 1, "done": 1, "verifying": 1}
    # metrics come from the seeded snapshot
    m13 = next(m for m in body["metrics"] if m["spec_id"] == "SPEC-013")
    assert m13["first_run_pass_rate"] == 0.9
    assert m13["status"] == "verifying"  # joined from the registry


def test_big_picture_shows_hygiene_orphans(client):
    body = client.get("/api/big-picture").json()
    # the seed includes one commit with no trailer -> one orphan commit
    assert body["hygiene"]["orphan_commits"] == 1


def test_big_picture_shows_perception_aggregate_only(client):
    body = client.get("/api/big-picture").json()
    perception = body["perception"]
    assert perception["n_samples"] == 2
    assert perception["n_skipped"] == 1
    # aggregate only — no per-respondent field leaks into the payload
    assert "author" not in body and "respondent" not in str(body).lower()


def test_pipeline_tells_the_spec_story_in_order(client):
    body = client.get("/api/specs/SPEC-013/pipeline").json()

    assert body["spec_id"] == "SPEC-013"
    stages = [s["stage"] for s in body["stages"]]
    assert stages == ["readiness", "commits", "bdd", "review", "perception"]
    by_stage = {s["stage"]: s for s in body["stages"]}
    assert by_stage["commits"]["status"] == "done"  # SPEC-013 has a seeded commit
    assert by_stage["perception"]["status"] == "done"  # and a perception sample
    assert by_stage["review"]["status"] == "unavailable"  # reviews not ingested


def test_pipeline_for_an_unknown_spec_is_404(client):
    assert client.get("/api/specs/SPEC-999/pipeline").status_code == 404


def test_openapi_documents_the_dashboard_contract(client):
    schema = client.get("/openapi.json").json()
    assert "/api/big-picture" in schema["paths"]
    assert "/api/specs/{spec_id}/pipeline" in schema["paths"]
    # the response model is part of the contract the web client is generated from
    assert "BigPicture" in schema["components"]["schemas"]


def test_seed_is_idempotent(client, tmp_path):
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    assert seed(target) is False  # already seeded by the fixture


# --- modo demo (SPEC-018, ADR-019) ------------------------------------------


def test_big_picture_reports_live_data_source(client):
    body = client.get("/api/big-picture").json()

    assert body["data_source"] == "live"


@pytest.fixture
def demo_client(monkeypatch, tmp_path):
    # registry real numa sprint real; o modo demo tem de defaultar a sprint do seed
    monkeypatch.setenv(DATABASE_URL_ENV, "")
    monkeypatch.chdir(tmp_path)
    specs = tmp_path / "specs"
    specs.mkdir()
    _write_spec(specs, "SPEC-013", "verifying", sprint="2026-A4")
    monkeypatch.setenv("SPECHARNESS_SPECS_DIR", str(specs))
    monkeypatch.setenv("SPECHARNESS_DEMO", "1")
    seed(demo_target())
    return TestClient(app)


def test_demo_mode_serves_the_demo_db_and_flags_it(demo_client):
    body = demo_client.get("/api/big-picture").json()

    assert body["data_source"] == "demo"
    assert body["sprint"] == SEED_SPRINT  # não a sprint real do registry
    assert body["metrics"]  # as métricas do seed aparecem
    pipeline = demo_client.get("/api/specs/SPEC-013/pipeline").json()
    assert pipeline["stages"]  # o pipeline também sai do banco demo


def test_seed_main_never_touches_the_env_database(monkeypatch, tmp_path):
    from specharness_server import seed as seed_module

    real = tmp_path / "real.db"
    monkeypatch.setenv(DATABASE_URL_ENV, f"sqlite:///{real.as_posix()}")
    monkeypatch.chdir(tmp_path)

    seed_module.main()

    assert (tmp_path / ".specharness" / "demo.db").is_file()
    assert not real.exists()  # o banco resolvido do ambiente ficou intacto


def test_pipeline_stages_carry_translation_keys_and_counts(client):
    body = client.get("/api/specs/SPEC-013/pipeline").json()

    by_stage = {s["stage"]: s for s in body["stages"]}
    assert all(s["detail_key"] for s in body["stages"])  # nenhum estágio sem chave
    assert by_stage["readiness"]["detail_key"] == "detailSpecStatus"
    assert by_stage["readiness"]["detail_value"] == "verifying"
    assert by_stage["commits"]["detail_key"] == "detailLinkedCommits"
    assert by_stage["commits"]["detail_count"] == 1  # commit do seed vinculado
    assert by_stage["bdd"]["detail_count"] == 0  # sem scenario runs no seed
    assert by_stage["perception"]["detail_count"] == 1  # amostra do seed


# ADR-008 sobre respostas POPULADAS (seed) — pega vazamento em campo que carrega
# dado, que o teste dia-um (banco vazio) não pegaria (SPEC-024, ressalva).
_INDIVIDUAL_HINTS = ("author", "respondent", "assignee", "committer", "email", "@")


def test_no_individual_data_over_populated_dashboard(client):
    for path in ("/api/big-picture", "/api/specs/SPEC-013/pipeline"):
        raw = client.get(path).text.lower()
        for hint in _INDIVIDUAL_HINTS:
            assert hint not in raw, f"{hint!r} vazou em {path}"
