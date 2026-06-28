from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.shared import rust
from tasks.test import cli

INSTRUMENTED = "cargo llvm-cov nextest -p luminosity --summary-only"
PLAIN = "cargo nextest run -p luminosity"


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestCoverageEnabled:
    def test_defaults_on_when_env_absent(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        assert rust.coverage_enabled() is True

    @pytest.mark.parametrize(
        "value", ["off", "false", "0", "no", "OFF", " no "]
    )
    def test_falsey_values_disable(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ):
        monkeypatch.setenv("LUMINOSITY_COVERAGE", value)
        assert rust.coverage_enabled() is False


class TestTestUnitCli:
    def test_instrumented_by_default(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        cli.run(ctx)
        assert _command(ctx) == INSTRUMENTED

    def test_plain_nextest_when_coverage_off(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("LUMINOSITY_COVERAGE", "off")
        cli.run(ctx)
        assert _command(ctx) == PLAIN

    def test_instrumented_command_carries_no_coverage_threshold(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        cli.run(ctx)
        assert "--fail-under" not in _command(ctx)

    def test_raises_when_inner_tests_fail_on_instrumented_path(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            cli.run(ctx)
