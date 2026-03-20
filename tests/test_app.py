"""tests/test_app.py - Integration tests for the Flask API in app.py."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Provide a test Flask client with an isolated database and no scheduler."""
    import database as db_module

    db_file = str(tmp_path / "test_app.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    # Patch create_scheduler so it doesn't start background threads
    import scheduler as sched_module
    from unittest.mock import MagicMock

    fake_scheduler = MagicMock()
    monkeypatch.setattr(sched_module, "create_scheduler", lambda *a, **kw: fake_scheduler)

    import app as app_module

    flask_app = app_module.create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_add_and_list_site(client):
    resp = client.post("/sites", json={"url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["url"] == "https://example.com"

    resp = client.get("/sites")
    assert resp.status_code == 200
    sites = resp.get_json()
    assert len(sites) == 1
    assert sites[0]["url"] == "https://example.com"


def test_add_site_missing_url(client):
    resp = client.post("/sites", json={})
    assert resp.status_code == 400


def test_add_site_no_body(client):
    resp = client.post("/sites", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_delete_site(client):
    client.post("/sites", json={"url": "https://example.com"})
    resp = client.delete("/sites/https://example.com")
    assert resp.status_code == 200

    resp = client.get("/sites")
    assert resp.get_json() == []


def test_acknowledge_valid_token(client):
    import database as db

    client.post("/sites", json={"url": "https://example.com"})
    site = db.get_site_by_url("https://example.com")
    token = site["ack_token"]

    resp = client.get(f"/acknowledge/{token}")
    assert resp.status_code == 200
    assert "acknowledged" in resp.get_json()["message"].lower()

    site = db.get_site_by_url("https://example.com")
    assert site["status"] == "done"


def test_acknowledge_invalid_token(client):
    resp = client.get("/acknowledge/bad-token-xyz")
    assert resp.status_code == 404
