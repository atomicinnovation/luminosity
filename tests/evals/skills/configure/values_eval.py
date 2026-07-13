"""The configure skill's configuration-values eval.

The `values` capability is the CLI-owned side of the skill: reading and writing
a dotted `section.key` through `luminosity config get`/`set`. A baseline is a
real control for it — an agent without the skill can still reach for the CLI —
which is what the baseline arm measures.

Its sibling capability, `context`, is the free-form config-file bodies injected
into the prompt, graded separately in `context_eval.py`.
"""

from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS, baseline_arm, with_skill_arm
from tests.evals.skills.configure.scorer import configure_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

SKILL = "configure"
CAPABILITY = "values"

# The solver drives claude -p itself, so Inspect's provider is never called.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


def _task(*, with_skill: bool) -> Task:
    return Task(
        dataset=json_dataset(str(_HERE / "dataset.json")),
        solver=run_configure_agent(with_skill=with_skill),
        scorer=configure_scorer(skill=SKILL, with_skill=with_skill),
        epochs=Epochs(TRIALS, pass_k(TRIALS)),
        model=MODEL,
        fail_on_error=True,
        name=(
            with_skill_arm(SKILL, CAPABILITY)
            if with_skill
            else baseline_arm(SKILL, CAPABILITY)
        ),
    )


@task
def configure_values_with_skill() -> Task:
    return _task(with_skill=True)


@task
def configure_values_baseline() -> Task:
    return _task(with_skill=False)
