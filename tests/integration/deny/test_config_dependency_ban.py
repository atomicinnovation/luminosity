"""Regression: the serde-free `config` core must not reach serde.

Copies the workspace into a tempdir, injects a direct `serde` dependency into
the copied `config` crate, and asserts `cargo deny check bans` rejects it —
proving the cross-crate dependency-direction ban still bans.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_CARGO = shutil.which("cargo")
_CARGO_DENY = shutil.which("cargo-deny")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKSPACE = _REPO_ROOT / "cli"


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


def _inject_serde_into_config(workspace: Path) -> None:
    manifest = workspace / "config" / "Cargo.toml"
    manifest.write_text(manifest.read_text() + "serde = { workspace = true }\n")


def test_adding_serde_to_config_fails_the_bans_check(
    tmp_path: Path,
) -> None:
    _require_tools()
    workspace = tmp_path / "cli"
    shutil.copytree(
        _WORKSPACE,
        workspace,
        ignore=shutil.ignore_patterns("target"),
    )
    _inject_serde_into_config(workspace)

    result = subprocess.run(
        ["cargo", "deny", "check", "bans"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode != 0, combined
    assert "serde" in combined
    assert "config" in combined
