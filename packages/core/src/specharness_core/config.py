"""Project configuration — LLM model routing (SPEC-005, ADR-005).

Pure domain (ADR-001): this turns already-read text into a validated
`RoutingConfig`. Reading `specharness.yaml` from disk is I/O and belongs at the
edge (CLI/adapter); parsing it is a decision and lives here, mirroring
`parse_spec`.

No secret ever appears in this file. Keys come from the environment only
(SPEC-005, métrica 3), and `RoutingConfig` has no field that could hold one —
so a config file can never be the place a key leaks.
"""

from __future__ import annotations

import yaml
from pydantic import BaseModel, Field

#: The per-project config the tool reads from the repository root.
CONFIG_FILENAME = "specharness.yaml"


class ConfigError(ValueError):
    """Raised when `specharness.yaml` cannot be parsed as routing config."""


class RoutingConfig(BaseModel):
    """Task -> model routing (SPEC-005, critério 3).

    `default` is the model used unless a task overrides it; `fallback` is the
    model tried when the primary call fails at runtime (ADR-006 degradation).
    """

    model_config = {"extra": "forbid"}

    default: str
    tasks: dict[str, str] = Field(default_factory=dict)
    fallback: str | None = None

    def model_for_task(self, task: str) -> str:
        return self.tasks.get(task, self.default)


def load_routing(text: str) -> RoutingConfig:
    """Parse routing from `specharness.yaml` text, or raise `ConfigError`.

    The routing may sit at the top level or under an `llm:` key, so a project
    can grow other sections without moving this one.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{CONFIG_FILENAME} inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{CONFIG_FILENAME} deve ser um mapa YAML")
    section = raw.get("llm", raw)
    if not isinstance(section, dict):
        raise ConfigError("a seção 'llm' de specharness.yaml deve ser um mapa YAML")
    try:
        return RoutingConfig.model_validate(section)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
