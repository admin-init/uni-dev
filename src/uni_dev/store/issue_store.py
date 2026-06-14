"""IssueStore — SQLite-backed issue lifecycle tracker.

Persists issues from webhooks, CLI, and the chat modal. Tracks
status transitions: pending → running → completed/failed/needs_human.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS issues (
    issue_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT DEFAULT '',
    repo TEXT DEFAULT '',
    sender TEXT DEFAULT '',
    source TEXT DEFAULT 'cli',
    status TEXT DEFAULT 'pending',
    classification TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    task_runs TEXT DEFAULT '[]',
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_created ON issues(created_at);
"""


class IssueStore:
    """SQLite store for issue lifecycle tracking.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(SCHEMA)

    def insert_issue(self, data: dict[str, Any]) -> str:
        """Insert a new issue, returns the issue_id.

        Args:
            data: Issue data with at minimum 'title'. Optional: body,
                  repo, sender, source, classification.

        Returns:
            Generated issue_id string.
        """
        issue_id = data.get("issue_id") or uuid.uuid4().hex[:12]
        now = time.time()
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT INTO issues
                   (issue_id, title, body, repo, sender, source, status,
                    classification, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
                (
                    issue_id,
                    data["title"],
                    data.get("body", ""),
                    data.get("repo", ""),
                    data.get("sender", ""),
                    data.get("source", "cli"),
                    data.get("classification"),
                    now,
                    now,
                ),
            )
        return issue_id

    def next_pending(self) -> dict[str, Any] | None:
        """Get the oldest pending issue, or None if queue is empty.

        Returns:
            Issue dict or None.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """SELECT * FROM issues
                   WHERE status = 'pending'
                   ORDER BY created_at ASC LIMIT 1"""
            ).fetchone()
            return dict(row) if row else None

    def update_status(
        self, issue_id: str, status: str, **kwargs: Any
    ) -> None:
        """Update issue status and optional fields.

        Args:
            issue_id: The issue to update.
            status: New status (running, completed, failed, needs_human).
            **kwargs: Additional fields to update (task_runs, error,
                      classification, etc.).
        """
        now = time.time()
        sets = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status, now]

        if status == "running":
            sets.append("started_at = ?")
            params.append(now)
        elif status in ("completed", "failed", "needs_human"):
            sets.append("completed_at = ?")
            params.append(now)

        for key, value in kwargs.items():
            if key in (
                "task_runs", "error", "classification",
            ):
                sets.append(f"{key} = ?")
                params.append(
                    json.dumps(value) if isinstance(value, (list, dict)) else value
                )

        params.append(issue_id)
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                f"UPDATE issues SET {', '.join(sets)} WHERE issue_id = ?",
                params,
            )

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get a single issue by ID.

        Args:
            issue_id: The issue ID.

        Returns:
            Issue dict or None.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM issues WHERE issue_id = ?", (issue_id,)
            ).fetchone()
            return dict(row) if row else None

    def list_issues(
        self, status: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """List issues, optionally filtered by status.

        Args:
            status: Filter by status, or None for all.
            limit: Maximum number of issues to return.

        Returns:
            List of issue dicts ordered by created_at descending.
        """
        query = "SELECT * FROM issues"
        params: list[Any] = []
        if status is not None:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        """Get aggregate counts by status.

        Returns:
            Dict with total, pending, running, needs_human, completed, failed.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as total,
                     SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                     SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                     SUM(CASE WHEN status = 'needs_human' THEN 1 ELSE 0 END) as needs_human,
                     SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                     SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                   FROM issues"""
            ).fetchone()
            return {
                "total": row[0] or 0,
                "pending": row[1] or 0,
                "running": row[2] or 0,
                "needs_human": row[3] or 0,
                "completed": row[4] or 0,
                "failed": row[5] or 0,
            }
