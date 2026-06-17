"""CostTrackingMiddleware — token/cost budget monitoring for uni-dev.

Tracks token usage from model response metadata and warns when
the cumulative total exceeds the configured budget.
"""

from __future__ import annotations

import logging
import time
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
)

logger = logging.getLogger(__name__)


def _usage_reducer(
    existing: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reducer that concatenates token usage lists."""
    return (existing or []) + (new or [])


class CostTrackingState(AgentState):
    """State schema for the cost tracking middleware."""

    token_usage: Annotated[
        NotRequired[list[dict[str, Any]]],
        _usage_reducer,
    ]


class CostTrackingMiddleware(
    AgentMiddleware[CostTrackingState, Any, Any]
):
    """Tracks token usage and cost per model call.

    Args:
        budget_tokens: Maximum allowed cumulative tokens before warning.
    """

    state_schema = CostTrackingState

    def __init__(self, budget_tokens: int = 1_000_000) -> None:
        super().__init__()
        self._budget_tokens = budget_tokens
        self._total_tokens = 0

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Any,
    ) -> Any:
        """Track token usage from model response metadata.

        Args:
            request: The model call request.
            handler: The wrapped handler to call for actual execution.

        Returns:
            The model response, unmodified.
        """
        response = handler(request)

        if hasattr(response, "response_metadata"):
            meta = response.response_metadata or {}
            token_usage = meta.get("token_usage", {})
            usage = {
                "prompt_tokens": token_usage.get("prompt_tokens", 0),
                "completion_tokens": token_usage.get(
                    "completion_tokens", 0
                ),
                "total_tokens": token_usage.get("total_tokens", 0),
                "model": meta.get("model_name", "unknown"),
                "timestamp": time.time(),
            }
            total = usage.get("total_tokens", 0)
            self._total_tokens += total

            if self._total_tokens > self._budget_tokens:
                logger.warning(
                    "Token budget exceeded: %d / %d",
                    self._total_tokens,
                    self._budget_tokens,
                )

        return response
