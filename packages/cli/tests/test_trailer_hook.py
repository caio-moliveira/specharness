"""Hook de commit-msg: rejeição ensina o bloco único de trailers (SPEC-032).

O hook roda como subprocesso real — o mesmo caminho do pre-commit — sobre
arquivos de mensagem temporários.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "trailer_check.py"


def _run_hook(message: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    msg_file = tmp_path / "COMMIT_EDITMSG"
    msg_file.write_text(message, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(HOOK), str(msg_file)], capture_output=True, text=True
    )


def test_rejection_teaches_the_single_trailer_block(tmp_path):
    # Spec: separado dos demais trailers por linha em branco — o formato que
    # agentes de código geram e o git NÃO reconhece como trailer.
    proc = _run_hook(
        "feat: x\n\nSpec: SPEC-003\n\nCo-Authored-By: Fulana <f@exemplo.com>\n", tmp_path
    )

    assert proc.returncode == 1
    assert "ÚLTIMO bloco" in proc.stdout
    assert "Co-Authored-By" in proc.stdout  # o exemplo mostra os trailers juntos


def test_single_block_with_multiple_trailers_passes(tmp_path):
    proc = _run_hook(
        "feat: x\n\nSpec: SPEC-003\nCo-Authored-By: Fulana <f@exemplo.com>\n", tmp_path
    )

    assert proc.returncode == 0, proc.stdout


def test_merge_commit_is_exempt(tmp_path):
    proc = _run_hook("Merge pull request #7 from x/y\n", tmp_path)

    assert proc.returncode == 0, proc.stdout
