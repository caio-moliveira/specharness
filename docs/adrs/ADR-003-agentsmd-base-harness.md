# ADR-003 — AGENTS.md como base do harness + camada por runtime

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Cada runtime de agente tem seu formato de instrução. Manter N arquivos divergentes é o problema que o AGENTS.md — padrão aberto mantido sob a Linux Foundation, adotado por dezenas de ferramentas — resolve.

## Opções consideradas

1. Um arquivo proprietário por runtime — divergência garantida
2. AGENTS.md como base comum + camadas específicas por runtime nos profiles

## Decisão

O harness gerado sempre produz AGENTS.md como base universal; a camada específica (skills/hooks do Claude Code, hierarquia do Codex, formato do Kimi) vem do profile do runtime.

## Consequências

Harness portável entre runtimes; conteúdo vendor-specific isolado e atualizável como dados.
