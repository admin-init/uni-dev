"""FastAPI webhook server for uni-dev.

Exposes endpoints for GitHub and Codeberg webhook ingestion
with HMAC-SHA256 signature validation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status as http_status
from fastapi.responses import JSONResponse

from uni_dev.core.factory import DEFAULT_ISSUES_DB
from uni_dev.webhooks.codeberg_handler import (
    validate_signature as validate_codeberg_signature,
    handle_event as handle_codeberg_event,
)
from uni_dev.webhooks.github_handler import (
    validate_signature as validate_github_signature,
    handle_event as handle_github_event,
)

logger = logging.getLogger(__name__)


def _get_secret() -> str:
    """Get webhook secret from environment."""
    return os.environ.get("WEBHOOK_SECRET", "")


def create_app() -> FastAPI:
    """Create the FastAPI webhook application.

    Returns:
        Configured FastAPI app with webhook routes.
    """
    app = FastAPI(
        title="uni-dev Webhooks",
        description="Webhook ingestion for uni-dev — GitHub and Codeberg issue events",
        version="0.1.0",
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/webhook/github")
    async def github_webhook(request: Request) -> JSONResponse:
        """Receive GitHub issue/PR webhook events."""
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        secret = _get_secret()

        if secret and not validate_github_signature(body, signature, secret):
            logger.warning("GitHub webhook: invalid signature")
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        try:
            payload: dict[str, Any] = await request.json()
        except Exception:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        result = handle_github_event(payload)
        if result.get("status") == "accepted":
            issue_data = result.get("issue", {})
            from uni_dev.store.issue_store import IssueStore
            store = IssueStore(DEFAULT_ISSUES_DB)
            issue_id = store.insert_issue({
                "title": issue_data.get("title", ""),
                "body": issue_data.get("body", ""),
                "repo": issue_data.get("repo", ""),
                "sender": issue_data.get("sender", ""),
                "source": "github",
            })
            result["issue_id"] = issue_id
        logger.info(
            "GitHub webhook: %s %s — %s",
            result.get("event_type", "?"),
            result.get("issue", {}).get("title", "?"),
            result.get("status", "?"),
        )

        return JSONResponse(content=result)

    @app.post("/webhook/codeberg")
    async def codeberg_webhook(request: Request) -> JSONResponse:
        """Receive Codeberg/Tea issue webhook events."""
        body = await request.body()
        signature = request.headers.get("X-Codeberg-Signature", "")
        secret = _get_secret()

        if secret and not validate_codeberg_signature(body, signature, secret):
            logger.warning("Codeberg webhook: invalid signature")
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature",
            )

        try:
            payload: dict[str, Any] = await request.json()
        except Exception:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            )

        result = handle_codeberg_event(payload)
        if result.get("status") == "accepted":
            issue_data = result.get("issue", {})
            from uni_dev.store.issue_store import IssueStore
            store = IssueStore(DEFAULT_ISSUES_DB)
            issue_id = store.insert_issue({
                "title": issue_data.get("title", ""),
                "body": issue_data.get("body", ""),
                "repo": issue_data.get("repo", ""),
                "sender": issue_data.get("sender", ""),
                "source": "codeberg",
            })
            result["issue_id"] = issue_id
        logger.info(
            "Codeberg webhook: %s — %s",
            result.get("issue", {}).get("title", "?"),
            result.get("status", "?"),
        )

        return JSONResponse(content=result)

    return app
