from inspect_ai.model import ChatMessageAssistant, ChatMessageUser

from tests.evals.skills.configure.context_scorer import (
    grade_behaviour,
    grade_block,
    transcript_text,
)


class TestGradeBlock:
    def test_stdout_reconciles_the_single_terminating_newline(self) -> None:
        assert grade_block(
            "## Project Context\n\nx\n", "## Project Context\n\nx"
        )

    def test_a_block_with_no_terminator_is_rejected(self) -> None:
        assert not grade_block(
            "## Project Context\n\nx", "## Project Context\n\nx"
        )

    def test_mismatch_is_rejected(self) -> None:
        assert not grade_block(
            "## Project Context\n\nx\n", "## Project Context"
        )

    def test_empty_block_accepts_empty_stdout(self) -> None:
        assert grade_block("", "")

    def test_a_present_block_against_an_empty_expectation_is_rejected(
        self,
    ) -> None:
        assert not grade_block("## Project Context\n\nx\n", "")

    def test_a_trailing_blank_line_breaks_the_match(self) -> None:
        assert not grade_block("body\n\n", "body")


class TestGradeBehaviour:
    def test_sentinel_present(self) -> None:
        assert grade_behaviour("... GILDED-OTTER-42 ...", "GILDED-OTTER-42")

    def test_sentinel_absent(self) -> None:
        assert not grade_behaviour("no marker here", "GILDED-OTTER-42")


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
