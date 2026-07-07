"""Assert the mise task wiring by parsing mise.toml and the Rust configs."""

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import TARGETS

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = REPO_ROOT / "cli"

Mise = dict[str, Any]


@pytest.fixture
def mise() -> Mise:
    return tomllib.loads((REPO_ROOT / "mise.toml").read_text())


def _tasks(mise: Mise) -> Mise:
    return mise["tasks"]


def _depends(mise: Mise, name: str) -> list[str]:
    return _tasks(mise)[name].get("depends", [])


class TestCliCheckWiring:
    """`cli:check` is the workspace-wide roll-up that feeds `check`."""

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


class TestLauncherCheckWiring:
    """`launcher:check` is a single-crate (`-p luminosity`) ad-hoc roll-up."""

    def test_launcher_check_folds_format_and_lint_only(self, mise: Mise):
        assert _depends(mise, "launcher:check") == [
            "format:launcher:check",
            "lint:launcher:check",
        ]

    def test_launcher_check_is_excluded_from_check(self, mise: Mise):
        # The aggregate covers the launcher crate via the workspace-wide
        # cli:check pass; a per-crate roll-up in `check` would only pay a second
        # tool startup for no extra coverage.
        assert "launcher:check" not in _depends(mise, "check")

    @pytest.mark.parametrize(
        "leaf",
        [
            "format:launcher:check",
            "format:launcher:fix",
            "lint:launcher:check",
            "lint:launcher:fix",
        ],
    )
    def test_launcher_leaves_provision_rustfmt_and_clippy(
        self, mise: Mise, leaf: str
    ):
        assert "deps:install:rust-components" in _depends(mise, leaf)


class TestKernelCheckWiring:
    """`kernel:check` is a single-crate (`-p kernel`) ad-hoc roll-up."""

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

    def test_test_unit_kernel_is_not_in_test_unit(self, mise: Mise):
        # The workspace-wide test:unit:cli pass covers the kernel crate; the
        # per-crate task is ad-hoc convenience, not part of the aggregate.
        assert "test:unit:kernel" not in _depends(mise, "test:unit")

    def test_test_unit_kernel_is_not_in_kernel_check(self, mise: Mise):
        assert "test:unit:kernel" not in _depends(mise, "kernel:check")

    def test_test_unit_kernel_provisions_llvm_tools(self, mise: Mise):
        assert "deps:install:rust-components" in _depends(
            mise, "test:unit:kernel"
        )


class TestBuildLauncherWiring:
    def test_build_launcher_is_in_default(self, mise: Mise):
        assert "build:launcher" in _depends(mise, "default")

    def test_build_launcher_is_absent_from_check(self, mise: Mise):
        assert "build:launcher" not in _depends(mise, "check")

    def test_build_launcher_is_absent_from_cli_check(self, mise: Mise):
        assert "build:launcher" not in _depends(mise, "cli:check")

    def test_build_launcher_provisions_cross_targets(self, mise: Mise):
        assert "deps:install:rust-targets" in _depends(mise, "build:launcher")


class TestTestUnitCliWiring:
    """`test:unit:cli` is the workspace-wide coverage pass in `test:unit`."""

    def test_test_unit_cli_is_folded_into_test_unit(self, mise: Mise):
        assert "test:unit:cli" in _depends(mise, "test:unit")

    def test_test_unit_cli_is_not_in_cli_check(self, mise: Mise):
        assert "test:unit:cli" not in _depends(mise, "cli:check")

    def test_test_unit_cli_provisions_llvm_tools(self, mise: Mise):
        # Provision llvm-tools-preview up front so the coverage pass does not
        # trigger cargo-llvm-cov's implicit `rustup component add` at runtime.
        assert "deps:install:rust-components" in _depends(mise, "test:unit:cli")

    def test_per_crate_test_tasks_are_ad_hoc_not_aggregated(self, mise: Mise):
        # The single --workspace pass replaces per-crate concurrency, so the
        # single-crate test tasks stay out of the aggregate.
        assert "test:unit:launcher" not in _depends(mise, "test:unit")
        assert "test:unit:kernel" not in _depends(mise, "test:unit")

    def test_no_coverage_task_exists(self, mise: Mise):
        names = set(_tasks(mise))
        assert "coverage:check" not in names
        assert "coverage:cli:check" not in names

    def test_no_coverage_edge_on_default(self, mise: Mise):
        assert "coverage:check" not in _depends(mise, "default")


