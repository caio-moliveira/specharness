# ADR-014 — Cliente TypeScript gerado do OpenAPI (hey-api)

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

O contrato server↔web precisa quebrar em build, não em runtime; escrever cliente à mão descola do backend.

## Opções consideradas

1. Cliente manual — descola silenciosamente
2. tRPC — type-safe mas acopla front e back em runtime compartilhado
3. Codegen do OpenAPI do FastAPI — contrato explícito e versionável

## Decisão

@hey-api/openapi-ts gera o cliente no build; o schema OpenAPI é artefato de CI e o lint proíbe fetch fora do cliente gerado.

## Consequências

Mudança de contrato quebra o build do web imediatamente; OpenAPI vira documentação viva da API.
