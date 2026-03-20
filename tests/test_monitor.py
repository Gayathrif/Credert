"""tests/test_monitor.py - Unit tests for monitor.py."""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import monitor


def test_compute_hash_deterministic():
    h1 = monitor.compute_hash("hello world")
    h2 = monitor.compute_hash("hello world")
    assert h1 == h2


def test_compute_hash_changes_with_content():
    assert monitor.compute_hash("foo") != monitor.compute_hash("bar")


def test_compute_hash_is_md5_length():
    # MD5 hex digest is always 32 chars
    assert len(monitor.compute_hash("anything")) == 32


def test_check_for_change_first_time(monkeypatch):
    """When stored_hash is None it should return changed=False and the hash."""
    monkeypatch.setattr(monitor, "fetch_content", lambda url: "<html>content</html>")
    changed, h = monitor.check_for_change("https://example.com", None)
    assert changed is False
    assert len(h) == 32


def test_check_for_change_no_change(monkeypatch):
    content = "<html>same</html>"
    existing_hash = monitor.compute_hash(content)
    monkeypatch.setattr(monitor, "fetch_content", lambda url: content)

    changed, h = monitor.check_for_change("https://example.com", existing_hash)
    assert changed is False
    assert h == existing_hash


def test_check_for_change_detects_change(monkeypatch):
    old_content = "<html>old</html>"
    new_content = "<html>new</html>"
    stored_hash = monitor.compute_hash(old_content)
    monkeypatch.setattr(monitor, "fetch_content", lambda url: new_content)

    changed, h = monitor.check_for_change("https://example.com", stored_hash)
    assert changed is True
    assert h == monitor.compute_hash(new_content)


def test_check_for_change_network_error(monkeypatch):
    """On network failure should return changed=False and preserve stored hash."""

    def raise_error(url):
        raise requests.RequestException("timeout")

    monkeypatch.setattr(monitor, "fetch_content", raise_error)
    stored = "deadbeef" * 4

    changed, h = monitor.check_for_change("https://example.com", stored)
    assert changed is False
    assert h == stored
