"""Structure and golden-coherence tests for the context injection datasets.

The `expected_block` goldens mirror the launcher's renderers
(cli/launcher/src/context_command/inbound/cli.rs). `BLOCK_PREFIX` and
`SKILL_BLOCK_PREFIX` transcribe its two headers and their prose,
`BLOCK_SEPARATOR` transcribes the blank line `join_blocks` composes them with,
and the rebuild test derives each golden from those plus the fixture bodies each
scenario *declares* as its sources.

The pinning tests keep that transcription honest: they scrape the Rust literals
themselves, so a change to a header, a prose line, or the separator that is not
mirrored here fails in CI rather than silently staling a golden — which would
otherwise surface only in a live, billed eval run.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[5]
_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "context_dataset.json"
_BEHAVIOURAL_DATASET = _EVAL_DIR / "context_behavioural_dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"
_RUST_INBOUND = (
    _REPO_ROOT
    / "cli"
    / "launcher"
    / "src"
    / "context_command"
    / "inbound"
    / "cli.rs"
)
_SKILL_MD = _REPO_ROOT / "skills" / "config" / "configure" / "SKILL.md"

SKILL = "configure"

# Hand-synced with render_project() / render_skill() / join_blocks() in
# cli/launcher/src/context_command/inbound/cli.rs, and pinned against those
# literals by the three scraper tests below.
BLOCK_PREFIX = (
    "## Project Context\n\n"
    "The following project-specific context has been provided. Take this into\n"
    "account when making decisions, selecting approaches, and generating "
    "output.\n\n"
)
SKILL_BLOCK_PREFIX = (
    "## Skill-Specific Context\n\n"
    f"The following context is specific to the {SKILL} skill. Apply this\n"
    "context in addition to any project-wide context above.\n\n"
)
BLOCK_SEPARATOR = "\n\n"

PROJECT_SOURCES = ("config.md", "config.local.md")
SKILL_SOURCES = (
    f"skills/{SKILL}/context.md",
    f"skills/{SKILL}/context.local.md",
)

# The dotted key a behavioural prompt tells the agent to read, e.g. the
# `core.example` in "Read the luminosity config value core.example".
_KEY_REFERENCE = re.compile(r"config value ([a-z0-9_.]+)")

_SCENARIOS = {
    "team_only",
    "personal_only",
    "both",
    "both_empty",
    "skill_team_only",
    "skill_both_levels",
    "skill_empty",
    "global_and_skill",
    "skill_behavioural",
}

_DETERMINISTIC = [
    "team_only",
    "personal_only",
    "both",
    "both_empty",
    "skill_team_only",
    "skill_both_levels",
    "skill_empty",
]


def _rust_source() -> str:
    return _RUST_INBOUND.read_text()


def _unescape(literal: str) -> str:
    # Rust's trailing-backslash line continuation swallows the newline and the
    # next line's leading whitespace; nothing else in the prose is escaped.
    return re.sub(r"\\\n\s*", "", literal)


def _rust_project_prose() -> str:
    match = re.search(
        r'const PROSE: &str = "(.*?)";', _rust_source(), re.DOTALL
    )
    if match is None:
        message = f"no PROSE const found in {_RUST_INBOUND}"
        raise AssertionError(message)
    return _unescape(match.group(1))


def _rust_skill_prose() -> str:
    match = re.search(
        r'fn skill_prose\(.*?format!\(\s*"(.*?)"\s*\)',
        _rust_source(),
        re.DOTALL,
    )
    if match is None:
        message = f"no skill_prose() found in {_RUST_INBOUND}"
        raise AssertionError(message)
    return _unescape(match.group(1)).replace("{skill}", SKILL)


def _rust_header(prose_anchor: str) -> str:
    # One scraper for both renderers: each format!'s literal is a `##` header
    # followed by a blank line and its prose placeholder, which is the only
    # thing that differs between them.
    match = re.search(
        rf'format!\("(#[^"\\]*?)\\n\\n\{{{prose_anchor}\}}', _rust_source()
    )
    if match is None:
        message = f"no {prose_anchor} header found in {_RUST_INBOUND}"
        raise AssertionError(message)
    return match.group(1)


def _rust_block_separator() -> str:
    match = re.search(
        r'fn join_blocks\(.*?blocks\.join\("(.*?)"\)', _rust_source(), re.DOTALL
    )
    if match is None:
        message = f"no join_blocks() separator found in {_RUST_INBOUND}"
        raise AssertionError(message)
    return match.group(1).encode().decode("unicode_escape")


def _records(dataset: Path = _DATASET) -> list[dict[str, Any]]:
    return json.loads(dataset.read_text())


def _body(fixture: str, relative_path: str) -> str:
    path = _FIXTURES / fixture / ".luminosity" / relative_path
    if not path.is_file():
        message = (
            f"{fixture} declares a source it does not carry: {relative_path}"
        )
        raise AssertionError(message)
    text = path.read_text()
    # Mirrors the adapter: a frontmatter mapping is stripped, a file without one
    # is injected whole.
    if not text.startswith("---"):
        return text
    return text.split("---", 2)[2]


def _frontmatter(fixture: str, relative_path: str) -> dict[str, Any]:
    path = _FIXTURES / fixture / ".luminosity" / relative_path
    if not path.is_file():
        message = f"{fixture} carries no {relative_path}"
        raise AssertionError(message)
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    parsed = yaml.safe_load(text.split("---", 2)[1])
    return parsed if isinstance(parsed, dict) else {}


def _defines(frontmatter: dict[str, Any], key: str) -> bool:
    node: Any = frontmatter
    for segment in key.split("."):
        if not isinstance(node, dict) or segment not in node:
            return False
        node = node[segment]
    return True


def _trim(body: str) -> str:
    # Mirrors `trim_blank_lines` (cli/config/src/context.rs): whole leading and
    # trailing blank lines go, interior blank lines and leading indentation stay
    # — and only the *last kept* line sheds a trailing `\r`, because the Rust
    # trimmer returns a slice of the original body and so leaves interior CRLF
    # line endings intact.
    lines = body.split("\n")
    non_blank = [index for index, line in enumerate(lines) if line.strip()]
    if not non_blank:
        return ""
    kept = lines[non_blank[0] : non_blank[-1] + 1]
    kept[-1] = kept[-1].rstrip("\r")
    return "\n".join(kept)


def _block(
    prefix: str, fixture: str, sources: list[str], names: tuple[str, ...]
) -> str:
    parts = [
        trimmed
        for trimmed in (
            _trim(_body(fixture, name)) for name in names if name in sources
        )
        if trimmed
    ]
    return prefix + BLOCK_SEPARATOR.join(parts) if parts else ""


def _expected_block(fixture: str, sources: list[str]) -> str:
    blocks = [
        block
        for block in (
            _block(BLOCK_PREFIX, fixture, sources, PROJECT_SOURCES),
            _block(SKILL_BLOCK_PREFIX, fixture, sources, SKILL_SOURCES),
        )
        if block
    ]
    return BLOCK_SEPARATOR.join(blocks)


def _record(scenario: str, dataset: Path = _DATASET) -> dict[str, Any]:
    return next(
        r for r in _records(dataset) if r["metadata"]["scenario"] == scenario
    )


def test_block_prefix_matches_the_rust_source() -> None:
    assert f"{_rust_header('PROSE')}\n\n{_rust_project_prose()}\n\n" == (
        BLOCK_PREFIX
    )


def test_skill_block_prefix_matches_the_rust_source() -> None:
    assert f"{_rust_header('prose')}\n\n{_rust_skill_prose()}\n\n" == (
        SKILL_BLOCK_PREFIX
    )


def test_the_skill_prose_interpolates_the_skill_name() -> None:
    assert "{skill}" in _unescape(
        re.search(  # type: ignore[union-attr]
            r'fn skill_prose\(.*?format!\(\s*"(.*?)"\s*\)',
            _rust_source(),
            re.DOTALL,
        ).group(1)
    )
    assert f"the {SKILL} skill" in SKILL_BLOCK_PREFIX


def test_the_block_separator_matches_the_rust_join_blocks() -> None:
    assert _rust_block_separator() == BLOCK_SEPARATOR


def test_the_scorer_argv_matches_the_skill_injection_line() -> None:
    from tests.evals.skills.configure.context_scorer import (  # noqa: PLC0415
        SCORER_ARGV,
    )

    match = re.search(
        r"!`\$\{CLAUDE_PLUGIN_ROOT\}/bin/luminosity (.+?)`",
        _SKILL_MD.read_text(),
    )
    if match is None:
        message = f"no injection line found in {_SKILL_MD}"
        raise AssertionError(message)
    assert match.group(1).split() == SCORER_ARGV


def test_every_line_parses_and_carries_required_fields() -> None:
    for record in _records():
        assert isinstance(record["input"], str)
        metadata = record["metadata"]
        assert metadata["scenario"] in _SCENARIOS
        assert (_FIXTURES / metadata["fixture"]).is_dir()
        assert isinstance(metadata["behavioural"], bool)
        assert isinstance(metadata["expected_block"], str)
        assert metadata["sources"]


def test_one_case_per_scenario() -> None:
    scenarios = [r["metadata"]["scenario"] for r in _records()]
    assert sorted(scenarios) == sorted(_SCENARIOS)


def test_every_scenario_fixture_file_exists_on_disk() -> None:
    for record in _records():
        metadata = record["metadata"]
        for source in metadata["sources"]:
            path = _FIXTURES / metadata["fixture"] / ".luminosity" / source
            assert path.is_file(), f"missing fixture source: {path}"


def test_a_mispathed_declared_source_raises() -> None:
    with pytest.raises(AssertionError):
        _body("context_team_only", "skills/configure/context.md")


@pytest.mark.parametrize("scenario", sorted(_SCENARIOS))
def test_deterministic_golden_matches_the_fixture_body(scenario: str) -> None:
    metadata = _record(scenario)["metadata"]
    assert metadata["expected_block"] == _expected_block(
        metadata["fixture"], metadata["sources"]
    )


@pytest.mark.parametrize("scenario", _DETERMINISTIC)
def test_the_deterministic_scenarios_are_not_billed(scenario: str) -> None:
    assert _record(scenario)["metadata"]["behavioural"] is False


def test_both_empty_expects_no_block() -> None:
    assert _record("both_empty")["metadata"]["expected_block"] == ""


def test_skill_empty_expects_no_skill_block() -> None:
    assert _record("skill_empty")["metadata"]["expected_block"] == ""


def test_both_orders_team_before_personal_with_one_blank_line() -> None:
    block = _record("both")["metadata"]["expected_block"]
    assert block.startswith(BLOCK_PREFIX)
    body = block[len(BLOCK_PREFIX) :]
    assert body == (
        "Team rule: BOTH-TEAM-SENTINEL.\n\n"
        "Personal rule: BOTH-PERSONAL-SENTINEL."
    )


def test_skill_both_levels_orders_team_before_personal_within_the_block() -> (
    None
):
    block = _record("skill_both_levels")["metadata"]["expected_block"]
    assert block.startswith(SKILL_BLOCK_PREFIX)
    body = block[len(SKILL_BLOCK_PREFIX) :]
    assert body == (
        "Skill team rule: SKILL-TEAM-SENTINEL.\n\n"
        "Skill personal rule: SKILL-PERSONAL-SENTINEL."
    )


def test_global_and_skill_orders_project_before_skill_with_one_blank_line() -> (
    None
):
    block = _record("global_and_skill")["metadata"]["expected_block"]
    assert block.startswith(BLOCK_PREFIX)
    project, separator, skill = block.partition(SKILL_BLOCK_PREFIX)
    assert separator == SKILL_BLOCK_PREFIX
    assert project.endswith(BLOCK_SEPARATOR)
    assert not project[: -len(BLOCK_SEPARATOR)].endswith("\n")
    assert skill


def test_the_behavioural_bodies_are_declarative_conventions() -> None:
    # The behavioural body must read as declarative project context (a
    # convention the agent applies), not an imperative "emit this token in
    # every response" — the model recognises the latter as a prompt injection
    # and refuses it, failing the arm for a reason unrelated to injection.
    for record in _records(_BEHAVIOURAL_DATASET):
        metadata = record["metadata"]
        bodies = "".join(
            _body(metadata["fixture"], source) for source in metadata["sources"]
        )
        for sentinel in metadata["sentinels"]:
            assert sentinel in bodies


def test_global_and_skill_carries_two_sentinels_present_in_both_bodies() -> (
    None
):
    metadata = _record("global_and_skill")["metadata"]
    project, skill = metadata["sentinels"]
    assert project in _body(metadata["fixture"], "config.md")
    assert skill in _body(metadata["fixture"], f"skills/{SKILL}/context.md")


def test_every_behavioural_prompt_reads_a_key_its_fixture_defines() -> None:
    # Each behavioural prompt opens with a config read, because that is what
    # routes the agent through the skill — which is where injection fires. A
    # prompt naming a key the fixture does not define still *usually* passes
    # (the agent recovers and describes configuration anyway), so the premise
    # can rot silently and only surface as a flake mid-billed-run. Pin it.
    for record in _records(_BEHAVIOURAL_DATASET):
        fixture = record["metadata"]["fixture"]
        for key in _KEY_REFERENCE.findall(record["input"]):
            defined = _defines(_frontmatter(fixture, "config.md"), key)
            assert defined, (
                f"{fixture} does not define '{key}', which its prompt reads"
            )


def test_the_behavioural_dataset_holds_exactly_the_behavioural_rows() -> None:
    behavioural = {
        r["metadata"]["scenario"]
        for r in _records()
        if r["metadata"]["behavioural"]
    }
    declared = {
        r["metadata"]["scenario"] for r in _records(_BEHAVIOURAL_DATASET)
    }
    assert declared == behavioural


def test_the_behavioural_dataset_rows_match_their_main_dataset_twins() -> None:
    # The billed copy is a duplicate, so a drift or typo in it must fail here,
    # in free CI, rather than mid-billed-run.
    for record in _records(_BEHAVIOURAL_DATASET):
        assert record == _record(record["metadata"]["scenario"])


def test_configure_dataset_count_is_unchanged() -> None:
    # The context datasets are separate; the configure get/set dataset stays 9.
    configure_dataset = json.loads((_EVAL_DIR / "dataset.json").read_text())
    assert len(configure_dataset) == 9
