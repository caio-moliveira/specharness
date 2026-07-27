"""Readiness Gate threshold config (SPEC-011)."""

from __future__ import annotations

import pytest
from specharness_core.config import ConfigError, ReadinessConfig, load_readiness


def test_default_threshold_is_70():
    assert ReadinessConfig().threshold == 70
    assert load_readiness("llm:\n  default: anthropic/x\n").threshold == 70


def test_reads_the_threshold_from_the_section():
    assert load_readiness("readiness:\n  threshold: 80\n").threshold == 80


def test_coexists_with_other_sections():
    text = "llm:\n  default: anthropic/x\nreadiness:\n  threshold: 75\n"
    assert load_readiness(text).threshold == 75


def test_a_stray_key_is_rejected():
    with pytest.raises(ConfigError):
        load_readiness("readiness:\n  limiar: 80\n")


def test_a_non_mapping_section_is_rejected():
    with pytest.raises(ConfigError):
        load_readiness("readiness:\n  - a\n  - b\n")
