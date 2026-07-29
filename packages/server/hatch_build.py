"""Build hook (SPEC-021): garante que o wheel do server embute o dashboard.

O dashboard compilado é colocado em `specharness_server/_web` por `just build-web`
(cópia de `web/dist`) e entra no sdist/wheel via `artifacts`. Este hook apenas
VERIFICA: um wheel real (version "standard") sem `_web` FALHA o build, em vez de
publicar um pacote sem dashboard em silêncio. Instalação editável (uv sync/dev)
é ignorada — não empacota nem exige o dashboard, então o CI que roda `uv sync`
sem build do web não quebra.

Não copiar de `web/dist` aqui de propósito: em `uv build` isolado o hook roda
num diretório temporário e não alcança a árvore do repo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class DashboardBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return
        target = Path(self.root) / "src" / "specharness_server" / "_web"
        if not (target / "index.html").is_file():
            raise RuntimeError(
                "Dashboard não compilado: specharness_server/_web ausente. "
                "Rode `just build-web` antes de empacotar o wheel (SPEC-021)."
            )
