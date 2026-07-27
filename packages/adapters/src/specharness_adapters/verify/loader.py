"""Load a repo's step definitions (SPEC-012, ADR-018).

Convention: the repo points `verify` at a Python module that exposes a top-level
`registry: StepRegistry` populated with `@registry.step(...)` definitions. This
is where importing user code (I/O) is allowed — the core never does it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from .registry import StepRegistry


class VerifyError(Exception):
    """A step-definition module could not be loaded."""


def load_steps(path: Path) -> StepRegistry:
    spec = importlib.util.spec_from_file_location("specharness_user_steps", path)
    if (
        spec is None or spec.loader is None
    ):  # pragma: no cover - defensivo; um path real sempre resolve
        raise VerifyError(f"não consegui carregar step definitions de {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # o módulo do usuário pode quebrar ao importar
        raise VerifyError(f"erro ao importar {path}: {exc}") from exc
    registry = getattr(module, "registry", None)
    if not isinstance(registry, StepRegistry):
        raise VerifyError(f"{path} não expõe um 'registry: StepRegistry'")
    return registry
