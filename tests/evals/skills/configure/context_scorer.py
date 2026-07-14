import asyncio
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

# The argv the `configure` SKILL.md's ! preprocessor injects, verbatim —
# including --fail-safe, so the graded command is the shipped command on the
# failure path as well as the healthy one.
# test_context_dataset.py scrapes the injection line out of SKILL.md and pins
# this against it.
SKILL = "configure"
SCORER_ARGV = ["context", f"--skill={SKILL}", "--fail-safe"]


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def grade_block(stdout: str, expected_block: str) -> bool:
    # An empty block is printed as nothing; a non-empty block is printed with
    # the single terminating newline `println!` adds — so exactly one, never a
    # trailing blank line.
    if expected_block == "":
        return stdout == ""
    return stdout == f"{expected_block}\n"


def grade_behaviour(transcript_text: str, sentinels: list[str]) -> bool:
    # Every sentinel, not any: the global-and-skill arm exists to prove that
    # *both* blocks reached the model, so clearing on one would not assert it.
    return bool(sentinels) and all(
        sentinel in transcript_text for sentinel in sentinels
    )


def transcript_text(messages: list[Any]) -> str:
    texts: list[str] = []
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str):
            texts.append(content)
    return "\n".join(texts)


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


async def _grade(state: TaskState) -> bool:
    metadata = state.metadata
    if metadata.get("behavioural"):
        return grade_behaviour(
            transcript_text(state.messages), metadata["sentinels"]
        )
    result = await _exec(SCORER_ARGV, workdir=metadata["workdir"])
    return result.exit_code == 0 and grade_block(
        result.stdout, metadata["expected_block"]
    )


def context_scorer():
    @scorer(metrics=[accuracy(), stderr()])
    def context():
        async def score(state: TaskState, target: Target) -> Score:
            passed = await _grade(state)
            return Score(
                value=CORRECT if passed else INCORRECT,
                metadata={"scenario": state.metadata.get("scenario")},
            )

        return score

    return context()
