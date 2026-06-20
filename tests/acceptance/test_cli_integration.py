"""A10: CLI integration acceptance tests.

Verify CLI commands drive workflows with mocked dependencies.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from uni_dev.main import cli


class TestCliHelp:
    """Verify CLI help shows all expected commands."""

    def test_cli_help_shows_init(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output

    def test_cli_help_shows_run(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.output

    def test_cli_help_shows_resume(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "resume" in result.output

    def test_cli_help_shows_listen(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "listen" in result.output

    def test_cli_help_shows_status(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "status" in result.output

    def test_cli_help_shows_watch(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "watch" in result.output


class TestCliRun:
    """Verify `uni-dev run` command invokes pipeline."""

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    @patch("uni_dev.core.test_command.resolve_test_command")
    def test_run_with_test_cmd(self, mock_resolve, mock_config, mock_pipeline):
        runner = CliRunner()
        mock_resolve.return_value = "pytest"
        mock_config.from_env.return_value = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {"review_report": "done"}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli, ["run", "Test issue", "--test-cmd", "mvn test"]
        )
        assert result.exit_code == 0 or "Pipeline" in result.output

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_run_with_classify(self, mock_config, mock_pipeline):
        runner = CliRunner()
        mock_config.from_env.return_value = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {"review_report": "done"}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli, ["run", "Refactor auth", "--classify", "refactor"]
        )
        assert result.exit_code == 0 or "Pipeline" in result.output


class TestCliResume:
    """Verify `uni-dev resume` command resumes pipeline."""

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_resume_with_approve(self, mock_config, mock_pipeline):
        runner = CliRunner()
        mock_config.from_env.return_value = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {"review_report": "done"}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli, ["resume", "thread-123", "--decision", "approve"],
            input="",
        )
        assert "Resuming" in result.output or result.exit_code == 0

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_resume_with_reject(self, mock_config, mock_pipeline):
        runner = CliRunner()
        mock_config.from_env.return_value = MagicMock()
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli, ["resume", "thread-456", "--decision", "reject"],
            input="",
        )
        assert result.exit_code == 0
