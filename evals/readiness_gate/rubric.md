# Rubric — Readiness Gate (SPEC-011)

O juiz avalia specs em quatro dimensões, devolvendo score 0–100 e issues:

1. **Testabilidade** — cada `Então` é verificável por máquina ou inspeção objetiva?
2. **Ambiguidade** — duas pessoas implementariam a mesma coisa lendo a spec?
3. **Contradição** — conflita com specs/ADRs referenciados no contexto?
4. **Completude** — caminho triste coberto (erros, vazios, limites)?

Faixas: <70 não-ready · 70–89 ready com ressalvas · ≥90 ready.
Cada golden define a faixa esperada, não o valor exato (variância entre modelos).
