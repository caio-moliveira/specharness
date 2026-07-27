"""Golden dataset da narrativa (SPEC-015, success_metric 3).

Cada golden traz uma tabela e uma narrativa; o checker de read-before-cite
(`extract_numbers`) deve classificar a narrativa como fiel ou divergente exatamente
como o frontmatter `expected_faithful` diz. É a validação determinística do
mecanismo — a parte "em todos os modelos suportados" é medida em runtime no CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from specharness_core import extract_numbers

_GOLDEN_DIR = Path(__file__).resolve().parent / "golden_narrative"
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SECTION_RE = re.compile(r"##\s+(\w+).*?```\s*\n(.*?)\n```", re.DOTALL)


def _cases():
    return sorted(_GOLDEN_DIR.glob("*.md"))


def _parse(text: str) -> tuple[bool, str, str]:
    fm = _FRONTMATTER_RE.match(text)
    assert fm is not None, "golden sem frontmatter"
    expected = bool(yaml.safe_load(fm.group(1))["expected_faithful"])
    sections = {m.group(1).lower(): m.group(2) for m in _SECTION_RE.finditer(fm.group(2))}
    return expected, sections["tabela"], sections["narrativa"]


def test_the_golden_directory_is_not_empty():
    assert _cases(), "nenhum golden de narrativa encontrado"


@pytest.mark.parametrize("path", _cases(), ids=lambda p: p.stem)
def test_the_checker_matches_the_golden_verdict(path):
    expected_faithful, tabela, narrativa = _parse(path.read_text(encoding="utf-8"))
    divergences = extract_numbers(narrativa) - extract_numbers(tabela)
    assert (not divergences) is expected_faithful
