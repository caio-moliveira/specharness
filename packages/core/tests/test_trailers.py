"""Tests for the Spec: trailer parser (SPEC-009 groundwork)."""

from specharness_core import extract_spec_trailers, valid_spec_trailers


def test_extracts_single_trailer():
    msg = "feat: busca exata\n\nCorpo da mensagem.\n\nSpec: SPEC-042\n"
    assert extract_spec_trailers(msg) == ["SPEC-042"]


def test_extracts_multiple_trailers():
    msg = "feat: x\n\nSpec: SPEC-001\nSpec: SPEC-002\n"
    assert extract_spec_trailers(msg) == ["SPEC-001", "SPEC-002"]


def test_ignores_trailer_like_text_outside_last_block():
    msg = "feat: x\n\nSpec: SPEC-001 mencionada no corpo.\n\nRefs: none\n"
    assert extract_spec_trailers(msg) == []


def test_no_trailers_in_plain_message():
    assert extract_spec_trailers("chore: bump deps") == []


def test_splits_valid_and_invalid_values():
    msg = "fix: y\n\nSpec: SPEC-010\nSpec: OOPS-1\n"
    valid, invalid = valid_spec_trailers(msg)
    assert valid == ["SPEC-010"]
    assert invalid == ["OOPS-1"]
