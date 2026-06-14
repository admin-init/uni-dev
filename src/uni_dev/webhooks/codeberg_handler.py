"""Codeberg webhook handler — validates and processes Codeberg/Tea events."""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate Codeberg webhook payload signature.

    Codeberg uses the X-Codeberg-Signature header with HMAC-SHA256.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Codeberg-Signature header.
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
    return hmac.compare_digest(expected, signature)


def extract_issue(body: dict[str, Any]) -> dict[str, Any] | None:
    """Extract issue data from a Codeberg webhook payload.

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
        "url": issue.get("html_url", issue.get("url", "")),
        "action": body.get("action", "opened"),
        "sender": body.get("sender", {}).get("username",
                     body.get("sender", {}).get("login", "unknown")),
        "repo": body.get("repository", {}).get("full_name", "unknown"),
    }


def handle_event(body: dict[str, Any]) -> dict[str, Any]:
    """Process a Codeberg webhook event and extract issue content.

    Args:
        body: Parsed JSON webhook body.

    Returns:
        Dict with status, issue_data, and event_type.
    """
    issue_data = extract_issue(body)

    if issue_data is None:
        return {"status": "skipped", "reason": "no issue in payload"}

    event_type = "issue"

    return {
        "status": "accepted",
        "event_type": event_type,
        "issue": issue_data,
    }
