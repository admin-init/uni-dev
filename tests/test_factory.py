from __future__ import annotations

import os
from unittest.mock import patch

from uni_dev.core.factory import PipelineConfig


class TestPipelineConfig:
    def test_default_values(self):
        config = PipelineConfig()
        assert config.api_key == ""
        assert config.base_url == "https://api.deepseek.com"
        assert config.test_command == "pytest"
        assert config.monitor_db_path == ".uni-kb/monitor.db"
        assert config.langsmith_enabled is False

    def test_from_env(self):
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://custom.api.com",
        }):
            config = PipelineConfig.from_env()
            assert config.api_key == "sk-test"
            assert config.base_url == "https://custom.api.com"

    def test_from_env_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            os.environ.pop("DEEPSEEK_BASE_URL", None)
            config = PipelineConfig.from_env()
            assert config.api_key == ""
            assert config.base_url == "https://api.deepseek.com"

    def test_custom_values(self):
        config = PipelineConfig(
            api_key="sk-custom",
            base_url="https://custom.com",
            test_command="mvn test",
            monitor_db_path=None,
            langsmith_enabled=True,
        )
        assert config.api_key == "sk-custom"
        assert config.test_command == "mvn test"
        assert config.monitor_db_path is None
        assert config.langsmith_enabled is True
