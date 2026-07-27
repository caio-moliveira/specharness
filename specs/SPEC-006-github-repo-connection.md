---
spec: SPEC-006
title: "Conexão de repositório GitHub: commits, trailers e PRs"
status: in_progress
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A2
tracker_refs: []
depends_on: [SPEC-004]
adrs: [ADR-001, ADR-011]
success_metrics:
  - "Sync inicial de repo com 5.000 commits em < 60s"
  - "Reprocessamento idempotente: 2ª execução do sync produz 0 registros novos"
  - "Contract tests com cassettes cobrindo paginação, rate limit e auth inválida"
acceptance:
  - Usuário conecta um repo GitHub com token de escopo mínimo documentado
  - Commits são ingeridos com hash, autor, data, mensagem e trailers extraídos
  - PRs são ingeridos com estado, branch e vínculo aos commits
  - Erro de auth exibe mensagem em português com o escopo de token necessário
---

## Contexto

Terceira conexão do onboarding (SPEC-001 §5.1). Fonte dos dados que alimentam
linking (SPEC-009) e métricas (SPEC-013). Leitura de trailers usa o wrapper
sobre o git CLI (ADR-011); a API do GitHub complementa com PRs e CI status.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: conexão de repositório GitHub

  Cenário: sync inicial ingere commits com trailers
    Dado um repositório GitHub conectado com token válido
    Quando o sync inicial é executado
    Então cada commit fica disponível com hash, autor, data, mensagem e os trailers "Spec:" extraídos

  Cenário: sync ingere pull requests vinculados aos commits
    Dado um repositório conectado com token válido e pull requests abertos
    Quando o sync inicial é executado
    Então cada PR fica disponível com estado, branch e o vínculo aos seus commits

  Cenário: reprocessamento não duplica dados
    Dado um repositório já sincronizado
    Quando o sync é executado novamente sem novos commits
    Então nenhum registro novo é criado

  Cenário: token sem escopo suficiente orienta o usuário
    Dado um token sem permissão de leitura de PRs
    Quando o sync tenta ler pull requests
    Então a mensagem de erro em português informa o escopo mínimo necessário
```
