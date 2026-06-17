from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def review_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase node: delegates to reviewer sub-agent."""
    from uni_dev.orchestrator import _create_model, _MODEL_MAP, _MODEL_TEMPERATURE_MAP
    from deepagents import create_deep_agent
    from uni_dev.agents.reviewer import REVIEWER_SYSTEM_PROMPT

    issue = state.get("issue", "")
    project_path = state.get("project_path", ".")
    api_spec = state.get("api_spec", "")
    modified_files = state.get("modified_files", [])
    test_results = state.get("test_results", {})

    agent = create_deep_agent(
        model=_create_model(
            model=_MODEL_MAP["reviewer"],
            base_url="https://api.deepseek.com",
            api_key="",
            temperature=_MODEL_TEMPERATURE_MAP["reviewer"],
            thinking={"type": "enabled"},
        ),
        system_prompt=REVIEWER_SYSTEM_PROMPT,
    )

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
