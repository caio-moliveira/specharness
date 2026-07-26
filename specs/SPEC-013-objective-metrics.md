---
spec: SPEC-013
title: "Métricas objetivas da camada 2: first-run, cycle time, churn e turnover 30/90d"
status: approved
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-009, SPEC-012]
adrs: [ADR-008]
success_metrics:
  - "Snapshots imutáveis: recálculo a partir dos eventos reproduz 100% dos valores (determinismo verificado em teste)"
  - "Turnover 30/90d calculado por spec com atribuição de linhas via blame na janela"
  - "Dashboard consome qualquer métrica da camada 2 com uma única query por sprint"
acceptance:
  - first-run BDD pass rate, iterações até verde, ciclos de review e cycle time ready->done calculados por spec
  - Turnover mede linhas de commits da spec revertidas ou reescritas em 30/90 dias, com razão sobre baseline do repo
  - Snapshots são append-only; correções de cálculo geram nova série, nunca sobrescrevem
  - Nenhuma métrica é exposta por indivíduo; agregação mínima é spec/sprint/time
  - Toda métrica de volume só é exibida pareada com uma de qualidade
---

## Contexto

A colheita automática da camada 2 (SPEC-001 §9), incluindo o requisito
diferenciador: observar o código DEPOIS do merge para medir sobrevivência.
ADR-008 (anti-vigilância) é invariante estrutural aqui, não guideline.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: métricas objetivas por spec

  Cenário: cycle time medido de ready a done
    Dado uma spec que transicionou de ready até done com timestamps registrados
    Quando o snapshot da sprint é calculado
    Então o cycle time da spec reflete o intervalo entre as duas transições

  Cenário: turnover captura reescrita pós-merge
    Dado commits de uma spec cujas linhas foram majoritariamente reescritas em 20 dias
    Quando o cálculo de turnover 30d executa
    Então a taxa da spec reflete a proporção reescrita e a razão sobre o baseline do repo

  Cenário: recálculo é determinístico
    Dado o conjunto de eventos brutos de uma sprint encerrada
    Quando as métricas são recalculadas do zero
    Então todos os valores coincidem com os snapshots originais

  Cenário: agregação nunca expõe indivíduo
    Dado uma consulta de métricas filtrada por autor específico
    Quando a API processa a consulta
    Então a consulta é rejeitada com referência à política anti-vigilância
```
