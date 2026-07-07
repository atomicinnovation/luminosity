"""Regression coverage for the cargo-pup architecture lane.

Needs the nightly lane, so it lives in its own directory and runs only in
check-architecture.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tasks.shared.rust import PUP_NIGHTLY

REPO_ROOT = Path(__file__).resolve().parents[3]

# cargo-pup colours print-modules output even under NO_COLOR; strip the SGR
# escapes before asserting on the text.
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

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


def test_real_inward_rule_binds_to_a_real_module() -> None:
    # Guards against a green-but-inert rule: `print-modules` lists each module
    # with its applicable lints, so the rule on the core line proves attachment.
    _require_tools()
    result = _pup("print-modules", cwd=REPO_ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    plain = _ANSI.sub("", result.stdout)
    core_line = next(
        (
            line
            for line in plain.splitlines()
            if line.strip().startswith("::version::core")
        ),
        None,
    )
    assert core_line is not None, f"version::core not reported:\n{plain}"
    assert "version_core_imports_only_permitted" in core_line, (
        f"inward rule not attached to version::core:\n{plain}"
    )


# A probe crate mirroring the hexagon (core + outbound) with the same rule
# shape. The violating core imports the adapter; the compliant core does not.
_PROBE_INWARD_LIB = "pub mod core;\npub mod outbound;\n"
_PROBE_INWARD_OUTBOUND = "pub struct Exposed {\n    pub value: u8,\n}\n"
_PROBE_INWARD_CORE_VIOLATION = (
    "use crate::outbound::Exposed;\n\n"
    "pub fn make() -> Exposed {\n    Exposed { value: 0 }\n}\n"
)
_PROBE_INWARD_CORE_COMPLIANT = "pub fn make() -> u8 {\n    0\n}\n"
_PROBE_INWARD_PUP_RON = """\
(
    lints: [
        Module((
            name: "probe_core_imports_only_permitted",
            matches: Module("^pup_probe::core($|::)"),
            rules: [
                RestrictImports(
                    allowed_only: Some([
                        "^(std|core|alloc)(::|$)",
                        "^crate::core(::|$)",
                    ]),
                    denied: None,
                    severity: Error,
                ),
            ],
        )),
    ],
)
"""


def test_inward_violation_is_rejected_and_removal_passes(
    tmp_path: Path,
) -> None:
    _require_tools()
    (tmp_path / "Cargo.toml").write_text(_PROBE_MANIFEST)
    (tmp_path / "lib.rs").write_text(_PROBE_INWARD_LIB)
    (tmp_path / "outbound.rs").write_text(_PROBE_INWARD_OUTBOUND)
    (tmp_path / "pup.ron").write_text(_PROBE_INWARD_PUP_RON)

    (tmp_path / "core.rs").write_text(_PROBE_INWARD_CORE_VIOLATION)
    violation = _pup(cwd=tmp_path)
    assert violation.returncode != 0, violation.stdout + violation.stderr

    (tmp_path / "core.rs").write_text(_PROBE_INWARD_CORE_COMPLIANT)
    compliant = _pup(cwd=tmp_path)
    assert compliant.returncode == 0, compliant.stdout + compliant.stderr
