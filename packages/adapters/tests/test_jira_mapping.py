"""Jira -> WorkItem mapping (SPEC-019: tabela de kind, sprint, extras).

Pure mapping: no client, no network. Locks the spec's tables — issuetype→kind,
the sprint disambiguation rule, and the extras policy (flat, payload verbatim,
empty omitted, nothing preenchido discarded).
"""

from __future__ import annotations

import pytest
from specharness_adapters.jira import candidate_sprint, kind_from_issuetype, work_item_from_issue

SPRINT_FIELD = "customfield_10020"


def _issue(key="KAN-1", issuetype="Story", status="To Do", sprints=None, **fields):
    payload = {
        "key": key,
        "fields": {
            "summary": "Uma story",
            "issuetype": {"id": "10001", "name": issuetype},
            "status": {"id": "1", "name": status},
            **({SPRINT_FIELD: sprints} if sprints is not None else {}),
            **fields,
        },
    }
    return payload


# --- tabela issuetype -> kind (critério 1) ----------------------------------


@pytest.mark.parametrize(
    ("issuetype", "kind"),
    [
        ("Epic", "epic"),
        ("Story", "story"),
        ("Task", "task"),
        ("Bug", "bug"),
        ("Sub-task", "subtask"),
        ("Subtask", "subtask"),
        ("EPIC", "epic"),  # caso-insensível
        ("Incident", "incident"),  # fora da tabela: nome nativo em minúsculas
    ],
)
def test_issuetype_maps_to_canonical_kind(issuetype, kind):
    assert kind_from_issuetype(issuetype) == kind


def test_canonical_fields_and_ref():
    item = work_item_from_issue(_issue(key="KAN-7", status="In Progress"), "https://j.ex", None)

    assert item.origin == "jira"
    assert item.external_id == "KAN-7"
    assert item.kind == "story"
    assert item.title == "Uma story"
    assert item.state == "In Progress"  # status.name bruto, sem normalização
    assert item.url == "https://j.ex/browse/KAN-7"
    assert item.ref == "jira:story:KAN-7"


# --- regra de sprint candidata (critérios 1 e 2) ----------------------------


def test_first_active_sprint_wins():
    sprints = [
        {"id": 3, "name": "Sprint 3", "state": "future"},
        {"id": 1, "name": "Sprint 1", "state": "active"},
        {"id": 2, "name": "Sprint 2", "state": "active"},
    ]
    assert candidate_sprint(sprints) == "Sprint 1"


def test_without_active_the_highest_id_future_wins():
    sprints = [
        {"id": 1, "name": "Sprint 1", "state": "closed"},
        {"id": 5, "name": "Sprint 5", "state": "future"},
        {"id": 3, "name": "Sprint 3", "state": "future"},
    ]
    assert candidate_sprint(sprints) == "Sprint 5"


def test_issue_without_sprint_is_backlog():
    assert candidate_sprint(None) is None
    assert candidate_sprint([]) is None
    assert candidate_sprint([{"id": 1, "name": "S1", "state": "closed"}]) is None


def test_sprint_field_flows_into_the_workitem():
    sprints = [{"id": 1, "name": "Sprint A", "state": "active"}]
    item = work_item_from_issue(_issue(sprints=sprints), "https://j.ex", SPRINT_FIELD)
    assert item.sprint == "Sprint A"


def test_without_a_sprint_field_the_sprint_is_null():
    item = work_item_from_issue(_issue(), "https://j.ex", None)
    assert item.sprint is None


# --- extras: flat, verbatim, vazios omitidos (critério 3, métrica 3) --------


def test_filled_noncanonical_fields_are_preserved_flat():
    item = work_item_from_issue(
        _issue(
            labels=["backend", "urgente"],
            components=[{"id": "1", "name": "api"}],
            customfield_10050="valor livre",
        ),
        "https://j.ex",
        None,
    )

    assert item.extras["labels"] == ["backend", "urgente"]
    assert item.extras["components"] == [{"id": "1", "name": "api"}]
    assert item.extras["customfield_10050"] == "valor livre"


def test_assignee_is_preserved_as_the_payload_object():
    assignee = {"accountId": "abc123", "displayName": "Alguém"}
    item = work_item_from_issue(_issue(assignee=assignee), "https://j.ex", None)
    assert item.extras["assignee"] == assignee


def test_empty_fields_are_omitted_from_extras():
    item = work_item_from_issue(
        _issue(assignee=None, labels=[], components=[], description=""),
        "https://j.ex",
        None,
    )
    for key in ("assignee", "labels", "components", "description"):
        assert key not in item.extras


def test_canonical_and_sprint_fields_do_not_leak_into_extras():
    sprints = [{"id": 1, "name": "S", "state": "active"}]
    item = work_item_from_issue(_issue(sprints=sprints), "https://j.ex", SPRINT_FIELD)
    for key in ("summary", "issuetype", "status", SPRINT_FIELD):
        assert key not in item.extras
