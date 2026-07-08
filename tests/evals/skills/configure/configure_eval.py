"""Inspect A/B eval for the configure skill (with-skill vs suppressed baseline).

One parameterised task shares the dataset, scorer, and pass^k reducer across
both arms; they differ only in the solver — the with-skill arm loads the plugin
skill via `claude -p --plugin-dir`, the baseline suppresses the `Skill` tool so
the bare model must self-discover the CLI on PATH. Grading is deterministic and
outcome-based; the baseline is for attribution (the gate is the with-skill
pass^k alone — see tasks/eval).

The agent is driven host-natively on the Claude subscription (see solvers.py),
so Inspect's own model is a no-op `mockllm` — the solver produces the transcript
and never calls `generate()`.

Addressed by the task layer via the file-path specifier
`configure_eval.py@<arm>`, so the strict-typed `tasks/` package never imports
this deliberately non-packaged tree. All imports are fully-absolute
(`from tests.evals.…`) — Inspect's file-path loader loads this file as a
top-level module, so relative imports fail under it.
"""

from pathlib import Path

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k

from tests.evals.shared.names import ARM_BASELINE, ARM_WITH_SKILL, EPOCHS
from tests.evals.skills.configure.scorer import configure_scorer
from tests.evals.skills.configure.solvers import run_configure_agent

# The solver drives claude -p itself, so Inspect's provider is never called; a
# no-op mock keeps the framework happy without any API key or model call.
MODEL = "mockllm/model"

_HERE = Path(__file__).parent


def _task(*, with_skill: bool) -> Task:
    return Task(
        dataset=json_dataset(str(_HERE / "dataset.json")),
        solver=run_configure_agent(with_skill=with_skill),
        scorer=configure_scorer(with_skill=with_skill),
        epochs=Epochs(EPOCHS, pass_k(EPOCHS)),
        model=MODEL,
        fail_on_error=True,
        name=ARM_WITH_SKILL if with_skill else ARM_BASELINE,
    )


@task
def configure_with_skill() -> Task:
    return _task(with_skill=True)


@task
def configure_baseline() -> Task:
    return _task(with_skill=False)
