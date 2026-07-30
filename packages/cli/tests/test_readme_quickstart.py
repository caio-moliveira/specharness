"""O quickstart do README declara o requisito de LLM (SPEC-030, ADR-006).

O requisito é cobrado cedo: quem lê os Requirements descobre que precisa de
uma API key ou de um Ollama local antes de rodar o primeiro comando.
"""

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[3] / "README.md"


def test_quickstart_requirements_declare_the_llm_requirement():
    text = README.read_text(encoding="utf-8")
    requirements = text[text.index("Requirements:") : text.index("```bash")]
    assert "API key" in requirements
    assert "Ollama" in requirements
    assert "ADR-006" in requirements


def test_quickstart_commands_are_copy_paste_executable():
    text = README.read_text(encoding="utf-8")
    requirements = text[text.index("Requirements:") : text.index("```bash")]
    commands = text[text.index("```bash") : text.index("```", text.index("```bash") + 3)]
    assert "<org>" not in commands
    assert "git clone https://github.com/caio-moliveira/specharness" in commands
    assert "uv tool install rust-just" in requirements
    assert "Node" in requirements
