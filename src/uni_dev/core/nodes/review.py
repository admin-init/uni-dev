from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def make_review_node(
    config: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create review_node with config baked in."""
    from deepagents import create_deep_agent
    from deepagents.middleware.filesystem import FilesystemMiddleware

    from uni_dev.agents.reviewer import REVIEWER_SYSTEM_PROMPT
    from uni_dev.middleware import CostTrackingMiddleware, OutputCleanerMiddleware
    from uni_dev.orchestrator import (
        _MODEL_MAP,
        _MODEL_TEMPERATURE_MAP,
        _create_model,
    )
    from uni_dev.security import SecurityFilterMiddleware

    def node(state: dict[str, Any]) -> dict[str, Any]:
        agent = create_deep_agent(
            model=_create_model(
                model=_MODEL_MAP["reviewer"],
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=_MODEL_TEMPERATURE_MAP["reviewer"],
                thinking={"type": "enabled"},
            ),
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            middleware=[
                FilesystemMiddleware(),
                OutputCleanerMiddleware(),
                CostTrackingMiddleware(),
                SecurityFilterMiddleware(),
            ],
        )

        issue = state.get("issue", "")
        project_path = state.get("project_path", ".")
        api_spec = state.get("api_spec", "")
        modified_files = state.get("modified_files", [])
        test_results = state.get("test_results", {})

        result = agent.invoke({
            "messages": [HumanMessage(
                f"Issue: {issue}\n"
                f"Project path: {project_path}\n"
                f"API spec:\n{api_spec}\n"
                f"Modified files: {modified_files}\n"
                f"Test results: {test_results}\n"
                f"Review implementation against spec."
            )]
        })

        messages = result.get("messages", [])
        review_report = ""
        if messages:
            last = messages[-1]
            review_report = getattr(last, "content", str(last))

        return {"review_report": review_report}

    return node
