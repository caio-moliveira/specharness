---
spec: SPEC-002
title: "specharness — Stack de Desenvolvimento & Ambiente de Engenharia"
version: 1.0
status: draft
type: architecture
owner: caio
created: 2026-07-25
sprint: null
tracker_refs: []
depends_on: [SPEC-001]
adrs: [ADR-009, ADR-010, ADR-011, ADR-012, ADR-013, ADR-014, ADR-015]
success_metrics:
  - "Contribuidor: clone → testes verdes em < 10 min (medido em máquina limpa)"
  - "Pipeline de PR completo em < 5 min"
  - "Zero configuração manual além de .env para subir o ambiente local"
acceptance:
  - Toda escolha de tecnologia tem justificativa e alternativa considerada
  - O harness de desenvolvimento (Claude Code) está especificado como parte da stack
  - Um dev sênior consegue montar o ambiente lendo apenas este documento
---

# SPEC-002 — Stack de Desenvolvimento & Ambiente de Engenharia

> A stack que constrói o specharness — incluindo o harness de agente com que o
> specharness constrói a si mesmo.

---

## 0. Princípios de Escolha

1. **Boring technology no core, moderno nas bordas.** O domínio roda sobre
   ferramentas estáveis e amplamente conhecidas; experimentação só onde o
   custo de troca é baixo.
2. **Uma ferramenta por função.** Sem duplicidade (ex.: Ruff faz lint E
   format; justfile é o único task runner).
3. **Tudo versionado no repo.** Configs de lint, hooks, harness, evals,
   golden datasets — contribuidor não instala opinião, clona.
4. **A stack demonstra a tese.** Se pregamos spec-driven + eval-driven com
   harness bem feito, nosso repositório é a prova viva.

---

## 1. Stack Python (core, server, cli, adapters, metrics)

### 1.1 Runtime e gestão

| Item | Escolha | Justificativa |
|---|---|---|
| Python | **3.12** (target) · suporte 3.11–3.13 (matrix CI) | 3.12 equilibra performance e adoção; 3.11 mantém compatibilidade com ambientes corporativos conservadores |
| Gerenciador | **uv** com **workspaces** | Instalação instantânea, lockfile único do monorepo, `uv sync` resolve todos os packages de uma vez (ADR-009) |
| Versão pinada | `.python-version` na raiz | uv respeita automaticamente |

### 1.2 Bibliotecas por responsabilidade

| Responsabilidade | Lib | Notas |
|---|---|---|
| CLI | **Typer** + **Rich** | Typer para comandos tipados; Rich para output do dashboard em terminal, tabelas de métricas e progresso |
| API | **FastAPI** + **uvicorn** | OpenAPI de graça alimenta o codegen do frontend (§2.4) |
| Config | **pydantic-settings** | `specharness.yaml` + env vars com precedência clara; secrets só por env |
| ORM | **SQLAlchemy 2** (estilo 2.0, type-annotated) | Async no server (aiosqlite/asyncpg), sync no CLI — mesmos models (ADR-010) |
| Migrações | **Alembic** | Desde o commit 1; autogenerate revisado à mão |
| Validação/domínio | **Pydantic v2** | Schemas de spec, structured outputs de LLM, contratos de adapter |
| LLM | **LiteLLM** sob porta própria `LLMClient` | ADR-005 (SPEC-001); retry com **tenacity**; structured output validado por Pydantic |
| Git | **wrapper fino sobre o `git` CLI** (subprocess) | `git interpret-trailers`, `git log --format` — zero dependência nativa (libgit2), comportamento idêntico ao do usuário (ADR-011) |
| Parser Gherkin | **gherkin-official** | Parser mantido pelo projeto Cucumber; AST estável para o Readiness Gate e o lint de BDD |
| BDD (nosso gate) | **pytest-bdd** | Integra na suíte pytest existente — um runner só (ADR-012) |
| HTTP (adapters) | **httpx** | Async + sync com a mesma API; base dos adapters de tracker |
| Agendamento (daemon `track`) | **APScheduler** | Polling configurável; alternativa GitHub Action usa os mesmos jobs |
| Logs | **structlog** | JSON estruturado; correlação por spec_id/sprint_id em todos os eventos |
| Observabilidade opcional | **OpenTelemetry** + hook **Langfuse** | Off por default (SPEC-001 §11) |

### 1.3 Qualidade e testes

