---
spec: SPEC-027
title: "Defaults de LLM unificados e Azure conectável de fábrica"
status: verifying
type: feature
owner: caio
created: 2026-07-29
updated: 2026-07-29
sprint: 2026-C2
tracker_refs: []
depends_on: [SPEC-005, SPEC-022]
adrs: [ADR-005, ADR-006]
success_metrics:
  - "1 única fonte de verdade para o modelo default por provedor: onboarding e runtime resolvem o mesmo valor (teste de igualdade)"
  - "Provedor azure selecionado no init gera no .env a variável de api_version, hoje ausente em 100% dos casos (teste)"
acceptance:
  - O modelo default de cada provedor é idêntico entre o que o init grava e o que o runtime resolve
  - Selecionar azure no init provisiona no .env a variável de api_version que o litellm exige para conectar
  - A chamada ao litellm para azure repassa a api_version resolvida do ambiente
---

## Contexto

Dois defaults do MESMO provedor divergem: `onboarding.DEFAULT_MODEL` grava
`gpt-4o` (openai/azure) enquanto `ports/llm.DEFAULT_MODELS` resolve `gpt-4o-mini`
— o yaml gerado e o runtime discordam. Pior, o provedor azure quebra de fábrica:
o litellm exige `api_version` no roteamento azure, mas o `init` só provisiona
`AZURE_OPENAI_API_KEY` e `AZURE_OPENAI_ENDPOINT`, e o cliente nunca passa
`api_version` — não há via para o usuário azure conectar pelo caminho documentado.

## Fora de escopo

- Mudar os provedores anthropic/openai/ollama, cujos defaults já coincidem e
  conectam; a unificação apenas passa a lê-los de uma fonte só.
- Escolher o nome do deployment azure pelo usuário: o default segue ajustável no
  yaml (comentado); aqui garante-se apenas a via de api_version.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: defaults de LLM unificados e azure conectável

  Cenário: default do provedor idêntico entre init e runtime
    Dado um provedor suportado escolhido no init
    Quando o modelo default é lido no onboarding e resolvido no runtime
    Então os dois valores do default são idênticos, vindos de uma fonte única

  Cenário: azure provisiona a variável de api_version no .env
    Dado um init com provedor azure
    Quando o .env é gerado com as variáveis exigidas
    Então a variável de api_version do azure consta entre as variáveis a preencher

  Cenário: chamada azure repassa a api_version do ambiente
    Dado um alvo azure com api_version definida no ambiente
    Quando o cliente faz a chamada ao litellm
    Então a api_version resolvida do ambiente é repassada na chamada
```
