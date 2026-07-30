# specs/ — o Spec Registry do specharness (dogfooding)

Cada arquivo é uma spec no schema definido em SPEC-001 §7 e implementado em
`packages/core/src/specharness_core/specschema.py`. Este diretório é ao mesmo
tempo:

1. **O backlog real do projeto** — o que vamos construir, sprint a sprint
2. **O insumo de demonstração** — specs com BDD e métricas no formato que o
   produto gerencia; o seed data e os primeiros goldens de eval derivam daqui

## Ciclo de vida

`draft → approved → ready → in_progress → verifying → done → archived`

- `approved → ready` exige passar no Readiness Gate (skill `readiness-review`
  até a SPEC-010/011 automatizarem)
- `verifying → done` exige BDD verde no CI
- Commits referenciam specs via trailer `Spec: SPEC-NNN` (hook bloqueia sem)

## Step definitions (gate de BDD — SPEC-012)

Os cenários Gherkin de uma spec viram executáveis com um módulo de steps em
`specs/steps/spec_NNN_steps.py` (expõe `registry: StepRegistry`):

```
specharness verify SPEC-029 --steps specs/steps/spec_029_steps.py
```

Cenário sem step definition fica `pendente` — e pendente bloqueia `done`.

## Mapa da Fase A

| Sprint | Specs |
|---|---|
| 2026-A1 | SPEC-003 parser · SPEC-004 banco · SPEC-005 LLM |
| 2026-A2 | SPEC-006 repo GitHub · SPEC-009 linking · SPEC-010 gate determinístico |
| 2026-A3 | SPEC-007 Redmine · SPEC-008 GH Issues · SPEC-011 gate LLM · SPEC-012 verify |
| 2026-A4 | SPEC-013 métricas · SPEC-014 percepção · SPEC-015 report · SPEC-016 dashboard |
| 2026-A5 | SPEC-017 veredito/diagnóstico CLI · SPEC-018 modo demo do dashboard |
