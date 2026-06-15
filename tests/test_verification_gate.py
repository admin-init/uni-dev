"""Tests for core/verification_gate.py — deterministic pass/fail gate."""

from uni_dev.core.verification_gate import verification_gate


def test_verification_gate_pass():
    """Given passing tests and empty failures, expect 'pass'."""
    state = {"test_results": {"pass": True, "failures": [], "output": "OK"}}
    result = verification_gate(state)
    assert result == {"status": "pass"}


def test_verification_gate_fail_on_false_pass():
    """Given test_results.pass is False, expect 'fail'."""
    state = {"test_results": {"pass": False, "failures": ["test_login"], "output": ""}}
    result = verification_gate(state)
    assert result == {"status": "fail"}


def test_verification_gate_fail_on_nonempty_failures():
    """Given pass=True but failures list is non-empty, expect 'fail'."""
    state = {"test_results": {"pass": True, "failures": ["test_auth"], "output": ""}}
    result = verification_gate(state)
    assert result == {"status": "fail"}


def test_verification_gate_fail_missing_test_results():
    """Given state without test_results key, expect 'fail'."""
    state = {"messages": [], "classification": "add_feature"}
    result = verification_gate(state)
    assert result == {"status": "fail"}


def test_verification_gate_fail_none_test_results():
    """Given test_results is None, expect 'fail'."""
    state = {"test_results": None}
    result = verification_gate(state)
    assert result == {"status": "fail"}


def test_verification_gate_does_not_modify_state():
    """Verification gate returns only status, never mutates input state."""
    state = {"test_results": {"pass": True, "failures": [], "output": "OK"}, "other": 1}
    original = dict(state)
    verification_gate(state)
    assert state == original


def test_verification_gate_blocked_on_blockers():
    """Given state with blockers, expect 'blocked'."""
    state = {
        "blockers": [{"reason": "API not found", "suggested_action": "REVISE_SPEC"}],
        "test_results": {"pass": True, "failures": [], "output": ""},
    }
    result = verification_gate(state)
    assert result == {"status": "blocked"}


def test_verification_gate_blockers_take_priority_over_fail():
    """Blockers take priority — even with failing tests, return blocked."""
    state = {
        "blockers": [{"reason": "spec missing"}],
        "test_results": {"pass": False, "failures": ["test_x"], "output": ""},
    }
    result = verification_gate(state)
    assert result == {"status": "blocked"}


def test_verification_gate_blockers_priority_over_missing_tests():
    """Blockers take priority over missing test_results."""
    state = {"blockers": [{"reason": "spec missing"}]}
    result = verification_gate(state)
    assert result == {"status": "blocked"}


def test_verification_gate_no_llm():
    """Verification gate is pure Python — no LLM imports or API calls."""
    import inspect
    source = inspect.getsource(verification_gate)
    assert "import langchain" not in source
    assert "from langchain" not in source
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
