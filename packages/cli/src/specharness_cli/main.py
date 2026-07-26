"""specharness CLI (SPEC-002 §1.2). Commands land as their specs are built."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from specharness_adapters.db import gateway_from_env
from specharness_core import __version__
from specharness_core.ports.database import DatabaseError

app = typer.Typer(
    name="specharness",
    help="Decision, quality and metrics layer for spec-driven development.",
    no_args_is_help=True,
)
console = Console()
# Errors go to stderr unwrapped: the message names an env var and a URL, and a
# line break in the middle of either makes it harder to act on (SPEC-004).
err_console = Console(stderr=True, soft_wrap=True)

connect_app = typer.Typer(
    name="connect",
    help="Conecta o specharness aos serviços do onboarding (SPEC-001 §5.1).",
    no_args_is_help=True,
)
app.add_typer(connect_app, name="connect")


@app.command()
def version() -> None:
    """Show specharness version."""
    console.print(f"specharness [bold]{__version__}[/bold] (Fase A)")


@app.command()
def status() -> None:
    """Overview of what is implemented in this build."""
    table = Table(title="specharness — Fase A build map")
    table.add_column("Comando")
    table.add_column("Spec")
    table.add_column("Estado")
    rows = [
        ("specharness connect db", "SPEC-004", "disponível"),
        ("specharness llm test", "SPEC-005", "planejado"),
        ("specharness connect repo", "SPEC-006", "planejado"),
        ("specharness track", "SPEC-009", "planejado"),
        ("specharness ready <spec>", "SPEC-010/011", "planejado"),
        ("specharness verify", "SPEC-012", "planejado"),
        ("specharness report", "SPEC-015", "planejado"),
    ]
    for row in rows:
        table.add_row(*row)
    console.print(table)


@connect_app.command("db")
def connect_db() -> None:
    """Conecta ao banco, criando e migrando o que faltar.

    Sem configuração, cria um SQLite local em .specharness/ e o migra — zero
    perguntas (ADR-002). Defina SPECHARNESS_DATABASE_URL para usar o seu
    Postgres; nada mais muda.
    """
    try:
        gateway = gateway_from_env()
        gateway.healthcheck()
        result = gateway.migrate()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    console.print(f"✓ Conectado — {_describe(gateway)}", markup=False, soft_wrap=True)
    if result.was_noop:
        console.print(f"  Migrações em dia (revisão {result.revision}).", markup=False)
    else:
        applied = ", ".join(result.applied)
        console.print(
            f"  Migrações aplicadas: {applied} (revisão {result.revision}).", markup=False
        )


def _describe(gateway) -> str:
    """Where we landed, in terms the user can act on — never with a password."""
    target = gateway.target
    if target.sqlite_path is None:
        return f"PostgreSQL em {target.safe_sync_url}"
    path = Path(target.sqlite_path)
    try:
        # A relative path is what the user recognises as "o banco deste repo".
        shown = path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        shown = path.as_posix()
    return f"SQLite em {shown}"


if __name__ == "__main__":
    app()
