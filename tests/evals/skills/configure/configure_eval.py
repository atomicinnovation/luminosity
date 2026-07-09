from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS, baseline_arm, with_skill_arm
from tests.evals.skills.configure.scorer import configure_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

SKILL = "configure"

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
        name=with_skill_arm(SKILL) if with_skill else baseline_arm(SKILL),
    )


@task
def configure_with_skill() -> Task:
    return _task(with_skill=True)


@task
def configure_baseline() -> Task:
    return _task(with_skill=False)
