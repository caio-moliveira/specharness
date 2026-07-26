#!/usr/bin/env python3
"""Checagem de integridade dos testes (ADR-016 — anti reward-hacking).

Compara HEAD contra a base e falha se, em arquivos de teste:
- asserts foram removidos em saldo líquido negativo, ou
- skips/xfails foram adicionados sem `reason=`.

Override auditável (aparece no log do CI): SPECHARNESS_ALLOW_TEST_WEAKENING=1
com justificativa obrigatória na descrição do PR.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Consoles Windows usam cp1252 por padrão: sem isto, o print dos marcadores
# ✓/✗/⚠ levanta UnicodeEncodeError e o gate falha por causa do console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASSERT_RE = re.compile(r"^\s*assert\b")
SKIP_RE = re.compile(r"pytest\.mark\.(skip|skipif|xfail)|\bunittest\.skip")
REASON_RE = re.compile(r"reason\s*=")


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main")
    args = parser.parse_args()

    if git("rev-parse", "--verify", args.base).returncode != 0:
        print(f"[test-integrity] base '{args.base}' inexistente — nada a comparar.")
        return 0

    diff = git("diff", "--unified=0", f"{args.base}...HEAD")
    if diff.returncode != 0:
        print(diff.stderr)
        return 1

    current: str | None = None
    removed: dict[str, int] = {}
    added: dict[str, int] = {}
    naked_skips: list[tuple[str, str]] = []

    for line in diff.stdout.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/")[-1]
            continue
        if current is None or "/tests/" not in current:
            continue
        if line.startswith("-") and not line.startswith("---"):
            if ASSERT_RE.match(line[1:]):
                removed[current] = removed.get(current, 0) + 1
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if ASSERT_RE.match(body):
                added[current] = added.get(current, 0) + 1
            if SKIP_RE.search(body) and not REASON_RE.search(body):
                naked_skips.append((current, body.strip()))

    failures = 0
    for path, count in sorted(removed.items()):
        net = count - added.get(path, 0)
        if net > 0:
            print(f"✗ {path}: {net} assert(s) removidos em saldo líquido")
            failures += 1
    for path, snippet in naked_skips:
        print(f"✗ {path}: skip/xfail sem reason= -> {snippet}")
        failures += 1

    if failures and os.environ.get("SPECHARNESS_ALLOW_TEST_WEAKENING") == "1":
        print("⚠ Override SPECHARNESS_ALLOW_TEST_WEAKENING=1 ativo — registrado no log.")
        return 0
    if failures:
        print("\nTestes não são afrouxados em tarefa de implementação (ADR-016).")
        return 1
    print("✓ Integridade dos testes ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
