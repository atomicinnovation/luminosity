"""Host-native solver: drive the real `claude -p` on the Claude subscription.

Replaces inspect_swe's bridge (which routes model calls through Inspect's
metered API provider) with a direct headless Claude Code invocation that uses
the CLI's own subscription auth. The agent runs in a fresh per-sample temp dir
seeded with the fixture; its `--output-format stream-json` transcript is parsed
into `state.messages` so the scorer reads a *known* shape (no assumed-shape
risk), and the temp dir is stashed for the scorer's level-scoped re-reads.
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolCall

from tests.evals.skills.configure.environment import plugin_dir

_FIXTURES = Path(__file__).parent / "fixtures"

# A dated snapshot so the committed log is reproducible against a fixed model;
# recorded with the CLI version. The subscription serves it as-is.
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# Loop guard: sized to the longest task (one CLI call plus a report; a couple
# for a precedence set) with headroom, so a looping agent is bounded.
MAX_TURNS = 8

# The configure skill's contract is to manage config ONLY through the CLI, never
# to read/parse the files itself. Disallowing the file-access tools removes the
# shortcut of reading .luminosity/config.md directly, so the eval measures
# skill-driven CLI routing rather than the model's file-reading instincts.
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
    """Build assistant messages (with tool calls) from a stream-json transcript.

    Only assistant turns carry the tool calls the scorer grades on (the
    `luminosity config` Bash call and any `Skill` event); non-JSON and other
    event lines are skipped, so a malformed line never aborts grading.
    """
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


def _seed(workdir: Path, fixture: str) -> None:
    source = _FIXTURES / fixture / ".luminosity"
    (workdir / ".git").mkdir(parents=True)
    destination = workdir / ".luminosity"
    destination.mkdir()
    for path in sorted(source.glob("*")):
        shutil.copy(path, destination / path.name)


def _claude_argv(prompt: str, *, with_skill: bool, plugin: Path) -> list[str]:
    allowed = ["Bash", "Skill"] if with_skill else ["Bash"]
    # Baseline additionally suppresses the skill so the bare model must
    # self-discover the CLI on PATH.
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
        env: dict[str, Any] = {
            **os.environ,
            "PATH": f"{plugin / 'bin'}{os.pathsep}{os.environ['PATH']}",
        }
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
        return state

    return solve
