"""Deterministic outcome scorer for the configure skill eval.

The scorer never grades the model's prose (the skill tells Claude to relay the
CLI's stdout, but it may frame it — "The value is team-v"). Instead it grades
two observable facts:

- **Routing** — did the agent run the *correct* `luminosity config` command for
  the task (right verb, key, and `--level`)? This is read from the transcript
  as an argv-token match over the agent's Bash tool calls, never a loose
  substring, so an exploratory or wrongly-scoped command is not mistaken for the
  graded one.
- **Outcome** — grade the CLI's real stdout / exit code / stderr by re-running
  the canonical command (or, for a `set`, the level-scoped reads that reveal the
  end state) via `sandbox().exec`, whose `ExecResult` carries a structured
  `returncode`. The transcript's Bash *result* content cannot reliably surface a
  numeric exit code, so it cannot distinguish clap's exit 2 from a domain exit 1
  — the sandbox re-read can, which the bad-`--level` task requires.

The pure decision/extraction helpers (`grade_value`, `grade_error`,
`grade_precedence`, `config_command_ran`, `skill_was_invoked`) are split from
the sandbox I/O so every branch is unit-testable against message stubs with no
live run. Two transcript-shape assumptions are Phase-3-verified against the
golden fixture: the Bash tool-call argument key (`command`) and the `Skill`
tool-use event structure. Skill attribution is a **logged diagnostic** here, not
a hard pass/fail conjunct; Phase 3 promotes it once the event shape is captured.
"""

import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    scorer,
    stderr,
)
from inspect_ai.util import sandbox

from tests.evals.shared.names import SKILL_NAME
from tests.evals.skills.configure.environment import LUMINOSITY_BIN, WORKDIR

if TYPE_CHECKING:
    from inspect_ai.solver import TaskState


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def grade_value(actual: str, expected: str) -> bool:
    return actual == expected


def grade_precedence(
    personal_read: str,
    team_read: str,
    expected_new: str,
    expected_team: str,
) -> bool:
    return personal_read == expected_new and team_read == expected_team


def grade_error(
    result: CommandResult, marker: str, expected_exit: int | None
) -> bool:
    code_ok = (
        result.exit_code != 0
        if expected_exit is None
        else result.exit_code == expected_exit
    )
    return code_ok and result.stdout == "" and marker in result.stderr


def canonical_command(
    action: str, key: str, level: str | None, value: str | None
) -> list[str]:
    argv = ["config", action, key]
    if action == "set" and value is not None:
        argv.append(value)
    if level is not None:
        argv += ["--level", level]
    return argv


def _bash_commands(messages: list[Any]) -> list[str]:
    commands: list[str] = []
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        for call in message.tool_calls or []:
            if call.function.lower() != "bash":
                continue
            command = (call.arguments or {}).get("command")
            if isinstance(command, str):
                commands.append(command)
    return commands


def _split_config_args(
    tokens: list[str],
) -> tuple[list[str], str | None] | None:
    """Positionals and `--level` value for the `config` sub-command in tokens.

    Returns None when the token list is not a `... config ...` invocation, so a
    bare shell command is never mistaken for one.
    """
    if "config" not in tokens:
        return None
    tail = tokens[tokens.index("config") + 1 :]
    positionals: list[str] = []
    level: str | None = None
    iterator = iter(tail)
    for token in iterator:
        if token == "--level":
            level = next(iterator, None)
        elif token.startswith("--level="):
            level = token.split("=", 1)[1]
        else:
            positionals.append(token)
    return positionals, level


def config_command_ran(
    messages: list[Any],
    *,
    action: str,
    key: str,
    level: str | None,
    value: str | None = None,
) -> bool:
    """Whether the agent ran the exact `config` command the task requires.

    A `get` must match the verb, key, and `--level` (its absence when the task
    is unscoped) so a wrongly-scoped read is caught here — the outcome re-read
    cannot see the agent's level choice. A `set` matches verb + key + value;
    its level correctness surfaces in the precedence outcome (a mis-routed
    `--level team` overwrites the shared value), so it is not enforced here.
    """
    for command in _bash_commands(messages):
        parsed = _split_config_args(shlex.split(command))
        if parsed is None:
            continue
        positionals, invoked_level = parsed
        if action == "get":
            if positionals == [action, key] and invoked_level == level:
                return True
        elif positionals == [action, key, value]:
            return True
    return False


def skill_was_invoked(messages: list[Any], name: str) -> bool:
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        for call in message.tool_calls or []:
            if (
                call.function == "Skill"
                and (call.arguments or {}).get("name") == name
            ):
                return True
    return False


async def _exec(argv: list[str]) -> CommandResult:
    result = await sandbox().exec([LUMINOSITY_BIN, *argv], cwd=WORKDIR)
    return CommandResult(
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


async def _grade(state: TaskState, target: Target) -> bool:
    metadata = state.metadata
    action = metadata["action"]
    key = metadata["key"]
    level = metadata.get("level")
    value = metadata.get("value")

    if not config_command_ran(
        state.messages, action=action, key=key, level=level, value=value
    ):
        return False

    if metadata.get("expect_error"):
        result = await _exec(canonical_command(action, key, level, value))
        return grade_error(result, metadata["marker"], metadata.get("exit"))

    if action == "set":
        personal = await _exec(canonical_command("get", key, "personal", None))
        team = await _exec(canonical_command("get", key, "team", None))
        return grade_precedence(
            personal.stdout,
            team.stdout,
            target.text + "\n",
            metadata["expected_team"] + "\n",
        )

    result = await _exec(canonical_command(action, key, level, value))
    return result.exit_code == 0 and grade_value(
        result.stdout, target.text + "\n"
    )


def configure_scorer(*, with_skill: bool):
    @scorer(metrics=[accuracy(), stderr()])
    def configure():
        async def score(state: TaskState, target: Target) -> Score:
            passed = await _grade(state, target)
            invoked = skill_was_invoked(state.messages, SKILL_NAME)
            return Score(
                value=CORRECT if passed else INCORRECT,
                metadata={
                    "skill_invoked": invoked,
                    "skill_expected": with_skill,
                },
            )

        return score

    return configure()
