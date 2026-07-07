"""Inspect A/B eval for the configure skill (with-skill vs suppressed baseline).

One parameterised task shares the dataset, scorer, model, and Task-level limits
across both arms; they differ only in the `claude_code()` configuration — the
with-skill arm loads the skill, the baseline suppresses the `Skill` tool so the
bare model must self-discover the CLI. Grading is the baseline for attribution;
the gate is on the with-skill pass^k alone (see tasks/eval).

Addressed by the task layer via the file-path specifier
`configure_eval.py@<arm>`, so the strict-typed `tasks/` package never imports
this deliberately non-packaged tree. All imports are fully-absolute
(`from tests.evals.…`) because Inspect's file-path loader loads this file as a
top-level module with no package context — relative imports fail under it.
"""

from pathlib import Path

import yaml
from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.scorer import pass_k
from inspect_ai.solver import chain
from inspect_ai.tool import Skill
from inspect_swe import claude_code

from tests.evals.shared.names import ARM_BASELINE, ARM_WITH_SKILL, EPOCHS
from tests.evals.skills.configure.environment import WORKDIR
from tests.evals.skills.configure.scorer import configure_scorer
from tests.evals.skills.configure.solvers import seed_fixtures

# A dated snapshot so the committed log is reproducible against a fixed model;
# recorded in the log. Anthropic retires dated snapshots on a schedule, so the
# log is a point-in-time record, not an indefinitely re-runnable artifact.
MODEL = "anthropic/claude-haiku-4-5-20251001"

# The Claude Code CLI version. Must match the Dockerfile's pinned install (a
# hand-synced mirror); at or above the plugin's v2.1.144 skill-preload floor.
CC_VERSION = "2.1.203"

# A loop-guard cap, not an expected-turns figure: sized to the longest task
# (one CLI call plus a report; a couple for a precedence set) with headroom, so
# a looping agent is bounded without truncating a legitimate turn.
MESSAGE_LIMIT = 16
TIME_LIMIT = 300

_HERE = Path(__file__).parent
_SKILL_FILE = _HERE.parents[3] / "skills" / "config" / "configure" / "SKILL.md"


def _configure_skill() -> Skill:
    """The shipped configure skill as an inspect Skill.

    inspect's file-based skill reader validates against a stricter schema than
    the Claude Code plugin format (it wants a *string* `allowed-tools` and
    rejects `argument-hint`), so the plugin's SKILL.md cannot be pointed at
    directly. Building the Skill from the file preserves the behavioural content
    — the instructions body Claude actually follows — which is what the eval
    grades; only the metadata envelope is adapted. Phase 3 confirms the skill
    is discovered and invoked in the sandbox.
    """
    _, frontmatter, body = _SKILL_FILE.read_text().split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return Skill(
        name=meta["name"],
        description=meta["description"],
        instructions=body.strip(),
    )


def _task(*, with_skill: bool) -> Task:
    agent = (
        claude_code(
            skills=[_configure_skill()],
            version=CC_VERSION,
            cwd=WORKDIR,
        )
        if with_skill
        else claude_code(
            disallowed_tools=["Skill"],
            version=CC_VERSION,
            cwd=WORKDIR,
        )
    )
    return Task(
        dataset=json_dataset(str(_HERE / "dataset.jsonl")),
        solver=chain(seed_fixtures(), agent),
        scorer=configure_scorer(with_skill=with_skill),
        epochs=Epochs(EPOCHS, pass_k(EPOCHS)),
        sandbox=("docker", str(_HERE / "compose.yaml")),
        model=MODEL,
        message_limit=MESSAGE_LIMIT,
        time_limit=TIME_LIMIT,
        fail_on_error=True,
        name=ARM_WITH_SKILL if with_skill else ARM_BASELINE,
    )


@task
def configure_with_skill() -> Task:
    return _task(with_skill=True)


@task
def configure_baseline() -> Task:
    return _task(with_skill=False)
