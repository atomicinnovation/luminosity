import json
from typing import TYPE_CHECKING

from inspect_ai.model import ChatMessageAssistant

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from tests.evals.skills.configure.solvers import (
    CLAUDE_MODEL,
    _agent_env,
    _claude_argv,
    parse_transcript,
)


def _line(**event: object) -> str:
    return json.dumps(event)


def _assistant(*blocks: dict[str, object]) -> str:
    return _line(
        type="assistant", message={"role": "assistant", "content": list(blocks)}
    )


class TestParseTranscript:
    def test_extracts_a_bash_tool_call_with_its_command(self):
        stdout = "\n".join(
            [
                _line(type="system", subtype="init"),
                _assistant(
                    {"type": "text", "text": "Let me check."},
                    {
                        "type": "tool_use",
                        "id": "t1",
                        "name": "Bash",
                        "input": {
                            "command": "luminosity config get core.example"
                        },
                    },
                ),
                _line(type="result", subtype="success", result="team-v"),
            ]
        )
        messages = parse_transcript(stdout)
        assert len(messages) == 1
        message = messages[0]
        assert isinstance(message, ChatMessageAssistant)
        assert message.tool_calls is not None
        call = message.tool_calls[0]
        assert call.function == "Bash"
        assert call.arguments == {
            "command": "luminosity config get core.example"
        }

    def test_captures_a_skill_tool_use(self):
        stdout = _assistant(
            {
                "type": "tool_use",
                "id": "s",
                "name": "Skill",
                "input": {"skill": "luminosity:configure", "args": "get x"},
            }
        )
        call = parse_transcript(stdout)[0].tool_calls[0]
        assert call.function == "Skill"
        assert call.arguments == {
            "skill": "luminosity:configure",
            "args": "get x",
        }

    def test_text_only_turn_has_no_tool_calls(self):
        message = parse_transcript(_assistant({"type": "text", "text": "hi"}))[
            0
        ]
        assert message.tool_calls is None

    def test_non_assistant_and_blank_and_malformed_lines_are_skipped(self):
        stdout = "\n".join(
            [
                "",
                "not json at all",
                _line(type="system", subtype="init"),
                _line(type="user", message={"role": "user", "content": []}),
            ]
        )
        assert parse_transcript(stdout) == []

    def test_empty_transcript(self):
        assert parse_transcript("") == []


class TestClaudeArgv:
    def test_with_skill_loads_the_plugin_and_allows_skill(self, tmp_path: Path):
        argv = _claude_argv("q", with_skill=True, plugin=tmp_path)
        assert argv[:3] == ["claude", "-p", "q"]
        assert "--plugin-dir" in argv
        assert argv[argv.index("--plugin-dir") + 1] == str(tmp_path)
        assert "Skill" in argv
        assert argv[argv.index("--model") + 1] == CLAUDE_MODEL

    def test_both_arms_disallow_the_file_reading_bypass_tools(
        self, tmp_path: Path
    ):
        for with_skill in (True, False):
            argv = _claude_argv("q", with_skill=with_skill, plugin=tmp_path)
            assert "Read" in argv
            assert "Grep" in argv

    def test_baseline_suppresses_skill_and_loads_no_plugin(
        self, tmp_path: Path
    ):
        argv = _claude_argv("q", with_skill=False, plugin=tmp_path)
        assert "--plugin-dir" not in argv
        assert "Skill" in argv[argv.index("--disallowedTools") + 1 :]


class TestAgentEnv:
    def test_strips_the_metered_api_auth_so_the_subscription_is_used(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # A stray key would otherwise override the CLI's subscription login.
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-stray")
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok")
        env = _agent_env(tmp_path)
        assert "ANTHROPIC_API_KEY" not in env
        assert "ANTHROPIC_AUTH_TOKEN" not in env

    def test_puts_the_staged_plugin_bin_first_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("PATH", "/usr/bin")
        env = _agent_env(tmp_path)
        assert env["PATH"].startswith(f"{tmp_path / 'bin'}:")
