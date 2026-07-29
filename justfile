# specharness — task runner unificado (humanos e agentes usam OS MESMOS comandos)

# O .env do repo é a fonte das credenciais de onboarding (SPEC-004/005):
# carregado aqui e nos entrypoints, para nenhum comando exigir --env-file.
set dotenv-load := true

default:
    @just --list

# Setup completo do ambiente de desenvolvimento
setup:
    uv sync
    uv run pre-commit install --hook-type pre-commit --hook-type commit-msg
    @echo "✓ Ambiente pronto. Rode 'just test' para validar."

# Roda todos os testes
test:
    uv run pytest

# Testes rápidos, só do core
test-core:
    uv run pytest packages/core

# Cobertura do core, por módulo (métrica das specs — ADR-016: medida, não afirmada)
cov:
    uv run pytest packages/core --cov=specharness_core --cov-report=term-missing

# Cobertura do adapter de banco (métrica da SPEC-004 — ADR-016: medida, não afirmada)
cov-db:
    uv run pytest packages/adapters --cov=specharness_adapters.db --cov-report=term-missing --cov-fail-under=90

# Cobertura do adapter de LLM (métrica da SPEC-005 — ADR-016: medida, não afirmada)
cov-llm:
    uv run pytest packages/adapters --cov=specharness_adapters.llm --cov-report=term-missing --cov-fail-under=90

# Cobertura dos adapters de repositório: git + GitHub (SPEC-006 — ADR-016)
cov-repo:
    uv run pytest packages/adapters --cov=specharness_adapters.git --cov=specharness_adapters.github --cov=specharness_adapters.db.repository_store --cov-report=term-missing --cov-fail-under=90

# Cobertura do adapter de tracker: Redmine + store (SPEC-007 — ADR-016)
cov-tracker:
    uv run pytest packages/adapters --cov=specharness_adapters.redmine --cov=specharness_adapters.db.workitem_store --cov-report=term-missing --cov-fail-under=90

# Cobertura do adapter de GitHub Issues (SPEC-008 — ADR-016)
cov-issues:
    uv run pytest packages/adapters --cov=specharness_adapters.github_issues --cov-report=term-missing --cov-fail-under=90

# Cobertura da camada LLM do Readiness Gate: gate + stores (SPEC-011 — ADR-016)
cov-readiness:
    uv run pytest packages/adapters --cov=specharness_adapters.llm.gate --cov=specharness_adapters.db.readiness_store --cov-report=term-missing --cov-fail-under=90

# Cobertura do runner de BDD + store de scenario runs (SPEC-012 — ADR-016/018)
cov-verify:
    uv run pytest packages/adapters --cov=specharness_adapters.verify --cov=specharness_adapters.db.scenario_run_store --cov-report=term-missing --cov-fail-under=90

cov-metrics:
    uv run pytest packages/adapters --cov=specharness_adapters.metrics --cov=specharness_adapters.db.metrics_store --cov-report=term-missing --cov-fail-under=90

cov-perception:
    uv run pytest packages/adapters --cov=specharness_adapters.db.perception_store --cov-report=term-missing --cov-fail-under=90

cov-report:
    uv run pytest packages/adapters --cov=specharness_adapters.report --cov-report=term-missing --cov-fail-under=90

cov-server:
    uv run pytest packages/server --cov=specharness_server --cov-report=term-missing --cov-fail-under=90

# Mutation score do parser: cobertura diz que o teste rodou, isto diz que ele prova
mutants threshold="90":
    uv run python scripts/mutants.py --threshold {{threshold}}

# Lint + format check + tipos
lint:
    uv run ruff check .
    uv run ruff format --check .

# Aplica format e fixes automáticos
fix:
    uv run ruff check --fix .
    uv run ruff format .

# Valida o schema de todas as specs (mesmo check do hook)
specs-validate:
    uv run python .claude/hooks/schema_validate.py specs/*.md

# Integridade dos testes vs base (anti reward-hacking — ADR-016)
test-integrity base="main":
    uv run python scripts/test_integrity.py --base {{base}}

# Roda os golden datasets de evals (placeholder Fase A — SPEC-011)
evals:
    uv run python -m evals.runner

# Carrega seed data no banco demo dedicado (.specharness/demo.db — SPEC-016/018)
seed:
    uv run python -m specharness_server.seed

# Sobe o server em modo demo: seed + banco demo + aviso na UI (SPEC-018, ADR-019)
dev: seed
    SPECHARNESS_DEMO=1 uv run uvicorn specharness_server.app:app --reload --port 8321

# Sobe o server servindo os DADOS REAIS do projeto (sem seed, sem aviso de demo)
serve:
    uv run uvicorn specharness_server.app:app --reload --port 8321

# Conecta e migra o banco. Mesmo caminho de código que o usuário roda (SPEC-004):
# sem SPECHARNESS_DATABASE_URL cria o SQLite local; com ela, usa o seu Postgres.
db-migrate:
    uv run specharness connect db

# Gera o sprint report do próprio specharness (SPEC-015)
report sprint="2026-A4":
    uv run specharness report {{sprint}}

# Compila o dashboard e o embute no pacote do server (SPEC-021). Node é build-time.
build-web:
    cd web && npm ci && npm run build
    rm -rf packages/server/src/specharness_server/_web
    cp -r web/dist packages/server/src/specharness_server/_web

# Constrói os wheels publicáveis com o dashboard embutido (SPEC-021).
build: build-web
    uv build --all-packages -o dist

# Gate de artefato (SPEC-021): dashboard embutido e sem segredos (ADR-016)
check-dist:
    uv run python scripts/check_dist.py dist
