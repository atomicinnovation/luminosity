"""Regression: the ADR-0010 native-tls ban must fail the build, not warn.

Runs `cargo deny check bans` against a throwaway manifest that depends on
native-tls and asserts a non-zero exit, so a future edit loosening `[bans] deny`
is caught automatically. The manifest is isolated in `tmp_path` with its own
`[workspace]` table so cargo/cargo-deny do not walk upward and absorb the real
workspace or its committed Cargo.lock — otherwise the test could pass for the
wrong reason (resolving the real graph rather than the banned dependency).
"""

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

_CARGO = shutil.which("cargo")
_CARGO_DENY = shutil.which("cargo-deny")

_PROBE_MANIFEST = """\
[workspace]

[package]
name = "ban-probe"
version = "0.0.0"
edition = "2021"
license = "MIT"

[dependencies]
native-tls = "0.2"

[[bin]]
name = "ban-probe"
path = "main.rs"
"""

_PROBE_DENY = """\
[bans]
deny = [{ crate = "native-tls" }]
"""


def _in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def _require_tools() -> None:
    missing = [
        name
        for name, path in (("cargo", _CARGO), ("cargo-deny", _CARGO_DENY))
        if path is None
    ]
    if not missing:
        return
    message = f"tools not on PATH: {', '.join(missing)}"
    if _in_ci():
        pytest.fail(f"{message} — provisioning regression in CI")
    pytest.skip(message)


def _write_probe(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").write_text(_PROBE_MANIFEST)
    (tmp_path / "deny.toml").write_text(_PROBE_DENY)
    (tmp_path / "main.rs").write_text("fn main() {}\n")


def test_native_tls_dependency_fails_the_bans_check(tmp_path: Path) -> None:
    _require_tools()
    _write_probe(tmp_path)
    subprocess.run(
        ["cargo", "generate-lockfile"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["cargo", "deny", "check", "bans"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "native-tls" in (result.stdout + result.stderr)
