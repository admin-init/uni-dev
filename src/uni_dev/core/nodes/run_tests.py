from __future__ import annotations

import subprocess
from typing import Any, Callable

def make_run_tests_node(config: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create run_tests_node with config baked in."""

    def node(state: dict[str, Any]) -> dict[str, Any]:
        project_path = state.get("project_path", ".")
        test_cmd = config.test_command

        try:
            cmd_parts = test_cmd.split()
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                cwd=project_path,
                timeout=300,
            )
            test_results = {
                "pass": result.returncode == 0,
                "exit_code": result.returncode,
                "output": result.stdout + result.stderr,
                "failures": _parse_failures(
                    result.stdout + result.stderr, test_cmd
                ),
            }
        except subprocess.TimeoutExpired:
            test_results = {
                "pass": False,
                "exit_code": -1,
                "output": f"Test execution timed out (300s): {test_cmd}",
                "failures": ["timeout"],
            }
        except FileNotFoundError:
            test_results = {
                "pass": False,
                "exit_code": -1,
                "output": f"Command not found: {test_cmd}",
                "failures": ["command_not_found"],
            }

        return {"test_results": test_results}

    return node


def _parse_failures(output: str, test_cmd: str) -> list[str]:
    """Extract failure summaries from test output."""
    failures: list[str] = []

    if "pytest" in test_cmd or "pytest" in output:
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("FAILED") or line.startswith("E "):
                failures.append(line)
    elif "mvn" in test_cmd or "maven" in test_cmd.lower():
        for line in output.splitlines():
            line = line.strip()
            if "FAILURE" in line or "ERROR" in line:
                failures.append(line)
            if line.startswith("[ERROR]"):
                failures.append(line)
    elif "gradle" in test_cmd:
        for line in output.splitlines():
            line = line.strip()
            if "FAILED" in line or "FAILURE" in line:
                failures.append(line)
    else:
        for line in output.splitlines():
            line = line.strip()
            if "FAIL" in line or "ERROR" in line:
                failures.append(line)

    return failures[:20]
