#!/usr/bin/env python3
"""Validate spec files against the schema (SPEC-001 §7). Used by pre-commit
and by the Claude Code PostToolUse hook — a spec that doesn't parse never lands."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "core" / "src"))

# Consoles Windows usam cp1252 por padrão: sem isto, o print dos marcadores
# ✓/✗ levanta UnicodeEncodeError e o hook reprova uma spec que parseou bem.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from specharness_core import SpecParseError, parse_spec  # noqa: E402


def _previous_status(path: Path) -> str | None:
    """Status da spec em HEAD, ou None se o arquivo é novo / git indisponível."""
    rel = os.path.relpath(path.resolve(), REPO_ROOT)
    proc = subprocess.run(
        ["git", "show", f"HEAD:{rel}"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    try:
        return parse_spec(proc.stdout).frontmatter.status.value
    except SpecParseError:
        return None


def _in_ci() -> bool:
    return os.environ.get("CI", "").lower() in {"true", "1"}


def main(paths: list[str]) -> int:
    failures = 0
    seen: dict[str, str] = {}
    for raw in paths:
        path = Path(raw)
        if not path.name.startswith("SPEC-"):
            continue
        try:
            parsed = parse_spec(path.read_text(encoding="utf-8"))
        except SpecParseError as exc:
            print(f"✗ {path}: {exc}")
            failures += 1
            continue
        if parsed.spec_id in seen:
            print(f"✗ {path}: id duplicado {parsed.spec_id} (também em {seen[parsed.spec_id]})")
            failures += 1
            continue
        seen[parsed.spec_id] = str(path)
        if (
            parsed.frontmatter.status.value == "done"
            and not _in_ci()
            and _previous_status(path) != "done"
        ):
            print(f"✗ {path}: transição para 'done' é exclusiva do CI (ADR-016)")
            failures += 1
            continue
        expected_prefix = parsed.spec_id
        if not path.name.startswith(expected_prefix):
            print(f"✗ {path}: nome do arquivo não começa com {expected_prefix}")
            failures += 1
            continue
        print(f"✓ {path} ({parsed.spec_id}, {parsed.frontmatter.status.value})")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
