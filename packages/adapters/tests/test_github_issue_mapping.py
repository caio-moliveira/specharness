"""GitHub issue JSON -> WorkItem mapping (SPEC-008, critério 1, fidelidade)."""

from __future__ import annotations

from specharness_adapters.github_issues import work_item_from_issue


def test_labels_assignees_and_other_fields_are_preserved_in_extras():
    issue = {
        "number": 7,
        "title": "Bug",
        "state": "open",
        "milestone": {"title": "Sprint 2"},
        "html_url": "https://github.com/acme/tool/issues/7",
        "labels": [{"name": "bug"}, {"name": "p1"}],
        "assignees": [{"login": "ana"}, {"login": "bob"}],
        "body": "descrição",
        "comments": 3,
    }

    item = work_item_from_issue(issue)

    assert item.sprint == "Sprint 2"
    assert item.url == "https://github.com/acme/tool/issues/7"
    assert item.extras["labels"] == ["bug", "p1"]
    assert item.extras["assignees"] == ["ana", "bob"]
    assert item.extras["body"] == "descrição"  # campo sem equivalente, preservado
    assert item.extras["comments"] == 3
    # os canônicos não são duplicados em extras
    assert "title" not in item.extras
    assert "milestone" not in item.extras


def test_missing_fields_are_explicitly_null_never_invented():
    item = work_item_from_issue({"number": 9})

    assert item.external_id == "9"
    assert item.title == ""
    assert item.state == ""
    assert item.sprint is None
    assert item.url is None
    assert item.extras["labels"] == []
    assert item.extras["assignees"] == []


def test_plain_string_labels_are_handled():
    item = work_item_from_issue({"number": 1, "labels": ["bug", "urgent"]})

    assert item.extras["labels"] == ["bug", "urgent"]
