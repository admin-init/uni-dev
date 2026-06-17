from __future__ import annotations

import os
from dataclasses import dataclass

import yaml

DEFAULT_ISSUES_DB = ".uni-kb/issues.db"
DEFAULT_CHECKPOINTS_DB = ".uni-dev/checkpoints.db"
DEFAULT_MONITOR_DB = ".uni-kb/monitor.db"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    test_command: str = "pytest"
    monitor_db_path: str | None = DEFAULT_MONITOR_DB
    langsmith_enabled: bool = False

    @classmethod
    def from_env(cls) -> PipelineConfig:
        """Create config from environment variables."""
        return cls(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )

    @classmethod
    def from_yaml(cls, path: str) -> PipelineConfig:
        """Load config from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        model_cfg = data.get("model", {})
        return cls(
            api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            base_url=model_cfg.get("base_url", "https://api.deepseek.com"),
            langsmith_enabled=data.get("tracing", {}).get("enabled", False),
        )
