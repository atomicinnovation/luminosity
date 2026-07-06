from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.shared import rust
from tasks.test import cli, integration, unit

CLI_INSTRUMENTED = "cargo llvm-cov nextest --workspace --summary-only"
CLI_PLAIN = "cargo nextest run --workspace"


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
    """The workspace-wide coverage pass folded into test:unit."""

    def test_instrumented_by_default(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_COVERAGE", raising=False)
        cli.run(ctx)
        assert _command(ctx) == CLI_INSTRUMENTED

    def test_plain_nextest_when_coverage_off(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("LUMINOSITY_COVERAGE", "off")
        cli.run(ctx)
        assert _command(ctx) == CLI_PLAIN

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


class TestUnitTasks:
    def test_runs_the_unit_pytest_suite(self, ctx: MagicMock):
        unit.tasks(ctx)
        assert _command(ctx) == "uv run pytest tests/unit/tasks -v"

    def test_raises_when_the_suite_fails(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            unit.tasks(ctx)


class TestIntegrationTasks:
    def test_runs_the_general_integration_suite(self, ctx: MagicMock):
        integration.tasks(ctx)
        assert _command(ctx) == "uv run pytest tests/integration/tasks -v"

    def test_raises_when_the_suite_fails(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            integration.tasks(ctx)


class TestIntegrationDeny:
    def test_runs_the_deny_suite_directory(self, ctx: MagicMock):
        integration.deny(ctx)
        assert _command(ctx) == "uv run pytest tests/integration/deny -v"

    def test_raises_when_the_regression_fails(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            integration.deny(ctx)


class TestIntegrationPup:
    def test_runs_the_pup_suite_directory(self, ctx: MagicMock):
        integration.pup(ctx)
        assert _command(ctx) == "uv run pytest tests/integration/pup -v"

    def test_raises_when_the_regression_fails(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            integration.pup(ctx)
