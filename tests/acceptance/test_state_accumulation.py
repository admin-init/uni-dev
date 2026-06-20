"""A8: State accumulation acceptance test.

After full pipeline, all state fields should be populated correctly.
"""
from __future__ import annotations


class TestStateAccumulation:
    """Verify all pipeline state fields accumulate across phases."""

    def test_after_ddd_has_domain_model(self, state_after_ddd):
        assert state_after_ddd.get("domain_model"), "domain_model missing"

    def test_after_sdd_has_api_spec(self, state_after_sdd):
        assert state_after_sdd.get("api_spec"), "api_spec missing"

    def test_after_test_gen_has_test_files(self, state_after_test_gen):
        test_files = state_after_test_gen.get("test_files", [])
        assert test_files, "test_files missing"
        assert isinstance(test_files, list)

    def test_after_code_gen_has_modified_files(self, state_with_tests_passing):
        modified = state_with_tests_passing.get("modified_files", [])
        assert modified, "modified_files missing"
        assert isinstance(modified, list)

    def test_after_tests_passing_has_test_results(self, state_with_tests_passing):
        results = state_with_tests_passing.get("test_results", {})
        assert results.get("pass") is True
        assert not results.get("failures", [])

    def test_after_tests_failing_has_failures(self, state_with_tests_failing):
        results = state_with_tests_failing.get("test_results", {})
        assert results.get("pass") is False
        assert results.get("failures"), "Expected failure details"

    def test_state_retains_issue(self, state_with_tests_passing):
        assert state_with_tests_passing.get("issue")

    def test_state_retains_project_path(self, state_with_tests_passing):
        assert state_with_tests_passing.get("project_path") == "."

    def test_state_retains_classification(self, state_with_tests_passing):
        assert state_with_tests_passing.get("classification") == "add_feature"
