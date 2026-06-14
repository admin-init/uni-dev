from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click


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


if __name__ == "__main__":
    cli()
