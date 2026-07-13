"""The configure skill's context-injection eval.

Injection is passive — no agent command can be attributed to it — so it cannot
share the configure eval's skill-vs-baseline grading. It rides the same
`eval:skills:configure` run as a supplementary single-arm eval instead.
"""

from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from common.eval import TRIALS
from tests.evals.skills.configure.context_scorer import context_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

# The solver drives claude -p itself, so Inspect's provider is never called.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


@task
def context() -> Task:
    return Task(
        dataset=json_dataset(str(_HERE / "context_dataset.json")),
        solver=run_configure_agent(with_skill=True),
        scorer=context_scorer(),
        epochs=Epochs(TRIALS, pass_k(TRIALS)),
        model=MODEL,
        fail_on_error=True,
        name="context",
    )
