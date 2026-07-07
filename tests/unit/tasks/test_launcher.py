from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.format import launcher as fmt_launcher
from tasks.lint import launcher as lint_launcher
from tasks.shared import rust
from tasks.test import launcher as test_launcher

INSTRUMENTED = "cargo llvm-cov nextest -p luminosity --summary-only"
PLAIN = "cargo nextest run -p luminosity"


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestFormatLauncherCheck:
    def test_runs_cargo_fmt_launcher_check(self, ctx: MagicMock):
        fmt_launcher.check(ctx)
        assert _command(ctx) == "cargo fmt -p luminosity --check"

    def test_raises_on_drift(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            fmt_launcher.check(ctx)


class TestFormatLauncherFix:
    def test_runs_cargo_fmt_launcher(self, ctx: MagicMock):
        fmt_launcher.fix(ctx)
        assert _command(ctx) == "cargo fmt -p luminosity"


class TestLintLauncherCheck:
    def test_runs_clippy_with_deny_warnings(self, ctx: MagicMock):
        lint_launcher.check(ctx)
        assert _command(ctx) == (
            "cargo clippy -p luminosity --all-targets --all-features "
            "-- -D warnings"
        )

    def test_raises_on_findings(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            lint_launcher.check(ctx)


class TestLintLauncherFix:
    def test_runs_clippy_fix_rewriting_dirty_tree(self, ctx: MagicMock):
        lint_launcher.fix(ctx)
        assert _command(ctx) == (
            "cargo clippy -p luminosity --all-targets --all-features "
            "--fix --allow-dirty --allow-staged"
        )

    def test_warns_when_autofix_fails(
        self, ctx: MagicMock, capsys: pytest.CaptureFixture[str]
    ):
        ctx.run.return_value = MagicMock(exited=1)
        lint_launcher.fix(ctx)
        assert "WARNING" in capsys.readouterr().out


class TestTestUnitLauncher:
    def test_instrumented_by_default(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        test_launcher.run(ctx)
        assert _command(ctx) == INSTRUMENTED

    def test_plain_nextest_when_coverage_off(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("LUMINOSITY_COVERAGE", "off")
        test_launcher.run(ctx)
        assert _command(ctx) == PLAIN

    def test_instrumented_command_carries_no_coverage_threshold(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        test_launcher.run(ctx)
        assert "--fail-under" not in _command(ctx)

    def test_raises_when_inner_tests_fail_on_instrumented_path(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            test_launcher.run(ctx)

    def test_launcher_crate_constant_matches_manifest(self):
        assert rust.LAUNCHER_CRATE == "luminosity"
