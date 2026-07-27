"""The tiny Gherkin parser (SPEC-010)."""

from __future__ import annotations

from specharness_core import parse_feature

BLOCK = """# language: pt
Funcionalidade: exemplo

  Cenário: primeiro
    Dado um contexto
    Quando algo acontece
    Então um resultado

  Cenário: segundo
    Dado x
    Quando y
    E z
    Então w
"""


def test_parses_language_and_scenarios():
    feature = parse_feature(BLOCK)

    assert feature.language == "pt"
    assert [s.title for s in feature.scenarios] == ["primeiro", "segundo"]


def test_counts_exactly_one_when():
    feature = parse_feature(BLOCK)

    assert len(feature.scenarios[0].when_steps) == 1
    assert "acontece" in feature.scenarios[0].step_text


def test_two_whens_are_visible():
    block = "Funcionalidade: x\n\n  Cenário: c\n    Quando a\n    Quando b\n    Então r\n"

    feature = parse_feature(block)

    assert len(feature.scenarios[0].when_steps) == 2


def test_e_and_mas_are_not_mistaken_for_a_step_keyword():
    block = "Funcionalidade: x\n\n  Cenário: c\n    Dado a\n    E b\n    Mas c\n    Então r\n"

    feature = parse_feature(block)

    assert [s.keyword for s in feature.scenarios[0].steps] == ["Dado", "E", "Mas", "Então"]


def test_entao_without_accent_normalizes():
    feature = parse_feature("Cenário: c\n    Quando a\n    Entao r\n")

    assert feature.scenarios[0].steps[-1].keyword == "Então"


def test_a_block_without_language_reports_none():
    feature = parse_feature("Funcionalidade: x\n\n  Cenário: c\n    Quando a\n    Então r\n")

    assert feature.language is None


def test_a_non_step_line_inside_a_scenario_is_ignored():
    block = "Cenário: c\n    Quando a\n    isto não é um passo\n    Então r\n"

    feature = parse_feature(block)

    assert [s.keyword for s in feature.scenarios[0].steps] == ["Quando", "Então"]
