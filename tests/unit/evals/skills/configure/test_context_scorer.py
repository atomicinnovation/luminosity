from inspect_ai.model import ChatMessageAssistant, ChatMessageUser

from tests.evals.skills.configure.context_scorer import (
    grade_behaviour,
    transcript_text,
)


class TestGradeBehaviour:
    def test_sentinel_present(self) -> None:
        assert grade_behaviour("... GILDED-OTTER-42 ...", ["GILDED-OTTER-42"])

    def test_sentinel_absent(self) -> None:
        assert not grade_behaviour("no marker here", ["GILDED-OTTER-42"])

    def test_every_sentinel_must_be_present(self) -> None:
        # The global-and-skill arm exists to prove both blocks reached the
        # model, so one sentinel out of two must not clear it.
        assert grade_behaviour("Lantern and Tier", ["Lantern", "Tier"])
        assert not grade_behaviour("Lantern only", ["Lantern", "Tier"])

    def test_no_sentinels_is_not_a_pass(self) -> None:
        assert not grade_behaviour("anything at all", [])

    def test_a_sentinel_used_as_a_common_noun_still_counts(self) -> None:
        # The agent applied the convention — "resolved across two tiers" — and
        # lower-cased it as English prose does. That is the convention landing,
        # not failing to.
        assert grade_behaviour("resolved across two tiers", ["Tier"])


class TestTranscriptText:
    def test_joins_assistant_content_only(self) -> None:
        messages = [
            ChatMessageUser(content="user prompt with GILDED-OTTER-42"),
            ChatMessageAssistant(content="assistant said SILVER-FOX"),
            ChatMessageAssistant(content="and then GILDED-OTTER-42"),
        ]
        text = transcript_text(messages)
        assert "SILVER-FOX" in text
        assert "GILDED-OTTER-42" in text
        # the user message must not leak into the behavioural check
        assert text.count("GILDED-OTTER-42") == 1
