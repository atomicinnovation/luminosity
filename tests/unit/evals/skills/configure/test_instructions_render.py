"""Byte-grade the deterministic instructions scenarios against the binary.

This is the one seam the Rust tiers cannot see: that the exact argv the
configure SKILL.md injects, run against each committed fixture, renders the
committed golden. It runs the host-native release launcher (built by
`build:launcher:host`, a dependency of the eval-logic tier) with `SCORER_ARGV`
and byte-compares stdout against each scenario's `expected_block`.
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

from tasks.shared.eval.run import host_binary
from tests.evals.skills.configure.instructions_scorer import SCORER_ARGV

_EVAL_DIR = (
    Path(__file__).resolve().parents[4] / "evals" / "skills" / "configure"
)
_DATASET = _EVAL_DIR / "instructions_dataset.json"
_FIXTURES = _EVAL_DIR / "fixtures"


def _records() -> list[dict[str, Any]]:
    return json.loads(_DATASET.read_text())


def grade_block(stdout: str, expected: str) -> bool:
    # The binary appends one trailing newline via println!; an empty block
    # prints nothing at all.
    if not expected:
        return stdout == ""
    return stdout == f"{expected}\n"


def _render(fixture: str) -> str:
    workdir = Path(tempfile.mkdtemp(prefix="luminosity-render-"))
    try:
        (workdir / ".git").mkdir()
        shutil.copytree(
            _FIXTURES / fixture / ".luminosity", workdir / ".luminosity"
        )
        result = subprocess.run(
            [str(host_binary()), *SCORER_ARGV],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.parametrize(
    "record", _records(), ids=lambda record: record["metadata"]["scenario"]
)
def test_binary_output_matches_each_golden(record: dict[str, Any]) -> None:
    metadata = record["metadata"]
    stdout = _render(metadata["fixture"])
    assert grade_block(stdout, metadata["expected_block"]), (
        f"binary output drifted from the golden for {metadata['scenario']}"
    )
