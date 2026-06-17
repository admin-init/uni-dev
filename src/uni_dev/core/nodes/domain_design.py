from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def domain_design_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase node: delegates to domain-designer sub-agent."""
    from uni_dev.orchestrator import _create_model, _MODEL_MAP, _MODEL_TEMPERATURE_MAP
    from deepagents import create_deep_agent
    from uni_dev.agents.domain_designer import DOMAIN_DESIGNER_SYSTEM_PROMPT

    issue = state.get("issue", "")
    project_path = state.get("project_path", ".")

    agent = create_deep_agent(
        model=_create_model(
            model=_MODEL_MAP["domain_designer"],
            base_url="https://api.deepseek.com",
            api_key="",
            temperature=_MODEL_TEMPERATURE_MAP["domain_designer"],
            reasoning_effort="high",
            thinking={"type": "enabled"},
        ),
        system_prompt=DOMAIN_DESIGNER_SYSTEM_PROMPT,
    )

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
