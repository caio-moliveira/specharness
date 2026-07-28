"""Seed data for the read-only dashboard (SPEC-016, acceptance[3]).

The whole point: a frontend contributor runs the dashboard with no external
connection. `seed` migrates the database and inserts one representative sprint —
a metrics snapshot, perception samples and commits — so every view has something
real to show. It only writes to an empty database, so re-running is safe.
"""

from __future__ import annotations

from datetime import UTC, datetime

from specharness_adapters.db import (
    MetricSnapshotStore,
    PerceptionStore,
    RepositoryStore,
    SqlAlchemyDatabaseGateway,
)
from specharness_core import PerceptionSample, SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DatabaseTarget
from specharness_core.ports.repository import Commit, PullRequest

SEED_SPRINT = "2026-A4"


def seed(target: DatabaseTarget, *, at: datetime | None = None) -> bool:
    """Populate an empty database with one representative sprint. Returns True if seeded."""
    stamp = at or datetime(2026, 7, 27, tzinfo=UTC)
    SqlAlchemyDatabaseGateway(target).migrate()

    snapshot_store = MetricSnapshotStore(target)
    if snapshot_store.latest(SEED_SPRINT) is not None:
        return False  # already seeded — leave it be

    snapshot_store.record(
        SprintSnapshot(
            SEED_SPRINT,
            (
                SpecMetrics("SPEC-013", 288000.0, 0.9, 2, 0.08, 0.16, 0.9, 1.4, commits=8),
                SpecMetrics("SPEC-014", 172800.0, 1.0, 1, 0.03, 0.05, 0.4, 0.6, commits=5),
                SpecMetrics("SPEC-015", None, None, None, None, None, None, None, commits=0),
            ),
        ),
        stamp,
    )

    perception = PerceptionStore(target)
    perception.record_sample(
        PerceptionSample(
            "caio-moliveira/specharness#11",
            "SPEC-013",
            SEED_SPRINT,
            "Claude Code",
            "claude-opus",
            5,
            "leve",
            "economizou",
            "fluiu bem",
        ),
        stamp,
    )
    perception.record_sample(
        PerceptionSample(
            "caio-moliveira/specharness#12",
            "SPEC-014",
            SEED_SPRINT,
            "Claude Code",
            "claude-opus",
            4,
            "nenhum",
            "neutro",
        ),
        stamp,
    )
    perception.record_skip(
        "caio-moliveira/specharness#13",
        "SPEC-015",
        SEED_SPRINT,
        "Claude Code",
        "claude-opus",
        stamp,
    )

    RepositoryStore(target).sync(
        "caio-moliveira/specharness",
        [
            Commit("a1", "Caio", stamp, "feat: metrics\n\nSpec: SPEC-013", ("SPEC-013",)),
            Commit("b2", "Caio", stamp, "feat: survey\n\nSpec: SPEC-014", ("SPEC-014",)),
            Commit("c3", "Caio", stamp, "chore: sem trailer", ()),  # órfão: alerta de higiene
        ],
        [PullRequest(11, "SPEC-013", "merged", "spec/013", "main", ("a1",))],
    )
    return True


def main() -> None:  # pragma: no cover - thin CLI wrapper over seed()
    import sys

    from specharness_adapters.db import gateway_from_env

    # Consoles Windows padrão usam cp1252: sem isto o ✓ abaixo estoura
    # UnicodeEncodeError (mesmo guard da CLI e dos scripts do repo).
    encoding = (getattr(sys.stdout, "encoding", "") or "").replace("-", "").lower()
    if encoding != "utf8" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    seeded = seed(gateway_from_env().target)
    print("✓ seed data carregado." if seeded else "• banco já tinha seed — nada a fazer.")


if __name__ == "__main__":  # pragma: no cover
    main()
