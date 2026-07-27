# specharness — task runner unificado (humanos e agentes usam OS MESMOS comandos)

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

# Sobe o server de desenvolvimento
dev:
    uv run uvicorn specharness_server.app:app --reload --port 8321

# Conecta e migra o banco. Mesmo caminho de código que o usuário roda (SPEC-004):
# sem SPECHARNESS_DATABASE_URL cria o SQLite local; com ela, usa o seu Postgres.
db-migrate:
    uv run specharness connect db

# Gera o sprint report do próprio specharness (habilitado na SPEC-015)
report:
    @echo "O módulo report entra na SPEC-015."
