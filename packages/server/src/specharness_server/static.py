"""Servir o dashboard compilado a partir da API (SPEC-021).

`specharness up` serve API + dashboard numa porta só. O dashboard compilado
(Vite → dist) é localizado aqui, nesta ordem: um override por env, o pacote
embutido no wheel, e o `web/dist` de desenvolvimento. Quando ausente (checkout
de código sem build), a raiz devolve uma orientação em vez de um 404 seco.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

#: Onde o build do dashboard fica embutido no pacote publicado (SPEC-021).
_PACKAGED = Path(__file__).parent / "_web"


def dashboard_dir() -> Path | None:
    """Diretório com o dashboard compilado (contém index.html), ou None."""
    candidates: list[Path] = []
    override = os.environ.get("SPECHARNESS_WEB_DIST")
    if override:
        candidates.append(Path(override))
    candidates.append(_PACKAGED)  # embutido no wheel
    candidates.append(Path.cwd() / "web" / "dist")  # checkout de desenvolvimento
    for path in candidates:
        if (path / "index.html").is_file():
            return path
    return None


def mount_dashboard(app: FastAPI) -> None:
    """Monta o dashboard em / (depois das rotas de API), ou uma dica se não houver build.

    Deve ser chamada por último: as rotas /health, /api/* e /docs já estão
    registradas e têm precedência sobre o mount em "/".
    """
    dist = dashboard_dir()
    if dist is not None:
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
        return

    @app.get("/", include_in_schema=False)
    def _dashboard_missing() -> PlainTextResponse:
        return PlainTextResponse(
            "Dashboard não compilado. Instale o pacote publicado (o wheel já traz o "
            "dashboard) ou, em desenvolvimento, rode o build do web/. A API está em "
            "/api e a documentação em /docs.",
            status_code=200,
        )
