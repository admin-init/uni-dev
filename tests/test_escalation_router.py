"""Tests for core/escalation_router.py — deterministic escalation routing."""

from uni_dev.core.escalation_router import escalation_router


def test_escalation_router_revise_spec():
    """Blocker with REVISE_SPEC routes to SpecWriter, appends to escalation_history."""
    state = {
        "blockers": [{"reason": "contract mismatch", "suggested_action": "REVISE_SPEC"}],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "SpecWriter"
    assert result["escalation_history"] == ["code_gen->SpecWriter"]


def test_escalation_router_revise_design():
    """Blocker with REVISE_DESIGN routes to DomainDesigner."""
    state = {
        "blockers": [{"reason": "domain boundary unclear", "suggested_action": "REVISE_DESIGN"}],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "DomainDesigner"
    assert result["escalation_history"] == ["code_gen->DomainDesigner"]


def test_escalation_router_human_required():
    """Blocker with HUMAN_REQUIRED routes to __end__."""
    state = {
        "blockers": [{"reason": "ambiguous requirements", "suggested_action": "HUMAN_REQUIRED"}],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "__end__"
    assert result["escalation_history"] == ["code_gen->__end__"]


def test_escalation_router_unknown_action_defaults_to_human():
    """Unknown suggested_action defaults to __end__."""
    state = {
        "blockers": [{"reason": "edge case", "suggested_action": "DO_SOMETHING_WEIRD"}],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "__end__"


def test_escalation_router_no_blockers_defaults_to_human():
    """Empty blockers defaults to HUMAN_REQUIRED -> __end__."""
    state = {
        "blockers": [],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "__end__"
    assert result["escalation_history"] == ["code_gen->__end__"]


def test_escalation_router_repeated_path_detection():
    """History has 2 identical entries -> returns repeated_escalation_detected with __end__."""
    state = {
        "blockers": [{"reason": "test blocked", "suggested_action": "REVISE_SPEC"}],
        "current_phase": "code_gen",
        "escalation_history": ["code_gen->SpecWriter", "code_gen->SpecWriter"],
    }
    result = escalation_router(state)
    assert result["next_node"] == "__end__"
    assert result["status"] == "repeated_escalation_detected"


def test_escalation_router_max_escalations():
    """History has 3 entries -> returns max_escalations_exceeded with __end__."""
    state = {
        "blockers": [{"reason": "test blocked", "suggested_action": "REVISE_SPEC"}],
        "current_phase": "code_gen",
        "escalation_history": [
            "code_gen->SpecWriter",
            "code_gen->DomainDesigner",
            "code_gen->SpecWriter",
        ],
    }
    result = escalation_router(state)
    assert result["next_node"] == "__end__"
    assert result["status"] == "max_escalations_exceeded"


def test_escalation_router_multiple_blockers_uses_last():
    """Multiple blockers -> uses last one's suggested_action."""
    state = {
        "blockers": [
            {"reason": "contract mismatch", "suggested_action": "REVISE_DESIGN"},
            {"reason": "domain boundary unclear", "suggested_action": "REVISE_SPEC"},
        ],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    result = escalation_router(state)
    assert result["next_node"] == "SpecWriter"


def test_escalation_router_no_llm():
    """Escalation router is pure Python — no LLM imports or API calls."""
    import inspect
    source = inspect.getsource(escalation_router)
    assert "import langchain" not in source
    assert "from langchain" not in source
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()


def test_escalation_router_does_not_mutate_input():
    """Does not mutate original state dict."""
    state = {
        "blockers": [{"reason": "contract mismatch", "suggested_action": "REVISE_SPEC"}],
        "current_phase": "code_gen",
        "escalation_history": [],
    }
    state_before = {
        "blockers": state["blockers"],
        "current_phase": state["current_phase"],
        "escalation_history": list(state["escalation_history"]),
    }
    escalation_router(state)
    assert state == state_before
