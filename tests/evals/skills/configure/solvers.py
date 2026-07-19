import asyncio
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolCall

from common.eval import WORKDIR_PREFIX
from tests.evals.skills.configure.environment import plugin_dir

_FIXTURES = Path(__file__).parent / "fixtures"

CLAUDE_MODEL = "claude-sonnet-5"
MAX_TURNS = 8
_AGENT_TOOLS = ("Bash", "Read", "Grep", "Glob")


class ClaudeCliVersionError(RuntimeError):
    pass


_VERSION = re.compile(r"\d+\.\d+\.\d+")


def parse_cli_version(stdout: str) -> str:
    match = _VERSION.search(stdout)
    if match is None:
        raise ClaudeCliVersionError(
            f"cannot read a Claude Code version from {stdout!r}"
        )
    return match.group(0)


def provenance(cli_version: str) -> dict[str, str]:
    return {"claude_model": CLAUDE_MODEL, "claude_cli_version": cli_version}


def parse_transcript(stdout: str) -> list[ChatMessageAssistant]:
    messages: list[ChatMessageAssistant] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "assistant":
            continue
        content = (event.get("message") or {}).get("content") or []
        tool_calls: list[ToolCall] = []
        texts: list[str] = []
        for block in content:
            if block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        function=block.get("name", ""),
                        arguments=block.get("input") or {},
                    )
                )
            elif block.get("type") == "text":
                texts.append(block.get("text", ""))
        messages.append(
            ChatMessageAssistant(
                content="".join(texts), tool_calls=tool_calls or None
            )
        )
    return messages


def _agent_env(plugin: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{plugin / 'bin'}{os.pathsep}{env['PATH']}"
    return env


def _seed(workdir: Path, fixture: str) -> None:
    (workdir / ".git").mkdir(parents=True)
    shutil.copytree(
        _FIXTURES / fixture / ".luminosity", workdir / ".luminosity"
    )


def _claude_argv(prompt: str, *, with_skill: bool, plugin: Path) -> list[str]:
    argv = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        CLAUDE_MODEL,
        "--max-turns",
        str(MAX_TURNS),
        "--allowedTools",
        *_AGENT_TOOLS,
    ]
    if with_skill:
        argv += ["Skill", "--plugin-dir", str(plugin)]
    else:
        argv += ["--disallowedTools", "Skill"]
    return argv


async def _run_claude(
    argv: list[str], *, cwd: Path, env: dict[str, str]
) -> tuple[str, str]:
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return stdout.decode(), stderr.decode()


_cli_version_cache: str | None = None


async def _cli_version(env: dict[str, str]) -> str:
    global _cli_version_cache  # noqa: PLW0603 (one probe per eval process)
    if _cli_version_cache is None:
        stdout, _ = await _run_claude(
            ["claude", "--version"], cwd=Path.cwd(), env=env
        )
        _cli_version_cache = parse_cli_version(stdout)
    return _cli_version_cache


@solver
def run_configure_agent(*, with_skill: bool) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        plugin = plugin_dir()
        env = _agent_env(plugin)
        workdir = Path(tempfile.mkdtemp(prefix=WORKDIR_PREFIX))
        _seed(workdir, state.metadata["fixture"])
        stdout, stderr = await _run_claude(
            _claude_argv(
                state.input_text, with_skill=with_skill, plugin=plugin
            ),
            cwd=workdir,
            env=env,
        )
        state.messages.extend(parse_transcript(stdout))
        state.metadata["workdir"] = str(workdir)
        state.metadata["agent_stderr"] = stderr[-2000:]
        state.metadata.update(provenance(await _cli_version(env)))
        return state

    return solve
