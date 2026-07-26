# CLAUDE.md — camada Claude Code do specharness

Leia primeiro o **AGENTS.md** (base comum). Este arquivo adiciona apenas o que
é específico do Claude Code.

## Skills disponíveis (.claude/skills/)

| Skill | Quando usar |
|---|---|
| `escrever-spec` | Criar/editar specs no schema SPEC-001 §7, com BDD e métricas |
| `registrar-adr` | Registrar decisão de arquitetura em docs/adrs/ |
| `readiness-review` | Avaliar prontidão de uma spec (espelho do Readiness Gate) |
| `novo-adapter` | Scaffold de adapter (tracker/git/importer) com contract test |
| `entregar-spec` | Fechar a entrega: gates, evidência, verificador, relatório |

## Subagentes

- `verificar-spec` — verificação adversarial em contexto limpo (ADR-016).
  Acione ao final de TODA implementação, antes do relatório de entrega.

## Hooks ativos

- **PostToolUse** em `specs/*.md` → `schema_validate.py` (spec inválida não entra)
- **commit-msg** (via pre-commit) → `trailer_check.py` (commit sem `Spec:` não passa)
- **schema hook** também rejeita `status: done` fora do CI (ADR-016)

## Regras de permissão

- Escrita liberada: `packages/`, `specs/`, `evals/`, `docs/`, `web/`
- Confirmação em `packages/**/tests/**` durante implementação (ADR-016)
- Confirmação obrigatória: `profiles/` (dados canônicos), `.github/workflows/`
- Proibido: editar `uv.lock` manualmente, `git push --force`, deletar specs

## Ao terminar qualquer tarefa

Rode `just lint && just test`. Falhou → a tarefa não terminou.
