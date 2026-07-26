# ADR-006 — Conexão LLM obrigatória; gate de qualidade é LLM-first

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

O Readiness Gate avalia testabilidade, ambiguidade e contradição — julgamentos semânticos. Parsing sozinho não sustenta a promessa central do produto. Ollama garante caminho de custo zero para quem não tem API key.

## Opções consideradas

1. Gate 100% determinístico — barato, mas incapaz de julgar semântica; a promessa vira teatro
2. LLM opcional com gate degradado — usuário médio ficaria no modo fraco sem perceber
3. LLM obrigatória no onboarding (API ou Ollama), determinístico como piso

## Decisão

O onboarding exige uma via de LLM funcional antes de liberar o gate. Checks determinísticos são o piso que roda sempre; a camada LLM completa o julgamento. Em falha de runtime, funções determinísticas seguem e as semânticas ficam explicitamente pendentes — nunca silenciosamente puladas.

## Consequências

Substitui a versão anterior desta decisão (fallback determinístico completo). Custo de entrada mitigado por Ollama first-class e cache.
