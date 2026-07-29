---
spec: SPEC-024
title: "Dashboard live do Tech Lead sobre o repo do usuário"
status: in_progress
type: feature
owner: caio
created: 2026-07-29
updated: 2026-07-29
sprint: 2026-C1
tracker_refs: []
depends_on: [SPEC-016, SPEC-018]
adrs: [ADR-021, ADR-008, ADR-019]
success_metrics:
  - "Apontado para um repo com dados reais, a big picture reflete o specs_by_status e as métricas do banco do usuário (teste E2E)"
  - "data_source=live por padrão em specharness up; demo só com flag explícito"
  - "0 endpoints do dashboard expõem dado em nível de indivíduo (assert)"
acceptance:
  - specharness up serve o dashboard em modo live sobre o banco configurado do usuário
  - A big picture mostra o funil de specs, o que está em desenvolvimento e as métricas do sprint do usuário
  - Cada número exibe seu chip de proveniência (registry, git, snapshot, survey)
  - Nenhuma métrica ou endpoint expõe indivíduos
  - O modo demo continua disponível, mas atrás de flag explícito e rotulado
---

## Contexto

Quarta spec da v1.0 (ADR-021): a janela do Tech Lead. Reusa o dashboard read-only
da Fase A (SPEC-016) e o modo demo honesto (SPEC-018), agora apontado para os
DADOS REAIS do projeto do usuário — o funil de specs, o que está em
desenvolvimento, os gates e as métricas — sobre o banco que ele configurou no
init.

Decisões (a fechar no readiness):

- `specharness up` serve `data_source=live` por padrão; o seed/demo fica atrás de
  flag explícito e rotulado (ADR-019), para nunca confundir dado semente com dado
  real.
- A anti-vigilância é preservada (ADR-008): agregados de processo/spec/agente,
  nunca o indivíduo. Cada número mantém o chip de proveniência (ADR-017).
- Boa parte do contrato (`data_source=live` default, demo com flag, agregados,
  proveniência) já vem da SPEC-021 (`up`) reusando SPEC-016/018. A SPEC-024 TRAVA
  esse contrato com testes e garante o **dia-um**: o dashboard do TL funciona com
  banco vazio e só a spec-semente do `init`, sem crash — o usuário vê o funil já
  no primeiro `specharness up`, antes de ingerir qualquer métrica.

## Fora de escopo

- Novas visualizações além do funil + métricas + higiene já existentes — a v1.0
  reaponta o dashboard atual; visões novas são backlog posterior.
- Escrita ou edição de specs pela UI — o dashboard é read-only.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: dashboard live do Tech Lead

  Cenário: big picture reflete o projeto real do usuário
    Dado um repositório com specs e métricas reais no banco configurado
    Quando o Tech Lead abre o dashboard servido por specharness up
    Então a big picture mostra o funil de specs e as métricas do sprint a partir do banco do usuário

  Cenário: live por padrão, demo só com flag
    Dado o specharness up sem flag de demo
    Quando o dashboard é servido
    Então o data_source é live e usa o banco do usuário

  Cenário: proveniência em cada número
    Dado a big picture carregada com dados reais
    Quando o Tech Lead inspeciona qualquer métrica
    Então o número exibe o chip de proveniência da sua origem

  Cenário: nenhum dado de indivíduo é exposto
    Dado o dashboard live carregado
    Quando qualquer endpoint do dashboard é consultado
    Então nenhuma resposta contém métrica em nível de indivíduo

  Cenário: dia-um do usuário, com banco vazio
    Dado um repositório recém-inicializado, com banco vazio e só a spec-semente
    Quando o Tech Lead abre o dashboard live
    Então o funil mostra a spec-semente e as métricas ficam vazias, sem erro
```
