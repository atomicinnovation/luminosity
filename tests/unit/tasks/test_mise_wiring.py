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

    @pytest.mark.parametrize(
        "leaf",
        [
            "format:cli:check",
            "format:cli:fix",
            "lint:cli:check",
            "lint:cli:fix",
        ],
    )
    def test_cli_leaves_provision_rustfmt_and_clippy(
        self, mise: Mise, leaf: str
    ):
        # mise's [tools] rust `components` is silently skipped for an
        # already-present toolchain (a cached CI stable), so each cli leaf must
        # self-provision rustfmt/clippy — the same convention as pup:check <->
        # deps:install:pup. Attached to the leaves (not the cli:check roll-up)
        # so format:fix / lint:fix provision them too.
        assert "deps:install:rust-components" in _depends(mise, leaf)


class TestKernelCheckWiring:
    def test_kernel_check_folds_format_and_lint_only(self, mise: Mise):
        assert _depends(mise, "kernel:check") == [
            "format:kernel:check",
            "lint:kernel:check",
        ]

    def test_kernel_check_is_deliberately_excluded_from_check(self, mise: Mise):
        assert "kernel:check" not in _depends(mise, "check")

    @pytest.mark.parametrize(
        "leaf",
        [
            "format:kernel:check",
            "format:kernel:fix",
            "lint:kernel:check",
            "lint:kernel:fix",
        ],
    )
    def test_kernel_leaves_provision_rustfmt_and_clippy(
        self, mise: Mise, leaf: str
    ):
        assert "deps:install:rust-components" in _depends(mise, leaf)

    def test_test_unit_kernel_wraps_an_invoke_task(self, mise: Mise):
        assert (
            _tasks(mise)["test:unit:kernel"]["run"] == "invoke test.kernel.run"
        )

    def test_test_unit_kernel_is_folded_into_test_unit(self, mise: Mise):
        assert "test:unit:kernel" in _depends(mise, "test:unit")

    def test_test_unit_kernel_is_not_in_kernel_check(self, mise: Mise):
        assert "test:unit:kernel" not in _depends(mise, "kernel:check")

    def test_test_unit_kernel_provisions_llvm_tools(self, mise: Mise):
        # Provision llvm-tools-preview up front so parallel cli/kernel llvm-cov
        # runs don't race on `rustup component add`.
        assert "deps:install:rust-components" in _depends(
            mise, "test:unit:kernel"
        )


class TestBuildCliWiring:
    def test_build_cli_is_in_default(self, mise: Mise):
        assert "build:cli" in _depends(mise, "default")

    def test_build_cli_is_absent_from_check(self, mise: Mise):
        assert "build:cli" not in _depends(mise, "check")

    def test_build_cli_is_absent_from_cli_check(self, mise: Mise):
        assert "build:cli" not in _depends(mise, "cli:check")

    def test_build_cli_provisions_cross_targets(self, mise: Mise):
        assert "deps:install:rust-targets" in _depends(mise, "build:cli")


class TestTestUnitCliWiring:
    def test_test_unit_cli_is_folded_into_test_unit(self, mise: Mise):
        assert "test:unit:cli" in _depends(mise, "test:unit")

    def test_test_unit_cli_is_not_in_cli_check(self, mise: Mise):
        assert "test:unit:cli" not in _depends(mise, "cli:check")

    def test_test_unit_cli_provisions_llvm_tools(self, mise: Mise):
        # Provision llvm-tools-preview up front so parallel cli/kernel llvm-cov
        # runs don't race on `rustup component add`.
        assert "deps:install:rust-components" in _depends(mise, "test:unit:cli")

    def test_no_coverage_task_exists(self, mise: Mise):
        names = set(_tasks(mise))
        assert "coverage:check" not in names
        assert "coverage:cli:check" not in names

    def test_no_coverage_edge_on_default(self, mise: Mise):
        assert "coverage:check" not in _depends(mise, "default")


class TestPytestSuiteWiring:
    """The pytest suites run via invoke tasks, not pytest invoked directly.

    Suites are separated by directory (tests/integration/{tasks,deny,pup}),
    not pytest markers. The actual pytest command strings are asserted in
    test_test.py.
    """

    def test_unit_tasks_wraps_an_invoke_task(self, mise: Mise):
        assert (
            _tasks(mise)["test:unit:tasks"]["run"] == "invoke test.unit.tasks"
        )

    def test_integration_tasks_wraps_an_invoke_task(self, mise: Mise):
        assert (
            _tasks(mise)["test:integration:tasks"]["run"]
            == "invoke test.integration.tasks"
        )

    def test_integration_deny_wraps_an_invoke_task(self, mise: Mise):
        assert (
            _tasks(mise)["test:integration:deny"]["run"]
            == "invoke test.integration.deny"
        )

    def test_integration_roll_up_includes_tasks_and_deny(self, mise: Mise):
        # The deny ban regression rides the general test-integration job; the
        # nightly-only pup suite does not (asserted in TestPupWiring).
        assert _depends(mise, "test:integration") == [
            "test:integration:tasks",
            "test:integration:deny",
        ]


class TestDenyWiring:
    def test_deny_check_is_in_check(self, mise: Mise):
        assert "deny:check" in _depends(mise, "check")

    def test_deny_check_is_in_default(self, mise: Mise):
        assert "deny:check" in _depends(mise, "default")


class TestPupWiring:
    def test_pup_check_is_in_check(self, mise: Mise):
        assert "pup:check" in _depends(mise, "check")

    def test_pup_check_is_in_default(self, mise: Mise):
        assert "pup:check" in _depends(mise, "default")

    def test_pup_check_depends_on_its_provisioning_task(self, mise: Mise):
        # Mirrors the Python-check <-> deps:install:python convention: a check
        # provisions the non-[tools] it needs (here the rustup-managed nightly +
        # cargo-pup), so a fresh checkout's pup:check self-provisions.
        assert "deps:install:pup" in _depends(mise, "pup:check")

    def test_integration_pup_task_wraps_an_invoke_task(self, mise: Mise):
        # The check-architecture job runs the regression via this mise task
        # (not pytest directly); it self-provisions the nightly lane.
        pup_task = _tasks(mise)["test:integration:pup"]
        assert pup_task["run"] == "invoke test.integration.pup"
        assert "deps:install:pup" in pup_task.get("depends", [])

    def test_integration_pup_is_not_in_the_test_roll_up(self, mise: Mise):
        # It needs the nightly, so it must not ride the general aggregate.
        assert "test:integration:pup" not in _depends(mise, "test:integration")


class TestFinalEnumeratedArrays:
    """Pin the complete top-level arrays the plan enumerates.

    Together with test_workflows.py these are the automated backstop for the
    whole mise + CI wiring.
    """

    def test_check_array(self, mise: Mise):
        assert _depends(mise, "check") == [
            "build-system:check",
            "scripts:check",
            "cli:check",
            "deny:check",
            "pup:check",
        ]

    def test_default_array(self, mise: Mise):
        assert _depends(mise, "default") == [
            "format:fix",
            "lint:check",
            "types:check",
            "test",
            "build:cli",
            "deny:check",
            "pup:check",
        ]

    def test_test_unit_array(self, mise: Mise):
        assert _depends(mise, "test:unit") == [
            "test:unit:tasks",
            "test:unit:cli",
            "test:unit:kernel",
        ]


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
