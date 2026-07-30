---
spec: SPEC-012
title: "verify: cenários BDD como gate de done no CI"
status: done
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A3
tracker_refs: []
depends_on: [SPEC-003, SPEC-009]
adrs: [ADR-016, ADR-018]
success_metrics:
  - "First-run BDD pass registrado por spec em 100% das execuções (a métrica-mãe da camada 2)"
  - "Overhead do verify no CI < 30s além do tempo dos próprios testes"
  - "0 specs done sem execução BDD verde registrada (invariante verificada por query)"
acceptance:
  - specharness verify localiza os cenários da spec e executa contra a suite do repositório do usuário
  - Resultado por cenário (passou/falhou/pendente) é registrado como ScenarioRun com marcação de first-run
  - Transição verifying -> done é bloqueada se qualquer cenário da spec falhar
  - Cenário sem step definition é reportado como pendente, distinto de falha
  - Saída em modo CI usa exit code e resumo legível por máquina
  - A transição verifying para done é executada exclusivamente pelo pipeline de CI; edição direta de status para done é rejeitada (ADR-016)
  - first-run é registrado apenas a partir do primeiro run no CI após ready; execuções locais do verify são informativas e nunca geram first-run
---

## Contexto

Fecha o contrato: spec só é done com comportamento comprovado (SPEC-001 §7.2).
A primeira execução **no CI** após ready é marcada first-run — o sinal mais
limpo da qualidade do par spec+agente (§9 camada 2). O CI é o único árbitro:
quem implementa não arbitra (ADR-016).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: BDD como gate de conclusão

  Cenário: todos os cenários verdes liberam done
    Dado uma spec em verifying cujos cenários passam na suite do repositório
    Quando o verify executa no CI
    Então a transição para done é liberada e o ScenarioRun registra o resultado

  Cenário: cenário vermelho bloqueia done
    Dado uma spec em verifying com um cenário falhando
    Quando o verify executa no CI
    Então a transição para done é bloqueada e a falha aponta o cenário

  Cenário: primeira execução é marcada como first-run
    Dado uma spec que acabou de sair de ready para in_progress
    Quando o verify executa pela primeira vez após a implementação
    Então o resultado é registrado com a marcação de first-run

  Cenário: done fora do CI é rejeitado
    Dado uma spec em verifying com o status editado localmente para done
    Quando a validação de schema processa a mudança fora do CI
    Então a transição é rejeitada com referência ao ADR-016

  Cenário: execução local não conta como first-run
    Dado uma spec cujos cenários foram executados localmente antes de qualquer run no CI
    Quando o primeiro run no CI acontece após ready
    Então apenas o run do CI é registrado com a marcação de first-run

  Cenário: step ausente é pendência, não falha
    Dado uma spec com cenário sem step definition correspondente
    Quando o verify executa
    Então o cenário é reportado como pendente com orientação de implementação

  Cenário: modo CI emite exit code e resumo legível por máquina
    Dado uma execução do verify em modo CI
    Quando o verify termina
    Então a saída é um resumo JSON legível por máquina e o exit code reflete o veredito
```

## Notas de implementação

O runner de BDD é interno e mínimo (ADR-018, emenda o ADR-012): um step registry
sobre o parser puro de Gherkin — step sem definição → pendente (distinto de
falha), step que levanta → falhou, todos passam → passou. O *veredito* (todos
verdes libera done) é core puro; o *runner* (importa/executa step definitions do
repo) é adapter. A rejeição de `done` fora do CI (A6) é do hook de schema, que
delega à decisão pura `done_edit_allowed` do core. Execuções locais são
informativas (não persistem); só o primeiro run no CI marca first-run.
