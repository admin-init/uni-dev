from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def test_generate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase node: delegates to test-generator sub-agent."""
    from uni_dev.orchestrator import _create_model, _MODEL_MAP, _MODEL_TEMPERATURE_MAP
    from deepagents import create_deep_agent
    from uni_dev.agents.test_generator import TEST_GENERATOR_SYSTEM_PROMPT

    issue = state.get("issue", "")
    project_path = state.get("project_path", ".")
    api_spec = state.get("api_spec", "")

    agent = create_deep_agent(
        model=_create_model(
            model=_MODEL_MAP["test_generator"],
            base_url="https://api.deepseek.com",
            api_key="",
            temperature=_MODEL_TEMPERATURE_MAP["test_generator"],
        ),
        system_prompt=TEST_GENERATOR_SYSTEM_PROMPT,
    )

    result = agent.invoke({
        "messages": [HumanMessage(
            f"Issue: {issue}\n"
            f"Project path: {project_path}\n"
            f"API spec:\n{api_spec}\n"
            f"Generate contract + unit tests (TDD Red phase)."
        )]
    })

    messages = result.get("messages", [])
    test_files: list[str] = []
    if messages:
        last = messages[-1]
        content = getattr(last, "content", str(last))
        test_files = [content] if content else []

    return {"test_files": test_files}
