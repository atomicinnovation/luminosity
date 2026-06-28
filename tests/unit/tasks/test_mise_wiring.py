"""Assert the mise task wiring the plan relies on.

The other task tests mock invoke's `Context` and assert command strings; none
reads `mise.toml`, so the `depends`/aggregate edges are otherwise untested. This
module parses `mise.toml` (and the Rust config files) directly so the wiring
prose becomes executable assertions. Introduced in Phase 1 and extended each
phase as edges are added.
"""

import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

Mise = dict[str, Any]


@pytest.fixture
def mise() -> Mise:
    return tomllib.loads((REPO_ROOT / "mise.toml").read_text())


def _tasks(mise: Mise) -> Mise:
    return mise["tasks"]


def _depends(mise: Mise, name: str) -> list[str]:
    return _tasks(mise)[name].get("depends", [])


class TestCliCheckWiring:
    def test_cli_check_folds_format_and_lint_only(self, mise: Mise):
        assert _depends(mise, "cli:check") == [
            "format:cli:check",
            "lint:cli:check",
        ]

    def test_cli_check_carries_no_tests(self, mise: Mise):
        assert "test:unit:cli" not in _depends(mise, "cli:check")

    def test_check_includes_cli_check(self, mise: Mise):
        assert "cli:check" in _depends(mise, "check")


class TestBuildCliWiring:
    def test_build_cli_is_in_default(self, mise: Mise):
        assert "build:cli" in _depends(mise, "default")

    def test_build_cli_is_absent_from_check(self, mise: Mise):
        assert "build:cli" not in _depends(mise, "check")

    def test_build_cli_is_absent_from_cli_check(self, mise: Mise):
        assert "build:cli" not in _depends(mise, "cli:check")

    def test_build_cli_provisions_cross_targets(self, mise: Mise):
        assert "deps:install:rust-targets" in _depends(mise, "build:cli")


class TestToolchainCoherence:
    """The clippy msrv and rustfmt edition mirror the mise rust pin by hand.

    A rust bump that updates mise.toml but forgets these silently applies
    MSRV-gated lints against a different stable than CI provisions, so the
    fourth-hand-synced-mirror hazard is converted into a tested invariant.
    """

    def test_clippy_msrv_matches_mise_rust_pin(self, mise: Mise):
        clippy = tomllib.loads((REPO_ROOT / "clippy.toml").read_text())
        assert clippy["msrv"] == mise["tools"]["rust"]["version"]

    def test_rustfmt_edition_matches_cli_crate_edition(self):
        rustfmt = tomllib.loads((REPO_ROOT / "rustfmt.toml").read_text())
        cli_cargo = tomllib.loads((REPO_ROOT / "cli/Cargo.toml").read_text())
        assert rustfmt["edition"] == cli_cargo["package"]["edition"]
