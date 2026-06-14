"""Tests for store/issue_store.py — IssueStore lifecycle tracking."""

import tempfile
from pathlib import Path

from uni_dev.store.issue_store import IssueStore


def _make_store() -> IssueStore:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    tmp.close()
    return IssueStore(path)


def test_insert_and_get_issue():
    """Insert an issue and retrieve it."""
    store = _make_store()
    iid = store.insert_issue({
        "title": "Add avatar upload",
        "body": "We need avatar upload with S3",
        "repo": "owner/repo",
        "sender": "dev",
        "source": "cli",
    })
    issue = store.get_issue(iid)
    assert issue is not None
    assert issue["title"] == "Add avatar upload"
    assert issue["status"] == "pending"
    assert issue["source"] == "cli"


def test_insert_issue_minimal():
    """Minimal insert with only title works."""
    store = _make_store()
    iid = store.insert_issue({"title": "Fix login"})
    issue = store.get_issue(iid)
    assert issue["title"] == "Fix login"
    assert issue["body"] == ""
    assert issue["status"] == "pending"


def test_next_pending_returns_oldest():
    """next_pending returns the oldest pending issue."""
    store = _make_store()
    store.insert_issue({"title": "First"})
    store.insert_issue({"title": "Second"})
    store.insert_issue({"title": "Third"})
    issue = store.next_pending()
    assert issue is not None
    assert issue["title"] == "First"


def test_next_pending_empty():
    """next_pending returns None for empty queue."""
    store = _make_store()
    assert store.next_pending() is None


def test_update_status_running():
    """Updating to running sets started_at."""
    store = _make_store()
    iid = store.insert_issue({"title": "Test"})
    store.update_status(iid, "running")
    issue = store.get_issue(iid)
    assert issue["status"] == "running"
    assert issue["started_at"] is not None


def test_update_status_completed():
    """Updating to completed sets completed_at."""
    store = _make_store()
    iid = store.insert_issue({"title": "Test"})
    store.update_status(iid, "running")
    store.update_status(iid, "completed", task_runs=[{"run_id": "abc"}])
    issue = store.get_issue(iid)
    assert issue["status"] == "completed"
    assert issue["completed_at"] is not None
    assert "abc" in (issue["task_runs"] or "")


def test_update_status_failed():
    """Failed status records error."""
    store = _make_store()
    iid = store.insert_issue({"title": "Test"})
    store.update_status(iid, "failed", error="Something broke")
    issue = store.get_issue(iid)
    assert issue["status"] == "failed"
    assert issue["error"] == "Something broke"


def test_list_issues_filter_by_status():
    """list_issues filters by status."""
    store = _make_store()
    store.insert_issue({"title": "Pending issue"})
    iid2 = store.insert_issue({"title": "Done issue"})
    store.update_status(iid2, "completed")
    pending = store.list_issues(status="pending")
    assert len(pending) >= 1
    assert all(i["status"] == "pending" for i in pending)
    completed = store.list_issues(status="completed")
    assert len(completed) == 1
    assert completed[0]["issue_id"] == iid2


def test_summary():
    """Summary returns correct counts."""
    store = _make_store()
    store.insert_issue({"title": "P1"})
    iid = store.insert_issue({"title": "P2"})
    store.update_status(iid, "completed")
    iid2 = store.insert_issue({"title": "P3"})
    store.update_status(iid2, "failed", error="x")
    s = store.summary()
    assert s["total"] == 3
    assert s["pending"] == 1
    assert s["completed"] == 1
    assert s["failed"] == 1
