"""Handler for -s (subagent) flag."""

from ai_flags.handlers.base import FlagHandler

DEFAULT_CONTENT = """Split work strategically:
- **Independent**: Spawn parallel subagents via multiple Task calls in one message
- **Dependent**: Use one subagent for the full sequential workflow
- **Hybrid**: Handle prerequisites first, then parallelize

Orchestrate, don't implement. Delegate to subagents. Review their work."""


class SubagentHandler(FlagHandler):
    """Handler for -s flag: Append subagent orchestration instructions."""

    def __init__(self, content: str | None = None):
        """Initialize with optional custom content."""
        self._custom_content = content

    @property
    def flag_letter(self) -> str:
        return "s"

    def get_xml_tag(self) -> str:
        return "subagents"

    def get_content(self, permission_mode: str | None = None) -> str:
        """Return subagent delegation instructions.

        Note: Only active when permission_mode == "plan"
        """
        # Skip if not in plan mode
        if permission_mode != "plan":
            return ""

        return self._custom_content if self._custom_content else DEFAULT_CONTENT
