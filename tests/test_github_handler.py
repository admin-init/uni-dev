"""Tests for webhooks/github_handler.py — GitHub webhook processing."""

import hashlib
import hmac

from uni_dev.webhooks.github_handler import (
    extract_issue,
    handle_event,
    validate_signature,
)


def test_validate_signature_valid():
    """Valid signature returns True."""
    secret = "test-secret"
    payload = b'{"test": true}'
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    signature = f"sha256={expected}"
    assert validate_signature(payload, signature, secret) is True


def test_validate_signature_invalid():
    """Invalid signature returns False."""
    secret = "test-secret"
    payload = b'{"test": true}'
    assert validate_signature(payload, "sha256=wrong", secret) is False


def test_validate_signature_no_secret():
    """Without secret, validation is skipped (returns True)."""
    assert validate_signature(b"payload", "anything", "") is True


def test_validate_signature_no_signature():
    """Without signature header, returns False."""
    assert validate_signature(b"payload", "", "secret") is False


def test_extract_issue_opened():
    """Extracts issue data from opened issue payload."""
    body = {
        "action": "opened",
        "issue": {
            "title": "Add avatar upload",
            "body": "We need avatar upload support",
            "number": 42,
            "html_url": "https://github.com/owner/repo/issues/42",
        },
        "sender": {"login": "devuser"},
        "repository": {"full_name": "owner/repo"},
    }
    result = extract_issue(body)
    assert result is not None
    assert result["title"] == "Add avatar upload"
    assert result["number"] == 42
    assert result["action"] == "opened"
    assert result["sender"] == "devuser"
    assert result["repo"] == "owner/repo"


def test_extract_issue_no_issue():
    """Returns None when no issue in payload."""
    body = {"action": "ping", "zen": "keep it logically awesome"}
    assert extract_issue(body) is None


def test_extract_issue_empty_body():
    """Issue with no body returns empty string."""
    body = {
        "action": "opened",
        "issue": {"title": "Test", "number": 1, "html_url": "http://example.com"},
        "sender": {"login": "user"},
        "repository": {"full_name": "r/r"},
    }
    result = extract_issue(body)
    assert result is not None
    assert result["body"] == ""


def test_handle_event_issue():
    """Handles issue event correctly."""
    body = {
        "action": "opened",
        "issue": {
            "title": "Test issue",
            "body": "Description",
            "number": 1,
            "html_url": "http://example.com/1",
        },
        "sender": {"login": "user"},
        "repository": {"full_name": "a/b"},
    }
    result = handle_event(body)
    assert result["status"] == "accepted"
    assert result["event_type"] == "issue"
    assert result["issue"]["title"] == "Test issue"


def test_handle_event_pull_request():
    """Handles PR event correctly."""
    body = {
        "action": "opened",
        "pull_request": {"title": "PR title", "number": 5},
        "issue": {
            "title": "PR issue",
            "body": "PR desc",
            "number": 5,
            "html_url": "http://example.com/5",
        },
        "sender": {"login": "dev"},
        "repository": {"full_name": "a/b"},
    }
    result = handle_event(body)
    assert result["status"] == "accepted"
    assert result["event_type"] == "pull_request"


def test_handle_event_skips_no_issue():
    """Non-issue events are skipped."""
    body = {"action": "ping", "zen": "hello"}
    result = handle_event(body)
    assert result["status"] == "skipped"
