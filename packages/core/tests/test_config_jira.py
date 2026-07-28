"""`jira:` section of specharness.yaml (SPEC-019).

Locks the same guarantees the tracker section has: no credential ever lives in
the file (extra="forbid" catches a pasted token), a missing section is "not
configured" rather than an error, and malformed YAML is an actionable
ConfigError.
"""

from __future__ import annotations

import pytest
from specharness_core.config import ConfigError, load_jira


def test_missing_section_means_not_configured():
    config = load_jira("llm:\n  default: x\n")
    assert config.project is None
    assert config.status_map == {}


def test_project_and_status_map_parse():
    config = load_jira("jira:\n  project: KAN\n  status_map:\n    done: Done\n")
    assert config.project == "KAN"
    assert config.status_map == {"done": "Done"}


def test_a_pasted_credential_is_rejected():
    with pytest.raises(ConfigError):
        load_jira("jira:\n  project: KAN\n  token: super-secret\n")


def test_non_mapping_section_is_a_config_error():
    with pytest.raises(ConfigError):
        load_jira("jira: nao-e-um-mapa\n")


def test_invalid_yaml_is_a_config_error():
    with pytest.raises(ConfigError):
        load_jira("jira: [unclosed\n")
