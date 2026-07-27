"""The tracker port's pure decisions (SPEC-007, ADR-007)."""

from __future__ import annotations

import pytest
from specharness_core.ports.tracker import (
    REDMINE_API_KEY_ENV,
    ImportResult,
    InvalidTrackerConfig,
    TrackerAuthenticationFailed,
    WorkItem,
    target_status,
)


def _item(**kw):
    base = dict(origin="redmine", external_id="5", kind="issue", title="t", state="New")
    base.update(kw)
    return WorkItem(**base)


# --- WorkItem.ref: referência externa estável (critério 1) -----------------


def test_ref_is_stable_and_disambiguates_kind():
    issue = _item(external_id="5", kind="issue")
    version = _item(external_id="5", kind="version")

    assert issue.ref == "redmine:issue:5"
    assert version.ref == "redmine:version:5"
    assert issue.ref != version.ref  # mesmo id, kinds distintos, sem colisão


def test_extras_default_to_empty_and_hold_preserved_fields():
    assert _item().extras == {}
    assert _item(extras={"priority": "Alta"}).extras == {"priority": "Alta"}


# --- ImportResult idempotência (métricas 2 e 3) ----------------------------


def test_import_result_is_a_noop_only_when_nothing_changed():
    assert ImportResult(0, 0, 10).was_noop is True
    assert ImportResult(1, 0, 10).was_noop is False
    assert ImportResult(0, 2, 10).was_noop is False


# --- target_status: mapa configurável (critério 2) -------------------------


def test_target_status_resolves_a_mapped_status():
    assert target_status({"done": "Fechada"}, "done") == "Fechada"


def test_an_unmapped_status_is_a_config_error_not_a_guess():
    with pytest.raises(InvalidTrackerConfig) as excinfo:
        target_status({"done": "Fechada"}, "in_progress")

    assert "in_progress" in str(excinfo.value)
    assert "status_map" in str(excinfo.value)


# --- erro de auth cita a env var da key ------------------------------------


def test_auth_error_names_the_api_key_env():
    error = TrackerAuthenticationFailed.for_tracker("https://redmine.exemplo", detail="HTTP 401")

    text = str(error)
    assert REDMINE_API_KEY_ENV in text
    assert "redmine.exemplo" in text
