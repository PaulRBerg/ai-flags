"""Integration tests for CLI commands."""

import json
import pytest
from click.testing import CliRunner
from unittest.mock import patch

from ai_flags.cli import cli
from ai_flags.config_loader import save_config, get_default_config


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Use temporary config file for tests."""
    temp_config_path = tmp_path / "config.yaml"
    temp_config_dir = tmp_path
    monkeypatch.setattr("ai_flags.config_loader.CONFIG_PATH", temp_config_path)
    monkeypatch.setattr("ai_flags.config_loader.CONFIG_DIR", temp_config_dir)
    monkeypatch.setattr("ai_flags.cli.CONFIG_PATH", temp_config_path)

    # Create default config
    with patch("ai_flags.config_loader.CONFIG_PATH", temp_config_path):
        config = get_default_config()
        save_config(config)

    return temp_config_path


class TestHandleCommand:
    """Test 'ai-flags handle' command."""

    def test_cli_mode_single_flag(self, runner, temp_config):
        """Should process prompt argument with single flag."""
        result = runner.invoke(cli, ["handle", "task -c"])
        assert result.exit_code == 0
        # Verify output contains expected information
        assert "task" in result.output
        assert "-c" in result.output or "commit" in result.output.lower()

    def test_cli_mode_multiple_flags(self, runner, temp_config):
        """Should process prompt argument with multiple flags."""
        result = runner.invoke(cli, ["handle", "implement feature -c -t"])
        assert result.exit_code == 0
        assert "implement feature" in result.output
        assert "commit" in result.output.lower() or "test" in result.output.lower()

    def test_hook_mode_valid_input(self, runner, temp_config):
        """Should process hook JSON input correctly."""
        hook_input = {"prompt": "task -c", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        # Parse JSON output
        output = json.loads(result.output)
        assert "hookSpecificOutput" in output
        assert "additionalContext" in output["hookSpecificOutput"]
        assert "commit_instructions" in output["hookSpecificOutput"]["additionalContext"]

    def test_hook_mode_no_flags(self, runner, temp_config):
        """Should handle prompts without flags gracefully."""
        hook_input = {"prompt": "task without flags"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should return empty context
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_hook_mode_invalid_flags(self, runner, temp_config):
        """Should handle unrecognized flags gracefully."""
        hook_input = {"prompt": "task -x -y"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should return empty context (silent failure)
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_cli_mode_invalid_flags(self, runner, temp_config):
        """Should error on invalid flags in CLI mode."""
        result = runner.invoke(cli, ["handle", "task -x"])
        assert result.exit_code != 0

    def test_hook_mode_permission_mode_plan(self, runner, temp_config):
        """Should activate -s flag only in plan mode."""
        hook_input = {"prompt": "task -s", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should contain subagent instructions
        assert len(context) > 0
        assert "subagent" in context.lower()

    def test_hook_mode_permission_mode_normal(self, runner, temp_config):
        """Should skip -s flag when not in plan mode."""
        hook_input = {"prompt": "task -s", "permission_mode": "normal"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        # Should be empty (no -s in normal mode)
        assert context == ""

    def test_no_input_error(self, runner, temp_config):
        """Should error when no prompt provided and stdin is empty."""
        result = runner.invoke(cli, ["handle"])
        assert result.exit_code != 0

    def test_hook_mode_single_flag(self, runner, temp_config):
        """Test hook mode with single flag."""
        hook_input = {"prompt": "my task -c"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

        context = output["hookSpecificOutput"]["additionalContext"]
        assert "<flag_metadata>" in context
        assert "</flag_metadata>" in context
        assert "<commit_instructions>" in context
        assert "</commit_instructions>" in context
        assert "/commit" in context
        assert "my task" in context

    def test_hook_mode_multiple_flags_all(self, runner, temp_config):
        """Test hook mode with multiple valid flags."""
        hook_input = {"prompt": "my task -s -c -t", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "<flag_metadata>" in context
        assert "Processed flags -s -c -t" in context
        assert "my task" in context
        assert "</flag_metadata>" in context
        assert "<subagent_delegation>" in context
        assert "</subagent_delegation>" in context
        assert "<commit_instructions>" in context
        assert "/commit" in context
        assert "</commit_instructions>" in context
        assert "<test_instructions>" in context
        assert "</test_instructions>" in context

    def test_hook_mode_empty_prompt(self, runner, temp_config):
        """Test hook mode with empty prompt."""
        hook_input = {"prompt": ""}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should return empty context
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_hook_mode_missing_prompt_field(self, runner, temp_config):
        """Test hook mode with missing prompt field."""
        hook_input = {"other_field": "value"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should return empty context
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_hook_mode_invalid_json(self, runner, temp_config):
        """Test hook mode with invalid JSON input."""
        result = runner.invoke(cli, ["handle"], input="not valid json")
        assert result.exit_code == 0

        # Should gracefully degrade with empty JSON
        output = json.loads(result.output)
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_hook_mode_all_recognized_flags(self, runner, temp_config):
        """Test hook mode with all recognized flags."""
        hook_input = {"prompt": "my task -s -c -t -d -n", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Verify all flags are processed with XML wrapping
        assert "<flag_metadata>" in context
        assert "Processed flags -s -c -t -d -n" in context
        assert "</flag_metadata>" in context
        assert "<subagent_delegation>" in context
        assert "</subagent_delegation>" in context
        assert "<commit_instructions>" in context
        assert "/commit" in context
        assert "</commit_instructions>" in context
        assert "<test_instructions>" in context
        assert "</test_instructions>" in context
        assert "<debug_instructions>" in context
        assert "</debug_instructions>" in context
        assert "<no_lint_instructions>" in context
        assert "</no_lint_instructions>" in context

    def test_hook_output_json_structure(self, runner, temp_config):
        """Test that hook output JSON has correct structure."""
        hook_input = {"prompt": "my task -c"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)

        # Verify JSON structure
        assert "hookSpecificOutput" in output
        assert "hookEventName" in output["hookSpecificOutput"]
        assert "additionalContext" in output["hookSpecificOutput"]
        assert output["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_hook_xml_structure_integrity(self, runner, temp_config):
        """Test that the entire XML structure is well-formed."""
        hook_input = {"prompt": "my task -c -t"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Verify all opening tags have matching closing tags
        assert context.count("<flag_metadata>") == context.count("</flag_metadata>") == 1
        assert (
            context.count("<commit_instructions>") == context.count("</commit_instructions>") == 1
        )
        assert context.count("<test_instructions>") == context.count("</test_instructions>") == 1

        # Verify flag_metadata comes before instruction tags
        metadata_start = context.index("<flag_metadata>")
        metadata_end = context.index("</flag_metadata>")
        commit_start = context.index("<commit_instructions>")

        assert metadata_start < metadata_end < commit_start

    def test_cli_mode_no_flags_in_prompt(self, runner, temp_config):
        """Should handle CLI mode with no flags gracefully."""
        result = runner.invoke(cli, ["handle", "task"])
        # Parser returns None when no flags found, which leads to error
        # This is expected behavior in CLI mode
        assert result.exit_code != 0


class TestConfigCommands:
    """Test 'ai-flags config' commands."""

    def test_config_show(self, runner, temp_config):
        """Should display current configuration."""
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        # Verify output contains flag information
        assert "-s" in result.output or "subagent" in result.output
        assert "-c" in result.output or "commit" in result.output

    def test_config_set_enable(self, runner, temp_config):
        """Should enable a flag."""
        result = runner.invoke(cli, ["config", "set", "s", "enabled"])
        assert result.exit_code == 0
        assert "enabled" in result.output

    def test_config_set_disable(self, runner, temp_config):
        """Should disable a flag."""
        result = runner.invoke(cli, ["config", "set", "c", "disabled"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    def test_config_set_accepts_long_name(self, runner, temp_config):
        """Should accept long flag names."""
        result = runner.invoke(cli, ["config", "set", "commit", "disabled"])
        assert result.exit_code == 0
        assert "disabled" in result.output

    def test_config_reset(self, runner, temp_config):
        """Should reset config to defaults."""
        # First disable a flag
        runner.invoke(cli, ["config", "set", "s", "disabled"])

        # Reset
        result = runner.invoke(cli, ["config", "reset"])
        assert result.exit_code == 0

        # Verify flag is enabled again (default)
        show_result = runner.invoke(cli, ["config", "show"])
        # Check that subagent is enabled in the output
        assert "✓" in show_result.output or "enabled" in show_result.output

    def test_config_edit_creates_file(self, runner, temp_config, monkeypatch):
        """Should create config file if it doesn't exist."""
        # Remove config file
        temp_config.unlink()

        # Mock editor to avoid opening real editor
        def mock_run(cmd):
            pass

        monkeypatch.setattr("subprocess.run", mock_run)

        result = runner.invoke(cli, ["config", "edit"])
        assert result.exit_code == 0
        # Config file should be created
        assert temp_config.exists()


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_disable_flag_not_processed(self, runner, temp_config):
        """Disabled flags should not be processed."""
        # Disable commit flag
        runner.invoke(cli, ["config", "set", "c", "disabled"])

        # Try to use it in hook mode
        hook_input = {"prompt": "task -c"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should return empty context (flag disabled)
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_all_flags_together(self, runner, temp_config):
        """Should handle all recognized flags together."""
        hook_input = {"prompt": "task -s -c -t -d -n", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Verify all XML tags present
        assert "<subagent_delegation>" in context
        assert "<commit_instructions>" in context
        assert "<test_instructions>" in context
        assert "<debug_instructions>" in context
        assert "<no_lint_instructions>" in context

    def test_config_persistence(self, runner, temp_config):
        """Config changes should persist across commands."""
        # Disable a flag
        runner.invoke(cli, ["config", "set", "t", "disabled"])

        # Verify it's disabled
        show_result = runner.invoke(cli, ["config", "show"])
        assert "test" in show_result.output
        assert "disabled" in show_result.output or "✗" in show_result.output

        # Try to use the disabled flag
        hook_input = {"prompt": "task -t"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        # Should be empty (flag disabled)
        assert output["hookSpecificOutput"]["additionalContext"] == ""

    def test_mixed_enabled_disabled_flags(self, runner, temp_config):
        """Should process only enabled flags."""
        # Disable some flags
        runner.invoke(cli, ["config", "set", "c", "disabled"])
        runner.invoke(cli, ["config", "set", "d", "disabled"])

        # Try to use mix of enabled and disabled flags
        hook_input = {"prompt": "task -c -t -d", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should only process -t (enabled)
        # -c and -d are disabled, so validation should fail
        # and we get empty context
        assert context == ""

    def test_permission_mode_filtering(self, runner, temp_config):
        """Test that -s flag respects permission mode."""
        # Test with plan mode (should include -s)
        hook_input_plan = {"prompt": "task -s -c", "permission_mode": "plan"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input_plan))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "<subagent_delegation>" in context
        assert "<commit_instructions>" in context

        # Test with normal mode (should skip -s)
        hook_input_normal = {"prompt": "task -s -c", "permission_mode": "normal"}
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input_normal))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "<subagent_delegation>" not in context
        assert "<commit_instructions>" in context  # -c should still be there

    def test_multiline_prompt_with_flags(self, runner, temp_config):
        """Should handle multiline prompts with trailing flags."""
        hook_input = {
            "prompt": "line 1\nline 2\nline 3 -c -t",
            "permission_mode": "plan",
        }
        result = runner.invoke(cli, ["handle"], input=json.dumps(hook_input))
        assert result.exit_code == 0

        output = json.loads(result.output)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert "line 1\nline 2\nline 3" in context
        assert "<commit_instructions>" in context
        assert "<test_instructions>" in context
