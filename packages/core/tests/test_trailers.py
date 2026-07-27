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


# --- paridade com git (SPEC-009, ADR-011): bloco final = 100% trailers -----


def test_a_prose_line_in_the_final_block_means_no_trailer():
    # git interpret-trailers vê ∅ aqui, então o parser puro também
    assert extract_spec_trailers("feat: x\n\nUm corpo de texto.\nSpec: SPEC-042") == []


def test_a_subject_only_message_has_no_trailer():
    assert extract_spec_trailers("Spec: SPEC-042") == []


def test_a_non_trailer_line_after_the_trailer_voids_the_block():
    assert extract_spec_trailers("feat: x\n\nSpec: SPEC-042\nmais corpo") == []


def test_a_pseudo_trailer_line_keeps_the_block_valid():
    # "See:" é trailer-formatado, então o bloco segue válido (como no git)
    assert extract_spec_trailers("feat: x\n\nSee: algo\nSpec: SPEC-042") == ["SPEC-042"]


def test_a_continuation_line_with_no_trailer_before_voids_the_block():
    assert extract_spec_trailers("feat: x\n\n  continuação solta\nSpec: SPEC-042") == []


def test_a_continuation_after_a_trailer_keeps_the_block_valid():
    # linha continuada de um trailer anterior não invalida o bloco (como no git)
    msg = "feat: x\n\nCo-Authored-By: Alguém\n  linha continuada\nSpec: SPEC-042"
    assert extract_spec_trailers(msg) == ["SPEC-042"]
