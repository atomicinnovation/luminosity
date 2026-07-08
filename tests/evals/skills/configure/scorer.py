"""Grade the configure skill by the CLI's real output, not the model's prose."""

import asyncio
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

from tests.evals.skills.configure.environment import luminosity_binary

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
    # A `get` must match its `--level` (the outcome re-read cannot see the
    # agent's level choice); a `set`'s level correctness surfaces in the
    # precedence outcome, so only its verb/key/value are matched here.
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
    # Claude Code names the skill namespace-qualified, e.g.
    # {"skill": "luminosity:configure"} — match the bare name after the colon.
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        for call in message.tool_calls or []:
            if call.function == "Skill":
                invoked = str((call.arguments or {}).get("skill", ""))
                if invoked.rsplit(":", 1)[-1] == name:
                    return True
    return False


async def _exec(argv: list[str], *, workdir: str) -> CommandResult:
    process = await asyncio.create_subprocess_exec(
        str(luminosity_binary()),
        *argv,
        cwd=workdir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return CommandResult(
        exit_code=process.returncode if process.returncode is not None else -1,
        stdout=stdout.decode(),
        stderr=stderr.decode(),
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

    workdir = metadata["workdir"]

    if metadata.get("expect_error"):
        result = await _exec(
            canonical_command(action, key, level, value), workdir=workdir
        )
        return grade_error(result, metadata["marker"], metadata.get("exit"))

    if action == "set":
        personal = await _exec(
            canonical_command("get", key, "personal", None), workdir=workdir
        )
        team = await _exec(
            canonical_command("get", key, "team", None), workdir=workdir
        )
        return grade_precedence(
            personal.stdout,
            team.stdout,
            target.text + "\n",
            metadata["expected_team"] + "\n",
        )

    result = await _exec(
        canonical_command(action, key, level, value), workdir=workdir
    )
    return result.exit_code == 0 and grade_value(
        result.stdout, target.text + "\n"
    )


def configure_scorer(*, skill: str, with_skill: bool):
    @scorer(metrics=[accuracy(), stderr()])
    def configure():
        async def score(state: TaskState, target: Target) -> Score:
            passed = await _grade(state, target)
            return Score(
                value=CORRECT if passed else INCORRECT,
                metadata={
                    "skill_invoked": skill_was_invoked(state.messages, skill),
                    "skill_expected": with_skill,
                },
            )

        return score

    return configure()
