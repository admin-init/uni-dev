from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import click

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(package_name="uni_dev")
def cli() -> None:
    """uni-dev — Multi-agent backend development automation."""


@cli.command()
@click.argument("project", type=click.Path(exists=True))
def init(project: str) -> None:
    """Initialize knowledge base for a project."""
    project_path = Path(project).resolve()
    click.echo(f"Initializing uni-dev for {project_path}...")
    result = subprocess.run(
        [sys.executable, "-m", "uni_kb.cli", "init", "--project", str(project_path)],
        capture_output=False,
    )
    if result.returncode != 0:
        click.echo("Initialization failed.", err=True)
        sys.exit(result.returncode)
    click.echo("Done.")


@cli.command()
@click.argument("issue")
@click.option(
    "-m", "--model",
    default="deepseek-v4-pro",
    help="Model for the orchestrator.",
)
@click.option(
    "-k", "--api-key",
    envvar="DEEPSEEK_API_KEY",
    default=None,
    help="DeepSeek API key.",
)
@click.option(
    "-c", "--classify",
    default=None,
    type=click.Choice(["add_feature", "update_api", "remove_feature", "refactor"]),
    help="Issue classification.",
)
@click.option(
    "--no-monitor",
    is_flag=True,
    default=False,
    help="Disable the monitor middleware.",
)
def run(issue: str, model: str, api_key: str | None, classify: str | None, no_monitor: bool) -> None:
    """Run the DDD→SDD→TDD pipeline for an issue."""
    from uni_dev.orchestrator import create_orchestrator

    click.echo(f"Running pipeline for: {issue}")
    if classify:
        click.echo(f"Classification: {classify}")

    monitor_db = None if no_monitor else ".uni-dev/monitor.db"

    orchestrator = create_orchestrator(
        api_key=api_key,
        monitor_db_path=monitor_db,
    )

    state = {
        "messages": [{"role": "user", "content": issue, "type": "human"}],
        "classification": classify or "add_feature",
        "attempt_count": 0,
        "test_results": {"pass": False, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "ddd",
        "kb_path": ".uni-dev",
    }

    click.echo("Invoking orchestrator...")
    result = orchestrator.invoke(state)
    messages = result.get("messages", [])
    last_msg = messages[-1] if messages else None

    if last_msg is not None:
        content = getattr(last_msg, "content", str(last_msg))
        click.echo(f"\nResult:\n{content}")

    task_runs = result.get("task_runs", [])
    if task_runs:
        click.echo(f"\nTask runs: {len(task_runs)}")
        for run in task_runs:
            click.echo(
                f"  {run['subagent_type']}: {run['status']} "
                f"({run.get('duration_ms', '?')}ms)"
            )


@cli.command()
@click.option(
    "-p", "--port",
    default=8080,
    type=int,
    help="Port to bind to.",
)
@click.option(
    "-h", "--host",
    default="0.0.0.0",
    help="Host to bind to.",
)
@click.option(
    "-s", "--secret",
    envvar="WEBHOOK_SECRET",
    default=None,
    help="Webhook HMAC secret.",
)
def listen(port: int, host: str, secret: str | None) -> None:
    """Start the webhook listener server."""
    import uvicorn

    if secret:
        os.environ["WEBHOOK_SECRET"] = secret
    elif "WEBHOOK_SECRET" not in os.environ:
        click.echo(
            "Warning: WEBHOOK_SECRET not set. "
            "Webhook signature validation disabled.",
        )

    from uni_dev.webhooks.server import create_app

    app = create_app()
    click.echo(f"Starting webhook listener on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


@cli.command()
@click.option(
    "-d", "--db",
    default=".uni-dev/monitor.db",
    help="Path to monitor SQLite database.",
)
def status(db: str) -> None:
    """Show pipeline status dashboard."""
    from uni_dev.monitoring.store import MonitorStore

    store = MonitorStore(Path(db))
    summary = store.summary()
    runs = store.query_runs(limit=20)

    click.echo("\n=== uni-dev Pipeline Status ===\n")
    click.echo(f"Total runs:   {summary['total']}")
    click.echo(f"Success:      {summary['success_count']}")
    click.echo(f"Errors:       {summary['error_count']}")
    click.echo(f"Running:      {summary['running_count']}")
    click.echo(f"Avg duration: {summary['avg_duration_ms']}ms")

    if runs:
        click.echo(f"\n{'Agent':<22} {'Status':<10} {'Duration':>8}  {'ID':<14}")
        click.echo("-" * 60)
        for run in runs:
            duration = run.get("duration_ms")
            duration_str = f"{duration}ms" if duration else "-"
            click.echo(
                f"{run['subagent_type']:<22} "
                f"{run['status']:<10} "
                f"{duration_str:>8}  "
                f"{run['run_id']:<14}"
            )


if __name__ == "__main__":
    cli()
