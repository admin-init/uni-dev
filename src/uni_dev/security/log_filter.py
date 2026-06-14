"""Log filter middleware for PII and secret redaction.

Intercepts tool call arguments and results to redact sensitive
information before it reaches logs, intermediate sub-agent outputs,
or the knowledge base.

Plugs into deepagent middleware as a tool-call wrapper.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS: list[tuple[str, str]] = [
    (r"REDIS_URL[=:]\s*[^\s]+", "REDIS_URL=<REDACTED>"),
    (r"postgresql://[^@\s]+@", "postgresql://<CREDENTIALS>@"),
    (r"mongodb://[^@\s]+@", "mongodb://<CREDENTIALS>@"),
    (r"Bearer\s+[A-Za-z0-9\-._~+/=]+", "Bearer <REDACTED>"),
    (r"api[_-]?key[=:]\s*[^\s&]+", "api_key=<REDACTED>"),
    (r"password[=:]\s*[^\s&]+", "password=<REDACTED>"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "<EMAIL>"),
]


class LogFilter:
    """Redact PII, secrets, and credentials from agent I/O.

    Applies regex-based pattern substitution to text. Used as a
    deepagent middleware hook wrapping tool call arguments and results.
    """

    def filter_text(self, text: Any) -> Any:
        """Filter a single text value, redacting sensitive patterns.

        Args:
            text: A string to filter, or any non-string value (returned as-is).

        Returns:
            Filtered string with secrets redacted, or the original
            value if not a string.
        """
        if not isinstance(text, str):
            return text
        for pattern, replacement in _PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def filter_dict(self, data: Any) -> Any:
        """Recursively filter all string values in a nested structure.

        Args:
            data: A dict, list, or other value to filter.

        Returns:
            Structure with all string values redacted.
        """
        if isinstance(data, dict):
            return {k: self.filter_dict(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.filter_dict(item) for item in data]
        return self.filter_text(data)
