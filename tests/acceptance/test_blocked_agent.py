"""A7: BLOCKED agent protocol acceptance test.

Sub-agent returns BLOCKED -> gate detects blockers -> fails -> HITL.
"""
from __future__ import annotations

from uni_dev.core.gates import ddd_verification_gate, sdd_verification_gate


class TestBlockedAgent:
    """Verify gates detect BLOCKED state from sub-agents."""

    def test_ddd_gate_blocks_when_blockers_present(self):
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [{"reason": "Cannot determine bounded contexts"}],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_sdd_gate_blocks_when_blockers_present(self):
        state = {
            "api_spec": "openapi: '3.0'\ninfo:\n  title: X\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: OK",
            "blockers": [{"reason": "API spec missing required schemas"}],
        }
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_multiple_blockers_cause_fail(self):
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [
                {"reason": "Block 1"},
                {"reason": "Block 2"},
                {"reason": "Block 3"},
            ],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_blockers_take_priority_over_domain_model(self):
        """Even with valid domain_model, blockers cause failure."""
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [{"reason": "BLOCKED"}],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_empty_blockers_list_passes(self):
        """Empty blockers list does NOT cause failure."""
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "pass"