| Item | Escolha | Configuração |
|---|---|---|
| Lint + format | **Ruff** | Regras: E, F, I, UP, B, SIM, PL (subset); format substitui Black |
| Type check | **pyright** | `strict` em `core/` e `metrics/`; `basic` em adapters (APIs externas sujas) |
| Testes | **pytest** + pytest-asyncio + pytest-cov | Cobertura ≥85% no core (gate de CI) |
| Mock HTTP | **respx** | Unit tests dos adapters |
| Contract tests | **pytest-recording** (VCR) | Cassettes gravadas contra APIs reais de Redmine/Jira/GitHub; re-gravação documentada por adapter |
| Property-based | **Hypothesis** | No parser de spec e no linker de trailers — os dois pontos onde input adversarial é garantido |
| Hooks | **pre-commit** | ruff, pyright (changed files), conventional-commit lint, trailer check (§4.3) |

---

## 2. Stack Frontend (web)

### 2.1 Base

| Item | Escolha | Justificativa |
|---|---|---|
| Build | **Vite** | Padrão de fato; HMR rápido |
| Linguagem | **TypeScript strict** | Não-negociável para contribuição séria |
| Gestão | **pnpm** | Workspaces coerentes com o monorepo; lockfile eficiente |
| Framework | **React 19** | Ecossistema, familiaridade do público-alvo |

### 2.2 Bibliotecas por responsabilidade

| Responsabilidade | Lib | Notas |
|---|---|---|
| Rotas | **TanStack Router** | Type-safe end-to-end, casa com Query |
| Server state | **TanStack Query** | Cache, polling do dashboard, invalidação por webhook/SSE |
| Client state | **Zustand** | Mínimo; a maior parte do estado é server state |
| UI | **Tailwind CSS 4** + **shadcn/ui** (Radix) | Componentes copiados pro repo = zero lock-in, tema customizável (ADR-013) |
| Ícones | **lucide-react** | Padrão do ecossistema shadcn |
| Gráficos | **Recharts** | Dashboards de métricas; suficiente e leve |
| Formulários | **react-hook-form** + **zod** | Wizards de conexão e Discovery |
| i18n | **react-i18next** | Base **en**, primeira tradução **pt-BR** (SPEC-001 §15.3) |
| Datas | **date-fns** | Leve, tree-shakeable |

### 2.3 Testes frontend

**Vitest** + **Testing Library** (componentes e hooks) · **Playwright** (E2E
dos fluxos críticos: onboarding de conexões, pipeline da spec, micro-survey).

### 2.4 Contrato API ↔ Web

Cliente TypeScript **gerado do OpenAPI** do FastAPI via **@hey-api/openapi-ts**
em passo de build (ADR-014). Consequência: mudança de contrato quebra o build
do frontend, nunca o runtime. O schema OpenAPI versionado é artefato de CI.

---

## 3. Monorepo, Build e Ambiente Local

### 3.1 Estrutura (refina SPEC-001 §12.2)

```
specharness/
├── .python-version
├── pyproject.toml            # workspace root (uv)
├── uv.lock                   # lockfile único
├── justfile                  # task runner unificado (§3.2)
├── docker-compose.yaml       # postgres, ollama (ambos opcionais)
├── .devcontainer/            # ambiente pronto p/ contribuidor (VS Code / Codespaces)
├── .pre-commit-config.yaml
├── packages/
│   ├── core/                 #   pyright strict · cobertura ≥85%
│   ├── server/
│   ├── cli/
│   ├── metrics/
│   └── adapters/
│       ├── trackers/{redmine,github,jira,azdevops,gitlab}/
│       ├── git/{github,gitlab,azrepos}/
│       ├── llm/
│       └── importers/{openspec,speckit}/
├── web/                      # pnpm, fora do workspace uv
├── profiles/                 # harness profiles (dados — SPEC-001 §10)
├── specs/                    # dogfooding
├── evals/                    # golden datasets + runner (§5)
├── docs/                     # MkDocs Material
├── .claude/                  # harness de desenvolvimento (§4)
├── AGENTS.md                 # base comum (ADR-003)
├── CLAUDE.md                 # camada Claude Code
└── .github/workflows/
```

### 3.2 Task runner: justfile (ADR-015)

Interface única para humanos **e para o agente de código** — o harness
referencia estes comandos, nunca invocações cruas:

```
just setup        # uv sync + pnpm install + pre-commit install
just dev          # server + web + (opcional) ollama via compose
just test         # pytest + vitest
just test-core    # rápido, só core
just lint         # ruff + pyright + eslint
just bdd          # pytest-bdd das nossas specs
just evals        # roda golden datasets contra modelos configurados
just db-migrate   # alembic upgrade head
just db-reset     # recria SQLite local + seed
just seed         # dados de demonstração (projeto fictício com specs/commits)
just report       # gera o sprint report do próprio specharness
```

### 3.3 Ambiente local

