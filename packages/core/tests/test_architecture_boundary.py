"""Guards ADR-001 at test time: the core stays a pure domain (SPEC-004 §7).

SPEC-004 is the first spec to bring I/O into the project. The boundary it is
most likely to break is the one ADR-001 declares inviolable, so the boundary
gets a test instead of a promise.
"""

import ast
import pathlib

import specharness_core

CORE_SRC = pathlib.Path(specharness_core.__file__).parent

#: Nothing in this set may be imported from `packages/core`. ORMs and drivers
#: are I/O; FastAPI/typer/httpx are frameworks and transports (ADR-001).
FORBIDDEN_ROOTS = frozenset(
    {
        "sqlalchemy",
        "alembic",
        "aiosqlite",
        "asyncpg",
        "psycopg",
        "psycopg2",
        "sqlite3",
        "fastapi",
        "uvicorn",
        "typer",
        "httpx",
        "requests",
    }
)


def _core_modules() -> list[pathlib.Path]:
    return sorted(p for p in CORE_SRC.rglob("*.py") if "__pycache__" not in p.parts)


def _imported_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_the_scan_actually_finds_the_core_modules():
    """Um teste de fronteira que varre zero arquivos passa por vacuidade."""
    modules = _core_modules()

    assert len(modules) >= 3
    assert any(p.name == "specschema.py" for p in modules)
    assert any(p.parent.name == "ports" for p in modules)


def test_core_never_imports_io_or_framework_packages():
    offenders: list[str] = []
    for module in _core_modules():
        for root in sorted(_imported_roots(module) & FORBIDDEN_ROOTS):
            offenders.append(f"{module.relative_to(CORE_SRC).as_posix()} importa {root}")

    assert offenders == []


def test_the_scan_would_catch_a_violation():
    """Prova que o detector detecta — senão o teste acima é decorativo."""
    tree = ast.parse("import sqlalchemy\nfrom fastapi import FastAPI\n")
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])

    assert roots & FORBIDDEN_ROOTS == {"sqlalchemy", "fastapi"}


def test_core_package_metadata_declares_no_database_dependency():
    pyproject = CORE_SRC.parents[1] / "pyproject.toml"
    assert pyproject.is_file(), f"esperava o pyproject do core em {pyproject}"
    text = pyproject.read_text(encoding="utf-8")

    assert "sqlalchemy" not in text.lower()
    assert "alembic" not in text.lower()
