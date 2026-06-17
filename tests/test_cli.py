from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from uni_dev.main import cli


class TestCliHelp:
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "run" in result.output
        assert "listen" in result.output
        assert "status" in result.output
        assert "watch" in result.output
        assert "resume" in result.output

    def test_no_old_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "approve" not in result.output
        assert "reject" not in result.output
        assert "retry" not in result.output


class TestWatchHelp:
    def test_watch_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--poll-interval" in result.output
        assert "--no-tui" in result.output
        assert "--db" in result.output


class TestResumeHelp:
    def test_resume_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["resume", "--help"])
        assert result.exit_code == 0
        assert "THREAD_ID" in result.output
        assert "--decision" in result.output


class TestCliRun:
    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    @patch("uni_dev.core.test_command.resolve_test_command")
    def test_run_with_test_cmd(self, mock_resolve, mock_config_cls, mock_pipeline):
        runner = CliRunner()
        mock_resolve.return_value = "mvn test"
        mock_config = MagicMock()
        mock_config_cls.from_env.return_value = mock_config
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {"review_report": "done"}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(cli, ["run", "Test issue", "--test-cmd", "mvn test"])
        assert result.exit_code == 0 or "Pipeline" in result.output


class TestCliResume:
    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_resume_command(self, mock_config_cls, mock_pipeline):
        runner = CliRunner()
        mock_config = MagicMock()
        mock_config_cls.from_env.return_value = mock_config
        mock_pipeline_instance = MagicMock()
        mock_pipeline_instance.invoke.return_value = {"review_report": "done"}
        mock_pipeline.return_value = mock_pipeline_instance

        result = runner.invoke(
            cli,
            ["resume", "thread-123", "--decision", "approve"],
            input="",
        )
        assert "Resuming" in result.output or result.exit_code == 0
