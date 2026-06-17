from __future__ import annotations

import logging
import os
import subprocess
import sys
import uuid
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


def _get_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver

    db_path = Path(".uni-dev/checkpoints.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(db_path))


@cli.command()
@click.argument("issue")
@click.option(
    "-c", "--classify", default=None,
    type=click.Choice(["add_feature", "update_api", "remove_feature", "refactor"]),
    help="Issue classification.",
)
@click.option(
    "--thread-id", default=None,
    help="Thread ID for checkpointing (auto-generated if omitted).",
)
def run(issue: str, classify: str | None, thread_id: str | None) -> None:
    """Run the DDD->SDD->TDD pipeline for an issue."""
    from uni_dev.core.graph import compile_pipeline

    thread_id = thread_id or uuid.uuid4().hex[:12]
    click.echo(f"Running pipeline for: {issue}")
    click.echo(f"Thread ID: {thread_id}")
    if classify:
        click.echo(f"Classification: {classify}")

    checkpointer = _get_checkpointer()
    pipeline = compile_pipeline(checkpointer=checkpointer)

    state = {
        "issue": issue,
        "project_path": str(Path.cwd()),
        "classification": classify or "add_feature",
        "attempt_count": 0,
    }
    config = {"configurable": {"thread_id": thread_id}}

    click.echo("Invoking pipeline...")
    try:
        result = pipeline.invoke(state, config)
        click.echo("\nPipeline completed.")
        click.echo(f"Domain model: {'yes' if result.get('domain_model') else 'no'}")
        click.echo(f"API spec: {'yes' if result.get('api_spec') else 'no'}")
        click.echo(f"Test files: {len(result.get('test_files', []))}")
        click.echo(f"Modified files: {len(result.get('modified_files', []))}")
        click.echo(f"Review report: {'yes' if result.get('review_report') else 'no'}")
    except Exception as e:
        click.echo(f"\nPipeline interrupted: {e}")
        click.echo(f"Resume with: uni-dev resume {thread_id}")


@cli.command()
@click.argument("thread_id")
@click.option(
    "--decision",
    type=click.Choice(["approve", "reject", "retry"]),
    prompt="Decision",
    help="Human decision for the interrupted pipeline.",
)
def resume(thread_id: str, decision: str) -> None:
    """Resume a paused pipeline from checkpoint."""
    from uni_dev.core.graph import compile_pipeline

    checkpointer = _get_checkpointer()
    pipeline = compile_pipeline(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    click.echo(f"Resuming pipeline {thread_id} with decision: {decision}")
    try:
        result = pipeline.invoke(
            {"_human_decision": decision},
            config,
        )
        click.echo("\nPipeline resumed and completed.")
        click.echo(f"Review report: {'yes' if result.get('review_report') else 'no'}")
    except Exception as e:
        click.echo(f"\nPipeline interrupted again: {e}")
        click.echo(f"Resume with: uni-dev resume {thread_id}")


@cli.command()
@click.option("-p", "--port", default=8080, type=int, help="Port to bind to.")
@click.option("-h", "--host", default="0.0.0.0", help="Host to bind to.")
@click.option("-s", "--secret", envvar="WEBHOOK_SECRET", default=None, help="Webhook HMAC secret.")
def listen(port: int, host: str, secret: str | None) -> None:
    """Start the webhook listener server."""
    import uvicorn

    if secret:
        os.environ["WEBHOOK_SECRET"] = secret
    elif "WEBHOOK_SECRET" not in os.environ:
        click.echo("Warning: WEBHOOK_SECRET not set. Webhook signature validation disabled.")
    from uni_dev.webhooks.server import create_app

    app = create_app()
    click.echo(f"Starting webhook listener on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


@cli.command()
@click.option("-d", "--db", default=".uni-kb/monitor.db", help="Path to monitor SQLite database.")
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
            click.echo(f"{run['subagent_type']:<22} {run['status']:<10} {duration_str:>8}  {run['run_id']:<14}")


@cli.command()
@click.option("--poll-interval", '-i', default=5, type=int, help="Seconds between poll (default: 5).")
@click.option("--no-tui", is_flag=True, default=False, help="Run headless (no dashboard).")
@click.option("--db", default=".uni-kb/issues.db", help="IssueStore database path.")
@click.option("--monitor-db", default=".uni-kb/monitor.db", help="MonitorStore database path.")
def watch(poll_interval: int, no_tui: bool, db: str, monitor_db: str) -> None:
    """Start continuous pipeline runner with TUI dashboard."""
    from uni_dev.runner import IssueRunner

    runner = IssueRunner(db, poll_interval)
    runner.start()
    click.echo(f"Runner started (poll every {poll_interval}s, db={db})")

    if no_tui:
        click.echo("Running headless. Press Ctrl+C to stop.")
        try:
            while runner.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        runner.stop()
    else:
        from uni_dev.tui.app import UniDevApp
        app = UniDevApp(db, poll_interval)
        app._runner = runner
        app.run()


if __name__ == "__main__":
    cli()
