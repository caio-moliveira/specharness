---
spec: SPEC-023
title: "Captura de processo e scaffolding do harness no repo do usuário"
status: draft
type: feature
owner: caio
created: 2026-07-29
sprint: 2026-C1
tracker_refs: []
depends_on: [SPEC-022]
adrs: [ADR-021, ADR-003, ADR-004, ADR-020]
success_metrics:
  - "Após o scaffolding, um commit sem trailer Spec: falha no repo do usuário (assert do hook gerado)"
  - "Cada coding agent suportado produz o seu arquivo de instrução correspondente a partir de profiles/ (assert por agente)"
  - "Os gates da espinha fixa estão presentes em 100% das combinações de resposta (assert)"
  - "Os arquivos gerados passam no schema/hook do próprio specharness: 0 inválidos"
acceptance:
  - O init coleta parâmetros do processo - convenção de commit, onde vive o planejamento, regras de PR, testes, BDD, métricas
  - A partir dos parâmetros, gera AGENTS.md e a camada do agente selecionado a partir de profiles/
  - Gera os hooks de enforcement (trailer Spec:, validação de schema de spec) no git do usuário
  - A espinha fixa do método é sempre incluída e nunca desligável pelas respostas
  - "Os arquivos gerados declaram de onde o agente puxa o trabalho: o próximo spec ready, derivado do tracker"
---

## Contexto

Terceira spec da v1.0 (ADR-021) e o coração da proposta: transformar as respostas
do time em arquivos físicos de instrução que um coding agent segue. Reusa o
AGENTS.md como base (ADR-003) e os profiles por agente como dados (ADR-004). O
método é espinha fixa (ADR-021): as respostas preenchem parâmetros, nunca
desligam gates.

Decisões (a fechar no readiness):

- Presets + parâmetros, sem LLM no caminho crítico: perguntas objetivas
  (convenção de commit, cobertura mínima, projeto/board do planejamento, checks
  de PR, linguagem do BDD, métricas objetivas desejadas) preenchem templates.
- Saída no repo do usuário: `AGENTS.md` (base), a camada do agente selecionado
  (ex.: `CLAUDE.md` para Claude Code, de `profiles/<agente>`), hooks de
  commit-msg (trailer) e de schema de spec, e um `specs/` semente.
- A espinha fixa — readiness gate, trailer `Spec:`, BDD travando `done`, métricas
  que nunca expõem indivíduos (ADR-006/008/016) — entra sempre. Parâmetros
  ajustam limiares e convenções, não a existência dos gates.
- O fluxo do agente é declarado: implementar o próximo spec `ready`, derivado do
  WorkItem do tracker (ADR-020).

## Fora de escopo

- Rodar o coding agent (ADR-021: instrumenta, não orquestra).
- Gerar o conteúdo dos specs por LLM — o scaffolding cria a estrutura e o
  template; escrever specs é a skill escrever-spec, com humano no loop.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: scaffolding do harness a partir do processo do time

  Cenário: parâmetros do processo geram os arquivos de instrução
    Dado o init com as respostas de commit, planejamento, PR, testes, BDD e métricas
    Quando o scaffolding é executado
    Então AGENTS.md e a camada do agente selecionado são gerados a partir dos templates e profiles

  Cenário: o enforcement de commit é instalado no repo do usuário
    Dado um repositório recém-scaffolded
    Quando um commit sem trailer Spec: é tentado
    Então o hook gerado bloqueia o commit

  Cenário: a espinha fixa não é desligável
    Dado qualquer combinação de respostas no init
    Quando os arquivos são gerados
    Então readiness gate, trailer Spec:, BDD travando done e métricas anti-vigilância estão presentes

  Cenário: cada agente recebe a sua camada
    Dado um coding agent suportado selecionado no init
    Quando o scaffolding é executado
    Então o arquivo de instrução correspondente a esse agente é gerado a partir de profiles/

  Cenário: o ponto de captura do trabalho é declarado
    Dado um repositório scaffolded
    Quando os arquivos de instrução são lidos
    Então eles apontam o próximo spec ready, derivado do tracker, como a fonte do trabalho do agente
```
