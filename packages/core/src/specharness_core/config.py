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


class TrackerConfig(BaseModel):
    """Tracker connection + status mapping (SPEC-007, ADR-007).

    `url` and `project` locate the Redmine instance; `status_map` maps a spec
    status (e.g. `done`) to the Redmine status name to write back, because each
    Redmine workflow is per-instance. No secret here — the API key comes from
    the environment only (`REDMINE_API_KEY`); `extra="forbid"` catches a stray
    key pasted into the file.
    """

    model_config = {"extra": "forbid"}

    url: str | None = None
    project: str | None = None
    status_map: dict[str, str] = Field(default_factory=dict)


def load_tracker(text: str) -> TrackerConfig:
    """Parse tracker config from `specharness.yaml` text, or raise `ConfigError`.

    The tracker config lives under a `tracker:` key (so it coexists with `llm:`
    in one file). No `tracker:` key means "not configured" — an empty config the
    caller can report on, not an error.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{CONFIG_FILENAME} inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{CONFIG_FILENAME} deve ser um mapa YAML")
    section = raw.get("tracker")
    if section is None:
        return TrackerConfig()
    if not isinstance(section, dict):
        raise ConfigError("a seção 'tracker' de specharness.yaml deve ser um mapa YAML")
    try:
        return TrackerConfig.model_validate(section)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


class JiraConfig(BaseModel):
    """Jira project scope + status mapping (SPEC-019, ADR-020).

    `project` is the Jira project key to import (e.g. `KAN`); `status_map` maps
    a spec status to the Jira status name to write back, because each Jira has
    its own workflow. No secret and no URL here — `JIRA_URL`, `JIRA_EMAIL` and
    `JIRA_TOKEN` come from the environment only; `extra="forbid"` catches a
    stray credential pasted into the file.
    """

    model_config = {"extra": "forbid"}

    project: str | None = None
    status_map: dict[str, str] = Field(default_factory=dict)


def load_jira(text: str) -> JiraConfig:
    """Parse Jira config from `specharness.yaml` text, or raise `ConfigError`.

    Mirrors `load_tracker`: the config lives under a `jira:` key; no key means
    "not configured", an empty config the caller can report on.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{CONFIG_FILENAME} inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{CONFIG_FILENAME} deve ser um mapa YAML")
    section = raw.get("jira")
    if section is None:
        return JiraConfig()
    if not isinstance(section, dict):
        raise ConfigError("a seção 'jira' de specharness.yaml deve ser um mapa YAML")
    try:
        return JiraConfig.model_validate(section)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc


class ReadinessConfig(BaseModel):
    """Readiness Gate LLM layer settings (SPEC-011).

    `threshold` is the score below which the LLM layer blocks approved -> ready
    (rubric default: < 70 não-ready). Configurable because teams calibrate their
    own bar. No secret here — the model routing lives in the `llm:` section.
    """

    model_config = {"extra": "forbid"}

    threshold: int = 70


def load_readiness(text: str) -> ReadinessConfig:
    """Parse the readiness section of `specharness.yaml`, or return the default.

    Mirrors `load_tracker`: the config lives under a `readiness:` key; its
    absence means "use defaults", not an error.
    """
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{CONFIG_FILENAME} inválido: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{CONFIG_FILENAME} deve ser um mapa YAML")
    section = raw.get("readiness")
    if section is None:
        return ReadinessConfig()
    if not isinstance(section, dict):
        raise ConfigError("a seção 'readiness' de specharness.yaml deve ser um mapa YAML")
    try:
        return ReadinessConfig.model_validate(section)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc
