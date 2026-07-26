"""specharness CLI (SPEC-002 §1.2). Commands land as their specs are built."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from specharness_core import __version__

app = typer.Typer(
    name="specharness",
    help="Decision, quality and metrics layer for spec-driven development.",
    no_args_is_help=True,
)
console = Console()


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
        ("specharness connect db", "SPEC-004", "planejado"),
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


if __name__ == "__main__":
    app()
