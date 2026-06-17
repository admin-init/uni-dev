from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def resolve_test_command(
    cli_flag: str | None,
    project_path: str,
) -> str:
    """Resolve test command with priority: CLI > config file > auto-detect.

    Args:
        cli_flag: Explicit --test-cmd from CLI.
        project_path: Path to the target project.

    Returns:
        Resolved test command string.
    """
    if cli_flag:
        return cli_flag

    config_path = Path(project_path) / ".uni-dev" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            if cmd := cfg.get("test_command"):
                logger.info("Using test_command from config: %s", cmd)
                return cmd
        except Exception as e:
            logger.warning("Failed to read config.yaml: %s", e)

    return auto_detect_test_command(project_path)


def auto_detect_test_command(project_path: str) -> str:
    """Auto-detect test command from project files.

    Args:
        project_path: Path to the target project.

    Returns:
        Detected test command string.
    """
    p = Path(project_path)

    if (p / "pom.xml").exists():
        logger.info("Detected Maven project, using 'mvn test'")
        return "mvn test"

    if (p / "build.gradle").exists() or (p / "build.gradle.kts").exists():
        logger.info("Detected Gradle project, using 'gradle test'")
        return "gradle test"

    if (p / "pyproject.toml").exists() or (p / "setup.py").exists():
        logger.info("Detected Python project, using 'pytest'")
        return "pytest"

    if (p / "package.json").exists():
        logger.info("Detected Node.js project, using 'npm test'")
        return "npm test"

    logger.warning("Could not detect test framework, defaulting to 'pytest'")
    return "pytest"
