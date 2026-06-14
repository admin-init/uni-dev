"""Tests for monitoring/store.py — MonitorStore SQLite persistence."""

import tempfile
from pathlib import Path

from uni_dev.monitoring.store import MonitorStore


def _make_store() -> MonitorStore:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    path = Path(tmp.name)
    tmp.close()
    return MonitorStore(path)


def test_insert_and_query_single_run():
    """Insert a run and retrieve it."""
    store = _make_store()
    run = {
        "run_id": "abc123",
        "subagent_type": "domain-designer",
        "description": "Analyze user module",
        "parent_agent": "orchestrator",
        "started_at": 1000.0,
        "completed_at": 1005.0,
        "duration_ms": 5000,
        "status": "success",
        "error": None,
        "result_length": 2340,
    }
    store.insert_run(run)

    results = store.query_runs()
    assert len(results) == 1
    assert results[0]["run_id"] == "abc123"
    assert results[0]["subagent_type"] == "domain-designer"
    assert results[0]["status"] == "success"


def test_query_filter_by_subagent_type():
    """Filter runs by subagent_type."""
    store = _make_store()
    store.insert_run({
        "run_id": "r1",
        "subagent_type": "spec-writer",
        "started_at": 1000.0,
        "status": "success",
    })
    store.insert_run({
        "run_id": "r2",
        "subagent_type": "domain-designer",
        "started_at": 2000.0,
        "status": "success",
    })

    results = store.query_runs(subagent_type="spec-writer")
    assert len(results) == 1
    assert results[0]["run_id"] == "r1"


def test_query_filter_by_status():
    """Filter runs by status."""
    store = _make_store()
    store.insert_run({
        "run_id": "r1",
        "subagent_type": "code-generator",
        "started_at": 1000.0,
        "status": "error",
    })
    store.insert_run({
        "run_id": "r2",
        "subagent_type": "code-generator",
        "started_at": 2000.0,
        "status": "success",
    })

    results = store.query_runs(status="error")
    assert len(results) == 1
    assert results[0]["run_id"] == "r1"


def test_query_empty_store():
    """Query returns empty list for empty store."""
    store = _make_store()
    results = store.query_runs()
    assert results == []


def test_insert_or_replace_updates_existing():
    """Inserting with same run_id replaces existing record."""
    store = _make_store()
    store.insert_run({
        "run_id": "same_id",
        "subagent_type": "test",
        "started_at": 1000.0,
        "status": "running",
    })
    store.insert_run({
        "run_id": "same_id",
        "subagent_type": "test",
        "started_at": 1000.0,
        "completed_at": 2000.0,
        "duration_ms": 1000,
        "status": "success",
        "result_length": 500,
    })

    results = store.query_runs()
    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["result_length"] == 500


def test_summary_empty_store():
    """Summary on empty store returns zeros."""
    store = _make_store()
    s = store.summary()
    assert s["total"] == 0
    assert s["success_count"] == 0
    assert s["error_count"] == 0


def test_summary_with_runs():
    """Summary aggregates correctly across runs."""
    store = _make_store()
    store.insert_run({
        "run_id": "r1",
        "subagent_type": "test",
        "started_at": 1000.0,
        "duration_ms": 100,
        "status": "success",
    })
    store.insert_run({
        "run_id": "r2",
        "subagent_type": "test",
        "started_at": 2000.0,
        "duration_ms": 200,
        "status": "success",
    })
    store.insert_run({
        "run_id": "r3",
        "subagent_type": "test",
        "started_at": 3000.0,
        "duration_ms": 300,
        "status": "error",
    })

    s = store.summary()
    assert s["total"] == 3
    assert s["success_count"] == 2
    assert s["error_count"] == 1
    assert s["avg_duration_ms"] == 200
    assert s["latest_started_at"] == 3000.0


def test_schema_created_automatically():
    """Store creates DB and schema on init even if file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "sub" / "dir" / "test.db"
        store = MonitorStore(db_path)
        results = store.query_runs()
        assert results == []
        assert db_path.exists()
