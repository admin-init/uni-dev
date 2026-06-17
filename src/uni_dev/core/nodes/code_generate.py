from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import HumanMessage

def make_code_generate_node(
    config: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create code_generate_node with config baked in."""
    from deepagents import create_deep_agent
    from deepagents.middleware.filesystem import FilesystemMiddleware

    from uni_dev.agents.code_generator import CODE_GENERATOR_SYSTEM_PROMPT
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
                model=_MODEL_MAP["code_generator"],
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=_MODEL_TEMPERATURE_MAP["code_generator"],
            ),
            system_prompt=CODE_GENERATOR_SYSTEM_PROMPT,
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
        test_files = state.get("test_files", [])
        test_results = state.get("test_results", {})
        attempt_count = state.get("attempt_count", 0)

        retry_context = ""
        if attempt_count > 0:
            failures = test_results.get("failures", [])
            if failures:
                retry_context = (
                    f"\nRetry attempt {attempt_count}. "
                    f"Previous failures:\n{failures}"
                )

        result = agent.invoke({
            "messages": [HumanMessage(
                f"Issue: {issue}\n"
                f"Project path: {project_path}\n"
                f"API spec:\n{api_spec}\n"
                f"Test files: {test_files}\n"
                f"Implement code to pass all tests "
                f"(TDD Green phase).{retry_context}"
            )]
        })

        messages = result.get("messages", [])
        modified_files: list[str] = []
        if messages:
            last = messages[-1]
            content = getattr(last, "content", str(last))
            modified_files = [content] if content else []

        return {"modified_files": modified_files}

    return node
