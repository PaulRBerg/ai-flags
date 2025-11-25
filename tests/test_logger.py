"""Tests for logging utilities."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_flags.logger import get_logger, log_handle


@pytest.fixture
def temp_log_dir(tmp_path, monkeypatch):
    """Use temporary log directory for tests."""
    temp_dir = tmp_path / "logs"
    monkeypatch.setattr("ai_flags.logger.LOG_DIR", temp_dir)
    # Clear any cached logger
    logger = logging.getLogger("ai-flags")
    logger.handlers.clear()
    return temp_dir


class TestGetLogger:
    """Test get_logger function."""

    def test_creates_log_directory(self, temp_log_dir):
        """Should create log directory if it doesn't exist."""
        assert not temp_log_dir.exists()
        get_logger()
        assert temp_log_dir.exists()

    def test_returns_logger_instance(self, temp_log_dir):
        """Should return a configured logger."""
        logger = get_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "ai-flags"

    def test_logger_has_handler(self, temp_log_dir):
        """Should configure logger with file handler."""
        logger = get_logger()
        assert len(logger.handlers) > 0

    def test_returns_same_logger_on_multiple_calls(self, temp_log_dir):
        """Should return the same configured logger on subsequent calls."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2
        # Should not add duplicate handlers
        assert len(logger1.handlers) == 1

    def test_handles_permission_error_gracefully(self, temp_log_dir, monkeypatch):
        """Should handle OSError gracefully when creating directory."""
        # Clear any cached logger
        logger = logging.getLogger("ai-flags")
        logger.handlers.clear()

        def raise_error(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "mkdir", raise_error)
        # Should not raise, just return logger without handlers
        result = get_logger()
        assert isinstance(result, logging.Logger)


class TestLogHandle:
    """Test log_handle function."""

    def test_logs_cli_mode_success(self, temp_log_dir):
        """Should log CLI mode success."""
        log_handle(
            mode="cli",
            flags=["c", "t"],
            cleaned_prompt="my task",
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "mode=cli" in content
        assert "flags=[c,t]" in content
        assert "my task" in content
        assert "OK" in content

    def test_logs_hook_mode_success(self, temp_log_dir):
        """Should log hook mode success."""
        log_handle(
            mode="hook",
            flags=["s"],
            cleaned_prompt="delegate task",
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        assert "mode=hook" in content
        assert "flags=[s]" in content
        assert "delegate task" in content
        assert "OK" in content

    def test_logs_error_with_message(self, temp_log_dir):
        """Should log error with message."""
        log_handle(
            mode="cli",
            flags=[],
            cleaned_prompt="task",
            success=False,
            error="No flags detected",
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        assert "ERROR: No flags detected" in content

    def test_logs_empty_flags_as_none(self, temp_log_dir):
        """Should log empty flags list as 'none'."""
        log_handle(
            mode="hook",
            flags=[],
            cleaned_prompt="no flags",
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        assert "flags=[none]" in content

    def test_truncates_long_prompts(self, temp_log_dir):
        """Should truncate prompts longer than 50 characters."""
        long_prompt = "a" * 100
        log_handle(
            mode="cli",
            flags=["c"],
            cleaned_prompt=long_prompt,
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        # Should have truncated prompt with ellipsis
        assert "a" * 50 + "..." in content
        assert "a" * 100 not in content

    def test_replaces_newlines_in_prompt(self, temp_log_dir):
        """Should replace newlines with spaces in prompt preview."""
        log_handle(
            mode="cli",
            flags=["c"],
            cleaned_prompt="line1\nline2\nline3",
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        assert "line1 line2 line3" in content
        assert "\n" not in content.split("|")[-2]  # Check just the prompt part

    def test_log_format_includes_timestamp(self, temp_log_dir):
        """Should include timestamp in log entries."""
        log_handle(
            mode="cli",
            flags=["c"],
            cleaned_prompt="task",
            success=True,
        )

        log_file = temp_log_dir / "handle.log"
        content = log_file.read_text()
        # Should have timestamp format YYYY-MM-DD HH:MM:SS
        import re

        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", content)

    def test_silent_when_logging_unavailable(self, temp_log_dir, monkeypatch):
        """Should not raise when logging is unavailable."""
        # Clear handlers to simulate unavailable logging
        logger = logging.getLogger("ai-flags")
        logger.handlers.clear()

        # Prevent get_logger from creating new handlers
        monkeypatch.setattr("ai_flags.logger.LOG_DIR", Path("/nonexistent/path"))

        # Should not raise
        log_handle(
            mode="cli",
            flags=["c"],
            cleaned_prompt="task",
            success=True,
        )


class TestLogIntegration:
    """Integration tests for logging with CLI."""

    def test_cli_logs_on_success(self, temp_log_dir, tmp_path, monkeypatch):
        """Should create log entry when handle command succeeds."""
        from click.testing import CliRunner
        from ai_flags.cli import cli
        from ai_flags.config_loader import save_config, get_default_config

        # Set up temp config
        temp_config_path = tmp_path / "config.yaml"
        temp_config_dir = tmp_path
        monkeypatch.setattr("ai_flags.config_loader.CONFIG_PATH", temp_config_path)
        monkeypatch.setattr("ai_flags.config_loader.CONFIG_DIR", temp_config_dir)
        monkeypatch.setattr("ai_flags.cli.CONFIG_PATH", temp_config_path)

        with patch("ai_flags.config_loader.CONFIG_PATH", temp_config_path):
            config = get_default_config()
            save_config(config)

        runner = CliRunner()
        result = runner.invoke(cli, ["handle", "task -c"])
        assert result.exit_code == 0

        log_file = temp_log_dir / "handle.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "mode=cli" in content
        assert "OK" in content
