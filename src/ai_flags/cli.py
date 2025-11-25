"""CLI commands for ai-flags."""

import click
import json
import sys
import os
import subprocess
from typing import Optional

from ai_flags.config_loader import load_config, save_config, reset_config, CONFIG_PATH
from ai_flags.parser import parse_trailing_flags
from ai_flags.validator import validate_flags
from ai_flags.executor import execute_flag_handlers
from ai_flags.output import format_hook_output, format_cli_output
from ai_flags.handlers import (
    SubagentHandler,
    CommitHandler,
    CoverageHandler,
    DebugHandler,
    NoLintHandler,
)
from ai_flags.logger import log_handle


@click.group()
def cli():
    """AI Flags - Parse and process Claude Code prompt flags."""
    pass


@cli.command()
@click.argument("prompt", required=False)
def handle(prompt: Optional[str]):
    """Handle a prompt with flags.

    Auto-detects input mode:
    - If PROMPT argument provided: CLI mode (plain text output)
    - If stdin has data: Hook mode (JSON in/out)
    """
    # Detect mode: prefer explicit prompt argument (CLI mode)
    if prompt:
        # CLI mode: process argument
        _handle_cli_mode(prompt)
    elif not sys.stdin.isatty():
        # Check if stdin actually has data
        try:
            # Hook mode: read JSON from stdin
            _handle_hook_mode()
        except (json.JSONDecodeError, EOFError):
            # stdin exists but has no valid JSON (or is empty)
            click.echo("Error: No valid JSON input on stdin", err=True)
            sys.exit(1)
    else:
        click.echo("Error: No prompt provided and stdin is empty", err=True)
        sys.exit(1)


def _handle_hook_mode():
    """Handle hook mode (JSON stdin → JSON stdout)."""
    # Read all stdin content first to check if empty
    stdin_content = sys.stdin.read()

    if not stdin_content.strip():
        # Empty stdin - this is an error condition
        raise json.JSONDecodeError("Empty stdin", "", 0)

    # Try to parse JSON
    try:
        hook_input = json.loads(stdin_content)
    except (json.JSONDecodeError, ValueError):
        # Invalid JSON (but not empty) - gracefully degrade for hooks
        log_handle(
            mode="hook", flags=[], cleaned_prompt="", success=False, error="Invalid JSON input"
        )
        click.echo(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": "",
                    }
                }
            ),
            err=False,
        )
        return

    try:
        # Extract prompt from hook input
        prompt = hook_input.get("prompt", "")
        permission_mode = hook_input.get("permission_mode")

        # Load config
        config = load_config()
        enabled_flags = config.get_enabled_flags()

        # Parse flags
        result = parse_trailing_flags(prompt)
        if result is None:
            # No flags detected - output empty JSON
            log_handle(mode="hook", flags=[], cleaned_prompt=prompt, success=True)
            click.echo(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": "",
                        }
                    }
                )
            )
            return

        cleaned_prompt, flags = result

        # Validate flags
        if not validate_flags(flags, enabled_flags):
            # Invalid flags - silent exit (output empty JSON)
            log_handle(
                mode="hook",
                flags=flags,
                cleaned_prompt=cleaned_prompt,
                success=False,
                error="Invalid or disabled flags",
            )
            click.echo(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": "",
                        }
                    }
                )
            )
            return

        # Build handlers with custom content from config
        handlers = _build_handlers(config)

        # Execute handlers
        context = execute_flag_handlers(flags, handlers, permission_mode)

        # If no context generated (e.g., -s filtered in normal mode), return empty
        if not context:
            log_handle(mode="hook", flags=flags, cleaned_prompt=cleaned_prompt, success=True)
            click.echo(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": "",
                        }
                    }
                )
            )
            return

        # Format and output
        output = format_hook_output(cleaned_prompt, flags, context)
        click.echo(output)
        log_handle(mode="hook", flags=flags, cleaned_prompt=cleaned_prompt, success=True)

    except Exception as e:
        # On error, output empty JSON (graceful degradation)
        log_handle(mode="hook", flags=[], cleaned_prompt="", success=False, error=str(e))
        click.echo(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": "",
                    }
                }
            ),
            err=False,
        )
        sys.exit(0)


