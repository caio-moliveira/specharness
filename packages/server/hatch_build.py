"""Build hook (SPEC-021): embute o dashboard compilado no wheel do server.

Escopado ao target `wheel` (não roda em instalação editável / `uv sync`). Copia
`web/dist` → `specharness_server/_web` na hora de empacotar. Se o dashboard não
foi compilado, FALHA o build — em vez de publicar um wheel sem dashboard em
silêncio (o furo que a verificação adversarial pegou).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class DashboardBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        server_root = Path(self.root)
        target = server_root / "src" / "specharness_server" / "_web"
        dist = server_root.parent.parent / "web" / "dist"

        if (dist / "index.html").is_file():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(dist, target)
        elif not (target / "index.html").is_file():
            raise RuntimeError(
                "Dashboard não compilado: nem web/dist nem _web existem. "
                "Rode `just build-web` antes de empacotar o wheel (SPEC-021)."
            )
