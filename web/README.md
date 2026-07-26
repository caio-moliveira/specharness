# web/ — frontend do specharness

O scaffold (Vite + React + TS + Tailwind + shadcn/ui + cliente OpenAPI gerado)
entra no passo 6 da ordem de implantação (SPEC-002 §8), junto com a SPEC-016.
Decisões já tomadas: ADR-013 (Tailwind + shadcn) e ADR-014 (codegen OpenAPI).

Até lá, o server expõe /health e o OpenAPI em /docs (rode `just dev`).
