"""Redmine JSON -> WorkItem mapping (SPEC-007, critério 3, métrica 2)."""

from __future__ import annotations

from specharness_adapters.redmine import work_item_from_issue, work_item_from_version


def test_fields_without_a_canonical_home_go_to_extras():
    issue = {
        "id": 7,
        "subject": "S",
        "status": {"id": 2, "name": "In Progress"},
        "priority": {"id": 4, "name": "Alta"},
        "author": {"name": "Ana"},
        "custom_fields": [{"name": "Órgão", "value": "TCE"}],
        "created_on": "2026-07-01",
    }

    item = work_item_from_issue(issue, "https://r.ex")

    assert item.state == "In Progress"
    for preserved in ("priority", "author", "custom_fields", "created_on"):
        assert preserved in item.extras
    # os campos canônicos não são duplicados em extras
    assert "subject" not in item.extras
    assert "status" not in item.extras


def test_missing_fields_are_explicitly_null_never_invented():
    item = work_item_from_issue({"id": 8}, "https://r.ex")

    assert item.external_id == "8"
    assert item.title == ""
    assert item.state == ""
    assert item.sprint is None


def test_version_maps_name_status_and_preserves_the_rest():
    version = {"id": 3, "name": "Sprint 3", "status": "closed", "description": "meta"}

    item = work_item_from_version(version, "https://r.ex")

    assert item.kind == "version"
    assert item.title == "Sprint 3"
    assert item.state == "closed"
    assert item.url == "https://r.ex/versions/3"
    assert item.extras["description"] == "meta"
    assert item.sprint is None
