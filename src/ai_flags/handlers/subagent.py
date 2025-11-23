"""Handler for -s (subagent) flag."""

from ai_flags.handlers.base import FlagHandler

DEFAULT_CONTENT = """Once you have an implementation plan, split the work strategically:

- **Independent tasks**: Spawn multiple subagents in parallel using multiple Task tool calls in a single message
- **Dependent tasks**: Use a single subagent for the entire sequential workflow
- **Hybrid workflows**: Handle sequential prerequisites first, then parallelize independent work

Orchestrate, don't implement. Delegate all implementation details to subagents. Review their work at the end."""


class SubagentHandler(FlagHandler):
    """Handler for -s flag: Append subagent orchestration instructions."""

    def __init__(self, content: str | None = None):
        """Initialize with optional custom content."""
        self._custom_content = content

    @property
    def flag_letter(self) -> str:
        return "s"

    def get_xml_tag(self) -> str:
        return "subagent_delegation"

    def get_content(self, permission_mode: str | None = None) -> str:
        """Return subagent delegation instructions.

        Note: Only active when permission_mode == "plan"
        """
        # Skip if not in plan mode
        if permission_mode != "plan":
            return ""

        return self._custom_content if self._custom_content else DEFAULT_CONTENT
