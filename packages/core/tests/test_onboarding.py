"""Lógica pura do `specharness init` (SPEC-022)."""

from __future__ import annotations

import itertools

import pytest
from specharness_core.config import load_routing
from specharness_core.onboarding import (
    CATEGORIES,
    OPTIONS,
    InvalidSelection,
    Selections,
    env_vars_for,
    render_config,
)


def _sel(**overrides: str) -> Selections:
    base = {
        "tracker": "jira",
        "git": "github",
        "db": "postgres",
        "agent": "claude-code",
        "llm": "anthropic",
    }
    base.update(overrides)
    return Selections(**base)


def test_env_vars_for_lists_selected_service_credentials():
    assert env_vars_for(_sel()) == [
        "JIRA_URL",
        "JIRA_EMAIL",
        "JIRA_TOKEN",
        "GITHUB_TOKEN",
        "SPECHARNESS_DATABASE_URL",
        "ANTHROPIC_API_KEY",
    ]


def test_env_vars_dedup_shared_github_token():
    names = env_vars_for(_sel(tracker="github-issues", git="github"))
    assert names.count("GITHUB_TOKEN") == 1


def test_sqlite_needs_no_database_url():
    assert "SPECHARNESS_DATABASE_URL" not in env_vars_for(_sel(db="sqlite"))


def test_render_config_is_valid_and_hides_secret_names():
    text = render_config(_sel(llm="anthropic"))
    load_routing(text)  # não levanta => yaml válido (llm.default presente)
    assert "anthropic/claude-sonnet-4-6" in text
    for name in env_vars_for(_sel()):
        assert name not in text  # nome de credencial nunca entra no yaml


def test_render_config_is_idempotent():
    sel = _sel()
    assert render_config(sel) == render_config(sel)


def test_invalid_selection_is_rejected():
    with pytest.raises(InvalidSelection):
        _sel(tracker="asana")


def test_no_credential_name_in_yaml_for_any_combination():
    # A métrica "0 segredo no yaml" vale para QUALQUER combinação, não uma só.
    for combo in itertools.product(*(OPTIONS[category] for category in CATEGORIES)):
        selections = Selections(**dict(zip(CATEGORIES, combo, strict=True)))
        text = render_config(selections)
        for name in env_vars_for(selections):
            assert name not in text
