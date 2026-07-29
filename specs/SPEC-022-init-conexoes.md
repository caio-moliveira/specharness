---
spec: SPEC-022
title: "specharness init: wizard de conexões (tracker, git, db, agente, LLM)"
status: draft
type: feature
owner: caio
created: 2026-07-29
sprint: 2026-C1
tracker_refs: []
depends_on: [SPEC-004, SPEC-005, SPEC-006]
adrs: [ADR-021, ADR-007, ADR-006]
success_metrics:
  - "init num repo novo produz um specharness.yaml válido e um scaffold de .env em < 2 min de interação"
  - "Re-rodar o init com as mesmas respostas é idempotente: 0 alterações no specharness.yaml (assert)"
  - "100% dos serviços selecionados geram no .env os nomes de env var corretos das suas credenciais"
  - "0 valores de segredo escritos no specharness.yaml em qualquer combinação de seleção (assert)"
acceptance:
  - O init pergunta interativamente tracker, git provider, db, coding agent e LLM
  - As seleções não-secretas são gravadas em specharness.yaml
  - Os nomes das env vars das credenciais dos serviços escolhidos são escritos no .env, nunca no yaml
  - O .env é garantido no .gitignore antes de qualquer credencial ser sugerida
  - Um modo não-interativo por flags permite rodar o init em script ou CI sem prompts
---

## Contexto

Segunda spec da v1.0 (ADR-021): o onboarding interativo. Depois de instalar, o
usuário roda `specharness init` no próprio repo e seleciona as ferramentas que
usa. O init reusa as portas/adapters existentes (db SPEC-004, llm SPEC-005, repo
SPEC-006, trackers SPEC-007/008/019) e grava a configuração — separando config
(yaml) de segredo (.env), como o resto do produto já faz.

Decisões (a fechar no readiness):

- Prompts via Typer + biblioteca de prompt. Cada serviço suportado conhece o
  nome da sua env var (ex.: JIRA_TOKEN, ANTHROPIC_API_KEY); o init escreve esses
  nomes no .env com valor em branco e instrui o usuário — nunca preenche nem lê
  o segredo.
- `specharness.yaml` recebe só o não-segredo (URLs, projeto do tracker, provider
  do LLM). Idempotente: re-rodar sem mudança não altera o arquivo.
- Antes de sugerir qualquer credencial, o init garante `.env` no `.gitignore`.
- `--non-interactive` com flags cobre CI e automação.

## Fora de escopo

- A captura do PROCESSO (commit, PR, testes, BDD, métricas) e o scaffolding dos
  arquivos do agente — isso é a SPEC-023.
- Implementar novos adapters — o init só orquestra os que já existem.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: configuração inicial interativa das conexões

  Cenário: seleção de ferramentas grava config e guia segredos
    Dado um repositório sem specharness.yaml
    Quando o usuário roda o init e seleciona tracker, git, db, agente e LLM
    Então o specharness.yaml recebe as seleções não-secretas e o .env recebe os nomes das env vars das credenciais

  Cenário: segredo nunca vai para o yaml
    Dado qualquer combinação de serviços selecionados no init
    Quando a configuração é gravada
    Então nenhum valor de credencial aparece no specharness.yaml

  Cenário: o .env é protegido antes de qualquer credencial
    Dado um repositório sem .env no .gitignore
    Quando o init começa a configurar credenciais
    Então o .env é adicionado ao .gitignore antes de qualquer nome de credencial ser sugerido

  Cenário: modo não-interativo para automação
    Dado um repositório e as seleções passadas por flags
    Quando o init roda em modo não-interativo
    Então a configuração é gravada sem nenhum prompt
```
