"""SQLAlchemy implementation of the database port (SPEC-004, ADR-002/ADR-010).

This is where I/O is allowed. The core decides *which* database; this package
knows how to reach it, migrate it and translate its failures.
"""

from .errors import classify
from .gateway import SqlAlchemyDatabaseGateway, gateway_from_env
from .metrics_store import MetricSnapshotStore
from .models import (
    Base,
    CommitRow,
    MetricSnapshotRow,
    PullRequestCommitRow,
    PullRequestRow,
    ReadinessCacheRow,
    ReadinessOverrideRow,
    ScenarioRunRow,
    SchemaMeta,
    WorkItemRow,
)
from .readiness_store import OverrideStore, ReadinessCacheStore
from .repository_store import RepositoryStore
from .scenario_run_store import ScenarioRunStore
from .workitem_store import WorkItemStore

__all__ = [
    "Base",
    "CommitRow",
    "MetricSnapshotRow",
    "MetricSnapshotStore",
    "OverrideStore",
    "PullRequestCommitRow",
    "PullRequestRow",
    "ReadinessCacheRow",
    "ReadinessCacheStore",
    "ReadinessOverrideRow",
    "RepositoryStore",
    "ScenarioRunRow",
    "ScenarioRunStore",
    "SchemaMeta",
    "WorkItemRow",
    "WorkItemStore",
    "SqlAlchemyDatabaseGateway",
    "classify",
    "gateway_from_env",
]
