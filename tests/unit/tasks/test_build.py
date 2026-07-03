import json
import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

if TYPE_CHECKING:
    from pathlib import Path

from tasks import build
from tasks.shared.paths import BOOTSTRAP, shim_path
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import (
    MACOS_DEPLOYMENT_TARGET,
    TARGETS,
    host_targets,
)

DARWIN_TRIPLES = ("aarch64-apple-darwin", "x86_64-apple-darwin")
MUSL_TRIPLES = ("aarch64-unknown-linux-musl", "x86_64-unknown-linux-musl")
RELEASE_TRIPLES = {triple for triple, _ in TARGETS}
_PLATFORMS = tuple(platform for _, platform in TARGETS)


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="", stderr="")
    return m


class TestHostTargets:
    def test_darwin_selects_the_two_apple_triples(self):
        assert set(host_targets("Darwin")) == set(DARWIN_TRIPLES)

    def test_linux_selects_the_two_musl_triples(self):
        assert set(host_targets("Linux")) == set(MUSL_TRIPLES)

    def test_unsupported_host_raises_rather_than_returning_empty(self):
        with pytest.raises(Exit):
            host_targets("Windows")

    def test_union_of_both_hosts_covers_every_shipped_triple(self):
        union = set(host_targets("Darwin")) | set(host_targets("Linux"))
        assert union == RELEASE_TRIPLES


class TestIsStaticallyLinked:
    def test_file_reporting_static_passes(self):
        assert build.is_statically_linked("ELF 64-bit, statically linked")

    def test_ldd_reporting_not_dynamic_passes(self):
        assert build.is_statically_linked(
            "ELF 64-bit", "not a dynamic executable"
        )

    def test_file_reporting_static_pie_passes(self):
        # The modern x86_64-unknown-linux-musl default links static-pie, which
        # `file` reports as "static-pie linked" — a genuinely static binary
        # whose phrasing omits the literal "statically linked" substring.
        assert build.is_statically_linked(
            "ELF 64-bit LSB pie executable, x86-64, static-pie linked"
        )

    def test_ldd_reporting_statically_linked_passes(self):
        # ldd describes a static-pie binary as "statically linked" rather than
        # "not a dynamic executable"; both mean no dynamic dependencies.
        assert build.is_statically_linked(
            "ELF 64-bit LSB pie executable", "statically linked"
        )

    def test_dynamic_binary_fails(self):
        assert not build.is_statically_linked(
            "ELF 64-bit, dynamically linked", "libc.so => ..."
        )


class TestHasExpectedArch:
    def test_matching_single_arch_passes(self):
        assert build.has_expected_arch("x86_64-apple-darwin", "x86_64")
        assert build.has_expected_arch("aarch64-apple-darwin", "arm64")

    def test_wrong_arch_fails(self):
        assert not build.has_expected_arch("x86_64-apple-darwin", "arm64")

    def test_fat_binary_carrying_both_archs_fails(self):
        assert not build.has_expected_arch(
            "x86_64-apple-darwin", "x86_64 arm64"
        )

    def test_objdump_hyphenated_x86_64_is_recognised(self):
        # llvm-objdump --macho reports the arch as "x86-64" (hyphenated) rather
        # than lipo's "x86_64"; both must be accepted so the darwin-on-Linux
        # cross-verification cell reads the arch correctly.
        assert build.has_expected_arch(
            "x86_64-apple-darwin", "... file format mach-o x86-64"
        )
        assert build.has_expected_arch(
            "aarch64-apple-darwin", "... file format mach-o arm64"
        )


class TestLinksOnlySystemLibraries:
    _OTOOL_SYSTEM = (
        "luminosity-darwin-arm64:\n"
        "\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0)\n"
        "\t/usr/lib/libiconv.2.dylib (compatibility version 7.0.0)\n"
    )
    _OTOOL_NON_SYSTEM = (
        "luminosity-darwin-arm64:\n"
        "\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0)\n"
        "\t/opt/homebrew/lib/libfoo.1.dylib (compatibility version 1.0.0)\n"
    )

    def test_only_system_libraries_passes(self):
        assert build.links_only_system_libraries(self._OTOOL_SYSTEM)

    def test_a_non_system_dylib_fails(self):
        assert not build.links_only_system_libraries(self._OTOOL_NON_SYSTEM)

    def test_system_library_framework_prefix_passes(self):
        assert build.links_only_system_libraries(
            "binary:\n\t/System/Library/Frameworks/CoreFoundation.framework"
            "/CoreFoundation (compatibility version 150.0.0)\n"
        )

    def test_no_dylibs_listed_passes_vacuously(self):
        assert build.links_only_system_libraries("binary:\n")


