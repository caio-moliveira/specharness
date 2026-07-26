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

# Migrações de banco (habilitado quando Alembic entrar — SPEC-004)
db-migrate:
    @echo "Alembic entra na SPEC-004 (conexão de banco)."

# Gera o sprint report do próprio specharness (habilitado na SPEC-015)
report:
    @echo "O módulo report entra na SPEC-015."
