"""Logging utilities for ai-flags."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".config" / "ai-flags" / "logs"


def get_logger() -> logging.Logger:
    """Get or create the ai-flags logger with daily rotation."""
    logger = logging.getLogger("ai-flags")
    if logger.handlers:
        return logger  # Already configured

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        handler = TimedRotatingFileHandler(
            LOG_DIR / "handle.log",
            when="midnight",
            backupCount=30,  # Keep 30 days
            encoding="utf-8",
        )
        handler.suffix = "%Y-%m-%d"
        handler.namer = lambda name: name.replace(".log.", "-") + ".log"

        formatter = logging.Formatter(
            "%(asctime)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except OSError:
        # Silently fail if we can't create logs - don't break the tool
        pass

    return logger


def log_handle(
    mode: str,
    flags: list[str],
    cleaned_prompt: str,
    success: bool,
    error: str | None = None,
) -> None:
    """Log a handle command invocation."""
    logger = get_logger()
    if not logger.handlers:
        return  # Logging not available

    flags_str = ",".join(flags) if flags else "none"
    prompt_preview = cleaned_prompt[:50] + "..." if len(cleaned_prompt) > 50 else cleaned_prompt
    prompt_preview = prompt_preview.replace("\n", " ")

    status = "OK" if success else f"ERROR: {error}"

    logger.info(f"mode={mode} | flags=[{flags_str}] | prompt={prompt_preview!r} | {status}")
