"""Tests for main.py — CLI commands."""

from click.testing import CliRunner

from uni_dev.main import cli


def test_cli_version():
    """--version outputs version string."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_cli_help():
    """--help outputs usage text."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "run" in result.output
    assert "listen" in result.output
    assert "status" in result.output


def test_init_help():
    """uni-dev init --help shows options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--help"])
    assert result.exit_code == 0
    assert "PROJECT" in result.output


def test_init_missing_arg():
    """uni-dev init without argument shows error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code != 0


def test_run_help():
    """uni-dev run --help shows options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.output
    assert "--api-key" in result.output
    assert "--classify" in result.output
    assert "--no-monitor" in result.output


def test_run_missing_issue():
    """uni-dev run without issue argument shows error."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0


def test_listen_help():
    """uni-dev listen --help shows options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["listen", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--host" in result.output
    assert "--secret" in result.output


def test_status_help():
    """uni-dev status --help shows options."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--help"])
    assert result.exit_code == 0
    assert "--db" in result.output


def test_status_with_no_db():
    """uni-dev status with non-existent db shows zeros."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--db", "/tmp/nonexistent_uni_dev_test.db"])
    assert result.exit_code == 0
    assert "Total runs" in result.output
    assert "0" in result.output
