#!/usr/bin/env python3
"""Mutation score do parser de specs (SPEC-003, success_metric).

Por que existe: cobertura de linha diz que o teste *executou* o código; não diz
que ele *provaria* uma quebra. Três rodadas de verificação adversarial da
SPEC-003 acharam testes com 100% de cobertura que passavam com a implementação
mutilada. Este script mede o que a cobertura não mede.

Cada mutante é uma quebra deliberada de `specschema.py`. Um mutante MORTO é
detectado pela suíte; um SOBREVIVENTE é teste que não prova o que afirma.

Mutantes equivalentes (que não alteram comportamento observável) ficam fora do
catálogo de propósito: incluí-los rebaixaria o score sem apontar defeito real.
Exemplos deixados de lado: remover `\\A` do regex de frontmatter quando o
chamador usa `.match`, e exigir `\\s*$` no id (o YAML já apara espaço final).

Uso:
    python scripts/mutants.py [--threshold 90]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "packages" / "core" / "src" / "specharness_core" / "specschema.py"

#: (id, alvo, original, mutado)
MUTANTS: list[tuple[str, str, str, str]] = [
    # --- campos obrigatórios (D1) ---
    ("req-title", "title obrigatório", "    title: str", '    title: str = "sem titulo"'),
    ("req-spec", "spec obrigatório", "    spec: str", '    spec: str = "SPEC-000"'),
    # --- defaults declarados (D1) ---
    (
        "def-status",
        "default de status",
        "    status: SpecStatus = SpecStatus.DRAFT",
        "    status: SpecStatus = SpecStatus.DONE",
    ),
    (
        "def-type",
        "default de type",
        "    type: SpecType = SpecType.FEATURE",
        "    type: SpecType = SpecType.HARNESS",
    ),
    (
        "def-adrs",
        "default de adrs",
        "    adrs: list[str] = Field(default_factory=list)",
        '    adrs: list[str] = Field(default_factory=lambda: ["ADR-000"])',
    ),
    (
        "def-metrics",
        "default de success_metrics",
        "    success_metrics: list[str] = Field(default_factory=list)",
        '    success_metrics: list[str] = Field(default_factory=lambda: ["fake"])',
    ),
    # --- regex do id da spec ---
    ("id-2digitos", "id com 2 dígitos", r'r"^SPEC-\d{3,}$"', r'r"^SPEC-\d{2,}$"'),
    ("id-sem-fim", "id sem âncora final", r'r"^SPEC-\d{3,}$"', r'r"^SPEC-\d{3,}"'),
    ("id-sem-ancoras", "id sem âncoras", r'r"^SPEC-\d{3,}$"', r'r"SPEC-\d{3,}"'),
    (
        "id-case-insensitive",
        "id aceitando minúsculas",
        r'r"^SPEC-\d{3,}$"',
        r'r"(?i)^SPEC-\d{3,}$"',
    ),
    # --- regex e posição do frontmatter ---
    (
        "fm-greedy",
        "frontmatter ganancioso",
        r'r"\A---\s*\n(.*?)\n---\s*\n?"',
        r'r"\A---\s*\n(.*)\n---\s*\n?"',
    ),
    (
        "fm-sem-dotall",
        "frontmatter sem DOTALL",
        'r"\\A---\\s*\\n(.*?)\\n---\\s*\\n?", re.DOTALL',
        'r"\\A---\\s*\\n(.*?)\\n---\\s*\\n?"',
    ),
    # Trocar só `.match` por `.search` seria mutante equivalente: o padrão
    # começa com `\A`, que já ancora no início. Para quebrar de verdade a
    # exigência de "frontmatter no topo", o mutante remove a âncora também.
    (
        "fm-fora-do-topo",
        "frontmatter fora do topo",
        "    match = _FRONTMATTER_RE.match(text)",
        r'    match = re.compile(_FRONTMATTER_RE.pattern.replace("\\A", ""), '
        r"re.DOTALL).search(text)",
    ),
    # --- fatiamento do corpo ---
    ("body-inteiro", "corpo com frontmatter", "body=text[match.end() :]", "body=text"),
    (
        "body-grupo1",
        "corpo a partir do grupo 1",
        "body=text[match.end() :]",
        "body=text[match.end(1) :]",
    ),
    # --- extração de gherkin ---
    (
        "gk-sem-rotulo",
        "cerca sem exigir rótulo",
        'r"```gherkin\\s*\\n(.*?)```"',
        'r"```\\s*\\n(.*?)```"',
    ),
    (
        "gk-prefixo",
        "rótulo por prefixo (```g...)",
        'r"```gherkin\\s*\\n(.*?)```"',
        'r"```g\\w*\\s*\\n(.*?)```"',
    ),
    (
        "gk-substring",
        "rótulo por substring",
        'r"```gherkin\\s*\\n(.*?)```"',
        'r"```\\w*gherkin\\w*\\s*\\n(.*?)```"',
    ),
    (
        "gk-sufixo-livre",
        "rótulo com sufixo livre",
        'r"```gherkin\\s*\\n(.*?)```"',
        'r"```gherkin[^\\n]*\\n(.*?)```"',
    ),
    (
        "gk-greedy",
        "gherkin ganancioso",
        'r"```gherkin\\s*\\n(.*?)```"',
        'r"```gherkin\\s*\\n(.*)```"',
    ),
    (
        "gk-sem-dotall",
        "gherkin sem DOTALL",
        'r"```gherkin\\s*\\n(.*?)```", self.body, re.DOTALL',
        'r"```gherkin\\s*\\n(.*?)```", self.body',
    ),
    # --- máquina de estados (D2) ---
    (
        "st-draft-ready",
        "draft->ready liberado",
        "SpecStatus.DRAFT: frozenset({SpecStatus.APPROVED})",
        "SpecStatus.DRAFT: frozenset({SpecStatus.APPROVED, SpecStatus.READY})",
    ),
    (
        "st-ready-verifying",
        "ready->verifying liberado",
        "SpecStatus.READY: frozenset({SpecStatus.IN_PROGRESS, SpecStatus.APPROVED})",
        "SpecStatus.READY: frozenset({SpecStatus.IN_PROGRESS, SpecStatus.APPROVED, "
        "SpecStatus.VERIFYING})",
    ),
    (
        "st-approved-done",
        "approved->done liberado",
        "SpecStatus.APPROVED: frozenset({SpecStatus.READY, SpecStatus.DRAFT})",
        "SpecStatus.APPROVED: frozenset({SpecStatus.READY, SpecStatus.DRAFT, SpecStatus.DONE})",
    ),
    (
        "st-inprogress-done",
        "in_progress->done liberado",
        "SpecStatus.IN_PROGRESS: frozenset({SpecStatus.VERIFYING, SpecStatus.READY})",
        "SpecStatus.IN_PROGRESS: frozenset({SpecStatus.VERIFYING, SpecStatus.READY, "
        "SpecStatus.DONE})",
    ),
    (
        "st-done-draft",
        "done->draft (reabertura)",
        "SpecStatus.DONE: frozenset({SpecStatus.ARCHIVED})",
        "SpecStatus.DONE: frozenset({SpecStatus.ARCHIVED, SpecStatus.DRAFT})",
    ),
    (
        "st-archived-saida",
        "archived deixa de ser terminal",
        "SpecStatus.ARCHIVED: frozenset()",
        "SpecStatus.ARCHIVED: frozenset({SpecStatus.DRAFT})",
    ),
    (
        "st-tudo-permitido",
        "can_transition sempre True",
        "return target in ALLOWED_TRANSITIONS[current]",
        "return True",
    ),
    # --- mensagens de erro acionáveis ---
    (
        "msg-frontmatter",
        "mensagem de frontmatter ausente",
        "\"document has no YAML frontmatter block ('---' fences)\"",
        '"documento malformado"',
    ),
    (
        "msg-yaml",
        "mensagem de YAML inválido",
        'f"invalid YAML in frontmatter: {exc}"',
        '"frontmatter ruim"',
    ),
    (
        "msg-mapping",
        "mensagem de mapping",
        '"frontmatter must be a YAML mapping"',
        '"formato inesperado"',
    ),
    (
        "msg-passthrough",
        "mensagem do pydantic engolida",
        "raise SpecParseError(str(exc)) from exc",
        'raise SpecParseError("frontmatter invalido") from exc',
    ),
]


def run_suite() -> bool:
    """True se a suíte passa (mutante sobreviveu)."""
    proc = subprocess.run(
        ["uv", "run", "pytest", "packages/core", "-q", "-x", "-p", "no:cacheprovider"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=90.0)
    args = parser.parse_args()

    original = SRC.read_text(encoding="utf-8")
    backup = Path(tempfile.mkdtemp()) / "specschema.orig"
    backup.write_text(original, encoding="utf-8")

    # Baseline obrigatório: sem ele, uma suíte já vermelha faria TODO mutante
    # ser lido como "morto" e o script imprimiria 100% saindo com 0 — um score
    # perfeito alcançável quebrando os testes, dentro da própria ferramenta
    # anti-reward-hacking (ADR-016).
    print("baseline: suíte sem mutação...")
    if not run_suite():
        print(
            "  SUÍTE VERMELHA — abortado. Score de mutação só tem sentido sobre\n"
            "  baseline verde; medido assim, todo mutante pareceria morto."
        )
        return 1
    print("  ok, baseline verde\n")

    survivors: list[str] = []
    invalid: list[str] = []
    try:
        for mid, label, old, new in MUTANTS:
            occurrences = original.count(old)
            if occurrences != 1:
                print(f"  ?  {mid:22} padrão não único ({occurrences}x) — catálogo desatualizado")
                invalid.append(mid)
                continue
            SRC.write_text(original.replace(old, new), encoding="utf-8")
            if run_suite():
                print(f"  !  {mid:22} SOBREVIVEU — {label}")
                survivors.append(f"{mid} ({label})")
            else:
                print(f"  x  {mid:22} morto")
    finally:
        SRC.write_text(original, encoding="utf-8")
        shutil.rmtree(backup.parent, ignore_errors=True)

    total = len(MUTANTS) - len(invalid)
    killed = total - len(survivors)
    score = 100.0 * killed / total if total else 0.0

    print(f"\nMutation score: {killed}/{total} = {score:.1f}% (limiar {args.threshold:.0f}%)")
    if survivors:
        print("Sobreviventes:")
        for s in survivors:
            print(f"  - {s}")
    if invalid:
        print(f"Mutantes não aplicados (catálogo desatualizado): {', '.join(invalid)}")
        return 1
    if score < args.threshold:
        print("\nAbaixo do limiar: há teste que não prova o que afirma (ADR-016).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
