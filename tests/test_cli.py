"""Tests for CLI commands (M8 + M10 additions)."""

from click.testing import CliRunner

from uni_dev.main import cli


def test_cli_help():
    """--help shows all commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "run" in result.output
    assert "listen" in result.output
    assert "status" in result.output
    assert "watch" in result.output
    assert "approve" in result.output
    assert "reject" in result.output
    assert "retry" in result.output


def test_watch_help():
    """watch --help shows options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["watch", "--help"])
    assert result.exit_code == 0
    assert "--poll-interval" in result.output
    assert "--no-tui" in result.output
    assert "--db" in result.output


def test_approve_help():
    """approve --help shows usage."""
    runner = CliRunner()
    result = runner.invoke(cli, ["approve", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output


def test_reject_help():
    """reject --help shows usage."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reject", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output


def test_retry_help():
    """retry --help shows usage."""
    runner = CliRunner()
    result = runner.invoke(cli, ["retry", "--help"])
    assert result.exit_code == 0
    assert "ISSUE_ID" in result.output


def test_approve_nonexistent():
    """approve on nonexistent issue returns error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["approve", "--db", "/tmp/nonexistent_test.db", "fakeid"])
    assert result.exit_code != 0


def test_reject_nonexistent():
    """reject on nonexistent issue returns error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["reject", "--db", "/tmp/nonexistent_test.db", "fakeid"])
    assert result.exit_code != 0


def test_retry_nonexistent():
    """retry on nonexistent issue returns error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["retry", "--db", "/tmp/nonexistent_test.db", "fakeid"])
    assert result.exit_code != 0