class TestPytestSuiteWiring:
    """The pytest suites run via invoke tasks, not pytest directly."""

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

    def test_integration_scripts_wraps_an_invoke_task(self, mise: Mise):
        assert (
            _tasks(mise)["test:integration:scripts"]["run"]
            == "invoke test.integration.scripts"
        )

    def test_integration_roll_up_includes_tasks_deny_and_scripts(
        self, mise: Mise
    ):
        # The deny ban regression and the shell-wrapper suite ride the general
        # test-integration job; the nightly-only pup suite does not (asserted in
        # TestPupWiring).
        assert _depends(mise, "test:integration") == [
            "test:integration:tasks",
            "test:integration:deny",
            "test:integration:scripts",
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


class TestEvalTierWiring:
    """The eval tier is declared but excluded from every CI aggregate."""

    @pytest.mark.parametrize(
        "name", ["eval", "eval:skills", "eval:skills:configure"]
    )
    def test_eval_task_is_declared(self, mise: Mise, name: str):
        assert name in _tasks(mise)

    @pytest.mark.parametrize(
        "name", ["eval", "eval:skills", "eval:skills:configure"]
    )
    def test_eval_task_is_absent_from_check(self, mise: Mise, name: str):
        assert name not in _depends(mise, "check")

    @pytest.mark.parametrize(
        "name", ["eval", "eval:skills", "eval:skills:configure"]
    )
    def test_eval_task_is_absent_from_default(self, mise: Mise, name: str):
        assert name not in _depends(mise, "default")

    def test_eval_roll_ups_are_pure_depends(self, mise: Mise):
        # The intermediate tiers mirror the test:unit roll-up shape: no `run`,
        # only `depends`, so a second skill slots under eval:skills cleanly.
        assert "run" not in _tasks(mise)["eval"]
        assert "run" not in _tasks(mise)["eval:skills"]
        assert _depends(mise, "eval") == ["eval:skills"]
        assert _depends(mise, "eval:skills") == ["eval:skills:configure"]

    def test_configure_leaf_wraps_the_invoke_task(self, mise: Mise):
        leaf = _tasks(mise)["eval:skills:configure"]
        assert leaf["run"] == "invoke eval.skills.configure"
        assert "deps:install:python" in leaf.get("depends", [])

    def test_configure_leaf_provisions_the_release_binary(self, mise: Mise):
        # The Docker sandbox COPYs the cross-built linux-musl launcher that
        # build:release stages, so the leaf must provision it.
        assert "build:release" in _depends(mise, "eval:skills:configure")


class TestEvalUnitSuiteWiring:
    """The eval-logic unit suite runs in the default sweep; the live tier does
    not.
    """

    def test_test_unit_evals_wraps_an_invoke_task(self, mise: Mise):
        assert _tasks(mise)["test:unit:evals"]["run"] == "invoke test.evals.run"

    def test_test_unit_evals_is_folded_into_test_unit(self, mise: Mise):
        # Mirror of the live-tier exclusion: the eval unit suite MUST run in CI
        # so the scorer/dataset/coherence tests cannot silently fall out.
        assert "test:unit:evals" in _depends(mise, "test:unit")

    def test_test_unit_evals_provisions_python(self, mise: Mise):
        assert "deps:install:python" in _depends(mise, "test:unit:evals")


class TestFinalEnumeratedArrays:
    """Pin the complete top-level task arrays."""

    def test_check_array(self, mise: Mise):
        assert _depends(mise, "check") == [
            "build-system:check",
            "scripts:check",
            "cli:check",
            "version:check",
            "deny:check",
            "pup:check",
        ]

    def test_default_array(self, mise: Mise):
        assert _depends(mise, "default") == [
            "format:fix",
            "lint:check",
            "types:check",
            "test",
            "build:launcher",
            "deny:check",
            "pup:check",
        ]

    def test_test_unit_array(self, mise: Mise):
        assert _depends(mise, "test:unit") == [
            "test:unit:tasks",
            "test:unit:cli",
            "test:unit:evals",
        ]


class TestVersionCheckWiring:
    def test_version_check_is_in_check(self, mise: Mise):
        assert "version:check" in _depends(mise, "check")

    def test_version_check_wraps_the_invoke_task(self, mise: Mise):
        assert _tasks(mise)["version:check"]["run"] == "invoke version.check"


class TestZigbuildProvisioning:
    """The four-triple release build provisions its cross-compile toolchain."""

    def test_build_release_provisions_zigbuild(self, mise: Mise):
        assert "deps:install:zigbuild" in _depends(mise, "build:release")

    def test_release_prepare_tasks_provision_zigbuild(self, mise: Mise):
        # The prepare halves run the cross-build, so they must provision zig +
        # cargo-zigbuild (which itself adds the rustup targets), not merely the
        # rustup targets the host-native build needed.
        assert "deps:install:zigbuild" in _depends(mise, "prerelease:prepare")
        assert "deps:install:zigbuild" in _depends(mise, "release:prepare")


class TestZigbuildPins:
    """zig + cargo-zigbuild are exact-pinned and coherent with uv.lock."""

    _PINNED = ("ziglang", "cargo-zigbuild")

    def _build_group(self) -> list[str]:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        return pyproject["dependency-groups"]["build"]

    def _locked_versions(self) -> dict[str, str]:
        lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
        return {
            p["name"]: p["version"] for p in lock["package"] if "version" in p
        }

    @pytest.mark.parametrize("name", _PINNED)
    def test_pinned_exactly(self, name: str):
        constraints = [
            dep for dep in self._build_group() if dep.startswith(name)
        ]
        assert constraints == [f"{name}=={self._locked_versions()[name]}"]


class TestToolchainCoherence:
    """The clippy msrv and rustfmt edition mirror the mise rust pin by hand."""

    def test_clippy_msrv_matches_mise_rust_pin(self, mise: Mise):
        clippy = tomllib.loads((WORKSPACE_ROOT / "clippy.toml").read_text())
        assert clippy["msrv"] == mise["tools"]["rust"]["version"]

    def test_launcher_rust_version_matches_mise_rust_pin(self, mise: Mise):
        # rust-version drives MSRV-aware resolution (resolver = "3"); it is a
        # further hand-synced mirror of the mise rust pin. A drift would resolve
        # the dep graph against a different floor than CI builds on.
        launcher_cargo = tomllib.loads(
            (WORKSPACE_ROOT / "launcher" / "Cargo.toml").read_text()
        )
        assert (
            launcher_cargo["package"]["rust-version"]
            == mise["tools"]["rust"]["version"]
        )

    def test_workspace_uses_msrv_aware_resolver(self):
        # resolver = "3" is what makes rust-version actually gate resolution;
        # resolver = "2" would silently ignore it.
        workspace = tomllib.loads((WORKSPACE_ROOT / "Cargo.toml").read_text())
        assert workspace["workspace"]["resolver"] == "3"

    def test_rustfmt_edition_matches_launcher_crate_edition(self):
        rustfmt = tomllib.loads((WORKSPACE_ROOT / "rustfmt.toml").read_text())
        launcher_cargo = tomllib.loads(
            (WORKSPACE_ROOT / "launcher" / "Cargo.toml").read_text()
        )
        assert rustfmt["edition"] == launcher_cargo["package"]["edition"]

    def test_launcher_crate_constant_matches_cargo_package_name(self):
        launcher_cargo = tomllib.loads(
            (WORKSPACE_ROOT / "launcher" / "Cargo.toml").read_text()
        )
        assert launcher_cargo["package"]["name"] == LAUNCHER_CRATE


class TestPlatformAliasCoherence:
    """The triple→alias map is single-sourced across Python, launcher, bash."""

    _RESOLVE_RS = (
        WORKSPACE_ROOT
        / "launcher"
        / "src"
        / "launch"
        / "outbound"
        / "resolve"
        / "mod.rs"
    )

    def _launcher_alias_map(self) -> dict[tuple[str, str], str]:
        pattern = re.compile(
            r'#\[cfg\(all\(target_arch = "([^"]+)", target_os = "([^"]+)"\)\)\]'
            r'\s*pub const HOST_PLATFORM: &str = "([^"]+)";'
        )
        source = self._RESOLVE_RS.read_text()
        return {
            (arch, os): alias for arch, os, alias in pattern.findall(source)
        }

    def _expected_alias_map(self) -> dict[tuple[str, str], str]:
        arch_of = {"aarch64": "aarch64", "x86_64": "x86_64"}
        os_of = {"apple-darwin": "macos", "unknown-linux": "linux"}
        expected: dict[tuple[str, str], str] = {}
        for triple, alias in TARGETS:
            arch = next(a for a in arch_of if triple.startswith(a))
            os_marker = next(marker for marker in os_of if marker in triple)
            expected[(arch, os_of[os_marker])] = alias
        return expected

    def test_launcher_host_platform_map_matches_targets(self):
        assert self._launcher_alias_map() == self._expected_alias_map()
