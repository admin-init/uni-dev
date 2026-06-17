"""UniDevApp — Textual TUI dashboard for uni-dev watch mode.

Three-panel layout: issue queue | detail + actions | pipeline log.
Press 'n' to open the chat modal for drafting new issues.
"""

from __future__ import annotations

import os
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    RichLog,
)
from textual.binding import Binding

from uni_dev.core.factory import DEFAULT_ISSUES_DB
from uni_dev.runner import IssueRunner
from uni_dev.store.issue_store import IssueStore
from uni_dev.tui.chat import ChatModal


class UniDevApp(App):
    """Continuous pipeline dashboard with issue queue, detail, and log."""

    TITLE = "uni-dev — Pipeline Runner"
    SUB_TITLE = "DDD → SDD → TDD"
    CSS = """
    #queue-panel { width: 35%; border: solid $primary; }
    #right-panel { width: 65%; }
    #detail-panel { height: 60%; border: solid $primary; }
    #action-panel { height: auto; padding: 1; }
    #log-panel { height: 40%; border: solid $primary; }
    #log-widget { height: 100%; }
    .hidden { display: none; }
    """

    BINDINGS = [
        Binding("n", "new_issue", "New Issue (Chat)"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        issue_db_path: str = DEFAULT_ISSUES_DB,
        poll_interval: int = 5,
    ) -> None:
        super().__init__()
        self._store = IssueStore(issue_db_path)
        self._runner = IssueRunner(issue_db_path, poll_interval)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DataTable(id="queue-panel", cursor_type="row")
            with Vertical(id="right-panel"):
                with Vertical(id="detail-panel"):
                    yield Label("Select an issue to see details", id="detail-content")
                with Vertical(id="action-panel", classes="hidden"):
                    yield Button("Approve", variant="success", id="approve-btn")
                    yield Button("Reject", variant="error", id="reject-btn")
                    yield Button("Retry", variant="warning", id="retry-btn")
                with Vertical(id="log-panel"):
                    yield RichLog(id="log-widget", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#queue-panel", DataTable)
        table.add_columns("ID", "St", "Source", "Title")
        self._runner.start()
        self.set_interval(2, self._refresh_data)
        self._log("Runner started")

    def on_unmount(self) -> None:
        self._runner.stop()

    def _refresh_data(self) -> None:
        table = self.query_one("#queue-panel", DataTable)
        table.clear()
        issues = self._store.list_issues(limit=100)
        for issue in issues:
            status_char = {
                "pending": "⏳",
                "running": "▶",
                "needs_human": "👤",
                "completed": "✓",
                "failed": "✗",
            }.get(issue["status"], "?")
            table.add_row(
                issue["issue_id"],
                f"{status_char} {issue['status']}",
                issue["source"],
                issue["title"][:40],
                key=issue["issue_id"],
            )
        summary = self._store.summary()
        self.sub_title = (
            f"P:{summary['pending']} R:{summary['running']} "
            f"H:{summary['needs_human']} C:{summary['completed']} "
            f"F:{summary['failed']}"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key is None or not event.row_key.value:
            return
        issue_id = str(event.row_key.value)
        issue = self._store.get_issue(issue_id)
        if issue is None:
            return

        detail = self.query_one("#detail-content", Label)
        detail.update(
            f"[bold]{issue['title']}[/bold]\n\n"
            f"Status: {issue['status']}\n"
            f"Source: {issue['source']}\n"
            f"Repo: {issue['repo']}\n"
            f"Sender: {issue['sender']}\n\n"
            f"{issue['body']}"
        )

        action_panel = self.query_one("#action-panel", Vertical)
        if issue["status"] == "needs_human":
            action_panel.remove_class("hidden")
            self._selected_id = issue_id
        else:
            action_panel.add_class("hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        issue_id = getattr(self, "_selected_id", None)
        if issue_id is None:
            return

        if event.button.id == "approve-btn":
            self._store.update_status(issue_id, "completed")
            self._log(f"Issue {issue_id}: approved")
            action_panel = self.query_one("#action-panel", Vertical)
            action_panel.add_class("hidden")
        elif event.button.id == "reject-btn":
            self._store.update_status(issue_id, "failed", error="Rejected by human")
            self._log(f"Issue {issue_id}: rejected")
            action_panel = self.query_one("#action-panel", Vertical)
            action_panel.add_class("hidden")
        elif event.button.id == "retry-btn":
            self._store.update_status(issue_id, "pending")
            self._log(f"Issue {issue_id}: retrying")
            action_panel = self.query_one("#action-panel", Vertical)
            action_panel.add_class("hidden")

    def action_new_issue(self) -> None:
        self.push_screen(ChatModal(), self._on_chat_done)

    def action_refresh(self) -> None:
        self._refresh_data()

    def _on_chat_done(self, result: dict[str, Any] | None) -> None:
        if result is None:
            return
        issue_id = self._store.insert_issue({
            "title": result.get("title", "Untitled"),
            "body": result.get("body", ""),
            "source": "chat",
            "sender": os.environ.get("USER", "unknown"),
        })
        self._log(f"Issue {issue_id}: created via chat")
        self._refresh_data()

    def _log(self, message: str) -> None:
        log = self.query_one("#log-widget", RichLog)
        log.write(message)