- `.env.example` completo e comentado; `just setup` copia se `.env` ausente
- **Seed data**: projeto fictício com 12 specs, commits com trailers, runs de
  BDD e amostras de percepção — o dashboard funciona no primeiro `just dev`,
  sem conectar nada (essencial para contribuidor de frontend)
- **Ollama opcional via compose** com modelo pequeno documentado — o
  contribuidor testa o Readiness Gate sem API key
- **devcontainer** publicado: contribuidor via Codespaces roda `just test` em
  minutos, sem instalar nada

---

## 4. O Harness de Desenvolvimento (dogfooding)

O specharness será construído com Claude Code usando o harness abaixo —
que depois evolui para o próprio profile `claude-code/` do produto. Comemos a
própria ração desde o commit 1.

### 4.1 Arquivos de contexto

- **AGENTS.md** (raiz): visão do projeto, comandos `just`, convenções de
  commit (Conventional Commits + trailer `Spec:`), estrutura do monorepo,
  regras de fronteira (core não importa adapter; nada de I/O no domínio)
- **CLAUDE.md**: aponta para AGENTS.md + camada específica (skills, hooks,
  permissões)
- **AGENTS.md aninhados** por package com regras locais: `core/` (pyright
  strict, zero deps externas), `adapters/` (contract tests obrigatórios,
  como re-gravar cassettes), `web/` (padrões shadcn, proibido fetch fora do
  client gerado)

### 4.2 Skills do projeto (`.claude/skills/`)

| Skill | Função | Gate que aplica |
|---|---|---|
| `escrever-spec` | Gera spec no schema SPEC-001 (frontmatter + BDD + success_metrics) a partir de uma descrição | Roda o lint determinístico de BDD antes de entregar |
| `readiness-review` | Executa o Readiness Gate na spec indicada e devolve score + issues | Espelho do produto — testamos o gate usando-o |
| `novo-adapter` | Scaffold de adapter (tracker/git/importer): porta implementada, contract test com cassette, entry point registrado, doc | Não conclui sem contract test passando |
| `eval-prompt` | Cria/atualiza golden dataset de uma tarefa LLM e roda `just evals` | Mudança de prompt sem eval verde não mergeia |
| `registrar-adr` | ADR completo em `docs/adrs/` + linha na tabela da SPEC-001 | Template com opções consideradas obrigatórias |
| `sprint-report` | Gera o relatório da sprint do próprio projeto via `just report` | Publicado no repo — marketing por dogfooding |
| `release` | Prepara release: changelog, versões, checklist de smoke test | Só roda com CI verde |

(Base nas skills já validadas em produção no fluxo Redmine do autor; a skill
`chatbot-eval-expert` existente informa o design do runner de evals.)

### 4.3 Hooks

| Evento | Hook | Ação |
|---|---|---|
| Pre-commit (agente ou humano) | trailer-check | Bloqueia commit sem `Spec: SPEC-NNN` válido apontando para spec existente e não-archived |
| Pre-commit | ruff + pyright changed | Feedback em segundos, não no CI |
| Stop (fim de tarefa do agente) | test-gate | Roda `just test-core`; falha reabre a tarefa |
| PostToolUse (edição em `specs/`) | schema-validate | Valida frontmatter contra o schema — spec inválida nunca entra |

### 4.4 Permissões e MCPs

- **Permissões**: escrita liberada em `packages/`, `web/`, `specs/`, `evals/`,
  `docs/`; `profiles/` exige confirmação (dados canônicos do produto);
  proibido tocar `uv.lock`/`pnpm-lock.yaml` manualmente (só via comandos)
- **MCPs de desenvolvimento**: GitHub MCP (issues/PRs do próprio repo) e
  Postgres MCP (inspeção do banco local em debug). Mais nada — contexto enxuto

### 4.5 Subagente revisor

`.claude/agents/revisor-pr`: checklist do projeto (fronteiras de arquitetura,
cobertura, BDD da spec vinculada, eval verde se tocou prompt, doc atualizada)
— roda antes de todo PR do agente. Custo baixo, pega o que o CI pega tarde.

---

## 5. Evals como Infraestrutura (`evals/`)

Cada tarefa LLM do produto tem um diretório com golden dataset versionado:

```
evals/
├── readiness_gate/
│   ├── golden/           # specs boas/ruins/ambíguas + score esperado (faixa)
│   ├── rubric.md         # o que o juiz avalia
│   └── config.yaml       # modelos alvo: sonnet, gpt, qwen3:8b, llama3.3
├── report_narrative/
├── link_suggestion/
└── runner/               # CLI: just evals [--task X] [--model Y]
```

