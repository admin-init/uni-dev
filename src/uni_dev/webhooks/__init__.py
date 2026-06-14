"""Webhook package — FastAPI server for issue ingestion."""

from uni_dev.webhooks.server import create_app

__all__ = ["create_app"]
