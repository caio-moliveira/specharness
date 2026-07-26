---
name: registrar-adr
description: Registra uma Architecture Decision Record em docs/adrs/ no formato do projeto e atualiza o índice. Use quando uma decisão técnica ou de produto relevante for tomada — escolha de lib, mudança de contrato, novo padrão — ou quando o usuário pedir para registrar/documentar uma decisão.
---

# registrar-adr

## Processo

1. Próximo número: `ls docs/adrs/ | sort` (formato `ADR-NNN-slug.md`).
2. Template obrigatório:

```markdown
# ADR-NNN — Título da decisão

- **Status:** proposta | aceita | substituída por ADR-MMM
- **Data:** YYYY-MM-DD
- **Specs relacionadas:** SPEC-...

## Contexto
O problema/força que exige decisão. 3–8 linhas.

## Opções consideradas
1. **Opção A** — prós / contras
2. **Opção B** — prós / contras
(≥2 opções SEMPRE. Decisão sem alternativa considerada é preferência, não decisão.)

## Decisão
O que foi decidido, em uma frase direta. Depois o porquê.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que passa a ser proibido.
```

3. Atualize a tabela-índice em `docs/adrs/README.md`.
4. Se a decisão contraria ADR anterior: marque o antigo como
   `substituída por ADR-NNN` — nunca edite o conteúdo histórico.
5. Referencie o ADR no frontmatter (`adrs:`) das specs afetadas.
