"""MonitorStore — SQLite persistence for task run records.

Stores TaskRun records in .uni-dev/monitor.db for multi-session
queryability. Used by MonitorMiddleware to persist runs across
agent sessions.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS task_runs (
    run_id TEXT PRIMARY KEY,
    subagent_type TEXT NOT NULL,
    description TEXT,
    parent_agent TEXT NOT NULL DEFAULT 'orchestrator',
    started_at REAL NOT NULL,
    completed_at REAL,
    duration_ms INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    error TEXT,
    result_length INTEGER
);

CREATE INDEX IF NOT EXISTS idx_task_runs_subagent ON task_runs(subagent_type);
CREATE INDEX IF NOT EXISTS idx_task_runs_status ON task_runs(status);
CREATE INDEX IF NOT EXISTS idx_task_runs_started ON task_runs(started_at);
"""


class MonitorStore:
    """SQLite store for task run records.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Create the database and schema if they do not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(SCHEMA)

    def insert_run(self, run: dict[str, Any]) -> None:
        """Insert a task run record.

        Args:
            run: TaskRun dict with all fields.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO task_runs
                   (run_id, subagent_type, description, parent_agent,
                    started_at, completed_at, duration_ms, status, error,
                    result_length)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run["run_id"],
                    run["subagent_type"],
                    run.get("description"),
                    run.get("parent_agent", "orchestrator"),
                    run["started_at"],
                    run.get("completed_at"),
                    run.get("duration_ms"),
                    run.get("status", "running"),
                    run.get("error"),
                    run.get("result_length"),
                ),
            )

    def query_runs(
        self,
        subagent_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query task runs with optional filters.

        Args:
            subagent_type: Filter by sub-agent name.
            status: Filter by status (running, success, error).
            limit: Maximum number of records to return.

        Returns:
            List of TaskRun dicts ordered by started_at descending.
        """
        query = "SELECT * FROM task_runs WHERE 1=1"
        params: list[Any] = []

        if subagent_type is not None:
            query += " AND subagent_type = ?"
            params.append(subagent_type)
        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        """Get aggregate summary of all recorded runs.

        Returns:
            Dict with total, success_count, error_count, running_count,
            avg_duration_ms, and latest_started_at.
        """
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                """SELECT
                     COUNT(*) as total,
                     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                     SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count,
                     SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running_count,
                     AVG(duration_ms) as avg_duration_ms,
                     MAX(started_at) as latest_started_at
                   FROM task_runs"""
            ).fetchone()
            return {
                "total": row[0] or 0,
                "success_count": row[1] or 0,
                "error_count": row[2] or 0,
                "running_count": row[3] or 0,
                "avg_duration_ms": int(row[4]) if row[4] else 0,
                "latest_started_at": row[5] or time.time(),
            }
