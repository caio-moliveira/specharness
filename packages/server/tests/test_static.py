"""Servir o dashboard compilado pela API, sem sombrear a API (SPEC-021)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from specharness_server.static import dashboard_dir, mount_dashboard


def _app_with_api() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_root_serves_dashboard_when_built(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<html>specharness dash</html>", encoding="utf-8")
    monkeypatch.setenv("SPECHARNESS_WEB_DIST", str(tmp_path))

    app = _app_with_api()
    mount_dashboard(app)
    client = TestClient(app)

    # A API continua respondendo — o mount em "/" não a sombreia.
    assert client.get("/health").json() == {"status": "ok"}
    root = client.get("/")
    assert root.status_code == 200
    assert "specharness dash" in root.text


def test_root_gives_hint_when_not_built(tmp_path, monkeypatch):
    # override aponta para um diretório sem index.html; cwd sem web/dist.
    monkeypatch.setenv("SPECHARNESS_WEB_DIST", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    assert dashboard_dir() is None

    app = _app_with_api()
    mount_dashboard(app)
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert "/docs" in root.text  # orientação, não 404 seco
    assert client.get("/health").json() == {"status": "ok"}
