from typing import TYPE_CHECKING

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    scorer,
    stderr,
)

from tests.evals.skills.configure.context_scorer import (
    grade_behaviour,
    transcript_text,
)

if TYPE_CHECKING:
    from inspect_ai.solver import TaskState

SKILL = "configure"


def instructions_scorer():
    @scorer(metrics=[accuracy(), stderr()])
    def instructions():
        async def score(state: TaskState, target: Target) -> Score:
            passed = grade_behaviour(
                transcript_text(state.messages), state.metadata["sentinels"]
            )
            return Score(
                value=CORRECT if passed else INCORRECT,
                metadata={"scenario": state.metadata.get("scenario")},
            )

        return score

    return instructions()
