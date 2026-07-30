#!/usr/bin/env python3
"""commit-msg hook: every commit must carry a valid `Spec:` trailer (SPEC-001 §7.3).

Usage (via pre-commit, stage commit-msg): trailer_check.py <path-to-commit-msg-file>
Exempt: merge commits, fixup!/squash!, and release-please commits.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "core" / "src"))

# Consoles Windows usam cp1252 por padrão: sem isto, o print dos marcadores
# ✓/✗ levanta UnicodeEncodeError e o commit-msg falha por causa do console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from specharness_core import is_trailer_exempt, parse_spec, valid_spec_trailers  # noqa: E402


def known_spec_ids() -> dict[str, str]:
    """Map of spec id -> status for every spec file in specs/."""
    ids: dict[str, str] = {}
    for path in sorted((REPO_ROOT / "specs").glob("SPEC-*.md")):
        try:
            parsed = parse_spec(path.read_text(encoding="utf-8"))
            ids[parsed.spec_id] = parsed.frontmatter.status.value
        except Exception:
            continue
    return ids


def main() -> int:
    message = Path(sys.argv[1]).read_text(encoding="utf-8")
    if is_trailer_exempt(message):
        return 0

    valid, invalid = valid_spec_trailers(message)
    if invalid:
        print(f"✗ Trailer 'Spec:' com valor inválido: {', '.join(invalid)}")
        return 1
    if not valid:
        print("✗ Commit sem trailer 'Spec: SPEC-NNN' no bloco final da mensagem.")
        print("  O git só reconhece trailers no ÚLTIMO bloco — uma linha em branco")
        print("  encerra o bloco. Deixe todos os trailers JUNTOS no fim, ex.:\n")
        print("    feat: minha mudança\n")
        print("    Spec: SPEC-003")
        print("    Co-Authored-By: Fulana <fulana@exemplo.com>\n")
        return 1

    known = known_spec_ids()
    for spec_id in valid:
        if spec_id not in known:
            print(f"✗ {spec_id} não existe em specs/.")
            return 1
        if known[spec_id] == "archived":
            print(f"✗ {spec_id} está archived — specs congeladas não recebem commits.")
            return 1
    print(f"✓ Spec trailer ok: {', '.join(valid)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
