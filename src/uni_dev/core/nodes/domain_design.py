from __future__ import annotations

import logging
from typing import Any, Callable

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def make_domain_design_node(
    config: Any,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create domain_design_node with config baked in."""
    from deepagents import create_deep_agent
    from deepagents.middleware.filesystem import FilesystemMiddleware

    from uni_dev.agents.domain_designer import DOMAIN_DESIGNER_SYSTEM_PROMPT
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
                model=_MODEL_MAP["domain_designer"],
                base_url=config.base_url,
                api_key=config.api_key,
                temperature=_MODEL_TEMPERATURE_MAP["domain_designer"],
                reasoning_effort="high",
                thinking={"type": "enabled"},
            ),
            system_prompt=DOMAIN_DESIGNER_SYSTEM_PROMPT,
            middleware=[
                FilesystemMiddleware(),
                OutputCleanerMiddleware(),
                CostTrackingMiddleware(),
                SecurityFilterMiddleware(),
            ],
        )

        issue = state.get("issue", "")
        project_path = state.get("project_path", ".")

        result = agent.invoke({
            "messages": [HumanMessage(
                f"Issue: {issue}\n"
                f"Project path: {project_path}\n"
                f"Analyze domain entities, aggregates, bounded contexts."
            )]
        })

        messages = result.get("messages", [])
        domain_model = ""
        if messages:
            last = messages[-1]
            domain_model = getattr(last, "content", str(last))

        return {"domain_model": domain_model}

    return node
