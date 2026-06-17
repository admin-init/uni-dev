"""OutputCleanerMiddleware — LLM output format cleaning for uni-dev.

Removes markdown code block markers and fixes common JSON escape
sequences in model responses.
"""

from __future__ import annotations

import re
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
)

class OutputCleanerMiddleware(AgentMiddleware[AgentState, Any, Any]):
    """Cleans LLM output format: removes markdown markers, fixes JSON escapes."""

    _MARKDOWN_BLOCK_RE = re.compile(
        r"^```(?:\w+)?\n?|\n?```$", re.MULTILINE
    )
    _ESCAPE_FIXES = [
        (r'\n', '\n'),
        (r'\t', '\t'),
        (r'\"', '"'),
    ]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Any,
    ) -> Any:
        """Clean the model response after it returns.

        Args:
            request: The model call request.
            handler: The wrapped handler to call for actual execution.

        Returns:
            The model response with cleaned content.
        """
        response = handler(request)
        if hasattr(response, "content") and isinstance(response.content, str):
            response.content = self._clean(response.content)
        return response

    def _clean(self, text: str) -> str:
        """Remove markdown blocks and fix escape sequences.

        Args:
            text: Raw model output.

        Returns:
            Cleaned text.
        """
        text = self._MARKDOWN_BLOCK_RE.sub("", text).strip()
        for pattern, replacement in self._ESCAPE_FIXES:
            if pattern in text:
                text = text.replace(pattern, replacement)
        return text
