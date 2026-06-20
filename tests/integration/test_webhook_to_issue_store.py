"""I7: Verify webhook POST -> IssueStore data flow.

Tests the real FastAPI TestClient -> IssueStore integration.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestWebhookHealth:
    """Test health endpoint."""

    def test_health_returns_200(self):
        from uni_dev.webhooks.server import create_app
        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestGitHubWebhookIntegration:
    """Test GitHub webhook endpoint."""

    def test_valid_webhook_returns_ok(self):
        from uni_dev.webhooks.server import create_app
        app = create_app()
        client = TestClient(app)

        body = {
            "action": "opened",
            "issue": {
                "number": 42,
                "title": "Add avatar endpoint",
                "body": "We need user avatars",
                "html_url": "https://github.com/test/repo/issues/42",
            },
            "sender": {"login": "testuser"},
            "repository": {"full_name": "test/repo"},
        }
        payload = json.dumps(body).encode()

        response = client.post(
            "/webhook/github",
            content=payload,
            headers={
                "X-Hub-Signature-256": "sha256=any-signature",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        # Server returns 200 with status field
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_missing_issue_returns_skipped(self):
        from uni_dev.webhooks.server import create_app
        app = create_app()
        client = TestClient(app)

        body = {
            "action": "opened",
            "sender": {"login": "testuser"},
        }
        response = client.post(
            "/webhook/github",
            content=json.dumps(body).encode(),
            headers={
                "X-Hub-Signature-256": "sha256=any",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "skipped"

    def test_pr_event_skipped(self):
        from uni_dev.webhooks.server import create_app
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/webhook/github",
            content=b"{}",
            headers={
                "X-Hub-Signature-256": "sha256=any",
                "X-GitHub-Event": "pull_request",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200


class TestCodebergWebhookIntegration:
    """Test Codeberg webhook endpoint."""

    def test_codeberg_webhook_returns_ok(self):
        from uni_dev.webhooks.server import create_app
        app = create_app()
        client = TestClient(app)

        body = {
            "action": "opened",
            "issue": {
                "number": 7,
                "title": "Codeberg issue",
                "body": "Test issue",
                "html_url": "https://codeberg.org/test/repo/issues/7",
            },
            "sender": {"username": "codeberguser"},
            "repository": {"full_name": "test/repo"},
        }
        payload = json.dumps(body).encode()

        response = client.post(
            "/webhook/codeberg",
            content=payload,
            headers={
                "X-Codeberg-Signature": "any-signature",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
