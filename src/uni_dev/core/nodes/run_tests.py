from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


def run_tests_node(state: dict[str, Any]) -> dict[str, Any]:
    """Execute tests via shell. Captures exit code and output."""
    project_path = state.get("project_path", ".")

    try:
        result = subprocess.run(
            ["pytest", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            cwd=project_path,
            timeout=300,
        )
        test_results = {
            "pass": result.returncode == 0,
            "exit_code": result.returncode,
            "output": result.stdout + result.stderr,
            "failures": _parse_failures(result.stdout),
        }
    except subprocess.TimeoutExpired:
        test_results = {
            "pass": False,
            "exit_code": -1,
            "output": "Test execution timed out (300s)",
            "failures": ["timeout"],
        }
    except FileNotFoundError:
        test_results = {
            "pass": False,
            "exit_code": -1,
            "output": "pytest not found",
            "failures": ["pytest_not_found"],
        }

    return {"test_results": test_results}


def _parse_failures(output: str) -> list[str]:
    """Extract failure summaries from pytest output."""
    failures = []
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("FAILED") or line.startswith("E "):
            failures.append(line)
    return failures
