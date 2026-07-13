"""Eval identifiers shared across the tasks/ and tests/ import boundary."""

ACCURACY_METRIC = "accuracy"
PLUGIN_DIR_ENV = "LUMINOSITY_EVAL_PLUGIN_DIR"
TRIALS = 3

WORKDIR_PREFIX = "luminosity-eval-"


# An arm is named for all three things that identify it: the skill it exercises,
# the capability of that skill under test, and the control — whether the skill
# was loaded. A skill grows capabilities over time, so leaving the capability
# implicit in the arm name only stays unambiguous while there is exactly one.
def with_skill_arm(skill: str, capability: str) -> str:
    return f"{skill}_{capability}_with_skill"


def baseline_arm(skill: str, capability: str) -> str:
    return f"{skill}_{capability}_baseline"


def pass_k_reducer(trials: int) -> str:
    return f"pass_k_{trials}"
