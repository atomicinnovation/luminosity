import json
from pathlib import Path
from typing import Any

import pytest
import yaml

_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"

# A Python transcription of the cli/config/src/error.rs Display templates. The
# Rust templates are not reachable from Python, so keeping these in step is a
# manual eval-refresh trigger on any error-message change.
_DOMAIN_TEMPLATES = (
    "config key '<key>' is not set",
    "config key '<key>' is not set at level '<level>'",
    "cannot set '<key>': '<at>' is a <existing>, not a <opposite>",
    "invalid config key '<key>': expected dot-separated non-empty segments",
    "config file '<path>' has malformed frontmatter: <detail>",
)


def _records() -> list[dict[str, Any]]:
    return json.loads(_DATASET.read_text())


def _seeded_value(fixture: str, key: str) -> Any:
    text = (_FIXTURES / fixture / ".luminosity" / "config.md").read_text()
    frontmatter = text.split("---")[1]
    tree = yaml.safe_load(frontmatter)
    for segment in key.split("."):
        tree = tree[segment]
    return tree


def test_every_line_parses_and_carries_required_fields():
    for record in _records():
        assert isinstance(record["input"], str)
        assert isinstance(record["target"], str)
        metadata = record["metadata"]
        assert metadata["action"] in {"get", "set"}
        assert isinstance(metadata["key"], str)
        assert isinstance(metadata["expect_error"], bool)
        assert (_FIXTURES / metadata["fixture"]).is_dir()


def test_domain_markers_are_substrings_of_the_templates():
    for record in _records():
        metadata = record["metadata"]
        if not metadata["expect_error"]:
            continue
        assert any(
            metadata["marker"] in template for template in _DOMAIN_TEMPLATES
        )


def test_get_hit_target_is_the_seeded_team_value():
    hit = next(
        r
        for r in _records()
        if r["metadata"]["action"] == "get"
        and not r["metadata"]["expect_error"]
        and r["metadata"]["fixture"] == "team_core_example"
        and r["metadata"].get("level") is None
    )
    assert hit["target"] == _seeded_value(
        hit["metadata"]["fixture"], hit["metadata"]["key"]
    )


def _count(predicate: Any) -> int:
    return sum(1 for r in _records() if predicate(r["metadata"]))


class TestNineScenarioClasses:
    def test_total_is_nine(self):
        assert len(_records()) == 9

    @pytest.mark.parametrize(
        "predicate",
        [
            lambda m: (
                m["action"] == "get"
                and not m["expect_error"]
                and m["fixture"] == "team_core_example"
                and m.get("level") is None
            ),
            lambda m: (
                m["action"] == "get"
                and not m["expect_error"]
                and m["fixture"] == "empty_value"
            ),
            lambda m: (
                m["action"] == "get"
                and not m["expect_error"]
                and m.get("level") == "team"
            ),
            lambda m: (
                m["action"] == "set"
                and not m["expect_error"]
                and "expected_team" in m
            ),
            lambda m: (
                m["action"] == "set"
                and m["expect_error"]
                and m["marker"] == "cannot set"
            ),
            lambda m: (
                m["action"] == "get"
                and m["expect_error"]
                and m["marker"] == "is not set"
            ),
            lambda m: m["expect_error"] and m["marker"] == "invalid config key",
            lambda m: (
                m["expect_error"] and m["marker"] == "malformed frontmatter"
            ),
            lambda m: (
                m["action"] == "get"
                and not m["expect_error"]
                and m.get("level") == "personal"
            ),
        ],
    )
    def test_exactly_one_of_each_class(self, predicate: Any):
        assert _count(predicate) == 1
