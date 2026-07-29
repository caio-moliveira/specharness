"""Nenhum rótulo interno do specharness vaza no produto do usuário (SPEC-025).

Cobre os quatro critérios: phase não expõe a fase interna do roadmap; os chips de
proveniência são genéricos; o estágio review não cita spec interna; e as mensagens
da UI apontam comandos do produto, não recipes internas (`just`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from specharness_adapters.db import gateway_from_env
from specharness_core.ports.database import DATABASE_URL_ENV
from specharness_core.scaffold import render_spec_template
from specharness_server.app import app

#: Raiz do repo, para varrer as fontes da UI servida (…/packages/server/tests).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_WEB_SOURCES = (
    _REPO_ROOT / "web" / "src" / "i18n.ts",
    _REPO_ROOT / "web" / "src" / "components" / "BigPictureView.tsx",
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv(DATABASE_URL_ENV, "")
    monkeypatch.delenv("SPECHARNESS_DEMO", raising=False)
    monkeypatch.chdir(tmp_path)
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "SPEC-000-exemplo.md").write_text(render_spec_template(), encoding="utf-8")
    monkeypatch.setenv("SPECHARNESS_SPECS_DIR", str(specs))
    gateway_from_env().migrate()
    return TestClient(app)


def test_phase_does_not_expose_the_internal_roadmap_phase(client):
    body = client.get("/api/big-picture").json()
    assert body["phase"] is None  # nunca a constante "Fase A" do roadmap do specharness
    assert "Fase A" not in client.get("/api/big-picture").text


def test_review_stage_text_names_no_internal_spec(client):
    body = client.get("/api/specs/SPEC-000/pipeline").json()
    review = next(s for s in body["stages"] if s["stage"] == "review")
    assert "SPEC-" not in review["detail"]  # sem citar a spec interna que adiou a ingestão


def _ui_strings(source: Path) -> str:
    """O conteúdo da fonte sem as linhas de comentário `//`.

    Comentários de dev citam a spec de origem (ex.: 'SPEC-016') legitimamente; o
    que vai à UI são os VALORES de string. Varremos só estes para não confundir
    documentação de código com rótulo servido ao usuário.
    """
    lines = [
        ln
        for ln in source.read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("//")
    ]
    return "\n".join(lines)


def test_ui_sources_carry_no_internal_labels(client):
    """Os textos da UI servida não trazem IDs de spec internas, 'Fase A' nem `just`."""
    for source in _WEB_SOURCES:
        text = _ui_strings(source)
        assert "Fase A" not in text, f"'Fase A' vazou em {source.name}"
        assert "SPEC-0" not in text, f"ID de spec interna vazou em {source.name}"
        assert "just " not in text, f"recipe interna 'just' vazou em {source.name}"


def test_provenance_chips_use_generic_sources(client):
    """Os chips citam a origem genérica (registry/git/snapshot/survey), sem ID de spec."""
    view = (_REPO_ROOT / "web" / "src" / "components" / "BigPictureView.tsx").read_text(
        encoding="utf-8"
    )
    assert 'source="snapshot"' in view
    assert 'source="survey"' in view
    assert "SPEC-013" not in view and "SPEC-014" not in view
