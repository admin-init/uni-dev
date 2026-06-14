"""Tests for webhooks/codeberg_handler.py — Codeberg webhook processing."""

import hashlib
import hmac

from uni_dev.webhooks.codeberg_handler import (
    extract_issue,
    handle_event,
    validate_signature,
)


def test_validate_signature_valid():
    """Valid signature returns True."""
    secret = "test-secret"
    payload = b'{"test": true}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert validate_signature(payload, expected, secret) is True


def test_validate_signature_invalid():
    """Invalid signature returns False."""
    secret = "test-secret"
    payload = b'{"test": true}'
    assert validate_signature(payload, "wronghash", secret) is False


def test_validate_signature_no_secret():
    """Without secret, validation is skipped (returns True)."""
    assert validate_signature(b"payload", "anything", "") is True


def test_validate_signature_no_signature():
    """Without signature header, returns False."""
    assert validate_signature(b"payload", "", "secret") is False


def test_extract_issue():
    """Extracts issue data from Codeberg payload."""
    body = {
        "action": "opened",
        "issue": {
            "title": "Fix login bug",
            "body": "Users cannot login with OAuth",
            "number": 15,
            "html_url": "https://codeberg.org/owner/repo/issues/15",
        },
        "sender": {"username": "coder123"},
        "repository": {"full_name": "owner/repo"},
    }
    result = extract_issue(body)
    assert result is not None
    assert result["title"] == "Fix login bug"
    assert result["number"] == 15
    assert result["sender"] == "coder123"


def test_extract_issue_fallback_sender():
    """Uses login when username is not available."""
    body = {
        "action": "opened",
        "issue": {
            "title": "Test",
            "body": "Desc",
            "number": 1,
            "html_url": "http://example.com/1",
        },
        "sender": {"login": "ghuser"},
        "repository": {"full_name": "a/b"},
    }
    result = extract_issue(body)
    assert result is not None
    assert result["sender"] == "ghuser"


def test_extract_issue_no_issue():
    """Returns None when no issue in payload."""
    body = {"action": "ping"}
    assert extract_issue(body) is None


def test_handle_event():
    """Handles Codeberg event correctly."""
    body = {
        "action": "opened",
        "issue": {
            "title": "New feature",
            "body": "Please add X",
            "number": 3,
            "html_url": "http://example.com/3",
        },
        "sender": {"username": "dev"},
        "repository": {"full_name": "a/b"},
    }
    result = handle_event(body)
    assert result["status"] == "accepted"
    assert result["event_type"] == "issue"
    assert result["issue"]["title"] == "New feature"
