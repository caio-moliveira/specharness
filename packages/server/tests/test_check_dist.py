"""Testa o gate de artefato da SPEC-021 (scripts/check_dist.py)."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

_PATH = Path(__file__).resolve().parents[3] / "scripts" / "check_dist.py"
_spec = importlib.util.spec_from_file_location("check_dist", _PATH)
assert _spec and _spec.loader
check_dist = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_dist)


def _wheel(path: Path, arcnames: list[str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name in arcnames:
            zf.writestr(name, "x")


def test_passes_when_dashboard_embedded_and_clean(tmp_path):
    _wheel(
        tmp_path / "specharness_server-0.1.0-py3-none-any.whl",
        ["specharness_server/_web/index.html"],
    )
    _wheel(tmp_path / "specharness_core-0.1.0-py3-none-any.whl", ["specharness_core/__init__.py"])
    assert check_dist.main(str(tmp_path)) == 0


def test_fails_when_dashboard_missing(tmp_path):
    _wheel(tmp_path / "specharness_server-0.1.0-py3-none-any.whl", ["specharness_server/app.py"])
    assert check_dist.main(str(tmp_path)) == 1


def test_fails_when_secret_present(tmp_path):
    _wheel(
        tmp_path / "specharness_server-0.1.0-py3-none-any.whl",
        ["specharness_server/_web/index.html"],
    )
    _wheel(tmp_path / "specharness_cli-0.1.0-py3-none-any.whl", [".env"])
    assert check_dist.main(str(tmp_path)) == 1


def test_fails_when_no_wheels(tmp_path):
    assert check_dist.main(str(tmp_path)) == 1
