from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def code_generate_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase node: delegates to code-generator sub-agent."""
    from uni_dev.orchestrator import _create_model, _MODEL_MAP, _MODEL_TEMPERATURE_MAP
    from deepagents import create_deep_agent
    from uni_dev.agents.code_generator import CODE_GENERATOR_SYSTEM_PROMPT

    issue = state.get("issue", "")
    project_path = state.get("project_path", ".")
    api_spec = state.get("api_spec", "")
    test_files = state.get("test_files", [])
    test_results = state.get("test_results", {})
    attempt_count = state.get("attempt_count", 0)

    is_retry = attempt_count > 0
    failures = test_results.get("failures", [])

    agent = create_deep_agent(
        model=_create_model(
            model=_MODEL_MAP["code_generator"],
            base_url="https://api.deepseek.com",
            api_key="",
            temperature=_MODEL_TEMPERATURE_MAP["code_generator"],
        ),
        system_prompt=CODE_GENERATOR_SYSTEM_PROMPT,
    )

    retry_context = ""
    if is_retry and failures:
        retry_context = f"\nRetry attempt {attempt_count}. Previous failures:\n{failures}"

    result = agent.invoke({
        "messages": [HumanMessage(
            f"Issue: {issue}\n"
            f"Project path: {project_path}\n"
            f"API spec:\n{api_spec}\n"
            f"Test files: {test_files}\n"
            f"Implement code to pass all tests (TDD Green phase).{retry_context}"
        )]
    })

    messages = result.get("messages", [])
    modified_files: list[str] = []
    if messages:
        last = messages[-1]
        content = getattr(last, "content", str(last))
        modified_files = [content] if content else []

    return {"modified_files": modified_files}
