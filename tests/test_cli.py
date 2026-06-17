from __future__ import annotations

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
