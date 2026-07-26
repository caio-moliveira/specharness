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

## Hooks ativos

- **PostToolUse** em `specs/*.md` → `schema_validate.py` (spec inválida não entra)
- **commit-msg** (via pre-commit) → `trailer_check.py` (commit sem `Spec:` não passa)

## Regras de permissão

- Escrita liberada: `packages/`, `specs/`, `evals/`, `docs/`, `web/`
- Confirmação obrigatória: `profiles/` (dados canônicos), `.github/workflows/`
- Proibido: editar `uv.lock` manualmente, `git push --force`, deletar specs

## Ao terminar qualquer tarefa

Rode `just lint && just test`. Falhou → a tarefa não terminou.
