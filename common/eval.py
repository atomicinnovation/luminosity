"""Eval identifiers shared across the tasks/ and tests/ import boundary."""

ACCURACY_METRIC = "accuracy"
PLUGIN_DIR_ENV = "LUMINOSITY_EVAL_PLUGIN_DIR"
TRIALS = 3

WORKDIR_PREFIX = "luminosity-eval-"


def with_skill_arm(skill: str) -> str:
    return f"{skill}_with_skill"


def baseline_arm(skill: str) -> str:
    return f"{skill}_baseline"


def pass_k_reducer(trials: int) -> str:
    return f"pass_k_{trials}"
