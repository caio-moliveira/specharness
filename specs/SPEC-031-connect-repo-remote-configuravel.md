---
spec: SPEC-031
title: "connect repo: remote e repositório configuráveis"
status: done
type: feature
owner: caio
created: 2026-07-30
updated: 2026-07-30
sprint: 2026-C2
depends_on: [SPEC-006]
adrs: [ADR-011]
success_metrics:
  - "100% das novas opções cobertas por teste de CLI: --remote usa o remote nomeado e --repo dispensa o parsing — 1 teste por opção"
  - "Mensagem de URL irreconhecível cita as duas saídas (--remote e --repo) — 1 teste"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "connect repo --remote <nome> resolve o repositório a partir do remote nomeado em vez de origin"
  - "connect repo --repo <owner/nome> usa o repositório informado sem parsear URL de remote"
  - "Quando a URL do remote não é reconhecida, o erro orienta a usar --remote ou --repo"
  - "Sem opções, o comportamento atual (origin) permanece inalterado"
---

## Contexto

A validação de M1 (2026-07-30) travou na primeira etapa da ingestão: o
`connect repo` parseia exclusivamente a URL do remote `origin` e só reconhece
formas github.com — um remote atrás de proxy corporativo, um alias SSH ou um
GitHub Enterprise quebram o onboarding com um erro sem saída. O repositório é
conhecido pelo usuário; falta um caminho para informá-lo.

## Fora de escopo

- Suportar API de GitHub Enterprise (base URL da API continua github.com).
- Autodetecção de múltiplos remotes ou fallback silencioso (explícito > mágico).
- Mudar o formato de ingestão ou o GitHubClient.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: origem do repositório configurável no connect repo

  Cenário: remote nomeado substitui o origin
    Dado um repositório git cujo remote upstream aponta para o GitHub
    Quando o connect repo roda com --remote upstream
    Então o repositório é resolvido a partir do remote upstream

  Cenário: par owner/nome dispensa o parsing de URL
    Dado um repositório git cujo remote origin tem URL irreconhecível
    Quando o connect repo roda com --repo indicando owner e nome
    Então a ingestão usa o repositório informado sem consultar a URL do remote

  Cenário: erro de URL irreconhecível aponta a saída
    Dado um repositório git cujo remote origin tem URL irreconhecível
    Quando o connect repo roda sem opções
    Então o erro menciona as opções --remote e --repo como alternativas

  Cenário: sem opções o origin continua sendo o default
    Dado um repositório git com remote origin apontando para o GitHub
    Quando o connect repo roda sem opções
    Então o repositório é resolvido a partir do origin
```

## Notas de implementação

- Só CLI (`connect_repo` em `packages/cli/src/specharness_cli/main.py`):
  `--remote` vai direto para `LocalGitCommitReader.remote_ref(remote)` (a
  assinatura já aceita o nome); `--repo owner/nome` constrói o `RepoRef` sem
  chamar `remote_ref`. Validação do formato `owner/nome` na borda da CLI.
- A orientação de erro embrulha a `InvalidRepositoryConfig` existente do core
  (`parse_github_remote` não muda — ADR-001).
