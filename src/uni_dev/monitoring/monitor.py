"""MonitorMiddleware — pipeline observability for uni-dev.

Intercepts all tool calls and records structured TaskRun records
for sub-agent task() delegation. Provides three output channels:
1. LangGraph state (task_runs field, append-only)
2. SQLite persistence (via MonitorStore)
3. Structured logging + custom stream events
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Annotated, Any, NotRequired

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ToolCallRequest,
)
from langgraph.prebuilt.tool_node import ToolCallWrapper
from langgraph.types import Command

from uni_dev.monitoring.store import MonitorStore

logger = logging.getLogger("uni_dev.monitor")


def _task_run_reducer(
    existing: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reducer that concatenates task run lists."""
    return (existing or []) + (new or [])


class MonitorState(AgentState):
    """State schema for the monitor middleware."""

    task_runs: Annotated[
        NotRequired[list[dict[str, Any]]],
        _task_run_reducer,
    ]


class MonitorMiddleware(AgentMiddleware[MonitorState, Any, Any]):
    """Middleware that records all tool calls and tracks sub-agent task delegation.

    Args:
        db_path: Path to the SQLite database file. If provided, runs
            are persisted across sessions. Use None for in-memory only.
        context: Optional parent context name (e.g. "orchestrator").
    """

    state_schema = MonitorState

    def __init__(
        self,
        db_path: str | None = None,
        context: str = "orchestrator",
    ) -> None:
        super().__init__()
        self._store = MonitorStore(db_path) if db_path else None
        self._context = context
        self._stream_writer: Any = None

    def before_agent(
        self, state: Any, runtime: Any
    ) -> dict[str, Any] | None:
        """Capture stream writer reference for stream events.

        Args:
            state: Current agent state.
            runtime: LangGraph runtime context.

        Returns:
            None — no state modification.
        """
        self._stream_writer = getattr(runtime, "stream_writer", None)
        return None

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: ToolCallWrapper,
    ) -> Any:
        """Intercept all tool calls. For task(), create TaskRun records.

        Args:
            request: The tool call request with tool_call, state, runtime.
            handler: The wrapped handler to call for actual execution.

        Returns:
            ToolMessage or Command from the handler.
        """
        tool_name = request.tool_call.get("name", "unknown")
        tool_args = request.tool_call.get("args", {})

        if tool_name != "task":
            logger.debug("Tool call: %s", tool_name)
            return handler(request)

        subagent_type = tool_args.get("subagent_type", "unknown")
        description = tool_args.get("description", "")
        run_id = uuid.uuid4().hex[:12]
        started_at = time.time()

        run: dict[str, Any] = {
            "run_id": run_id,
            "subagent_type": subagent_type,
            "description": description,
            "parent_agent": self._context,
            "started_at": started_at,
            "completed_at": None,
            "duration_ms": None,
            "status": "running",
            "error": None,
            "result_length": None,
        }

        self._emit("task_start", run)
        logger.info("Task %s#%s: dispatching", subagent_type, run_id)

        try:
            result = handler(request)
            completed_at = time.time()
            run["completed_at"] = completed_at
            run["duration_ms"] = int((completed_at - started_at) * 1000)
            run["status"] = "success"

            content = ""
            if isinstance(result, Command):
                update = getattr(result, "update", None)
                if isinstance(update, dict):
                    msgs = update.get("messages", [])
                    if msgs:
                        content = getattr(msgs[0], "content", "")
            elif hasattr(result, "content"):
                content = getattr(result, "content", "")
            run["result_length"] = len(str(content)) if content else 0

        except Exception as exc:
            completed_at = time.time()
            run["completed_at"] = completed_at
            run["duration_ms"] = int((completed_at - started_at) * 1000)
            run["status"] = "error"
            run["error"] = str(exc)
            logger.error(
                "Task %s#%s: error — %s", subagent_type, run_id, exc
            )
            self._emit("task_end", run)
            self._persist(run)
            return Command(update={"task_runs": [run]})

        logger.info(
            "Task %s#%s: success in %dms (%d chars)",
            subagent_type,
            run_id,
            run["duration_ms"],
            run["result_length"],
        )

        self._emit("task_end", run)
        self._persist(run)

        if isinstance(result, Command):
            current_update = getattr(result, "update", None)
            if isinstance(current_update, dict):
                result = Command(
                    update={
                        **current_update,
                        "task_runs": [run],
                    }
                )
            else:
                result = Command(
                    update={"task_runs": [run], **(current_update or {})}
                )
        else:
            result = Command(
                update={
                    "messages": [result],
                    "task_runs": [run],
                }
            )

        return result

    def after_agent(
        self, state: Any, runtime: Any
    ) -> dict[str, Any] | None:
        """Log session summary after agent completes.

        Args:
            state: Final agent state.
            runtime: LangGraph runtime context.

        Returns:
            None — no state modification.
        """
        runs = getattr(state, "get", None)
        if callable(runs):
            task_runs = runs("task_runs", [])
        elif isinstance(state, dict):
            task_runs = state.get("task_runs", [])
        else:
            task_runs = []

        total = len(task_runs)
        success = sum(1 for r in task_runs if r.get("status") == "success")
        errors = sum(1 for r in task_runs if r.get("status") == "error")

        logger.info(
            "Session complete: %d tasks (%d success, %d errors)",
            total,
            success,
            errors,
        )

        self._emit(
            "session_end",
            {"total": total, "success": success, "errors": errors},
        )
        return None

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        """Emit a custom stream event if stream_writer is available.

        Args:
            event: Event name.
            data: Event payload dict.
        """
        writer = self._stream_writer
        if writer is not None:
            try:
                writer((event, data))
            except Exception:
                pass

    def _persist(self, run: dict[str, Any]) -> None:
        """Persist a TaskRun to the SQLite store if configured.

        Args:
            run: TaskRun dict.
        """
        if self._store is not None:
            try:
                self._store.insert_run(run)
            except Exception as exc:
                logger.warning("Failed to persist run %s: %s", run.get("run_id"), exc)
