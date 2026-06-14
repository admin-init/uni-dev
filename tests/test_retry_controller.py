"""Tests for core/retry_controller.py — deterministic retry limiter."""

from uni_dev.core.retry_controller import retry_controller


def test_retry_controller_attempt_0():
    """Given attempt_count=0, expect retry with count incremented to 1."""
    state = {"attempt_count": 0}
    result = retry_controller(state)
    assert result == {"status": "retry", "attempt_count": 1}


def test_retry_controller_attempt_1():
    """Given attempt_count=1, expect retry with count incremented to 2."""
    state = {"attempt_count": 1}
    result = retry_controller(state)
    assert result == {"status": "retry", "attempt_count": 2}


def test_retry_controller_attempt_2():
    """Given attempt_count=2, expect retry with count incremented to 3."""
    state = {"attempt_count": 2}
    result = retry_controller(state)
    assert result == {"status": "retry", "attempt_count": 3}


def test_retry_controller_attempt_3_escalate():
    """Given attempt_count=3 (exhausted), expect escalate_to_human."""
    state = {"attempt_count": 3}
    result = retry_controller(state)
    assert result == {"status": "escalate_to_human", "attempt_count": 4}


def test_retry_controller_attempt_5_escalate():
    """Given attempt_count=5 (beyond limit), expect escalate_to_human."""
    state = {"attempt_count": 5}
    result = retry_controller(state)
    assert result == {"status": "escalate_to_human", "attempt_count": 6}


def test_retry_controller_missing_count_defaults_zero():
    """Given state without attempt_count, treat as 0 and retry."""
    state = {}
    result = retry_controller(state)
    assert result == {"status": "retry", "attempt_count": 1}


def test_retry_controller_no_llm():
    """Retry controller is pure Python — no LLM imports or API calls."""
    import inspect
    source = inspect.getsource(retry_controller)
    assert "import langchain" not in source
    assert "from langchain" not in source
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
