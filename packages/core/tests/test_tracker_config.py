"""Tracker config parsing (SPEC-007). No secret ever lives here."""

from __future__ import annotations

import pytest
from specharness_core.config import ConfigError, load_tracker


def test_loads_the_tracker_section():
    text = (
        "tracker:\n"
        "  url: https://redmine.exemplo\n"
        "  project: meu-projeto\n"
        "  status_map:\n"
        "    done: Fechada\n"
    )

    config = load_tracker(text)

    assert config.url == "https://redmine.exemplo"
    assert config.project == "meu-projeto"
    assert config.status_map == {"done": "Fechada"}


def test_coexists_with_an_llm_section():
    text = "llm:\n  default: anthropic/x\ntracker:\n  url: https://r.ex\n  project: p\n"

    config = load_tracker(text)

    assert config.url == "https://r.ex"


def test_no_tracker_section_is_an_empty_config_not_an_error():
    config = load_tracker("llm:\n  default: anthropic/x\n")

    assert config.url is None
    assert config.project is None


def test_a_stray_api_key_in_the_file_is_rejected():
    text = "tracker:\n  url: https://r.ex\n  api_key: super-secret\n"

    with pytest.raises(ConfigError):
        load_tracker(text)


def test_a_non_mapping_tracker_section_is_rejected():
    with pytest.raises(ConfigError):
        load_tracker("tracker:\n  - a\n  - b\n")
