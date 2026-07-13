"""Pin the binary the skill evals stage.

The eval leaves depend on `build:launcher`, which release-builds into the cargo
target dir and never populates the launcher's bin/ dir — that is the
distribution build's job. Staging from bin/ therefore evaluates whatever binary
a past release left behind, which is how a stale launcher silently graded a
skill eval. These tests hold the resolution to the fresh build.
"""

import platform
from pathlib import Path

import pytest
from invoke import Exit

from tasks.shared.eval.run import host_binary_path
from tasks.shared.paths import BIN_DIR, WORKSPACE_ROOT
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import host_triple


class TestHostTriple:
    @pytest.mark.parametrize(
        ("system", "machine", "expected"),
        [
            ("Darwin", "arm64", "aarch64-apple-darwin"),
            ("Darwin", "aarch64", "aarch64-apple-darwin"),
            ("Darwin", "x86_64", "x86_64-apple-darwin"),
            ("Linux", "aarch64", "aarch64-unknown-linux-musl"),
            ("Linux", "x86_64", "x86_64-unknown-linux-musl"),
            ("Linux", "AMD64", "x86_64-unknown-linux-musl"),
        ],
    )
    def test_resolves_the_single_host_triple(
        self, system: str, machine: str, expected: str
    ) -> None:
        assert host_triple(system, machine) == expected

    def test_an_unsupported_architecture_fails_loudly(self) -> None:
        with pytest.raises(Exit):
            host_triple("Darwin", "riscv64")

    def test_an_unsupported_os_fails_loudly(self) -> None:
        with pytest.raises(Exit):
            host_triple("Plan9", "x86_64")


class TestHostBinaryPath:
    def test_resolves_into_the_cargo_target_dir(self) -> None:
        binary = host_binary_path()
        triple = host_triple(platform.system(), platform.machine())
        assert binary == (
            WORKSPACE_ROOT / "target" / triple / "release" / LAUNCHER_CRATE
        )

    def test_never_resolves_into_the_distribution_bin_dir(self) -> None:
        # The regression: bin/ holds release artifacts, not the build:launcher
        # output the eval depends on.
        assert BIN_DIR not in Path(host_binary_path()).parents
