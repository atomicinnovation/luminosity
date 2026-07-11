from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS
from tasks.shared.eval.gate import live_run_enabled
from tests.evals.skills.configure.context_scorer import context_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

SKILL = "configure"

# The solver drives claude -p itself, so Inspect's provider is never called.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


def _include_sample(sample: Sample) -> bool:
    # The behavioural arm is noisy and only meaningful live; the deterministic
    # scenarios re-execute the binary and need no agent behaviour.
    if (sample.metadata or {}).get("behavioural"):
        return live_run_enabled()
    return True


@task
def context() -> Task:
    dataset = json_dataset(str(_HERE / "context_dataset.json")).filter(
        _include_sample
    )
    return Task(
        dataset=dataset,
        solver=run_configure_agent(with_skill=True),
        scorer=context_scorer(),
        epochs=Epochs(TRIALS, pass_k(TRIALS)),
        model=MODEL,
        fail_on_error=True,
        name="context",
    )
