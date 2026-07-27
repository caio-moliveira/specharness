"""SQLAlchemy implementation of the database port (SPEC-004, ADR-002/ADR-010).

This is where I/O is allowed. The core decides *which* database; this package
knows how to reach it, migrate it and translate its failures.
"""

from .errors import classify
from .gateway import SqlAlchemyDatabaseGateway, gateway_from_env
from .models import (
    Base,
    CommitRow,
    PullRequestCommitRow,
    PullRequestRow,
    SchemaMeta,
    WorkItemRow,
)
from .repository_store import RepositoryStore
from .workitem_store import WorkItemStore

__all__ = [
    "Base",
    "CommitRow",
    "PullRequestCommitRow",
    "PullRequestRow",
    "RepositoryStore",
    "SchemaMeta",
    "WorkItemRow",
    "WorkItemStore",
    "SqlAlchemyDatabaseGateway",
    "classify",
    "gateway_from_env",
]
