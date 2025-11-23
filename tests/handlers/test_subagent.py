"""Tests for subagent handler."""

from ai_flags.handlers.subagent import SubagentHandler


class TestSubagentHandler:
    """Test SubagentHandler for -s flag."""

    def test_flag_letter(self):
        """Should return 's'."""
        handler = SubagentHandler()
        assert handler.flag_letter == "s"

    def test_xml_tag(self):
        """Should return 'subagent_delegation'."""
        handler = SubagentHandler()
        assert handler.get_xml_tag() == "subagent_delegation"

    def test_default_content_in_plan_mode(self):
        """Should return content when permission_mode is 'plan'."""
        handler = SubagentHandler()
        content = handler.get_content(permission_mode="plan")
        assert len(content) > 0
        # Verify content has subagent-related keywords from original tests
        assert "implementation plan" in content.lower()
        assert "subagents in parallel" in content.lower()

    def test_empty_content_outside_plan_mode(self):
        """Should return empty string when not in plan mode."""
        handler = SubagentHandler()
        assert handler.get_content(permission_mode=None) == ""
        assert handler.get_content(permission_mode="normal") == ""
        assert handler.get_content(permission_mode="default") == ""

    def test_custom_content_overrides_default(self):
        """Should use custom content when provided."""
        custom = "Custom subagent instructions"
        handler = SubagentHandler(content=custom)
        assert handler.get_content(permission_mode="plan") == custom

    def test_custom_content_respects_permission_mode(self):
        """Custom content should still respect permission mode check."""
        custom = "Custom content"
        handler = SubagentHandler(content=custom)
        # Should only return content in plan mode
        assert handler.get_content(permission_mode="plan") == custom
        assert handler.get_content(permission_mode=None) == ""
        assert handler.get_content(permission_mode="normal") == ""

    def test_default_content_contains_task_tool_reference(self):
        """Default content should mention the Task tool."""
        handler = SubagentHandler()
        content = handler.get_content(permission_mode="plan")
        assert "Task tool" in content or "task tool" in content.lower()

    def test_default_content_mentions_orchestration(self):
        """Default content should mention orchestration role."""
        handler = SubagentHandler()
        content = handler.get_content(permission_mode="plan")
        assert "orchestrate" in content.lower()

    def test_different_permission_modes(self):
        """Test various permission mode values."""
        handler = SubagentHandler()

        # Only "plan" should return content
        assert len(handler.get_content(permission_mode="plan")) > 0

        # All other modes should return empty
        for mode in ["", "auto", "approval", "execute", "disabled"]:
            assert handler.get_content(permission_mode=mode) == ""
