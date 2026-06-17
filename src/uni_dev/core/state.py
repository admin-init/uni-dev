from __future__ import annotations

from typing import Any

from typing_extensions import NotRequired, TypedDict


class PipelineState(TypedDict):
    issue: str
    project_path: str
    classification: str
    attempt_count: int
    domain_model: NotRequired[str]
    api_spec: NotRequired[str]
    test_files: NotRequired[list[str]]
    modified_files: NotRequired[list[str]]
    test_results: NotRequired[dict[str, Any]]
    review_report: NotRequired[str]
    blockers: NotRequired[list[dict[str, Any]]]
    _gate_result: NotRequired[str]
    _human_decision: NotRequired[str]
