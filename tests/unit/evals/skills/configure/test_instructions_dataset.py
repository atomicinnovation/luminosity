"""Data-hygiene tests for the instructions injection eval datasets.

The deterministic scenarios carry an `expected_block` golden that the CI render
test byte-compares the compiled binary against; these tests keep those goldens
honest — each is re-derived here from the fixture bodies the adapter would read
(frontmatter stripped, blank-trimmed, combined team-then-personal) and pinned to
the block's prose, which is scraped from the Rust source. The behavioural
scenarios instead carry sentinels; those are pinned to the fixture bodies they
must appear in, and to their twins in the live behavioural dataset.
"""

import json
from pathlib import Path
from typing import Any

from tests.evals.skills.configure.instructions_scorer import SCORER_ARGV

_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "instructions_dataset.json"
_BEHAVIOURAL_DATASET = _EVAL_DIR / "instructions_behavioural_dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"
_RUST_CLI = (
    Path(__file__).resolve().parents[4].parent
    / "cli"
    / "launcher"
    / "src"
    / "instructions_command"
    / "inbound"
    / "cli.rs"
)

SKILL = "configure"


# A Python transcription of the block header and the instructions_prose literal
# in cli/launcher/src/instructions_command/inbound/cli.rs. The Rust literal is
# not reachable from Python, so test_instructions_block_prefix_matches_the_rust
# _source scrapes the source to keep this in step; the render test proves the
# compiled binary agrees byte-for-byte.
def _block_prefix(skill: str) -> str:
    return (
        "## Additional Instructions\n\n"
        "The following additional instructions have been provided for the\n"
        f"{skill} skill. Follow these instructions in addition to all\n"
        "instructions above.\n\n"
    )


INSTRUCTIONS_BLOCK_PREFIX = _block_prefix(SKILL)


def _records() -> list[dict[str, Any]]:
    return json.loads(_DATASET.read_text())


def _behavioural_records() -> list[dict[str, Any]]:
    return json.loads(_BEHAVIOURAL_DATASET.read_text())


def _record(scenario: str) -> dict[str, Any]:
    return next(
        record
        for record in _records()
        if record["metadata"]["scenario"] == scenario
    )


def _instruction_body(fixture: str, name: str) -> str:
    path = _FIXTURES / fixture / ".luminosity" / "skills" / "configure" / name
    if not path.is_file():
        return ""
    text = path.read_text()
    # Mirrors the adapter: a leading frontmatter fence is stripped, a file
    # without one is injected whole. The fixtures carry no frontmatter, so this
    # returns the body verbatim.
    if not text.startswith("---"):
        return text
    return text.split("---", 2)[2]


def _trim(body: str) -> str:
    # Mirrors the Rust trim_blank_lines: drop leading and trailing
    # whitespace-only lines and the trailing terminator; preserve the interior.
    lines = body.split("\n")
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    end = len(lines)
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


def _block(fixture: str) -> str:
    parts = [
        trimmed
        for name in ("instructions.md", "instructions.local.md")
        if (trimmed := _trim(_instruction_body(fixture, name)))
    ]
    if not parts:
        return ""
    return INSTRUCTIONS_BLOCK_PREFIX + "\n\n".join(parts)


def _fixture_body(fixture: str, relative_path: str) -> str:
    path = _FIXTURES / fixture / ".luminosity" / relative_path
    if not path.is_file():
        message = (
            f"{fixture} declares a source it does not carry: {relative_path}"
        )
        raise AssertionError(message)
    return path.read_text()


def test_instructions_block_prefix_matches_the_rust_source() -> None:
    rust = _RUST_CLI.read_text()
    prose = (
        "The following additional instructions have been provided for the\n"
        "{skill} skill. Follow these instructions in addition to all\n"
        "instructions above."
    )
    assert prose in rust, "instructions_prose drifted from the transcription"
    assert r'"## Additional Instructions\n\n{prose}\n\n{}"' in rust
    reconstructed = (
        "## Additional Instructions\n\n" + prose.format(skill=SKILL) + "\n\n"
    )
    assert reconstructed == INSTRUCTIONS_BLOCK_PREFIX


