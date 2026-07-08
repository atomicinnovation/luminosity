import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolCall

from tests.evals.skills.configure.environment import plugin_dir

_FIXTURES = Path(__file__).parent / "fixtures"

CLAUDE_MODEL = "claude-sonnet-5"
MAX_TURNS = 8

# The configure skill's contract is to manage config only through the CLI, so
# disallowing the file-access tools removes the shortcut of reading the config
# files directly — the eval then measures skill-driven CLI routing.
_BYPASS_TOOLS = (
    "Read",
    "Edit",
    "Write",
    "Grep",
    "Glob",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
)


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
    source = _FIXTURES / fixture / ".luminosity"
    (workdir / ".git").mkdir(parents=True)
    destination = workdir / ".luminosity"
    destination.mkdir()
    for path in sorted(source.glob("*")):
        shutil.copy(path, destination / path.name)


def _claude_argv(prompt: str, *, with_skill: bool, plugin: Path) -> list[str]:
    allowed = ["Bash", "Skill"] if with_skill else ["Bash"]
    disallowed = [*_BYPASS_TOOLS] if with_skill else ["Skill", *_BYPASS_TOOLS]
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
        *allowed,
        "--disallowedTools",
        *disallowed,
    ]
    if with_skill:
        argv += ["--plugin-dir", str(plugin)]
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


@solver
def run_configure_agent(*, with_skill: bool) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        plugin = plugin_dir()
        workdir = Path(tempfile.mkdtemp(prefix="configure-eval-"))
        _seed(workdir, state.metadata["fixture"])
        stdout, stderr = await _run_claude(
            _claude_argv(
                state.input_text, with_skill=with_skill, plugin=plugin
            ),
            cwd=workdir,
            env=_agent_env(plugin),
        )
        state.messages.extend(parse_transcript(stdout))
        state.metadata["workdir"] = str(workdir)
        state.metadata["agent_stderr"] = stderr[-2000:]
        return state

    return solve
