import json
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageAssistant

from tests.evals.skills.configure.solvers import (
    CLAUDE_MODEL,
    ClaudeCliVersionError,
    _agent_env,
    _claude_argv,
    _seed,
    parse_cli_version,
    parse_transcript,
    provenance,
)

_FIXTURES = (
    Path(__file__).resolve().parents[4]
    / "evals"
    / "skills"
    / "configure"
    / "fixtures"
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

    def test_both_arms_get_the_same_tools_apart_from_skill(
        self, tmp_path: Path
    ):
        def allowed_tools(*, with_skill: bool) -> set[str]:
            argv = _claude_argv("q", with_skill=with_skill, plugin=tmp_path)
            tools: set[str] = set()
            for token in argv[argv.index("--allowedTools") + 1 :]:
                if token.startswith("--"):
                    break
                tools.add(token)
            return tools

        with_skill = allowed_tools(with_skill=True)
        baseline = allowed_tools(with_skill=False)
        assert with_skill - baseline == {"Skill"}
        assert baseline - with_skill == set()

    def test_neither_arm_disallows_the_file_reading_tools(self, tmp_path: Path):
        for with_skill in (True, False):
            argv = _claude_argv("q", with_skill=with_skill, plugin=tmp_path)
            assert "Read" in argv
            assert "Grep" in argv
            disallowed: list[str] = (
                argv[argv.index("--disallowedTools") + 1 :]
                if "--disallowedTools" in argv
                else []
            )
            assert "Read" not in disallowed
            assert "Grep" not in disallowed

    def test_baseline_suppresses_skill_and_loads_no_plugin(
        self, tmp_path: Path
    ):
        argv = _claude_argv("q", with_skill=False, plugin=tmp_path)
        assert "--plugin-dir" not in argv
        assert "Skill" in argv[argv.index("--disallowedTools") + 1 :]
        assert "Skill" not in argv[: argv.index("--disallowedTools")]


class TestAgentEnv:
    def test_inherits_ambient_auth_so_it_can_be_overridden(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-override")
        assert _agent_env(tmp_path)["ANTHROPIC_API_KEY"] == "sk-ant-override"

    def test_puts_the_staged_plugin_bin_first_on_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("PATH", "/usr/bin")
        env = _agent_env(tmp_path)
        assert env["PATH"].startswith(f"{tmp_path / 'bin'}:")


class TestParseCliVersion:
    def test_reads_the_version_from_the_cli_banner(self):
        assert parse_cli_version("2.1.203 (Claude Code)\n") == "2.1.203"

    def test_unrecognised_output_fails_loudly(self):
        with pytest.raises(ClaudeCliVersionError):
            parse_cli_version("command not found")


class TestProvenance:
    def test_names_the_agent_model_and_cli_version(self):
        assert provenance("2.1.203") == {
            "claude_model": CLAUDE_MODEL,
            "claude_cli_version": "2.1.203",
        }


class TestSeed:
    def test_copies_a_nested_per_skill_fixture_tree(self, tmp_path: Path):
        # The flat glob + shutil.copy this replaced raised IsADirectoryError the
        # moment a fixture carried a skills/ directory.
        fixture = "context_skill_both_levels"
        workdir = tmp_path / "workdir"

        _seed(workdir, fixture)

        for name in ("context.md", "context.local.md"):
            seeded = workdir / ".luminosity" / "skills" / "configure" / name
            source = (
                _FIXTURES
                / fixture
                / ".luminosity"
                / "skills"
                / "configure"
                / name
            )
            assert seeded.read_text() == source.read_text()

    def test_marks_the_workdir_as_a_project_root(self, tmp_path: Path):
        # Without the .git marker the launcher's upward walk would escape the
        # fixture and root somewhere in the real working tree.
        workdir = tmp_path / "workdir"
        _seed(workdir, "context_team_only")
        assert (workdir / ".git").is_dir()
