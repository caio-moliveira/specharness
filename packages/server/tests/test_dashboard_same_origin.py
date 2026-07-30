"""Dashboard embutido resolve a API na mesma origem que o serve (SPEC-028).

O bundle de produção não pode assar um host absoluto (localhost): o `specharness
up` embute dashboard e API na mesma porta, e o usuário pode servir em outra
porta/host. O dev com Vite em porta separada aponta a API via variável explícita.
"""

from __future__ import annotations

from pathlib import Path

#: Raiz do repo (…/packages/server/tests) para ler as fontes/config do web.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_TS = _REPO_ROOT / "web" / "src" / "api.ts"
_ENV_DEV = _REPO_ROOT / "web" / ".env.development"


def test_api_client_defaults_to_same_origin_not_localhost():
    # Sem VITE_API_BASE_URL, a base é vazia (same-origin) — nunca um host absoluto
    # embutido na fonte (SPEC-028, critério 1).
    source = _API_TS.read_text(encoding="utf-8")
    assert "localhost" not in source, "host absoluto embutido em api.ts"
    assert '?? ""' in source, "o default do OpenAPI.BASE deve ser same-origin (string vazia)"


def test_dev_reaches_the_api_via_explicit_base_variable():
    # O dev com Vite em porta separada alcança a API pela variável explícita, que o
    # build de produção não carrega (SPEC-028, critério 2).
    assert _ENV_DEV.is_file(), "web/.env.development deve existir para o dev do frontend"
    env = _ENV_DEV.read_text(encoding="utf-8")
    assert "VITE_API_BASE_URL=" in env
    assert "8321" in env  # aponta a porta separada da API em dev
