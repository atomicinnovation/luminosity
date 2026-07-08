"""Skill-agnostic eval contract shared across the tasks/ and tests/ boundaries.

Both the task-side orchestration (which cannot import the tests/ tree) and the
tests-side eval definitions derive their arm names, reducer name, metric name,
and plugin-dir env var from here, so the two never drift.
"""

ACCURACY_METRIC = "accuracy"
PLUGIN_DIR_ENV = "LUMINOSITY_EVAL_PLUGIN_DIR"
TRIALS = 3


def with_skill_arm(skill: str) -> str:
    return f"{skill}_with_skill"


def baseline_arm(skill: str) -> str:
    return f"{skill}_baseline"


def pass_k_reducer(trials: int) -> str:
    return f"pass_k_{trials}"
