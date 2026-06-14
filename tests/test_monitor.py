"""Tests for monitoring/monitor.py — MonitorMiddleware."""

import logging
from unittest.mock import MagicMock

from uni_dev.monitoring.monitor import MonitorMiddleware, MonitorState

# Prevent actual log output during tests
logging.getLogger("uni_dev.monitor").setLevel(logging.CRITICAL)


def test_monitor_state_extends_agent_state():
    """MonitorState includes agent base fields plus task_runs."""
    assert hasattr(MonitorState, "__required_keys__") or hasattr(
        MonitorState, "__optional_keys__"
    )


def test_monitor_state_task_runs_field():
    """MonitorState has task_runs field."""
    annotations = MonitorState.__annotations__
    assert "task_runs" in annotations


def test_middleware_creation():
    """MonitorMiddleware can be created with default args."""
    mw = MonitorMiddleware()
    assert mw is not None
    assert mw.state_schema is MonitorState


def test_middleware_creation_with_db():
    """MonitorMiddleware can be created with a db_path."""
    mw = MonitorMiddleware(db_path=":memory:")
    assert mw is not None


def test_middleware_creation_with_context():
    """MonitorMiddleware accepts custom context name."""
    mw = MonitorMiddleware(context="domain-designer")
    assert mw is not None


def test_before_agent_returns_none():
    """before_agent returns None (no state modification)."""
    mw = MonitorMiddleware()
    result = mw.before_agent(state={}, runtime=MagicMock())
    assert result is None


def test_after_agent_with_empty_state():
    """after_agent with empty state logs correctly."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()
    result = mw.after_agent(state={}, runtime=MagicMock())
    assert result is None


def test_after_agent_with_runs():
    """after_agent with existing task_runs emits session_end."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()
    state = {
        "task_runs": [
            {"run_id": "r1", "status": "success"},
            {"run_id": "r2", "status": "error"},
            {"run_id": "r3", "status": "success"},
        ]
    }
    result = mw.after_agent(state=state, runtime=MagicMock())
    assert result is None
    assert mw._stream_writer.called


def test_wrap_tool_call_non_task():
    """Non-task tool calls are passed through without recording."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()

    request = MagicMock()
    request.tool_call = {"name": "read_file", "args": {"path": "/tmp"}}
    handler = MagicMock()
    handler.return_value = "file content"

    mw.wrap_tool_call(request, handler)
    handler.assert_called_once_with(request)
    assert mw._stream_writer.called is False


def test_wrap_tool_call_task_records_run():
    """Task tool calls create TaskRun and append to state."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()

    request = MagicMock()
    request.tool_call = {
        "name": "task",
        "args": {
            "subagent_type": "domain-designer",
            "description": "Analyze the domain",
        },
    }
    handler = MagicMock()
    handler.return_value = MagicMock()
    handler.return_value.content = "Domain analysis result"

    result = mw.wrap_tool_call(request, handler)
    handler.assert_called_once_with(request)

    assert result is not None
    assert hasattr(result, "update")
    update = result.update
    assert "task_runs" in update
    assert len(update["task_runs"]) == 1
    run = update["task_runs"][0]
    assert run["subagent_type"] == "domain-designer"
    assert run["status"] == "success"
    assert run["run_id"] is not None
    assert run["started_at"] is not None
    assert run["completed_at"] is not None
    assert run["duration_ms"] is not None
    assert mw._stream_writer.call_count >= 2  # task_start + task_end


def test_wrap_tool_call_task_handles_error():
    """Task failures are recorded with status='error'."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()

    request = MagicMock()
    request.tool_call = {
        "name": "task",
        "args": {
            "subagent_type": "code-generator",
            "description": "Implement user endpoint",
        },
    }
    handler = MagicMock()
    handler.side_effect = ValueError("Something went wrong")

    result = mw.wrap_tool_call(request, handler)

    assert hasattr(result, "update")
    update = result.update
    assert "task_runs" in update
    run = update["task_runs"][0]
    assert run["status"] == "error"
    assert "Something went wrong" in run["error"]


def test_wrap_tool_call_task_unknown_subagent():
    """Task with unknown subagent_type still records."""
    mw = MonitorMiddleware()
    mw._stream_writer = MagicMock()

    request = MagicMock()
    request.tool_call = {
        "name": "task",
        "args": {"subagent_type": "unknown-agent", "description": "test"},
    }
    handler = MagicMock()
    handler.return_value = MagicMock()
    handler.return_value.content = ""

    result = mw.wrap_tool_call(request, handler)
    run = result.update["task_runs"][0]
    assert run["subagent_type"] == "unknown-agent"
    assert run["status"] == "success"