def _handle_cli_mode(prompt: str):
    """Handle CLI mode (argument → plain text output)."""
    # Load config
    config = load_config()
    enabled_flags = config.get_enabled_flags()

    # Parse flags
    result = parse_trailing_flags(prompt)
    if result is None:
        log_handle(
            mode="cli", flags=[], cleaned_prompt=prompt, success=False, error="No flags detected"
        )
        click.echo("Error: No flags detected in prompt", err=True)
        sys.exit(1)

    cleaned_prompt, flags = result

    # Validate flags
    if not validate_flags(flags, enabled_flags):
        log_handle(
            mode="cli",
            flags=flags,
            cleaned_prompt=cleaned_prompt,
            success=False,
            error="Invalid or disabled flags",
        )
        click.echo("Error: Invalid or disabled flags detected", err=True)
        sys.exit(1)

    # Build handlers
    handlers = _build_handlers(config)

    # Execute handlers
    context = execute_flag_handlers(flags, handlers, permission_mode=None)

    # Format and output
    output = format_cli_output(cleaned_prompt, flags, context)
    click.echo(output)
    log_handle(mode="cli", flags=flags, cleaned_prompt=cleaned_prompt, success=True)


def _build_handlers(config):
    """Build handler instances with custom content from config."""
    handlers = {}

    s_cfg = config.subagent
    handlers["s"] = SubagentHandler(content=s_cfg.content)

    c_cfg = config.commit
    handlers["c"] = CommitHandler(content=c_cfg.content)

    t_cfg = config.test
    handlers["t"] = CoverageHandler(content=t_cfg.content)

    d_cfg = config.debug
    handlers["d"] = DebugHandler(content=d_cfg.content)

    n_cfg = config.no_lint
    handlers["n"] = NoLintHandler(content=n_cfg.content)

    return handlers


# Config commands
@cli.group()
def config():
    """Manage ai-flags configuration."""
    pass


@config.command("show")
def config_show():
    """Display current configuration."""
    cfg = load_config()

    click.echo("AI Flags Configuration")
    click.echo("=" * 50)
    click.echo(f"Config file: {CONFIG_PATH}")
    click.echo()

    flags_info = [
        ("s", "subagent", cfg.subagent),
        ("c", "commit", cfg.commit),
        ("t", "test", cfg.test),
        ("d", "debug", cfg.debug),
        ("n", "no_lint", cfg.no_lint),
    ]

    for letter, name, flag_cfg in flags_info:
        status = "✓ enabled" if flag_cfg.enabled else "✗ disabled"
        custom = " (custom content)" if flag_cfg.content else ""
        click.echo(f"-{letter} ({name:10s}): {status}{custom}")


@config.command("reset")
def config_reset():
    """Reset configuration to defaults."""
    reset_config()
    click.echo("Configuration reset to defaults")


@config.command("edit")
def config_edit():
    """Open config file in $EDITOR."""
    editor = os.environ.get("EDITOR", "nano")

    # Ensure config exists
    if not CONFIG_PATH.exists():
        save_config(load_config())

    subprocess.run([editor, str(CONFIG_PATH)])


@config.command("set")
@click.argument(
    "flag",
    type=click.Choice(["s", "c", "t", "d", "n", "subagent", "commit", "test", "debug", "no_lint"]),
)
@click.argument("value", type=click.Choice(["enabled", "disabled"]))
def config_set(flag: str, value: str):
    """Enable or disable a flag."""
    # Normalize flag name
    flag_map = {
        "s": "subagent",
        "c": "commit",
        "t": "test",
        "d": "debug",
        "n": "no_lint",
    }
    flag_name = flag_map.get(flag, flag)

    # Load config
    cfg = load_config()

    # Update
    enabled = value == "enabled"
    flag_cfg = getattr(cfg, flag_name)
    flag_cfg.enabled = enabled

    # Save
    save_config(cfg)

    status = "enabled" if enabled else "disabled"
    click.echo(f"Flag '{flag}' {status}")


if __name__ == "__main__":
    cli()
