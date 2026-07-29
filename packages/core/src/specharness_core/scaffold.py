"""Scaffolding do harness no repo do usuário, como lógica pura (SPEC-023).

Sem I/O (ADR-001): dadas as seleções (SPEC-022) e os parâmetros de processo,
RENDERIZA o conteúdo dos arquivos de instrução que um coding agent segue — o
`AGENTS.md` base (ADR-003), a camada do agente (dados de `profiles/`, ADR-004),
o hook de enforcement do trailer e o guia de `specs/`. Escrever no disco e
instalar o hook no git são responsabilidade do CLI.

A espinha fixa do método (readiness gate, trailer `Spec:`, BDD travando `done`,
métricas que nunca expõem indivíduos, ADR-016) entra SEMPRE — os parâmetros
ajustam limiares e convenções, nunca a existência dos gates (ADR-021).
"""

from __future__ import annotations

from dataclasses import dataclass

#: Marcadores que DEVEM aparecer no AGENTS.md gerado, em qualquer combinação —
#: a prova de que a espinha fixa é inegociável (ADR-021, cenário "não desligável").
FIXED_SPINE: tuple[str, ...] = (
    "Readiness Gate",
    "Spec: SPEC-",
    "BDD",
    "nunca expõem indivíduos",
    "quem implementa não arbitra",
    "verificar-spec",
)

#: Arquivo de instrução por coding agent suportado (a "camada" sobre o AGENTS.md).
AGENT_LAYER_FILE: dict[str, str] = {
    "claude-code": "CLAUDE.md",
    "codex": "CODEX.md",
    "kimi": "KIMI.md",
}


@dataclass(frozen=True)
class ScaffoldParams:
    """Parâmetros de processo do time. Ajustam a espinha fixa, não a desligam."""

    commit_convention: str = "conventional"
    coverage_min: int = 85
    bdd_language: str = "pt"


def render_agents_md(tracker: str, params: ScaffoldParams) -> str:
    """O AGENTS.md base: espinha fixa do método + parâmetros do time (SPEC-023)."""
    planning = "GitHub" if tracker == "github-issues" else tracker
    return f"""# Guia para Agentes de Código (gerado por specharness init)

Este repositório usa **Spec-Driven Development** instrumentado pelo specharness:
toda mudança pertence a uma spec, todo commit carrega o trailer `Spec:`, toda
spec `done` tem BDD verde. Os gates abaixo são a espinha fixa do método — não são
desligáveis.

## De onde você puxa o trabalho

Implemente sempre o próximo spec em estado `ready` em `specs/`, derivado do
WorkItem do tracker do time ({planning}). Se não existe spec para o que você vai
fazer, ela vem primeiro.

## Gates inegociáveis

1. **Readiness Gate antes do código** — nenhuma spec vira código sem passar no
   Definition of Ready (checagens determinísticas + revisão semântica).
2. **Trailer obrigatório** no último bloco do commit: `Spec: SPEC-NNN` (o hook
   de commit-msg bloqueia sem ele).
3. **BDD trava o `done`** — uma spec só fecha com os cenários Gherkin verdes.
4. **As métricas nunca expõem indivíduos** — medem processo, spec e agente;
   número auto-relatado por agente não entra no cálculo.
5. **quem implementa não arbitra** — seu auto-relato é alegação; a evidência vem
   de artefatos (CI, coverage, git). Toda entrega passa pelo `verificar-spec` em
   contexto limpo antes do relatório final.

## Convenções do time

- Commits: **{params.commit_convention}** + trailer `Spec: SPEC-NNN`.
- Testes: cobertura mínima de **{params.coverage_min}%** no código de domínio.
- BDD: cenários em Gherkin (`# language: {params.bdd_language}`).
- PR: exige checks verdes (lint + testes) e revisão antes do merge.

## Fluxo por spec

1. Leia a spec `ready` em `specs/`.
2. Implemente com testes que cobrem os cenários da spec.
3. Rode lint + testes antes de encerrar.
4. Commit com trailer. Atualize o `status` da spec até `verifying` (o `done` é
   do CI).
"""


def render_agent_layer(agent: str, tracker: str) -> str:
    """A camada do agente selecionado — aponta para o AGENTS.md base (ADR-003/004)."""
    return f"""# Camada {agent} (gerado por specharness init)

Este arquivo é a camada específica do agente **{agent}** sobre o `AGENTS.md`
base deste repositório. Leia `AGENTS.md` primeiro — ele define a espinha fixa do
método (Readiness Gate, trailer `Spec:`, BDD travando `done`, métricas que nunca
expõem indivíduos, e o `verificar-spec` antes de entregar).

- Puxe o trabalho do próximo spec `ready` em `specs/`, derivado do tracker
  ({tracker}).
- Este perfil deriva de `profiles/{agent}` (dados do specharness, ADR-004) e
  amadurece com as práticas oficiais do fornecedor.
"""


def render_commit_msg_hook() -> str:
    """Hook commit-msg portátil (POSIX sh): barra commit sem trailer `Spec:`."""
    return """#!/bin/sh
# Gerado por specharness init (SPEC-023): todo commit precisa do trailer
# `Spec: SPEC-NNN`. Merges e fixup!/squash! são isentos.
case "$(head -n 1 "$1")" in
  Merge*|fixup!*|squash!*) exit 0 ;;
esac
if grep -Eq '^Spec: SPEC-[0-9]{3,}' "$1"; then
  exit 0
fi
echo "✗ Commit sem trailer 'Spec: SPEC-NNN' (specharness)." >&2
exit 1
"""


def render_specs_readme(tracker: str) -> str:
    """Guia do diretório specs/ no repo do usuário."""
    return f"""# specs/ — o backlog deste projeto

Cada arquivo é uma spec: contexto, cenários BDD e métricas de sucesso. O fluxo:
WorkItem no tracker ({tracker}) → passa no Readiness Gate → vira spec aqui →
o coding agent implementa a spec `ready` → BDD verde fecha o `done`.

Credenciais ficam só no `.env` (nunca no specharness.yaml). Rode `specharness up`
para ver o dashboard do projeto.
"""


def scaffold_files(agent: str, tracker: str, params: ScaffoldParams) -> dict[str, str]:
    """Mapa caminho-relativo → conteúdo dos arquivos a escrever no repo do usuário.

    O hook de commit-msg NÃO está aqui: ele é instalado no `.git/hooks` pelo CLI,
    porque precisa virar executável e vive fora da árvore versionada.
    """
    if agent not in AGENT_LAYER_FILE:
        raise ValueError(
            f"agente '{agent}' sem camada conhecida; use um de: {list(AGENT_LAYER_FILE)}"
        )
    return {
        "AGENTS.md": render_agents_md(tracker, params),
        AGENT_LAYER_FILE[agent]: render_agent_layer(agent, tracker),
        "specs/README.md": render_specs_readme(tracker),
    }
