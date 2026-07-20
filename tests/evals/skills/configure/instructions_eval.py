"""The configure skill's instructions-injection eval.

The `instructions` capability is the per-skill `## Additional Instructions`
block injected at the end of the prompt. Injection is passive — no agent command
can be attributed to it — so it declares **no baseline arm**, the same as
context: without the skill there is no prompt for the instructions to land in.

Only the two behavioural arms run live here. The deterministic rendering — which
bytes the block is — is graded for free in CI by the compiled binary
(test_instructions_render.py), so no deterministic scenario belongs in the live
dataset.
"""

from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS, with_skill_arm
from tests.evals.skills.configure.instructions_scorer import (
    instructions_scorer,
)
from tests.evals.skills.configure.solvers import run_configure_agent

SKILL = "configure"
CAPABILITY = "instructions"

# The solver drives claude -p itself, so Inspect's provider is never called.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


@task
def configure_instructions_with_skill() -> Task:
    return Task(
        dataset=json_dataset(
            str(_HERE / "instructions_behavioural_dataset.json")
        ),
        solver=run_configure_agent(with_skill=True),
        scorer=instructions_scorer(),
        epochs=Epochs(TRIALS, pass_k(TRIALS)),
        model=MODEL,
        fail_on_error=True,
        name=with_skill_arm(SKILL, CAPABILITY),
    )
