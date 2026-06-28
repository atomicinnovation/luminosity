from typing import Any
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks import build
from tasks.shared.rust import CLI_CRATE
from tasks.shared.targets import TARGETS, host_targets

DARWIN_TRIPLES = ("aarch64-apple-darwin", "x86_64-apple-darwin")
MUSL_TRIPLES = ("aarch64-unknown-linux-musl", "x86_64-unknown-linux-musl")
RELEASE_TRIPLES = {triple for triple, _ in TARGETS}


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


def _fake_run(command: str, **_kwargs: Any) -> MagicMock:
    if command.startswith("lipo"):
        arch = "x86_64" if "x86_64-apple-darwin" in command else "arm64"
        return MagicMock(exited=0, stdout=arch, stderr="")
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


class TestBuildCli:
    def test_builds_each_host_triple_with_bin_flag(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.side_effect = _fake_run
        build.cli(ctx)
        commands = _build_commands(ctx)
        assert commands == [
            f"cargo build --release --bin {CLI_CRATE} --target {triple}"
            for triple in host_targets("Darwin")
        ]

    def test_raises_when_a_release_build_fails(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
        ctx.run.return_value = MagicMock(exited=1, stdout="", stderr="")
        with pytest.raises(Exit):
            build.cli(ctx)

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
            build.cli(ctx)
