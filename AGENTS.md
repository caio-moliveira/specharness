# specharness — Guia para Agentes de Código

specharness é a camada open source de decisão, qualidade e métricas para
Spec-Driven Development com agentes de código. Este repositório é desenvolvido
com a própria metodologia que o produto implementa (dogfooding): **toda mudança
pertence a uma spec, todo commit carrega o trailer `Spec:`, toda spec `done`
tem BDD verde.**

## Documentos que definem o projeto

- `specs/SPEC-001-founding-document.md` — o que é o produto, ADRs 001–008
- `specs/SPEC-002-dev-stack.md` — stack, ferramentas, ADRs 009–015
- `specs/SPEC-003+` — o backlog: cada feature é uma spec com BDD e métricas
- `docs/adrs/` — registro completo de decisões. **Nunca contrarie um ADR sem
  registrar um novo que o substitua.**

## Comandos (use SEMPRE o justfile — nunca invocações cruas)

```
just setup          # uv sync + pre-commit install
just test           # suíte completa
just test-core      # rápido, só o core
just lint           # ruff + format check
just fix            # aplica fixes
just specs-validate # valida schema de todas as specs
just dev            # server local na porta 8321
```

## Convenções de commit

- Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)
- **Trailer obrigatório** no último bloco da mensagem: `Spec: SPEC-NNN`
  (o hook de commit-msg bloqueia sem isso; a spec deve existir e não estar
  `archived`)
- Branch: `spec/SPEC-NNN-descricao-curta`

## Fronteiras de arquitetura (invioláveis — ADR-001)

1. `packages/core` é domínio puro: **zero I/O, zero imports de framework**
   (nada de FastAPI, SQLAlchemy, httpx, typer dentro do core).
2. Adapters implementam portas definidas no core; nunca o contrário.
3. `server` e `cli` orquestram; regras de negócio vivem no core.
4. `profiles/` são DADOS canônicos do produto — mudanças exigem fonte oficial
   citada (URL + data) e confirmação humana.
5. Locks (`uv.lock`) só mudam via `uv add/remove/sync` — nunca edição manual.

## Fluxo de trabalho por spec

1. Leia a spec em `specs/` antes de qualquer código. Se não existe, crie-a
   primeiro (skill `escrever-spec`).
2. Implemente com testes: pytest no core (cobertura ≥85%), contract tests em
   adapters, cenários da spec como referência de comportamento.
3. Rode `just lint && just test` antes de encerrar a tarefa.
4. Commit com trailer. Atualize o `status` da spec quando aplicável
   (`in_progress` → `verifying` quando os testes cobrem os cenários).

## Qualidade

- pyright `strict` em `core/` e `metrics/` — sem `# type: ignore` sem
  justificativa em comentário
- Docstrings em módulos públicos explicam o *porquê*, referenciando a spec/ADR
- Mensagens de erro voltadas ao usuário em português; código e identificadores
  em inglês
