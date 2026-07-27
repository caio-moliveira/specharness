"""specharness web API (SPEC-002 §1.2, SPEC-016).

Read-only in Fase A: the dashboard's big-picture and per-spec pipeline views. The
server is a delivery layer over core + the SPEC-013/014 stores; its Pydantic models
are the OpenAPI contract the web client is generated from (ADR-014).
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from specharness_adapters.db import gateway_from_env
from specharness_core import __version__

from .assembly import big_picture, spec_pipeline
from .models import BigPicture, SpecPipeline

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@app.get("/api/big-picture", response_model=BigPicture, tags=["dashboard"])
def get_big_picture(sprint: str | None = None) -> BigPicture:
    """Big picture: fase, specs por status, métricas da sprint e higiene (SPEC-016)."""
    return big_picture(gateway_from_env().target, _specs_dir(), sprint)


@app.get("/api/specs/{spec_id}/pipeline", response_model=SpecPipeline, tags=["dashboard"])
def get_spec_pipeline(spec_id: str) -> SpecPipeline:
    """Pipeline por spec: readiness → commits → BDD → review → percepção (SPEC-016)."""
    pipeline = spec_pipeline(gateway_from_env().target, _specs_dir(), spec_id)
    if pipeline is None:
        raise HTTPException(status_code=404, detail=f"spec {spec_id} não encontrada")
    return pipeline
