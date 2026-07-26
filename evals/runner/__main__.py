"""Eval runner (Fase A placeholder — implementação completa na SPEC-011).

Lista os golden datasets encontrados e valida a estrutura mínima.
Quando a SPEC-011 for implementada, este runner executa os goldens contra os
modelos do config.yaml e falha o CI fora dos pass_criteria.
"""

from __future__ import annotations

import sys
from pathlib import Path

EVALS_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tasks = [p for p in EVALS_ROOT.iterdir() if p.is_dir() and p.name != "runner"]
    if not tasks:
        print("Nenhuma task de eval encontrada.")
        return 1
    for task in sorted(tasks):
        goldens = sorted((task / "golden").glob("*.md")) if (task / "golden").exists() else []
        has_config = (task / "config.yaml").exists()
        has_rubric = (task / "rubric.md").exists()
        status = "ok" if (goldens and has_config and has_rubric) else "INCOMPLETA"
        detail = f"{len(goldens)} goldens, config={has_config}, rubric={has_rubric}"
        print(f"[{status}] {task.name}: {detail}")
    print("\nExecução real dos goldens chega com a SPEC-011.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
