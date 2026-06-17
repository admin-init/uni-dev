from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from uni_dev.runner import IssueRunner


class TestIssueRunner:
    def test_runner_start_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "issues.db")
            runner = IssueRunner(db_path, 1)
            runner.start()
            assert runner.running is True
            runner.stop()
            assert runner.running is False

    def test_runner_run_one_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "issues.db")
            runner = IssueRunner(db_path, 1)
            result = runner.run_one()
            assert result is None

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_runner_run_one_processes(self, mock_config_cls, mock_pipeline):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "issues.db")
            runner = IssueRunner(db_path, 1)
            runner._store.insert_issue({
                "title": "Test issue",
                "body": "Test body",
                "source": "test",
            })

            mock_config = MagicMock()
            mock_config_cls.from_env.return_value = mock_config
            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.invoke.return_value = {"review_report": "approved"}
            mock_pipeline.return_value = mock_pipeline_instance

            result = runner.run_one()
            assert result is not None
            assert result["status"] == "completed"

    @patch("uni_dev.core.graph.compile_pipeline")
    @patch("uni_dev.core.factory.PipelineConfig")
    def test_runner_failed_issue(self, mock_config_cls, mock_pipeline):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "issues.db")
            runner = IssueRunner(db_path, 1)
            runner._store.insert_issue({
                "title": "Test issue",
                "body": "Test body",
                "source": "test",
            })

            mock_config = MagicMock()
            mock_config_cls.from_env.return_value = mock_config
            mock_pipeline.side_effect = Exception("API error")

            result = runner.run_one()
            assert result is not None
            assert result["status"] == "failed"
            assert "API error" in result["error"]
