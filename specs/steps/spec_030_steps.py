"""Step definitions da SPEC-030 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-030 --steps specs/steps/spec_030_steps.py`.
Os passos rodam `init` e `up` reais via CliRunner em diretórios temporários
(mesmo padrão hermético de tests/test_init.py e test_up.py) e leem o README
da raiz do repo para os cenários de conteúdo do quickstart.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_cli import main
from specharness_core.ports.database import DATABASE_URL_ENV
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {}

_README = Path(__file__).resolve().parents[2] / "README.md"

_INIT_ARGS = [
    "init",
    "-y",
    "--tracker",
    "github-issues",
    "--git",
    "github",
    "--db",
    "sqlite",
    "--agent",
    "claude-code",
    "--llm",
    "anthropic",
]


@registry.step(r"um repositório recém-inicializado com specharness init")
def _given_fresh_repo() -> None:
    _state.clear()
    _state["tmp"] = Path(tempfile.mkdtemp(prefix="spec030-init-"))


@registry.step(r"o init termina")
def _when_init_finishes() -> None:
    saved_cwd = os.getcwd()
    try:
        os.chdir(_state["tmp"])
        result = CliRunner().invoke(main.app, _INIT_ARGS)
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        os.chdir(saved_cwd)


@registry.step(
    r"a mensagem de fechamento orienta a rodar specharness llm test antes do specharness up"
)
def _then_init_points_to_llm_test() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    flat = " ".join(_state["output"].split())
    assert "specharness llm test" in flat, flat
    assert flat.index("llm test") < flat.index("specharness up"), flat


def _run_up(*, providers: bool) -> None:
    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    originals = (main.detect_providers, main._run_server)
    started: list[tuple[str, int]] = []
    main.detect_providers = (lambda env: [object()]) if providers else (lambda env: [])
    main._run_server = lambda host, port: started.append((host, port))
    tmp = Path(tempfile.mkdtemp(prefix="spec030-up-"))
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(main.app, ["up"])
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
        _state["started"] = started
    finally:
        os.chdir(saved_cwd)
        main.detect_providers, main._run_server = originals
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


@registry.step(r"um ambiente sem nenhum provedor LLM disponível")
def _given_no_provider() -> None:
    _state.clear()
    _state["providers"] = False


@registry.step(r"um ambiente com um provedor LLM disponível")
def _given_with_provider() -> None:
    _state.clear()
    _state["providers"] = True


@registry.step(r"o up roda")
def _when_up_runs() -> None:
    _run_up(providers=_state["providers"])


@registry.step(
    r"o boot avisa que o Readiness Gate fica inoperante com a orientação "
    r"unificada de provedores e o servidor sobe"
)
def _then_up_warns_and_boots() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _state["started"], "o aviso não pode impedir o boot"
    flat = " ".join(_state["output"].split())
    assert "Nenhum provedor LLM" in flat, flat
    assert "ANTHROPIC_API_KEY" in flat, flat  # orientação unificada (SPEC-027)


@registry.step(r"o servidor sobe e nenhum aviso de provedor LLM aparece")
def _then_up_boots_without_warning() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _state["started"]
    assert "Nenhum provedor LLM" not in _state["output"], _state["output"]


@registry.step(r"o quickstart do README")
def _given_readme_quickstart() -> None:
    _state.clear()
    text = _README.read_text(encoding="utf-8")
    _state["requirements"] = text[text.index("Requirements:") : text.index("```bash")]
    _state["commands"] = text[text.index("```bash") : text.index("```", text.index("```bash") + 3)]


@registry.step(r"um usuário novo segue os requisitos listados")
def _when_user_reads_requirements() -> None:
    pass  # o conteúdo já está em _state["requirements"]


@registry.step(r"um usuário novo copia os comandos de setup")
def _when_user_copies_commands() -> None:
    pass  # o conteúdo já está em _state["commands"]


@registry.step(
    r"o requisito de uma API key de LLM ou Ollama local está declarado "
    r"antes dos comandos de setup"
)
def _then_llm_requirement_declared() -> None:
    requirements = _state["requirements"]
    assert "API key" in requirements, requirements
    assert "Ollama" in requirements, requirements
    assert "ADR-006" in requirements, requirements


@registry.step(
    r"o clone aponta o repositório real sem placeholder, a instalação do just "
    r"está indicada e o Node é listado como requisito do dashboard"
)
def _then_quickstart_is_copy_paste() -> None:
    assert "<org>" not in _state["commands"], _state["commands"]
    assert "git clone https://github.com/caio-moliveira/specharness" in _state["commands"]
    assert "uv tool install rust-just" in _state["requirements"], _state["requirements"]
    assert "Node" in _state["requirements"], _state["requirements"]
