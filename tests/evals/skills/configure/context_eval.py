"""The configure skill's context-injection eval.

The `context` capability is the free-form config-file bodies injected into the
prompt. Injection is passive — no agent command can be attributed to it — so it
cannot share the `values` capability's grading, and it declares **no baseline
arm**: without the skill there is no prompt for the context to be injected into,
so a no-skill run would not be a control, it would be a different experiment.

Both capabilities are graded in the one `eval:skills:configure` run.
"""

from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS, with_skill_arm
from tests.evals.skills.configure.context_scorer import context_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

SKILL = "configure"
CAPABILITY = "context"

# The solver drives claude -p itself, so Inspect's provider is never called.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


@task
def configure_context_with_skill() -> Task:
    # The billed arm reads the behavioural dataset, not the full one: the
    # deterministic scenarios are graded for free against the compiled binary by
    # tests/unit/evals/.../test_context_render.py, so paying a live agent to
    # re-run them would buy nothing. This file is also the single source of
    # truth for "the graded subset" that test_results.py pins the committed log
    # against.
    return Task(
        dataset=json_dataset(str(_HERE / "context_behavioural_dataset.json")),
        solver=run_configure_agent(with_skill=True),
        scorer=context_scorer(),
        epochs=Epochs(TRIALS, pass_k(TRIALS)),
        model=MODEL,
        fail_on_error=True,
        name=with_skill_arm(SKILL, CAPABILITY),
    )
