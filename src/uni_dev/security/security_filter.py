from __future__ import annotations

from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ToolCallRequest,
)
from langgraph.prebuilt.tool_node import ToolCallWrapper

from uni_dev.security.log_filter import LogFilter

class SecurityFilterMiddleware(AgentMiddleware[AgentState, Any, Any]):
    """Middleware that redacts PII/secrets from tool call args and results."""

    def __init__(self) -> None:
        super().__init__()
        self._filter = LogFilter()

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: ToolCallWrapper,
    ) -> Any:
        """Redact sensitive data from tool call arguments and results."""
        tool_call = request.tool_call
        args = tool_call.get("args", {})

        filtered_args = self._filter.filter_dict(args)
        tool_call["args"] = filtered_args

        result = handler(request)

        if hasattr(result, "content") and isinstance(result.content, str):
            result.content = self._filter.filter_text(result.content)

        return result
