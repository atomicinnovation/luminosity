"""Byte-compare the compiled binary's stdout against every committed golden.

`test_context_dataset.py` pins the goldens against the Rust *literals*, and
`cli/launcher/tests/context.rs` proves the binary's composition against
hand-written fixtures. Neither proves that *these* fixtures produce *these*
goldens — until now that only happened inside a live, billed eval run, so a
mis-pathed fixture could sit green in CI and fail against a real agent.

This runs the shipped argv against each fixture directory and compares stdout,
reusing the scorer's newline semantics so the two tiers cannot disagree about
what "no block" prints.
"""

import shutil
import subprocess
from pathlib import Path

import pytest
from invoke import Exit

from tasks.shared.eval.run import host_binary
from tests.evals.skills.configure.context_scorer import SCORER_ARGV, grade_block
from tests.unit.evals.skills.configure.test_context_dataset import _records

_FIXTURES = (
    Path(__file__).resolve().parents[4]
    / "evals"
    / "skills"
    / "configure"
    / "fixtures"
)

_CASES = [
    pytest.param(record["metadata"], id=str(record["metadata"]["scenario"]))
    for record in _records()
]


def _binary() -> Path:
    try:
        return host_binary()
    except Exit as absent:
        pytest.skip(str(absent))


def _seed(workdir: Path, fixture: str) -> None:
    # Mirrors solvers._seed: the .git marker bounds the launcher's upward walk
    # for the project root, and the fixture tree is copied whole.
    (workdir / ".git").mkdir(parents=True)
    shutil.copytree(
        _FIXTURES / fixture / ".luminosity", workdir / ".luminosity"
    )


@pytest.mark.parametrize("metadata", _CASES)
def test_binary_output_matches_each_golden(
    metadata: dict[str, object], tmp_path: Path
) -> None:
    binary = _binary()
    _seed(tmp_path, str(metadata["fixture"]))

    result = subprocess.run(
        [str(binary), *SCORER_ARGV],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert grade_block(result.stdout, str(metadata["expected_block"])), (
        f"{metadata['scenario']}: stdout {result.stdout!r} does not match "
        f"golden {metadata['expected_block']!r}"
    )


def test_the_matrix_covers_both_sources_present_and_absent() -> None:
    def carries(prefix: str) -> set[str]:
        return {
            str(record["metadata"]["scenario"])
            for record in _records()
            if any(
                str(source).startswith(prefix)
                for source in record["metadata"]["sources"]
            )
        }

    project = carries("config")
    skill = carries("skills/")
    assert project - skill, "no project-only scenario"
    assert skill - project, "no skill-only scenario"
    assert project & skill, "no both-sources scenario"
