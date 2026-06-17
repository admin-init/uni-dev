from __future__ import annotations

from uni_dev.core.hitl import route_human_decision


class TestRouteHumanDecision:
    def test_approve(self):
        state = {"_human_decision": "approve"}
        assert route_human_decision(state) == "approve"

    def test_retry(self):
        state = {"_human_decision": "retry"}
        assert route_human_decision(state) == "retry"

    def test_reject(self):
        state = {"_human_decision": "reject"}
        assert route_human_decision(state) == "reject"

    def test_default_reject(self):
        state = {}
        assert route_human_decision(state) == "reject"
