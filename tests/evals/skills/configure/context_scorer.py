from typing import TYPE_CHECKING, Any

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    scorer,
    stderr,
)

if TYPE_CHECKING:
    from inspect_ai.solver import TaskState

SKILL = "configure"


def grade_behaviour(transcript_text: str, sentinels: list[str]) -> bool:
    # Every sentinel, not any: the global-and-skill arm exists to prove that
    # *both* blocks reached the model, so clearing on one would not assert it.
    #
    # Case-insensitively, because a sentinel is a terminology *convention* the
    # agent adopts, and prose naturally lower-cases a term used as a common noun
    # ("resolved across two tiers"). Capitalisation is not part of what the
    # convention asserts, so grading on it would fail an arm that demonstrably
    # received the block.
    haystack = transcript_text.casefold()
    return bool(sentinels) and all(
        sentinel.casefold() in haystack for sentinel in sentinels
    )


def transcript_text(messages: list[Any]) -> str:
    texts: list[str] = []
    for message in messages:
        if getattr(message, "role", None) != "assistant":
            continue
        content = getattr(message, "content", "")
        if isinstance(content, str):
            texts.append(content)
    return "\n".join(texts)


def context_scorer():
    @scorer(metrics=[accuracy(), stderr()])
    def context():
        async def score(state: TaskState, target: Target) -> Score:
            passed = grade_behaviour(
                transcript_text(state.messages), state.metadata["sentinels"]
            )
            return Score(
                value=CORRECT if passed else INCORRECT,
                metadata={"scenario": state.metadata.get("scenario")},
            )

        return score

    return context()
