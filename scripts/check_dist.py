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


#: Rótulos internos do specharness que NUNCA podem chegar ao dashboard servido
#: (SPEC-025): a fase do roadmap interno, IDs de spec internas usadas como rótulo,
#: e as recipes internas do repo. Medido no artefato publicado, não só na fonte —
#: um `_web` obsoleto embutido passaria batido nos testes de fonte.
_INTERNAL_LABELS: tuple[str, ...] = (
    "Fase A",
    "SPEC-013",
    "SPEC-014",
    "just serve",
    "just dev",
)


def _embedded_web_leaks(server_wheel: Path) -> list[str]:
    """O que não pode chegar ao dashboard embutido do wheel (SPEC-025, SPEC-028).

    Rótulos internos do specharness (SPEC-025) e host absoluto `localhost`: o
    bundle de produção resolve a API na mesma origem que o serve, então uma URL
    de localhost embutida quebraria `specharness up` em outra porta/host (SPEC-028).
    """
    leaks: list[str] = []
    with zipfile.ZipFile(server_wheel) as zf:
        for name in zf.namelist():
            if "/_web/" not in name or not name.endswith((".js", ".css", ".html")):
                continue
            text = zf.read(name).decode("utf-8", errors="ignore")
            for label in _INTERNAL_LABELS:
                if label in text:
                    leaks.append(f"rótulo interno {label!r} no dashboard servido ({name})")
            if "localhost" in text:
                leaks.append(
                    f"host absoluto 'localhost' embutido no dashboard servido ({name}); "
                    "deve resolver same-origin (SPEC-028)"
                )
    return leaks


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
    else:
        problems.extend(_embedded_web_leaks(server))

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
