from dataclasses import dataclass
from typing import Any

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool import ToolCall

from tests.evals.skills.configure.scorer import (
    CommandResult,
    canonical_command,
    config_command_ran,
    grade_error,
    grade_precedence,
    grade_value,
    skill_was_invoked,
)

LUM = "${CLAUDE_PLUGIN_ROOT}/bin/luminosity"


def _bash(command: str) -> ChatMessageAssistant:
    return ChatMessageAssistant(
        content="",
        tool_calls=[
            ToolCall(id="1", function="Bash", arguments={"command": command})
        ],
    )


def _skill(name: str) -> ChatMessageAssistant:
    return ChatMessageAssistant(
        content="",
        tool_calls=[
            ToolCall(
                id="s",
                function="Skill",
                arguments={"skill": f"luminosity:{name}", "args": "get x"},
            )
        ],
    )


class TestGradeValue:
    def test_byte_exact_match(self):
        assert grade_value("team-v\n", "team-v\n") is True

    def test_unequal(self):
        assert grade_value("team-v\n", "team-w\n") is False

    def test_get_call_site_reconciles_the_trailing_newline(self):
        assert grade_value("team-v\n", "team-v" + "\n") is True

    def test_empty_value_line_is_distinct_from_a_miss(self):
        assert grade_value("\n", "" + "\n") is True
        assert grade_value("\n", "") is False


class TestGradeError:
    def test_any_nonzero_when_exit_unspecified(self):
        result = CommandResult(1, "", "luminosity: config key 'k' is not set")
        assert grade_error(result, "is not set", None) is True

    def test_exact_exit_two_accepted_for_clap(self):
        result = CommandResult(2, "", "error: invalid value 'bad'")
        assert grade_error(result, "bad", 2) is True

    def test_exit_one_when_two_expected_is_rejected(self):
        result = CommandResult(1, "", "error: invalid value 'bad'")
        assert grade_error(result, "bad", 2) is False

    def test_marker_absent_is_rejected(self):
        result = CommandResult(1, "", "some other message")
        assert grade_error(result, "is not set", None) is False

    def test_nonempty_stdout_is_rejected(self):
        result = CommandResult(1, "leaked", "luminosity: is not set")
        assert grade_error(result, "is not set", None) is False


class TestGradePrecedence:
    def test_personal_new_and_team_seed(self):
        assert (
            grade_precedence(
                "personal-v\n", "team-v\n", "personal-v\n", "team-v\n"
            )
            is True
        )

    def test_a_team_overwrite_fails(self):
        assert (
            grade_precedence(
                "personal-v\n", "personal-v\n", "personal-v\n", "team-v\n"
            )
            is False
        )


class TestCanonicalCommand:
    def test_get_unscoped(self):
        assert canonical_command("get", "core.example", None, None) == [
            "config",
            "get",
            "core.example",
        ]

    def test_get_scoped(self):
        assert canonical_command("get", "core.example", "team", None) == [
            "config",
            "get",
            "core.example",
            "--level",
            "team",
        ]

    def test_set_with_value_and_level(self):
        assert canonical_command("set", "core", "team", "blocked") == [
            "config",
            "set",
            "core",
            "blocked",
            "--level",
            "team",
        ]


class TestConfigCommandRan:
    def test_matches_the_agents_get(self):
        messages = [_bash(f"{LUM} config get core.example")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level=None
            )
            is True
        )

    def test_wrong_key_does_not_match(self):
        messages = [_bash(f"{LUM} config get other.key")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level=None
            )
            is False
        )

    def test_a_differently_levelled_get_does_not_match(self):
        messages = [_bash(f"{LUM} config get core.example --level team")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level=None
            )
            is False
        )

    def test_scoped_get_matches_its_level(self):
        messages = [_bash(f"{LUM} config get core.example --level team")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level="team"
            )
            is True
        )

    def test_bad_level_get_matches_despite_being_rejected(self):
        messages = [_bash(f"{LUM} config get core.example --level bad")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level="bad"
            )
            is True
        )

    def test_an_interleaved_set_is_not_a_get_match(self):
        messages = [_bash(f"{LUM} config set core.example x")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level=None
            )
            is False
        )

    def test_set_matches_verb_key_value(self):
        messages = [_bash(f"{LUM} config set core.example personal-v")]
        assert (
            config_command_ran(
                messages,
                action="set",
                key="core.example",
                level=None,
                value="personal-v",
            )
            is True
        )

    def test_set_with_wrong_value_does_not_match(self):
        messages = [_bash(f"{LUM} config set core.example other")]
        assert (
            config_command_ran(
                messages,
                action="set",
                key="core.example",
                level=None,
                value="personal-v",
            )
            is False
        )

    def test_a_command_with_no_config_token_is_skipped(self):
        assert (
            config_command_ran(
                [_bash("ls -la")],
                action="get",
                key="core.example",
                level=None,
            )
            is False
        )

    def test_no_matching_command_returns_false(self):
        assert (
            config_command_ran([], action="get", key="core.example", level=None)
            is False
        )

    def test_non_assistant_messages_are_ignored(self):
        messages: list[Any] = [ChatMessageUser(content="get core.example")]
        assert (
            config_command_ran(
                messages, action="get", key="core.example", level=None
            )
            is False
        )


class TestSkillWasInvoked:
    def test_present_naming_the_skill(self):
        assert skill_was_invoked([_skill("configure")], "configure") is True

    def test_absent(self):
        assert skill_was_invoked([_bash("ls")], "configure") is False

    def test_wrong_name(self):
        assert skill_was_invoked([_skill("other")], "configure") is False

    def test_none_arguments_does_not_raise(self):
        @dataclass
        class _Call:
            function: str
            arguments: dict[str, Any] | None

        @dataclass
        class _Msg:
            role: str
            tool_calls: list[_Call]

        messages = [_Msg("assistant", [_Call("Skill", None)])]
        assert skill_was_invoked(messages, "configure") is False
