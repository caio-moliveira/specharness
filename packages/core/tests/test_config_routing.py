"""specharness.yaml routing parses purely (SPEC-005, critério 3, métrica 3)."""

from __future__ import annotations

import pytest
from specharness_core.config import ConfigError, RoutingConfig, load_routing

YAML_NESTED = """
llm:
  default: anthropic/claude-3-5-sonnet-latest
  tasks:
    readiness_gate: anthropic/claude-3-5-haiku-latest
  fallback: ollama/llama3.2
"""

YAML_FLAT = """
default: openai/gpt-4o
tasks:
  readiness_gate: openai/gpt-4o-mini
"""


def test_parses_the_llm_section():
    routing = load_routing(YAML_NESTED)

    assert routing.default == "anthropic/claude-3-5-sonnet-latest"
    assert routing.model_for_task("readiness_gate") == "anthropic/claude-3-5-haiku-latest"
    assert routing.fallback == "ollama/llama3.2"


def test_parses_top_level_routing_too():
    routing = load_routing(YAML_FLAT)

    assert routing.default == "openai/gpt-4o"
    assert routing.model_for_task("readiness_gate") == "openai/gpt-4o-mini"


def test_unknown_task_falls_back_to_default():
    routing = RoutingConfig(default="anthropic/x", tasks={"a": "y"})

    assert routing.model_for_task("nao_existe") == "anthropic/x"


def test_missing_default_is_rejected():
    with pytest.raises(ConfigError):
        load_routing("llm:\n  tasks:\n    a: b\n")


def test_non_mapping_is_rejected():
    with pytest.raises(ConfigError):
        load_routing("- isto\n- é uma lista\n")


def test_invalid_yaml_syntax_is_rejected():
    with pytest.raises(ConfigError):
        load_routing("llm: [não fechado\n")


def test_llm_section_must_be_a_mapping():
    with pytest.raises(ConfigError):
        load_routing("llm: isto-nao-e-um-mapa\n")


def test_config_has_no_field_that_could_hold_a_secret():
    """Métrica 3: uma key nunca pode morar no arquivo de config."""
    fields = set(RoutingConfig.model_fields)

    assert "key" not in " ".join(fields).lower()
    assert "password" not in " ".join(fields).lower()
    assert "token" not in " ".join(fields).lower()


def test_extra_keys_are_forbidden_so_a_stray_api_key_is_caught():
    with pytest.raises(ConfigError):
        load_routing("llm:\n  default: anthropic/x\n  api_key: sk-leaked\n")
