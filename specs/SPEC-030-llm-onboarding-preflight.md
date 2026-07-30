---
spec: SPEC-030
title: "Onboarding: requisito de LLM cobrado cedo (init, preflight do up, README)"
status: done
type: feature
owner: caio
created: 2026-07-30
updated: 2026-07-30
sprint: 2026-C2
depends_on: [SPEC-005, SPEC-021, SPEC-022, SPEC-027]
adrs: [ADR-006]
success_metrics:
  - "100% dos caminhos de boot do up cobertos por teste de CLI: sem provedor LLM o aviso aparece e o boot prossegue (exit 0); com provedor o aviso não aparece — 1 teste por caminho"
  - "Mensagem de fechamento do init contém 'specharness llm test' — 1 teste de CLI"
  - "Quickstart do README contém o requisito de LLM (API key ou Ollama) — 1 teste de conteúdo"
  - "0 placeholders no quickstart do README (clone aponta o repositório real) e requisitos completos: instalação do just indicada e Node listado para o dashboard — 1 teste de conteúdo"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "O init termina orientando a validar a conexão LLM com specharness llm test antes do specharness up"
  - "O up sem nenhum provedor LLM disponível avisa no boot que o Readiness Gate fica inoperante, com a orientação unificada de provedores (SPEC-027), sem impedir o servidor de subir"
  - "O up com um provedor LLM disponível não emite o aviso"
  - "O quickstart do README declara que uma API key de LLM ou um Ollama local é obrigatório (ADR-006)"
  - "O quickstart do README é executável sem adaptação: clone do repositório real sem placeholder, instalação do just indicada e Node listado como requisito do build do dashboard"
---

## Contexto

A LLM é obrigatória no specharness (ADR-006): sem uma via funcional o
Readiness Gate não libera nenhuma spec. Hoje, porém, essa obrigação só é
cobrada no primeiro `specharness ready` — o `init` fecha sugerindo ir direto
para o `up`, o `up` sobe em silêncio sem nenhum provedor, e o README não
lista o requisito. A jornada ponta-a-ponta (2026-07-30) mostrou o custo: o
usuário só descobre a exigência no meio do fluxo, com a spec bloqueada.
O requisito não muda — muda o momento em que ele é comunicado.

## Fora de escopo

- Bloquear o boot do `up` sem provedor (o dashboard e a API funcionam sem
  LLM; obrigatoriedade é do gate, não do servidor).
- Validar a key dentro do `init` (o `.env` acabou de ser criado com valores
  vazios; a validação é do `specharness llm test`).
- Mudar o `ready`, o ADR-006 ou a mensagem unificada de provedores (SPEC-027).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: requisito de LLM cobrado no momento certo do onboarding

  Cenário: init encaminha para a validação da LLM
    Dado um repositório recém-inicializado com specharness init
    Quando o init termina
    Então a mensagem de fechamento orienta a rodar specharness llm test antes do specharness up

  Cenário: up sem provedor avisa e sobe mesmo assim
    Dado um ambiente sem nenhum provedor LLM disponível
    Quando o up roda
    Então o boot avisa que o Readiness Gate fica inoperante com a orientação unificada de provedores e o servidor sobe

  Cenário: up com provedor sobe sem aviso
    Dado um ambiente com um provedor LLM disponível
    Quando o up roda
    Então o servidor sobe e nenhum aviso de provedor LLM aparece

  Cenário: README declara o requisito no quickstart
    Dado o quickstart do README
    Quando um usuário novo segue os requisitos listados
    Então o requisito de uma API key de LLM ou Ollama local está declarado antes dos comandos de setup

  Cenário: quickstart é executável sem adaptação
    Dado o quickstart do README
    Quando um usuário novo copia os comandos de setup
    Então o clone aponta o repositório real sem placeholder, a instalação do just está indicada e o Node é listado como requisito do dashboard
```

## Notas de implementação

- `up` (`packages/cli/src/specharness_cli/main.py`): após o preflight de
  banco, `detect_providers(os.environ)` — vazio emite `⚠` com o
  `NoProviderConfigured.template` (mensagem unificada, SPEC-027) e segue o
  boot. Testes monkeypatcham `detect_providers` para não depender de rede.
- `init`: só a mensagem de fechamento muda — o passo `specharness llm test`
  entra entre "preencha o .env" e "rode specharness up".
- README: uma linha nos requisitos do quickstart; o teste de conteúdo lê o
  arquivo a partir da raiz do repo (mesmo padrão do teste de registry que lê
  specs/ do disco).
