"""Regression: the native-tls ban must fail the build, not warn."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

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


# Reading the real feature tree catches a regression even if deny's config
# drifts.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_WORKSPACE = _REPO_ROOT / "cli"

_FORBIDDEN_IN_LAUNCHER_TREE = (
    "openssl-sys",
    "native-tls",
    "rustls-native-certs",
    "security-framework",
    "aws-lc-rs",
    "aws-lc-sys",
)


def _launcher_feature_tree() -> str:
    result = subprocess.run(
        ["cargo", "tree", "-e", "features", "-p", "luminosity"],
        cwd=_WORKSPACE,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.mark.parametrize("crate", _FORBIDDEN_IN_LAUNCHER_TREE)
def test_launcher_tree_excludes_the_native_tls_closure(crate: str) -> None:
    _require_tools()
    tree = _launcher_feature_tree()
    assert crate not in tree, f"{crate} entered the launcher dependency tree"


def test_launcher_tree_uses_the_ring_crypto_provider() -> None:
    # Positive control: the negative aws-lc-rs assertion must not pass merely
    # because TLS dropped out.
    _require_tools()
    assert "ring" in _launcher_feature_tree()
