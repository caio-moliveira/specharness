# ADR-001 — Formato canônico primeiro, adapters depois (ports & adapters)

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Precisamos integrar múltiplos trackers (Redmine, Jira, Azure DevOps, GitHub), runtimes de agente e provedores de LLM, cada um com taxonomia e API próprias. Acoplar o domínio a qualquer um deles tornaria cada nova integração uma cirurgia no core.

## Opções consideradas

1. Acoplar direto ao primeiro tracker (Redmine) — mais rápido no início, insustentável a partir do segundo
2. Ports & adapters: core define portas, integrações implementam — mais desenho inicial, escala por plug-in

## Decisão

O core define o domínio e as portas; tudo que toca o mundo externo é adapter registrado por entry point. O core não importa nenhum framework nem faz I/O.

## Consequências

Contribuidor cria adapter sem tocar no core; core testável sem rede; custo: camada de tradução por integração.
