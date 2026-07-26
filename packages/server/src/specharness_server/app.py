"""specharness web API (SPEC-002 §1.2). Endpoints land as their specs are built."""

from __future__ import annotations

from fastapi import FastAPI
from specharness_core import __version__

app = FastAPI(
    title="specharness",
    version=__version__,
    description="Decision, quality and metrics layer for spec-driven development.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
