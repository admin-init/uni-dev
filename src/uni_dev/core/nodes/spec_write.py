from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def make_spec_write_node(
    config: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create spec_write_node with config baked in."""
    from deepagents import create_deep_agent
    from deepagents.middleware.filesystem import FilesystemMiddleware

    from uni_dev.agents.spec_writer import SPEC_WRITER_SYSTEM_PROMPT
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
                model=_MODEL_MAP["spec_writer"],
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=_MODEL_TEMPERATURE_MAP["spec_writer"],
            ),
            system_prompt=SPEC_WRITER_SYSTEM_PROMPT,
            middleware=[
                FilesystemMiddleware(),
                OutputCleanerMiddleware(),
                CostTrackingMiddleware(),
                SecurityFilterMiddleware(),
            ],
        )

        issue = state.get("issue", "")
        project_path = state.get("project_path", ".")
        domain_model = state.get("domain_model", "")

        result = agent.invoke({
            "messages": [HumanMessage(
                f"Issue: {issue}\n"
                f"Project path: {project_path}\n"
                f"Domain model:\n{domain_model}\n"
                f"Write OpenAPI 3.0 YAML specification."
            )]
        })

        messages = result.get("messages", [])
        api_spec = ""
        if messages:
            last = messages[-1]
            api_spec = getattr(last, "content", str(last))

        return {"api_spec": api_spec}

    return node
