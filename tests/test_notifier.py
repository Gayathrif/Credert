"""tests/test_notifier.py - Unit tests for notifier.py."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import notifier


def test_build_ack_url_default(monkeypatch):
    monkeypatch.delenv("CREDERT_BASE_URL", raising=False)
    url = notifier._build_ack_url("mytoken")
    assert url == "http://localhost:5000/acknowledge/mytoken"


def test_build_ack_url_custom(monkeypatch):
    monkeypatch.setenv("CREDERT_BASE_URL", "https://credert.example.com")
    url = notifier._build_ack_url("tok123")
    assert url == "https://credert.example.com/acknowledge/tok123"


def test_send_alert_prints(capsys, monkeypatch):
    monkeypatch.delenv("TWILIO_WHATSAPP_TO", raising=False)
    notifier.send_alert("https://example.com", "token1")
    out = capsys.readouterr().out
    assert "ALERT" in out
    assert "https://example.com" in out
    assert "token1" in out


def test_send_reminder_prints(capsys, monkeypatch):
    monkeypatch.delenv("TWILIO_WHATSAPP_TO", raising=False)
    notifier.send_reminder("https://example.com", "token2")
    out = capsys.readouterr().out
    assert "REMINDER" in out
    assert "https://example.com" in out


def test_whatsapp_skipped_without_credentials(monkeypatch):
    """_send_whatsapp should silently skip when env vars are unset."""
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_WHATSAPP_TO", raising=False)
    # Should not raise
    notifier._send_whatsapp("test message")
