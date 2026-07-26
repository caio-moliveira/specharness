# web/ — frontend do specharness

O scaffold (Vite + React + TS + Tailwind + shadcn/ui + cliente OpenAPI gerado)
entra no passo 6 da ordem de implantação (SPEC-002 §8), junto com a SPEC-016.
Decisões já tomadas: ADR-013 (Tailwind + shadcn) e ADR-014 (codegen OpenAPI).

O tema nasce pronto: importar `brand/tokens.css` (shadcn-compatible) e seguir
as regras de `brand/README.md` (verde só para evidência; números com chip de
proveniência — ADR-017).

Até lá, o server expõe /health e o OpenAPI em /docs (rode `just dev`).
