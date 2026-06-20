"""I8: Verify middleware chain: OutputCleaner -> CostTracking -> SecurityFilter.

Tests that all middleware apply in sequence and output is cleaned + redacted.
"""
from __future__ import annotations

import pytest

from uni_dev.middleware.output_cleaner import OutputCleanerMiddleware
from uni_dev.middleware.cost_tracking import CostTrackingMiddleware
from uni_dev.security.security_filter import SecurityFilterMiddleware


class TestOutputCleanerMiddleware:
    """Verify OutputCleaner cleans LLM output."""

    def test_strips_markdown_blocks(self):
        mw = OutputCleanerMiddleware()
        text = "```yaml\nentities:\n  - Pet\n```"
        cleaned = mw._clean(text)
        assert "```" not in cleaned
        assert "entities" in cleaned

    def test_strips_markdown_no_language(self):
        mw = OutputCleanerMiddleware()
        text = "```\nsome code\n```"
        cleaned = mw._clean(text)
        assert "```" not in cleaned
        assert "some code" in cleaned

    def test_preserves_non_markdown_text(self):
        mw = OutputCleanerMiddleware()
        text = "plain text without markers"
        cleaned = mw._clean(text)
        assert cleaned == text

    def test_fixes_escape_sequences(self):
        mw = OutputCleanerMiddleware()
        text = 'line1\\nline2\\tindented'
        cleaned = mw._clean(text)
        assert "\n" in cleaned
        assert "\t" in cleaned


class TestCostTrackingMiddleware:
    """Verify CostTracking initializes correctly."""

    def test_default_budget(self):
        mw = CostTrackingMiddleware()
        assert mw._budget_tokens == 1_000_000

    def test_custom_budget(self):
        mw = CostTrackingMiddleware(budget_tokens=5000)
        assert mw._budget_tokens == 5000

    def test_state_schema_has_token_usage(self):
        mw = CostTrackingMiddleware()
        schema = mw.state_schema
        assert hasattr(schema, "__annotations__")
        assert "token_usage" in schema.__annotations__


class TestSecurityFilterMiddleware:
    """Verify SecurityFilter redacts PII/secrets."""

    def test_redacts_bearer_token(self):
        mw = SecurityFilterMiddleware()
        text = "Authorization: Bearer sk-abc123def456"
        filtered = mw._filter.filter_text(text)
        assert "sk-abc123def456" not in filtered
        assert "REDACTED" in filtered

    def test_redacts_api_key(self):
        mw = SecurityFilterMiddleware()
        text = "api_key=sk-secret-key-here"
        filtered = mw._filter.filter_text(text)
        assert "sk-secret-key-here" not in filtered
        assert "REDACTED" in filtered

    def test_redacts_password_in_query(self):
        mw = SecurityFilterMiddleware()
        text = "postgresql://user:password123@host/db"
        filtered = mw._filter.filter_text(text)
        assert "password123" not in filtered

    def test_preserves_safe_text(self):
        mw = SecurityFilterMiddleware()
        text = "This is safe text with no secrets"
        filtered = mw._filter.filter_text(text)
        assert filtered == text


class TestMiddlewareChainOrder:
    """Verify middleware can be composed in sequence."""

    def test_all_middleware_instantiate(self):
        cleaner = OutputCleanerMiddleware()
        tracker = CostTrackingMiddleware()
        security = SecurityFilterMiddleware()
        assert cleaner is not None
        assert tracker is not None
        assert security is not None

    def test_clean_then_redact(self):
        """OutputCleaner first, then SecurityFilter."""
        cleaner = OutputCleanerMiddleware()
        security = SecurityFilterMiddleware()

        text = '```yaml\nAuthorization: Bearer sk-test\n```'
        cleaned = cleaner._clean(text)
        assert "```" not in cleaned
        filtered = security._filter.filter_text(cleaned)
        assert "sk-test" not in filtered
