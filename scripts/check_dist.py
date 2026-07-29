#!/usr/bin/env python
"""Gate de artefato da SPEC-021 (ADR-016: medido, não afirmado).

Depois de `just build`, verifica que:
- o wheel do specharness_server embute o dashboard compilado (_web/index.html);
- nenhum artefato publicável — wheel OU sdist — carrega segredo/arquivo indevido.

Uso: python scripts/check_dist.py [dist_dir]   (default: dist)
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path


def _members(artifact: Path) -> list[str]:
    """Nomes dos arquivos dentro de um wheel (zip) ou sdist (tar.gz)."""
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as zf:
            return zf.namelist()
    with tarfile.open(artifact) as tf:
        return tf.getnames()


def _is_forbidden(name: str) -> bool:
    """Segredo real, não um template. `.env.example` é legítimo; `.env` não."""
    base = name.rsplit("/", 1)[-1].lower()
    return base == ".env" or base.startswith("id_rsa") or base.endswith((".pem", ".key"))


def main(dist_dir: str | None = None) -> int:
    dist = Path(dist_dir or (sys.argv[1] if len(sys.argv) > 1 else "dist"))
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if not wheels:
        print(f"✗ nenhum wheel em {dist}/ — rode `just build` antes.")
        return 1

    problems: list[str] = []

    server = next((w for w in wheels if w.name.startswith("specharness_server-")), None)
    if server is None:
        problems.append("wheel do specharness_server ausente")
    elif "specharness_server/_web/index.html" not in _members(server):
        problems.append("dashboard não embutido no wheel do server (_web/index.html ausente)")

    for artifact in (*wheels, *sdists):
        for name in _members(artifact):
            if _is_forbidden(name):
                problems.append(f"arquivo indevido em {artifact.name}: {name}")

    if problems:
        for problem in problems:
            print(f"✗ {problem}")
        return 1

    print(f"✓ {len(wheels)} wheels + {len(sdists)} sdists ok: dashboard embutido, sem segredos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
