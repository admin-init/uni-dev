from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import HumanMessage

def make_test_generate_node(
    config: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create test_generate_node with config baked in."""
    from deepagents import create_deep_agent
    from deepagents.middleware.filesystem import FilesystemMiddleware

    from uni_dev.agents.test_generator import TEST_GENERATOR_SYSTEM_PROMPT
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
                model=_MODEL_MAP["test_generator"],
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=_MODEL_TEMPERATURE_MAP["test_generator"],
            ),
            system_prompt=TEST_GENERATOR_SYSTEM_PROMPT,
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

    return node
