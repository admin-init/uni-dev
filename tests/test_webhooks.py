"""Tests for webhooks/server.py — FastAPI webhook server."""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from uni_dev.webhooks.server import create_app


def test_health_endpoint():
    """GET /health returns status ok."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_github_webhook_valid():
    """POST /webhook/github with valid issue payload."""
    app = create_app()
    client = TestClient(app)
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
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/webhook/github", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["issue"]["title"] == "Test issue"


def test_github_webhook_no_issue():
    """POST /webhook/github with non-issue payload."""
    app = create_app()
    client = TestClient(app)
    body = {"action": "ping", "zen": "hello"}
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/webhook/github", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "skipped"


def test_github_webhook_invalid_json():
    """POST /webhook/github with invalid JSON returns 400."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/webhook/github",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


def test_github_webhook_signature_validation():
    """POST /webhook/github with secret set validates signature."""
    import hashlib
    import hmac

    app = create_app()
    client = TestClient(app)
    body = {
        "action": "opened",
        "issue": {
            "title": "Secure",
            "body": "Test",
            "number": 2,
            "html_url": "http://example.com/2",
        },
        "sender": {"login": "user"},
        "repository": {"full_name": "a/b"},
    }
    import json
    payload = json.dumps(body).encode()
    secret = "mysupersecret"
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    with patch.dict(os.environ, {"WEBHOOK_SECRET": secret}):
        response = client.post(
            "/webhook/github",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": f"sha256={sig}",
            },
        )
    assert response.status_code == 200


def test_github_webhook_bad_signature():
    """POST /webhook/github with wrong signature returns 401."""
    app = create_app()
    client = TestClient(app)

    with patch.dict(os.environ, {"WEBHOOK_SECRET": "secret"}):
        response = client.post(
            "/webhook/github",
            json={"test": True},
            headers={"X-Hub-Signature-256": "sha256=wronghash"},
        )
    assert response.status_code == 401


def test_codeberg_webhook_valid():
    """POST /webhook/codeberg with valid issue payload."""
    app = create_app()
    client = TestClient(app)
    body = {
        "action": "opened",
        "issue": {
            "title": "Codeberg issue",
            "body": "Codeberg desc",
            "number": 5,
            "html_url": "http://codeberg.example.com/5",
        },
        "sender": {"username": "cbuser"},
        "repository": {"full_name": "cb/repo"},
    }
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/webhook/codeberg", json=body)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["issue"]["title"] == "Codeberg issue"
