"""tests/test_database.py - Unit tests for database.py."""

import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Override DB_PATH so every test gets a fresh, isolated database."""
    import database as db_module

    db_file = str(tmp_path / "test_credert.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    db_module.init_db()
    yield db_file


def test_init_db_creates_table(tmp_db):
    conn = sqlite3.connect(tmp_db)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='monitored_sites'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_add_site_and_get_all():
    import database as db

    site_id = db.add_site("https://example.com")
    assert isinstance(site_id, int) and site_id > 0

    sites = db.get_all_sites()
    assert len(sites) == 1
    assert sites[0]["url"] == "https://example.com"


def test_add_site_idempotent():
    import database as db

    id1 = db.add_site("https://example.com")
    id2 = db.add_site("https://example.com")
    assert id1 == id2
    assert len(db.get_all_sites()) == 1


def test_get_site_by_url():
    import database as db

    db.add_site("https://example.com")
    site = db.get_site_by_url("https://example.com")
    assert site is not None
    assert site["url"] == "https://example.com"
    assert site["status"] == "pending"


def test_get_site_by_url_missing():
    import database as db

    assert db.get_site_by_url("https://does-not-exist.com") is None


def test_update_hash():
    import database as db

    db.add_site("https://example.com")
    db.update_hash("https://example.com", "abc123")
    site = db.get_site_by_url("https://example.com")
    assert site["last_hash"] == "abc123"
    assert site["status"] == "pending"


def test_acknowledge():
    import database as db

    db.add_site("https://example.com")
    site = db.get_site_by_url("https://example.com")
    token = site["ack_token"]
    assert token is not None

    result = db.acknowledge(token)
    assert result is True
    site = db.get_site_by_url("https://example.com")
    assert site["status"] == "done"


def test_acknowledge_invalid_token():
    import database as db

    result = db.acknowledge("no-such-token")
    assert result is False


def test_get_site_by_token():
    import database as db

    db.add_site("https://example.com")
    site = db.get_site_by_url("https://example.com")
    token = site["ack_token"]

    found = db.get_site_by_token(token)
    assert found is not None
    assert found["url"] == "https://example.com"


def test_remove_site():
    import database as db

    db.add_site("https://example.com")
    db.remove_site("https://example.com")
    assert db.get_site_by_url("https://example.com") is None
    assert len(db.get_all_sites()) == 0
