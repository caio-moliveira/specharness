# ADR-005 — LiteLLM sob interface própria LLMClient

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Prometemos BYOK com qualquer provedor + Ollama. Manter SDKs individuais é custo permanente; depender nu de uma lib externa no domínio é risco de acoplamento.

## Opções consideradas

1. SDKs oficiais individuais — controle total, manutenção cara
2. LiteLLM nu em todo o código — ecossistema de graça, acoplamento total
3. LiteLLM por baixo de porta própria — ecossistema de graça, troca possível

## Decisão

O core fala apenas com a porta LLMClient (complete, structured, stream); a implementação usa LiteLLM.

## Consequências

Troca de camada LLM sem tocar no domínio; dependência pesada aceita conscientemente e isolada.
