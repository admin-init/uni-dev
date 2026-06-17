from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from uni_dev.core.factory import DEFAULT_CHECKPOINTS_DB, DEFAULT_ISSUES_DB
from uni_dev.store.issue_store import IssueStore

logger = logging.getLogger("uni_dev.runner")

_DEFAULT_POLL_INTERVAL = 5


class IssueRunner:
    """Background runner that polls for pending issues and invokes the pipeline.

    Args:
        issue_db_path: Path to IssueStore SQLite database.
        poll_interval_sec: Seconds between polls (default 5).
    """

    def __init__(
        self,
        issue_db_path: str | Path = DEFAULT_ISSUES_DB,
        poll_interval_sec: int = _DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._store = IssueStore(issue_db_path)
        self._poll_interval = poll_interval_sec
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the runner in a background daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Runner started (poll every %ds)", self._poll_interval)

    def stop(self) -> None:
        """Signal the runner to stop at the next poll cycle."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("Runner stopped")

    def run_one(self) -> dict[str, Any] | None:
        """Process exactly one pending issue (synchronous, for headless use).

        Returns:
            Result dict or None if no pending issues.
        """
        issue = self._store.next_pending()
        if issue is None:
            return None
        return self._process_issue(issue)

    def _run_loop(self) -> None:
        """Main poll loop — runs in background thread."""
        while self._running:
            issue = self._store.next_pending()
            if issue is not None:
                self._process_issue(issue)
            time.sleep(self._poll_interval)

    def _process_issue(self, issue: dict[str, Any]) -> dict[str, Any]:
        """Process a single issue through the pipeline.

        Args:
            issue: Issue dict from IssueStore.

        Returns:
            Result dict with final status.
        """
        from langgraph.checkpoint.sqlite import SqliteSaver

        from uni_dev.core.factory import PipelineConfig
        from uni_dev.core.graph import compile_pipeline

        issue_id = issue["issue_id"]
        logger.info("Processing issue %s: %s", issue_id, issue["title"])

        self._store.update_status(issue_id, "running")

        try:
            config = PipelineConfig.from_env()
            checkpointer = SqliteSaver.from_conn_string(DEFAULT_CHECKPOINTS_DB)
            pipeline = compile_pipeline(config=config, checkpointer=checkpointer)

            state = {
                "issue": issue.get("body") or issue["title"],
                "project_path": issue.get("project_path", "."),
                "classification": issue.get("classification", "add_feature"),
                "attempt_count": 0,
            }
            thread_config = {"configurable": {"thread_id": issue_id}}

            result = pipeline.invoke(state, thread_config)

            review_report = result.get("review_report", "")
            if not review_report:
                self._store.update_status(issue_id, "needs_human")
                logger.info("Issue %s: needs human review", issue_id)
                return {"status": "needs_human", "issue_id": issue_id}

            self._store.update_status(issue_id, "completed")
            logger.info("Issue %s: completed", issue_id)
            return {"status": "completed", "issue_id": issue_id}

        except Exception as exc:
            logger.error("Issue %s: failed — %s", issue_id, exc)
            self._store.update_status(
                issue_id,
                "failed",
                error=str(exc),
            )
            return {"status": "failed", "issue_id": issue_id, "error": str(exc)}
