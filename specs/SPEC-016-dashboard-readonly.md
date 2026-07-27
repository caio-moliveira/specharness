---
spec: SPEC-016
title: "Dashboard web read-only: big picture e visão pipeline por spec"
status: in_progress
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-013]
adrs: [ADR-013, ADR-014]
success_metrics:
  - "Primeiro carregamento com seed data em < 2s (p95 local)"
  - "Time-to-first-value do critério da Fase A: conexões -> dashboard real em < 15 min"
  - "0 chamadas fora do cliente TypeScript gerado do OpenAPI (verificado por lint)"
acceptance:
  - Visão big picture mostra fase do projeto, specs por status, métricas da sprint corrente e alertas de higiene (órfãos)
  - Visão pipeline por spec mostra a linha do tempo readiness -> commits -> BDD -> review -> percepção
  - Com seed data carregado, todas as visões funcionam sem nenhuma conexão externa
  - Interface base em inglês com pt-BR selecionável (react-i18next)
  - Todo dado exibido vem do cliente gerado do OpenAPI (ADR-014)
---

## Contexto

A primeira entrega visível do web app (SPEC-001 §5): read-only na Fase A,
wizards chegam na Fase B. O seed data é essencial — contribuidor de frontend
trabalha sem conectar nada.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: dashboard read-only

  Cenário: big picture com seed data
    Dado o ambiente local com seed data carregado
    Quando o usuário abre o dashboard
    Então a big picture mostra specs por status e as métricas da sprint corrente

  Cenário: pipeline conta a história da spec
    Dado uma spec done com commits, execuções BDD e amostra de percepção
    Quando o usuário abre a visão pipeline da spec
    Então a linha do tempo exibe readiness, commits, BDD, review e percepção em ordem

  Cenário: alerta de higiene aparece na big picture
    Dado uma sprint com commits órfãos acima de zero
    Quando o usuário abre o dashboard
    Então o alerta de higiene indica a contagem de órfãos com link para a lista

  Cenário: troca de idioma
    Dado o dashboard aberto em inglês
    Quando o usuário seleciona pt-BR
    Então os textos da interface são exibidos em português

  Cenário: dado vem só do cliente gerado do OpenAPI
    Dado o web app consumindo a API do specharness
    Quando uma visão carrega qualquer dado
    Então a chamada usa exclusivamente o cliente TypeScript gerado do OpenAPI e o lint proíbe fetch fora dele
```

## Notas de implementação

Escopo fechado no readiness (2026-07-27): **backend rigorosamente testado + frontend
real (sem CI de JS)**. O repo não tem toolchain nem CI de frontend; a verificação
automatizada (pytest, subagente) cobre o backend, e o frontend é verificado por build.

- **Backend (`packages/server`, FastAPI).** Endpoints que servem a big picture (fase,
  specs por status, métricas da sprint corrente da SPEC-013, alertas de higiene/órfãos
  da SPEC-009) e a pipeline por spec (readiness → commits → BDD → review → percepção).
  Os modelos Pydantic são o contrato OpenAPI (ADR-014). Testado via FastAPI TestClient.
- **Seed data.** Um seed popula o banco com dados representativos (specs, snapshot de
  métricas, percepção, commits) para que todas as visões funcionem sem nenhuma conexão
  externa (git/tracker/LLM). É o que o contribuidor de frontend usa.
- **Frontend (`web/`).** Vite + React + TS + Tailwind + shadcn/ui (ADR-013), react-i18next
  (inglês base + pt-BR), consumindo o cliente TypeScript gerado do OpenAPI com
  @hey-api/openapi-ts (ADR-014). Números exibidos com chip de proveniência (ADR-017);
  verde reservado para evidência (brand/README). Verificado por build de produção.
- **Fronteira.** O server é camada de entrega (como a CLI): compõe core + stores, não
  contém regra de domínio nova. Todo dado do web vem do cliente gerado — o lint do
  frontend proíbe `fetch`/`axios` fora dele (acceptance[5]).