Regras: (1) toda mudança em prompt exige eval verde nos **modelos suportados,
incluindo os locais pequenos** — é isso que sustenta a promessa
"Ollama first-class"; (2) resultados versionados como artefato de CI para
comparação histórica; (3) o runner nasce como parte do repo e, madurecendo,
vira feature do produto (o módulo `verify` para specs de comportamento LLM).

---

## 6. CI/CD (GitHub Actions)

| Workflow | Trigger | Conteúdo | Budget |
|---|---|---|---|
| `pr.yaml` | todo PR | ruff + pyright + pytest (matrix 3.11/3.12/3.13) + vitest + build web + openapi-diff | **< 5 min** (paralelo, cache uv/pnpm) |
| `bdd.yaml` | PR que toca `specs/` ou `packages/` | pytest-bdd das nossas specs | < 3 min |
| `evals.yaml` | PR que toca `evals/` ou prompts | golden datasets nos modelos de API (locais rodam no dev) | < 8 min |
| `contract.yaml` | agendado semanal + label | contract tests contra cassettes; alerta se API real divergiu | — |
| `release.yaml` | merge em main | release-please → tag → PyPI (trusted publishing) + npm + changelog | — |
| `e2e.yaml` | agendado diário | Playwright nos fluxos críticos com seed data | — |

---

## 7. Decisões de Stack (ADRs 009–015)

| ADR | Decisão | Alternativas consideradas | Por quê |
|---|---|---|---|
| **009** | uv workspaces para o monorepo Python | Poetry, Hatch, PDM | Lockfile único, velocidade, virou padrão da comunidade; contribuidor roda um comando |
| **010** | SQLAlchemy async no server, sync no CLI, models únicos | Só async; SQLModel | CLI síncrono é mais simples e debugável; SQLModel abstrai demais para nosso uso de Alembic |
| **011** | Git via wrapper fino sobre o CLI | pygit2 (libgit2), GitPython, dulwich | `interpret-trailers` é nativo; zero dependência binária; comportamento idêntico ao ambiente do usuário |
| **012** | pytest-bdd para nosso gate BDD | behave, radish | Um runner só (pytest) para unit, contract e BDD; fixtures compartilhadas |
| **013** | Tailwind + shadcn/ui | MUI, Ant, Chakra | Componentes vivem no repo (zero lock-in), acessibilidade Radix, estética própria viável |
| **014** | Cliente TS gerado do OpenAPI (hey-api) | Cliente manual, tRPC | Contrato quebra em build, não em runtime; tRPC acoplaria demais front e back |
| **015** | justfile como task runner único | Make, Taskfile, scripts npm | Sintaxe limpa multiplataforma; interface compartilhada humano ↔ agente de código |

---

## 8. Ordem de Implantação da Stack

1. **Fundação do repo** — pyproject workspace + uv.lock, justfile, pre-commit,
   `.python-version`, licença, templates, AGENTS.md/CLAUDE.md iniciais
2. **CI mínimo** — `pr.yaml` com lint+test vazio-verde (pipeline antes do
   código: todo commit já nasce sob gate)
3. **Harness** — skills `escrever-spec` e `registrar-adr` + hooks de trailer e
   schema (a partir daqui, o desenvolvimento é spec-driven de fato)
4. **core: parser do Spec Registry** (SPEC-003) — com Hypothesis desde o início
5. **Readiness Gate determinístico → camada LLM** + primeiro golden dataset
   (`evals/readiness_gate/`)
6. **server + web scaffold** — FastAPI + OpenAPI codegen + dashboard com seed
   data
7. **Primeiro adapter (GitHub)** via skill `novo-adapter` — valida o padrão de
   contract test
8. **track + verify + report** — fecha o loop da Fase A

Cada passo entrega algo testável e mergeável; nenhum passo dura mais que uma
sprint.

---

## 9. Riscos da Stack

| Risco | Mitigação |
|---|---|
| Tailwind 4 / React 19 ainda em ondas de breaking changes no ecossistema | shadcn copia componentes pro repo — controlamos o ritmo de upgrade |
| LiteLLM: dependência pesada e superfície grande | Porta `LLMClient` isola; contract tests da porta permitem troca |
| Cassettes de contract test apodrecem | Workflow semanal `contract.yaml` detecta divergência da API real |
| pyright strict atrito com contribuidor iniciante | Strict só no core; adapters em basic; CONTRIBUTING explica |
| Evals de API custam dinheiro em CI | Locais rodam no dev; API só em PR com label `eval`; budget cap |

---

## 10. Questões em Aberto

1. Playwright no PR (mais lento) vs. só agendado — decidir após medir tempos.
2. SSE vs. polling curto para atualização do dashboard — spike na Fase A.
3. Publicar `web/` como package npm ou só como parte do release? (Provável:
   só release, com build servido pelo server.)
