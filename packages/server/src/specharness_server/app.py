"""specharness web API (SPEC-002 §1.2, SPEC-016).

Read-only in Fase A: the dashboard's big-picture and per-spec pipeline views. The
server is a delivery layer over core + the SPEC-013/014 stores; its Pydantic models
are the OpenAPI contract the web client is generated from (ADR-014).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from specharness_adapters.db import gateway_from_env
from specharness_core import __version__
from specharness_core.ports.database import DatabaseTarget

from .assembly import big_picture, spec_pipeline
from .models import BigPicture, SpecPipeline
from .seed import SEED_SPRINT, demo_target
from .static import mount_dashboard

# Onboarding sem fricção (SPEC-004/005): o server lê o mesmo .env que o CLI,
# então `uvicorn specharness_server.app:app` funciona sem --env-file. Variáveis
# já exportadas no shell têm precedência.
load_dotenv(Path.cwd() / ".env")

app = FastAPI(
    title="specharness",
    version=__version__,
    description="Decision, quality and metrics layer for spec-driven development.",
)

# The dev web app (Vite) runs on another origin; read-only GETs are safe to share.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _specs_dir() -> Path:
    return Path(os.environ.get("SPECHARNESS_SPECS_DIR", "specs"))


def _demo() -> bool:
    """Modo demo (SPEC-018, ADR-019): `just dev` seta SPECHARNESS_DEMO=1."""
    return os.environ.get("SPECHARNESS_DEMO", "") in {"1", "true"}


def _target() -> DatabaseTarget:
    return demo_target() if _demo() else gateway_from_env().target


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/big-picture", response_model=BigPicture, tags=["dashboard"])
def get_big_picture(sprint: str | None = None) -> BigPicture:
    """Big picture: fase, specs por status, métricas da sprint e higiene (SPEC-016).

    Em modo demo a sprint default é a do seed — o registry em disco escolheria a
    sprint real do projeto e as métricas demo sumiriam (SPEC-018).
    """
    if _demo():
        return big_picture(_target(), _specs_dir(), sprint or SEED_SPRINT, data_source="demo")
    # Live é o padrão (SPEC-024): dados reais do projeto do usuário, explícito para
    # o contrato não depender do default de big_picture.
    return big_picture(_target(), _specs_dir(), sprint, data_source="live")


@app.get("/api/specs/{spec_id}/pipeline", response_model=SpecPipeline, tags=["dashboard"])
def get_spec_pipeline(spec_id: str) -> SpecPipeline:
    """Pipeline por spec: readiness → commits → BDD → review → percepção (SPEC-016)."""
    pipeline = spec_pipeline(_target(), _specs_dir(), spec_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"spec {spec_id} não encontrada")
    return pipeline


# Por último (SPEC-021): o dashboard é servido em "/", sem sombrear /health,
# /api/* e /docs, que já foram registrados acima.
mount_dashboard(app)
