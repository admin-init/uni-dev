"""GitHub webhook handler — validates and processes GitHub events."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate GitHub webhook payload signature.

    Uses HMAC-SHA256 with the webhook secret.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header (sha256=<hex>).
        secret: Webhook secret string.

    Returns:
        True if the signature is valid.
    """
    if not secret:
        logger.warning("WEBHOOK_SECRET not set — skipping signature validation")
        return True
    if not signature:
        return False
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def extract_issue(body: dict[str, Any]) -> dict[str, Any] | None:
    """Extract issue data from a GitHub webhook payload.

    Args:
        body: Parsed JSON webhook body.

    Returns:
        IssueData dict or None if not an issue event.
    """
    issue = body.get("issue")
    if issue is None:
        return None

    return {
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "number": issue.get("number", 0),
        "url": issue.get("html_url", ""),
        "action": body.get("action", "opened"),
        "sender": body.get("sender", {}).get("login", "unknown"),
        "repo": body.get("repository", {}).get("full_name", "unknown"),
    }


def handle_event(body: dict[str, Any]) -> dict[str, Any]:
    """Process a GitHub webhook event and extract issue content.

    Args:
        body: Parsed JSON webhook body.

    Returns:
        Dict with status, issue_data, and event_type.
    """
    event_type = "unknown"
    issue_data = extract_issue(body)

    if issue_data is None:
        return {"status": "skipped", "reason": "no issue in payload"}

    if "pull_request" in body:
        event_type = "pull_request"
    elif "issue" in body:
        event_type = "issue"

    return {
        "status": "accepted",
        "event_type": event_type,
        "issue": issue_data,
    }
