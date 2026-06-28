"""Regression: the cargo-pup blocking lane has teeth, and pup.ron loads.

Parallel to the cargo-deny ban-violation test, this makes the blocking-check AC
self-verifying in 0006 rather than deferring it to 0007: a throwaway crate
carrying a rule it violates must make `cargo +<nightly> pup` exit non-zero. A
second assertion runs `print-modules` against the repo's real pup.ron — because
the bootstrap pup.ron is empty, a passing `pup:check` is otherwise
indistinguishable from one where the config silently failed to parse.

This suite lives in its own `tests/integration/pup/` directory (not the general
`tests/integration/tasks/`) so it is isolated by path, not a marker: it needs
the nightly lane and runs only in `check-architecture` (via
`mise run test:integration:pup`), which provisions the nightly through
pup:check's deps:install:pup dependency.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tasks.shared.rust import PUP_NIGHTLY

REPO_ROOT = Path(__file__).resolve().parents[3]

_CARGO = shutil.which("cargo")
_CARGO_PUP = shutil.which("cargo-pup")

_PROBE_MANIFEST = """\
[workspace]

[package]
name = "pup-probe"
version = "0.0.0"
edition = "2021"
license = "MIT"

[lib]
path = "lib.rs"
"""

_PROBE_LIB = "pub struct Exposed {\n    pub value: u8,\n}\n"

# A public struct required to be private — a rule the probe crate violates.
_PROBE_PUP_RON = """\
(
    lints: [
        Struct((
            name: "force_failure",
            matches: Name(".*"),
            rules: [
                MustBePrivate(Error),
            ],
        )),
    ],
)
"""


def _in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def _require_tools() -> None:
    missing = [
        name
        for name, path in (("cargo", _CARGO), ("cargo-pup", _CARGO_PUP))
        if path is None
    ]
    if not missing:
        return
    message = f"tools not on PATH: {', '.join(missing)}"
    if _in_ci():
        pytest.fail(f"{message} — pup provisioning regression in CI")
    pytest.skip(message)


def _pup(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["cargo", f"+{PUP_NIGHTLY}", "pup", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_rule_violation_fails_the_check(tmp_path: Path) -> None:
    _require_tools()
    (tmp_path / "Cargo.toml").write_text(_PROBE_MANIFEST)
    (tmp_path / "lib.rs").write_text(_PROBE_LIB)
    (tmp_path / "pup.ron").write_text(_PROBE_PUP_RON)
    result = _pup(cwd=tmp_path)
    assert result.returncode != 0, result.stdout + result.stderr


def test_repo_pup_ron_actually_loads() -> None:
    _require_tools()
    result = _pup("print-modules", cwd=REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
