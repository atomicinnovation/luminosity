"""Structure and golden-coherence tests for the context injection dataset.

The `expected_block` goldens are a hand-synced mirror of the launcher's
`render` (cli/launcher/src/context_command/inbound/cli.rs): the `BLOCK_PREFIX`
below transcribes its `## Project Context` header and two-line PROSE, and the
rebuild test derives each deterministic golden from that prefix plus the fixture
body, so a change to the Rust prose that is not mirrored here fails loudly
rather than silently staling the eval.
"""

import json
from pathlib import Path
from typing import Any

import pytest

_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "context_dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"

# Hand-synced with render() / PROSE in
# cli/launcher/src/context_command/inbound/cli.rs — the same literal that
# crate's byte-exact `renders_the_byte_exact_block` test asserts.
BLOCK_PREFIX = (
    "## Project Context\n\n"
    "The following project-specific context has been provided. Take this into\n"
    "account when making decisions, selecting approaches, and generating "
    "output.\n\n"
)

_SCENARIOS = {
    "team_only",
    "personal_only",
    "both",
    "both_empty",
    "behavioural",
}


def _records() -> list[dict[str, Any]]:
    return json.loads(_DATASET.read_text())


def _body(fixture: str, name: str) -> str:
    path = _FIXTURES / fixture / ".luminosity" / name
    if not path.exists():
        return ""
    return path.read_text().split("---", 2)[2]


def _trim(body: str) -> str:
    lines = body.split("\n")
    non_blank = [index for index, line in enumerate(lines) if line.strip()]
    if not non_blank:
        return ""
    return "\n".join(lines[non_blank[0] : non_blank[-1] + 1])


def _expected_block(fixture: str) -> str:
    parts = [
        trimmed
        for trimmed in (
            _trim(_body(fixture, "config.md")),
            _trim(_body(fixture, "config.local.md")),
        )
        if trimmed
    ]
    if not parts:
        return ""
    return BLOCK_PREFIX + "\n\n".join(parts)


def _record(scenario: str) -> dict[str, Any]:
    return next(r for r in _records() if r["metadata"]["scenario"] == scenario)


def test_every_line_parses_and_carries_required_fields() -> None:
    for record in _records():
        assert isinstance(record["input"], str)
        metadata = record["metadata"]
        assert metadata["scenario"] in _SCENARIOS
        assert (_FIXTURES / metadata["fixture"]).is_dir()
        assert isinstance(metadata["behavioural"], bool)


def test_one_case_per_scenario() -> None:
    scenarios = [r["metadata"]["scenario"] for r in _records()]
    assert sorted(scenarios) == sorted(_SCENARIOS)


@pytest.mark.parametrize(
    "scenario", ["team_only", "personal_only", "both", "both_empty"]
)
def test_deterministic_golden_matches_the_fixture_body(
    scenario: str,
) -> None:
    record = _record(scenario)
    assert record["metadata"]["behavioural"] is False
    assert record["metadata"]["expected_block"] == _expected_block(
        record["metadata"]["fixture"]
    )


def test_both_empty_expects_an_empty_block() -> None:
    assert _record("both_empty")["metadata"]["expected_block"] == ""


def test_both_orders_team_before_personal_with_one_blank_line() -> None:
    block = _record("both")["metadata"]["expected_block"]
    assert block.startswith(BLOCK_PREFIX)
    body = block[len(BLOCK_PREFIX) :]
    assert body == (
        "Team rule: BOTH-TEAM-SENTINEL.\n\n"
        "Personal rule: BOTH-PERSONAL-SENTINEL."
    )


def test_behavioural_case_names_a_sentinel_present_in_its_body() -> None:
    metadata = _record("behavioural")["metadata"]
    assert metadata["behavioural"] is True
    sentinel = metadata["sentinel"]
    assert sentinel in _body(metadata["fixture"], "config.md")


def test_configure_dataset_count_is_unchanged() -> None:
    # The context dataset is separate; the configure get/set dataset stays 9.
    configure_dataset = json.loads((_EVAL_DIR / "dataset.json").read_text())
    assert len(configure_dataset) == 9
