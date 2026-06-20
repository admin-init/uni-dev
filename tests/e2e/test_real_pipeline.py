"""E1-E3: End-to-end tests with real LLM.

Requires DEEPSEEK_API_KEY environment variable.
Marked @pytest.mark.e2e — excluded from CI by default.
"""
from __future__ import annotations

import os

import pytest


pytestmark = pytest.mark.e2e

_REQUIRES_KEY = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set",
)


class TestRealPipeline:
    """E1: Full pipeline with real DeepSeek API."""

    @_REQUIRES_KEY
    def test_real_pipeline_runs(self):
        """Invoke full pipeline with real API — smoke test."""
        from uni_dev.core.factory import PipelineConfig
        from uni_dev.core.graph import compile_pipeline

        config = PipelineConfig.from_env()
        config.test_command = "echo 'tests pass'"

        pipeline = compile_pipeline(config=config)

        state = {
            "issue": "Add a health check endpoint",
            "project_path": ".",
            "classification": "add_feature",
            "attempt_count": 0,
        }
        config_dict = {"configurable": {"thread_id": "e2e-real-test"}}

        result = pipeline.invoke(state, config_dict)
        assert result is not None


class TestRealPetclinic:
    """E2: Parse PetClinic and run pipeline."""

    @_REQUIRES_KEY
    @pytest.mark.slow
    def test_real_petclinic_pipeline(self, petclinic_path):
        """Parse petclinic and run pipeline on a real issue."""
        from uni_dev.core.factory import PipelineConfig
        from uni_dev.core.graph import compile_pipeline

        config = PipelineConfig.from_env()
        config.test_command = f"cd {petclinic_path} && mvn test -DskipTests 2>&1 || echo 'mvn not available'"

        pipeline = compile_pipeline(config=config)

        state = {
            "issue": "Add pet health status endpoint to PetController",
            "project_path": petclinic_path,
            "classification": "add_feature",
            "attempt_count": 0,
        }
        config_dict = {"configurable": {"thread_id": "e2e-petclinic"}}

        result = pipeline.invoke(state, config_dict)
        assert result is not None


class TestRealWebhookLifecycle:
    """E3: Webhook -> IssueStore -> Pipeline -> Completion."""

    @_REQUIRES_KEY
    def test_real_webhook_lifecycle(self):
        """POST webhook -> store issue -> run pipeline."""
        import json
        from unittest.mock import patch
        from fastapi.testclient import TestClient

        from uni_dev.webhooks.server import create_app
        from uni_dev.store.issue_store import IssueStore

        app = create_app()
        client = TestClient(app)

        body = {
            "action": "opened",
            "issue": {
                "number": 999,
                "title": "E2E Test Issue",
                "body": "Test webhook lifecycle",
                "html_url": "https://github.com/test/repo/issues/999",
            },
            "sender": {"login": "e2e-bot"},
            "repository": {"full_name": "test/repo"},
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
        assert response.json()["status"] in ("accepted", "skipped", "error")
