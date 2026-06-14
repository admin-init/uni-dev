"""Tests for runner.py — IssueRunner."""

import tempfile

from uni_dev.runner import IssueRunner
from uni_dev.store.issue_store import IssueStore


def test_runner_start_stop():
    """Runner can start and stop cleanly."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    runner = IssueRunner(db_path, poll_interval_sec=1)
    assert not runner.running
    runner.start()
    assert runner.running
    runner.stop()
    assert not runner.running


def test_runner_run_one_empty():
    """run_one returns None when queue is empty."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    runner = IssueRunner(db_path)
    result = runner.run_one()
    assert result is None


def test_runner_run_one_processes():
    """run_one picks up and processes a pending issue."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    store = IssueStore(db_path)
    iid = store.insert_issue({"title": "Test runner issue", "body": "A test"})
    runner = IssueRunner(db_path)
    result = runner.run_one()
    assert result is not None
    assert result["issue_id"] == iid
    assert result["status"] in ("completed", "failed", "needs_human")


def test_runner_failed_issue():
    """run_one marks as failed when orchestrator raises."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    store = IssueStore(db_path)
    iid = store.insert_issue({"title": "Bad issue"})
    runner = IssueRunner(db_path)

    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if "orchestrator" in name:
            raise ImportError("No orchestrator in test")
        return original_import(name, *args, **kwargs)

    try:
        builtins.__import__ = mock_import
        result = runner.run_one()
    finally:
        builtins.__import__ = original_import

    assert result["status"] == "failed"
    assert result["issue_id"] == iid
    issue = store.get_issue(iid)
    assert issue["status"] == "failed"
