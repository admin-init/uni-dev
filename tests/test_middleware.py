from __future__ import annotations

from uni_dev.middleware.output_cleaner import OutputCleanerMiddleware
from uni_dev.middleware.cost_tracking import CostTrackingMiddleware


class TestOutputCleanerMiddleware:
    def test_instantiation(self):
        mw = OutputCleanerMiddleware()
        assert mw is not None

    def test_clean_removes_markdown(self):
        mw = OutputCleanerMiddleware()
        result = mw._clean("```python\nprint('hello')\n```")
        assert "```" not in result
        assert "print('hello')" in result


class TestCostTrackingMiddleware:
    def test_instantiation(self):
        mw = CostTrackingMiddleware()
        assert mw is not None

    def test_budget_default(self):
        mw = CostTrackingMiddleware()
        assert mw._budget_tokens == 1_000_000

    def test_custom_budget(self):
        mw = CostTrackingMiddleware(budget_tokens=500_000)
        assert mw._budget_tokens == 500_000