def _fake_run(command: str, **_kwargs: Any) -> MagicMock:
    if command.startswith("lipo"):
        arch = "x86_64" if "x86_64-apple-darwin" in command else "arm64"
        return MagicMock(exited=0, stdout=arch, stderr="")
    if command.startswith("otool"):
        return MagicMock(
            exited=0,
            stdout="binary:\n\t/usr/lib/libSystem.B.dylib (version 1.0.0)\n",
            stderr="",
        )
    if command.startswith("file"):
        return MagicMock(exited=0, stdout="statically linked", stderr="")
    if command.startswith("ldd"):
        return MagicMock(exited=0, stdout="not a dynamic executable", stderr="")
    return MagicMock(exited=0, stdout="", stderr="")


def _build_commands(ctx: MagicMock) -> list[str]:
    return [
        call.args[0]
        for call in ctx.run.call_args_list
        if call.args[0].startswith("cargo build")
    ]


class TestBuildLauncher:
    def test_builds_each_host_triple_with_bin_flag(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.launcher(ctx)
        commands = _build_commands(ctx)
        assert commands == [
            f"cargo build --release --bin {LAUNCHER_CRATE} --target {triple}"
            for triple in host_targets("Darwin")
        ]

    def test_raises_when_a_release_build_fails(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.return_value = MagicMock(exited=1, stdout="", stderr="")
        with pytest.raises(Exit):
            build.launcher(ctx)

    def test_raises_on_wrong_arch_output(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")

        def wrong_arch(command: str, **_kwargs: Any) -> MagicMock:
            if command.startswith("lipo"):
                return MagicMock(exited=0, stdout="ppc", stderr="")
            return MagicMock(exited=0, stdout="", stderr="")

        ctx.run.side_effect = wrong_arch
        with pytest.raises(Exit):
            build.launcher(ctx)


def _zigbuild_commands(ctx: MagicMock) -> list[str]:
    return [
        call.args[0]
        for call in ctx.run.call_args_list
        if call.args[0].startswith("cargo zigbuild")
    ]


@pytest.fixture
def seeded_checksums(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    checksums = tmp_path / "checksums.json"
    checksums.write_text(
        json.dumps({"version": "0.1.0-pre.0", "binaries": {}}) + "\n"
    )
    monkeypatch.setattr(build, "CHECKSUMS", checksums)
    monkeypatch.setattr(
        build, "binary_path", lambda p: tmp_path / f"luminosity-{p}"
    )
    monkeypatch.setattr(
        build,
        "debug_archive_path",
        lambda p: tmp_path / f"luminosity-{p}.debug.tar.gz",
    )
    monkeypatch.setattr(
        build, "compute_sha256", lambda path: f"{'a' * 63}{len(path.name) % 10}"
    )
    return checksums


class TestBuildRelease:
    def test_cross_builds_every_shipped_triple_via_zigbuild(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.release(ctx)
        launcher_builds = [
            command
            for command in _zigbuild_commands(ctx)
            if f"--bin {LAUNCHER_CRATE} --target" in command
        ]
        assert launcher_builds == [
            f"cargo zigbuild --release --bin {LAUNCHER_CRATE} --target {triple}"
            for triple, _ in TARGETS
        ]

    def test_darwin_builds_set_the_macos_deployment_target(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.release(ctx)
        for call in ctx.run.call_args_list:
            command = call.args[0]
            if not command.startswith("cargo zigbuild"):
                continue
            env = call.kwargs.get("env") or {}
            if "apple-darwin" in command:
                assert env.get("MACOSX_DEPLOYMENT_TARGET") == (
                    MACOS_DEPLOYMENT_TARGET
                )
            else:
                assert "MACOSX_DEPLOYMENT_TARGET" not in env

    def test_cross_builds_and_stages_the_verify_shim_per_triple(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.release(ctx)
        shim_builds = [
            command
            for command in _zigbuild_commands(ctx)
            if "--bin luminosity-verify --target" in command
        ]
        assert shim_builds == [
            f"cargo zigbuild --release --bin luminosity-verify "
            f"--target {triple}"
            for triple, _ in TARGETS
        ]

    def test_stages_binaries_and_debug_archives_for_each_platform(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.release(ctx)
        all_commands = [c.args[0] for c in ctx.run.call_args_list]
        for platform in _PLATFORMS:
            assert any(
                cmd.startswith("cp ")
                and f"luminosity-{platform}" in cmd
                and ".debug.tar.gz" not in cmd
                for cmd in all_commands
            ), f"no binary staged for {platform}"
            assert any(
                cmd.startswith("tar ")
                and f"luminosity-{platform}.debug.tar.gz" in cmd
                for cmd in all_commands
            ), f"no debug archive for {platform}"

    def test_writes_prefixed_sha256_for_every_platform(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.release(ctx)
        data = json.loads(seeded_checksums.read_text())
        assert set(data["binaries"]) == set(_PLATFORMS)
        for digest in data["binaries"].values():
            assert digest.startswith("sha256:")
        assert data["version"] == "0.1.0-pre.0"

    def test_raises_when_a_cross_build_fails(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        seeded_checksums: Path,
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.return_value = MagicMock(exited=1, stdout="", stderr="")
        with pytest.raises(Exit):
            build.release(ctx)


class TestHostAwareVerification:
    """`_verify_output` branches on (build-host, target-family)."""

    def test_linux_host_verifies_darwin_target_with_objdump(
        self, ctx: MagicMock
    ):
        def run(command: str, **_kwargs: Any) -> MagicMock:
            if "llvm-objdump" in command and "--dylibs-used" in command:
                return MagicMock(
                    exited=0,
                    stdout="binary:\n\t/usr/lib/libSystem.B.dylib (1.0.0)\n",
                    stderr="",
                )
            if "llvm-objdump" in command:
                return MagicMock(
                    exited=0, stdout="file format mach-o arm64", stderr=""
                )
            return MagicMock(exited=0, stdout="", stderr="")

        ctx.run.side_effect = run
        build._verify_output(ctx, "aarch64-apple-darwin", "Linux")
        issued = [c.args[0] for c in ctx.run.call_args_list]
        assert any("llvm-objdump --macho" in c for c in issued)
        assert not any(c.startswith("lipo") for c in issued)

    def test_linux_host_rejects_non_system_dylib_on_darwin_target(
        self, ctx: MagicMock
    ):
        def run(command: str, **_kwargs: Any) -> MagicMock:
            if "--dylibs-used" in command:
                return MagicMock(
                    exited=0,
                    stdout="binary:\n\t/opt/homebrew/lib/libfoo.dylib (1.0)\n",
                    stderr="",
                )
            if "llvm-objdump" in command:
                return MagicMock(
                    exited=0, stdout="file format mach-o arm64", stderr=""
                )
            return MagicMock(exited=0, stdout="", stderr="")

        ctx.run.side_effect = run
        with pytest.raises(Exit):
            build._verify_output(ctx, "aarch64-apple-darwin", "Linux")

    def test_darwin_host_verifies_musl_target_with_file(self, ctx: MagicMock):
        def run(command: str, **_kwargs: Any) -> MagicMock:
            if command.startswith("file"):
                return MagicMock(
                    exited=0, stdout="ELF 64-bit, statically linked", stderr=""
                )
            return MagicMock(exited=0, stdout="", stderr="")

        ctx.run.side_effect = run
        build._verify_output(ctx, "x86_64-unknown-linux-musl", "Darwin")
        issued = [c.args[0] for c in ctx.run.call_args_list]
        assert any(c.startswith("file") for c in issued)
        assert not any(c.startswith("ldd") for c in issued)

    def test_darwin_host_verifies_darwin_target_with_lipo_and_otool(
        self, ctx: MagicMock
    ):
        ctx.run.side_effect = _fake_run
        build._verify_output(ctx, "aarch64-apple-darwin", "Darwin")
        issued = [c.args[0] for c in ctx.run.call_args_list]
        assert any(c.startswith("lipo") for c in issued)
        assert any(c.startswith("otool") for c in issued)


class TestPackagedRootOfTrustArtifacts:
    """The committed plugin-package artifacts the bootstrap depends on.

    The launcher is fetched on demand, but the entry point, the per-triple
    verify shims (the root of trust), and the public key ship committed over
    the marketplace channel — a guard that none is dropped from the package.
    """

    def test_a_verify_shim_ships_for_every_platform(self):
        for _, platform in TARGETS:
            assert shim_path(platform).exists(), (
                f"missing packaged verify shim for {platform}"
            )

    def test_the_bootstrap_entry_point_is_executable(self):
        assert BOOTSTRAP.exists()
        assert os.access(BOOTSTRAP, os.X_OK)
