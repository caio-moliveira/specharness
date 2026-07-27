---
spec: SPEC-013
title: "Métricas objetivas da camada 2: first-run, cycle time, churn e turnover 30/90d"
status: ready
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-009, SPEC-012]
adrs: [ADR-008, ADR-016]
success_metrics:
  - "Snapshots imutáveis: recálculo a partir dos eventos reproduz 100% dos valores (determinismo verificado em teste)"
  - "Turnover 30/90d calculado por spec com atribuição de linhas via blame na janela"
  - "Dashboard consome qualquer métrica da camada 2 com uma única query por sprint"
acceptance:
  - first-run BDD pass rate, iterações até verde e cycle time ready->done calculados por spec a partir de scenario_runs e do histórico de status no git
  - Turnover mede linhas de commits da spec revertidas ou reescritas em 30/90 dias, com razão sobre o churn médio do repositório na mesma janela
  - Snapshots são append-only; correções de cálculo geram nova série, nunca sobrescrevem
  - Nenhuma métrica é exposta por indivíduo; agregação mínima é spec/sprint/time
  - Toda métrica de volume só é exibida pareada com uma de qualidade
  - Métricas são calculadas exclusivamente de artefatos brutos (git, CI, tracker); números auto-relatados por agentes nunca entram no cálculo (ADR-016)
  - Sinais de test-tampering - asserts removidos, skips sem justificativa, tolerâncias afrouxadas em PR de implementação - integram o relatório de higiene da sprint
  - Spec da sprint sem commits vinculados degrada com métricas de volume em zero e turnover indisponível, nunca com erro
---

## Contexto

A colheita automática da camada 2 (SPEC-001 §9), incluindo o requisito
diferenciador: observar o código DEPOIS do merge para medir sobrevivência.
ADR-008 (anti-vigilância) e ADR-016 (quem implementa não arbitra) são
invariantes estruturais aqui, não guidelines.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: métricas objetivas por spec

  Cenário: cycle time medido de ready a done
    Dado uma spec cujo frontmatter transicionou de ready até done no histórico do git
    Quando o snapshot da sprint é calculado
    Então o cycle time da spec reflete o intervalo entre o commit de ready e o de done

  Cenário: first-run e iterações até verde derivam dos runs registrados
    Dado uma spec com uma sequência de scenario_runs no CI até todos ficarem verdes
    Quando o snapshot da sprint é calculado
    Então a spec registra o first-run pass rate e o número de iterações até o primeiro verde

  Cenário: turnover captura reescrita pós-merge sobre o baseline
    Dado commits de uma spec cujas linhas foram reescritas em proporção acima do churn médio do repo em 20 dias
    Quando o cálculo de turnover 30d executa
    Então a taxa da spec reflete a proporção reescrita e a razão sobre o churn médio do repo na janela

  Cenário: recálculo é determinístico
    Dado o conjunto de eventos brutos de uma sprint encerrada
    Quando as métricas são recalculadas do zero
    Então todos os valores coincidem com os snapshots originais

  Cenário: correção de cálculo gera nova série sem sobrescrever
    Dado um snapshot de sprint já persistido e uma correção na fórmula de cálculo
    Quando o recálculo corrigido é persistido
    Então uma nova série é acrescentada e o snapshot original permanece intacto

  Cenário: volume só aparece pareado com qualidade
    Dado um snapshot com uma métrica de volume sem uma métrica de qualidade correspondente
    Quando a camada de exibição monta a resposta
    Então a métrica de volume é omitida por falta do par de qualidade

  Cenário: sinal de test-tampering entra na higiene
    Dado um PR de implementação que remove asserts de testes existentes sem justificativa
    Quando o cálculo de higiene da sprint executa
    Então o relatório de higiene registra o sinal de tampering vinculado à spec do PR

  Cenário: auto-relato de agente não entra no cálculo
    Dado um relatório de entrega de agente alegando cobertura de 96 por cento
    Quando o snapshot de métricas da sprint é calculado
    Então o valor registrado deriva do artefato de cobertura do CI e o auto-relato é ignorado

  Cenário: agregação nunca expõe indivíduo
    Dado uma consulta de métricas filtrada por autor específico
    Quando a API processa a consulta
    Então a consulta é rejeitada com referência à política anti-vigilância

  Cenário: spec sem commits não quebra o cálculo
    Dado uma spec da sprint sem nenhum commit vinculado
    Quando o snapshot da sprint é calculado
    Então as métricas de volume da spec ficam em zero e o turnover é reportado como indisponível
```

## Notas de implementação

Escopo fechado no readiness (2026-07-27). Decisões:

- **Fontes brutas (acceptance[6], invariante ADR-016).** cycle time ready→done vem
  do histórico de `status:` no frontmatter da spec no git (cada transição é um
  commit com timestamp); first-run pass rate e iterações-até-verde vêm de
  `scenario_runs` (SPEC-012); turnover vem de `git blame`/log na janela; volume/
  churn vêm de `commits`. Nenhum número auto-relatado por agente entra.
- **"Ciclos de review" foi removido de acceptance[0]** e deferido: não ingerimos
  eventos de review (a tabela `pull_requests` guarda só `state`). Uma spec futura
  que ingira reviews do tracker/GitHub reabre essa métrica.
- **Baseline do turnover (acceptance[1]) = churn médio do repositório na mesma
  janela.** A razão da spec = turnover_da_spec / churn_médio_do_repo_na_janela,
  ambos calculados por `git` de forma determinística.
- **Núcleo puro vs. adapter (ADR-001).** O cálculo das métricas e o veredito de
  pareamento volume↔qualidade (acceptance[5]) são core puro sobre eventos já
  materializados; a coleta dos artefatos brutos (git blame/log, leitura de
  snapshots) é adapter. Snapshots são append-only (acceptance[2]); correção de
  fórmula gera nova série, nunca sobrescreve.
