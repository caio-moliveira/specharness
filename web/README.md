# web/ — frontend do specharness (SPEC-016)

Dashboard read-only da Fase A: big picture + visão pipeline por spec. Vite + React
+ TypeScript + Tailwind + tokens shadcn (ADR-013), react-i18next (inglês base,
pt-BR selecionável), consumindo o **cliente TypeScript gerado do OpenAPI** do
backend (ADR-014, `@hey-api/openapi-ts`).

## Rodar com seed data (sem conexão externa)

```bash
just seed                 # popula o banco com um sprint representativo
just dev                  # sobe o backend em :8321 (com seed) — API + /docs
cd web && npm install && npm run dev   # sobe o web em :5173
```

O web aponta para `VITE_API_BASE_URL` (padrão `http://localhost:8321`).

## Contrato e regras

- **`openapi.json`** é o schema do backend (fonte do codegen). Regerar após mudar a
  API: `uv run python -c "import json;from specharness_server.app import app;print(json.dumps(app.openapi()))" > web/openapi.json`.
- **`src/client/` é gerado no build** (`npm run gen`) e não é versionado — o schema é
  a fonte da verdade (ADR-014).
- **Todo dado vem do cliente gerado.** O ESLint proíbe `fetch`/`axios` fora de
  `src/client` (acceptance[5]) — uma chamada à mão quebra o `npm run lint`.
- **Tema:** `src/tokens.css` (cópia de `brand/tokens.css`). Verde (`--evidence`) só
  para prova; todo número carrega chip de proveniência (ADR-017).

## Scripts

`npm run gen` (cliente do OpenAPI) · `npm run dev` · `npm run build` · `npm run lint`.
