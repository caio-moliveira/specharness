#!/usr/bin/env python
"""Gate de artefato da SPEC-021 (ADR-016: medido, não afirmado).

Depois de `just build`, verifica que:
- o wheel do specharness_server embute o dashboard compilado (_web/index.html);
- nenhum wheel carrega segredo ou arquivo indevido.

Uso: python scripts/check_dist.py [dist_dir]   (default: dist)
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

#: Substrings que nunca deveriam aparecer num artefato publicável.
SECRET_HINTS = (".env", ".pem", "id_rsa", "secret", "credential")


def main(dist_dir: str | None = None) -> int:
    dist = Path(dist_dir or (sys.argv[1] if len(sys.argv) > 1 else "dist"))
    wheels = sorted(dist.glob("*.whl"))
    if not wheels:
        print(f"✗ nenhum wheel em {dist}/ — rode `just build` antes.")
        return 1

    problems: list[str] = []

    server = next((w for w in wheels if w.name.startswith("specharness_server-")), None)
    if server is None:
        problems.append("wheel do specharness_server ausente")
    elif "specharness_server/_web/index.html" not in zipfile.ZipFile(server).namelist():
        problems.append("dashboard não embutido no wheel do server (_web/index.html ausente)")

    for wheel in wheels:
        for name in zipfile.ZipFile(wheel).namelist():
            low = name.lower()
            if any(hint in low for hint in SECRET_HINTS):
                problems.append(f"arquivo indevido em {wheel.name}: {name}")

    if problems:
        for problem in problems:
            print(f"✗ {problem}")
        return 1

    print(f"✓ {len(wheels)} wheels ok: dashboard embutido, sem segredos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
