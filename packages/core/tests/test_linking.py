"""Commit <-> spec linking decisions (SPEC-009, todos os critérios)."""

from __future__ import annotations

from datetime import datetime

from specharness_core import SpecInfo, link_commits
from specharness_core.ports.repository import Commit


def _commit(sha, trailers=()):
    return Commit(
        sha=sha,
        author="Ana",
        authored_at=datetime(2026, 7, 27),
        message="m",
        spec_trailers=trailers,
    )


def _spec(spec_id, status="in_progress", sprint="2026-A2"):
    return SpecInfo(spec_id=spec_id, status=status, sprint=sprint)


# --- A1: trailer válido cria o vínculo -------------------------------------


def test_valid_trailer_creates_a_link():
    result = link_commits([_commit("a", ("SPEC-042",))], [_spec("SPEC-042")])

    assert len(result.valid_links) == 1
    assert result.valid_links[0].commit_sha == "a"
    assert result.valid_links[0].spec_id == "SPEC-042"


# --- A2: trailer para spec inexistente é sinalizado, não ignorado ----------


def test_trailer_for_a_nonexistent_spec_is_flagged_invalid():
    result = link_commits([_commit("a", ("SPEC-999",))], [_spec("SPEC-042")])

    assert len(result.invalid_links) == 1
    assert result.invalid_links[0].spec_id == "SPEC-999"
    assert result.invalid_links[0].valid is False
    assert len(result.links) == 1  # aparece nos links, não é descartado


def test_a_malformed_trailer_is_invalid_not_ignored():
    result = link_commits([_commit("a", ("lixo",))], [_spec("SPEC-042")])

    assert len(result.invalid_links) == 1
    assert result.invalid_links[0].spec_id == "lixo"


# --- A3: commit sem trailer vira órfão -------------------------------------


def test_commit_without_a_trailer_is_orphan():
    result = link_commits([_commit("a", ())], [_spec("SPEC-042")])

    assert result.orphan_commits == ("a",)
    assert result.links == ()


# --- A4: spec in_progress sem vínculo vira órfã ----------------------------


def test_an_in_progress_spec_without_a_link_is_orphan():
    result = link_commits([], [_spec("SPEC-042", status="in_progress")])

    assert result.orphan_specs == ("SPEC-042",)


def test_a_linked_in_progress_spec_is_not_orphan():
    result = link_commits([_commit("a", ("SPEC-042",))], [_spec("SPEC-042", status="in_progress")])

    assert result.orphan_specs == ()


def test_non_in_progress_specs_are_never_orphans():
    result = link_commits([], [_spec("SPEC-001", status="done"), _spec("SPEC-002", status="draft")])

    assert result.orphan_specs == ()


def test_a_spec_linked_only_by_an_invalid_trailer_is_still_orphan():
    result = link_commits([_commit("a", ("SPEC-999",))], [_spec("SPEC-042", status="in_progress")])

    assert "SPEC-042" in result.orphan_specs


# --- A5: múltiplos trailers geram múltiplos vínculos -----------------------


def test_multiple_trailers_create_multiple_links():
    result = link_commits(
        [_commit("a", ("SPEC-010", "SPEC-011"))], [_spec("SPEC-010"), _spec("SPEC-011")]
    )

    assert len(result.valid_links) == 2
    assert {link.spec_id for link in result.valid_links} == {"SPEC-010", "SPEC-011"}


# --- higiene ---------------------------------------------------------------


def test_is_clean_only_without_invalid_links_or_orphans():
    clean = link_commits([_commit("a", ("SPEC-042",))], [_spec("SPEC-042")])
    assert clean.is_clean is True

    dirty = link_commits([_commit("a", ())], [_spec("SPEC-042")])
    assert dirty.is_clean is False
