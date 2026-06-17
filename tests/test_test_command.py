from __future__ import annotations

import tempfile
from pathlib import Path

from uni_dev.core.test_command import (
    auto_detect_test_command,
    resolve_test_command,
)


class TestResolveTestCommand:
    def test_cli_flag_takes_priority(self):
        result = resolve_test_command("npm test", "/some/path")
        assert result == "npm test"

    def test_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".uni-dev"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            config_file.write_text("test_command: gradle test\n")
            result = resolve_test_command(None, tmpdir)
            assert result == "gradle test"

    def test_auto_detect_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = resolve_test_command(None, tmpdir)
            assert result == "pytest"


class TestAutoDetectTestCommand:
    def test_maven_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pom.xml").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "mvn test"

    def test_gradle_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "build.gradle").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "gradle test"

    def test_gradle_kts_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "build.gradle.kts").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "gradle test"

    def test_python_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "pyproject.toml").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "pytest"

    def test_python_setup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "setup.py").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "pytest"

    def test_nodejs_project(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "package.json").touch()
            result = auto_detect_test_command(tmpdir)
            assert result == "npm test"

    def test_unknown_defaults_to_pytest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = auto_detect_test_command(tmpdir)
            assert result == "pytest"
