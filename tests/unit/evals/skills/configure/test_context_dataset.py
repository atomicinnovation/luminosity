"""Data-hygiene tests for the context injection eval dataset.

Every row is behavioural — a live, billed agent run asserting that an injected
block *reached the model*. What the block renders to, byte for byte, is proved
for free by the compiled binary's own tests (cli/launcher/tests/context.rs), so
nothing here re-derives goldens or scrapes the Rust source. These tests instead
keep the billed dataset's premises honest: that each row's sentinels actually
appear in the fixture it seeds, and that each prompt reads a key its fixture
defines — so a rotten premise fails in free CI rather than mid-billed-run.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "context_dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"

SKILL = "configure"

# The dotted key a behavioural prompt tells the agent to read, e.g. the
# `core.example` in "Read the luminosity config value core.example".
_KEY_REFERENCE = re.compile(r"config value ([a-z0-9_.]+)")

_SCENARIOS = {"global_and_skill", "skill_behavioural"}


def _records() -> list[dict[str, Any]]:
    return json.loads(_DATASET.read_text())


def _record(scenario: str) -> dict[str, Any]:
    return next(r for r in _records() if r["metadata"]["scenario"] == scenario)


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


def test_every_line_parses_and_carries_required_fields() -> None:
    for record in _records():
        assert isinstance(record["input"], str)
        metadata = record["metadata"]
        assert metadata["scenario"] in _SCENARIOS
        assert (_FIXTURES / metadata["fixture"]).is_dir()
        assert metadata["behavioural"] is True
        assert metadata["sources"]
        assert metadata["sentinels"]


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
        _body("context_skill_behavioural", "config.local.md")


def test_the_bodies_are_declarative_conventions() -> None:
    # The behavioural body must read as declarative project context (a
    # convention the agent applies), not an imperative "emit this token in
    # every response" — the model recognises the latter as a prompt injection
    # and refuses it, failing the arm for a reason unrelated to injection.
    for record in _records():
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


def test_every_prompt_reads_a_key_its_fixture_defines() -> None:
    # Each behavioural prompt opens with a config read, because that is what
    # routes the agent through the skill — which is where injection fires. A
    # prompt naming a key the fixture does not define still *usually* passes
    # (the agent recovers and describes configuration anyway), so the premise
    # can rot silently and only surface as a flake mid-billed-run. Pin it.
    for record in _records():
        fixture = record["metadata"]["fixture"]
        for key in _KEY_REFERENCE.findall(record["input"]):
            defined = _defines(_frontmatter(fixture, "config.md"), key)
            assert defined, (
                f"{fixture} does not define '{key}', which its prompt reads"
            )
