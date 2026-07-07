from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.format import kernel as fmt_kernel
from tasks.lint import kernel as lint_kernel
from tasks.shared import rust
from tasks.test import kernel as test_kernel

INSTRUMENTED = "cargo llvm-cov nextest -p kernel --summary-only"
PLAIN = "cargo nextest run -p kernel"


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestFormatKernelCheck:
    def test_runs_cargo_fmt_kernel_check(self, ctx: MagicMock):
        fmt_kernel.check(ctx)
        assert _command(ctx) == "cargo fmt -p kernel --check"

    def test_raises_on_drift(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            fmt_kernel.check(ctx)


class TestFormatKernelFix:
    def test_runs_cargo_fmt_kernel(self, ctx: MagicMock):
        fmt_kernel.fix(ctx)
        assert _command(ctx) == "cargo fmt -p kernel"


class TestLintKernelCheck:
    def test_runs_clippy_with_deny_warnings(self, ctx: MagicMock):
        lint_kernel.check(ctx)
        assert _command(ctx) == (
            "cargo clippy -p kernel --all-targets --all-features -- -D warnings"
        )

    def test_raises_on_findings(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            lint_kernel.check(ctx)


class TestLintKernelFix:
    def test_runs_clippy_fix_rewriting_dirty_tree(self, ctx: MagicMock):
        lint_kernel.fix(ctx)
        assert _command(ctx) == (
            "cargo clippy -p kernel --all-targets --all-features "
            "--fix --allow-dirty --allow-staged"
        )

    def test_warns_when_autofix_fails(
        self, ctx: MagicMock, capsys: pytest.CaptureFixture[str]
    ):
        ctx.run.return_value = MagicMock(exited=1)
        lint_kernel.fix(ctx)
        assert "WARNING" in capsys.readouterr().out


class TestTestUnitKernel:
    def test_instrumented_by_default(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        test_kernel.run(ctx)
        assert _command(ctx) == INSTRUMENTED

    def test_plain_nextest_when_coverage_off(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("LUMINOSITY_COVERAGE", "off")
        test_kernel.run(ctx)
        assert _command(ctx) == PLAIN

    def test_instrumented_command_carries_no_coverage_threshold(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        test_kernel.run(ctx)
        assert "--fail-under" not in _command(ctx)

    def test_raises_when_inner_tests_fail_on_instrumented_path(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            test_kernel.run(ctx)

    def test_kernel_crate_constant_matches_manifest(self):
        assert rust.KERNEL_CRATE == "kernel"

    def test_runs_in_isolated_target_dir(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        # Isolated CARGO_TARGET_DIR so the kernel coverage pass cannot collide
        # with the concurrent cli coverage pass on llvm-cov's profraw dir.
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        test_kernel.run(ctx)
        env = ctx.run.call_args.kwargs["env"]
        assert env["CARGO_TARGET_DIR"] == "target/llvm-cov-kernel"