def test_the_instructions_prose_interpolates_the_skill_name() -> None:
    short = _block_prefix("a").split("\n")
    long = _block_prefix("create-plan").split("\n")
    assert len(short) == len(long)
    differing = [
        index for index in range(len(short)) if short[index] != long[index]
    ]
    assert differing == [3], "only the skill-name line may differ"
    assert short[3] == "a skill. Follow these instructions in addition to all"


def test_the_scorer_argv_matches_the_skill_injection_line() -> None:
    configure_md = (
        Path(__file__).resolve().parents[4].parent
        / "skills"
        / "config"
        / "configure"
        / "SKILL.md"
    ).read_text()
    assert f"luminosity {' '.join(SCORER_ARGV)}`" in configure_md


def test_every_line_parses_and_carries_required_fields() -> None:
    for record in _records():
        metadata = record["metadata"]
        assert isinstance(record["input"], str)
        assert (_FIXTURES / metadata["fixture"]).is_dir()
        assert isinstance(metadata["behavioural"], bool)
        assert isinstance(metadata["expected_block"], str)
        assert isinstance(metadata["sentinels"], list)
        assert metadata["sources"]


def test_every_scenario_fixture_file_exists_on_disk() -> None:
    for record in _records():
        metadata = record["metadata"]
        for source in metadata["sources"]:
            path = _FIXTURES / metadata["fixture"] / ".luminosity" / source
            assert path.is_file(), f"missing fixture source: {path}"


def test_deterministic_golden_matches_the_fixture_body() -> None:
    for record in _records():
        metadata = record["metadata"]
        assert _block(metadata["fixture"]) == metadata["expected_block"], (
            f"golden drifted for {metadata['scenario']}"
        )


def test_both_levels_orders_team_before_personal_within_the_block() -> None:
    block = _record("both_levels")["metadata"]["expected_block"]
    team = block.index("Cite the relevant ADR")
    personal = block.index("Prefer jj over raw git")
    assert team < personal


def test_mixed_empty_level_drops_the_empty_with_no_doubled_blank() -> None:
    block = _record("mixed_empty")["metadata"]["expected_block"]
    assert block.endswith("Cite the relevant ADR when explaining a decision.")
    assert "\n\n\n" not in block


def test_instructions_empty_expects_no_block() -> None:
    assert _record("empty")["metadata"]["expected_block"] == ""


def test_ordering_carries_both_sentinels() -> None:
    metadata = _record("context_and_instructions_ordering")["metadata"]
    context_sentinel, instructions_sentinel = metadata["sentinels"]
    assert context_sentinel in _fixture_body(
        metadata["fixture"], "skills/configure/context.md"
    )
    assert instructions_sentinel in _fixture_body(
        metadata["fixture"], "skills/configure/instructions.md"
    )


def test_the_bodies_are_declarative_conventions() -> None:
    # A behavioural body must read as a declarative convention the agent adopts,
    # not an imperative "emit this token" the model recognises as an injection
    # and refuses — the failure mode the context dataset test documents.
    for record in _records():
        metadata = record["metadata"]
        if not metadata["behavioural"]:
            continue
        bodies = "".join(
            _fixture_body(metadata["fixture"], source)
            for source in metadata["sources"]
        )
        for sentinel in metadata["sentinels"]:
            assert sentinel in bodies


def test_the_behavioural_dataset_rows_match_their_main_dataset_twins() -> None:
    for record in _behavioural_records():
        scenario = record["metadata"]["scenario"]
        assert record == _record(scenario), (
            f"{scenario} drifted between the datasets"
        )


def test_the_behavioural_dataset_holds_only_behavioural_rows() -> None:
    scenarios = {
        record["metadata"]["scenario"] for record in _behavioural_records()
    }
    assert scenarios == {"behavioural", "context_and_instructions_ordering"}
