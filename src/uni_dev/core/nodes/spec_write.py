from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def spec_write_node(state: dict[str, Any]) -> dict[str, Any]:
    """Phase node: delegates to spec-writer sub-agent."""
    from uni_dev.orchestrator import _create_model, _MODEL_MAP, _MODEL_TEMPERATURE_MAP
    from deepagents import create_deep_agent
    from uni_dev.agents.spec_writer import SPEC_WRITER_SYSTEM_PROMPT

    issue = state.get("issue", "")
    project_path = state.get("project_path", ".")
    domain_model = state.get("domain_model", "")

    agent = create_deep_agent(
        model=_create_model(
            model=_MODEL_MAP["spec_writer"],
            base_url="https://api.deepseek.com",
            api_key="",
            temperature=_MODEL_TEMPERATURE_MAP["spec_writer"],
        ),
        system_prompt=SPEC_WRITER_SYSTEM_PROMPT,
    )

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
