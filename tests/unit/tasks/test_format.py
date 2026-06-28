from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.format import cli as fmt_cli
from tasks.format import scripts as fmt

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def ctx():
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


_STYLE_FLAGS_OWNED_BY_EDITORCONFIG = (" -i ", " -ci", " -bn", " -sr", " -kp")


class TestFormatCheck:
    def test_runs_shfmt_diff_with_no_style_flags(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(fmt, "shell_sources", return_value=["a.sh", "b.sh"])
        fmt.check(ctx)
        cmd = _command(ctx)
        assert cmd.startswith("shfmt -d ")
        assert "a.sh" in cmd
        assert "b.sh" in cmd
        for flag in _STYLE_FLAGS_OWNED_BY_EDITORCONFIG:
            assert flag not in cmd

    def test_raises_on_drift(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(fmt, "shell_sources", return_value=["a.sh"])
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            fmt.check(ctx)

    def test_raises_when_source_discovery_is_empty(
        self, ctx: MagicMock, mocker: MockerFixture
    ):
        mocker.patch.object(fmt, "shell_sources", return_value=[])
        with pytest.raises(Exit):
            fmt.check(ctx)
        ctx.run.assert_not_called()


class TestFormatFix:
    def test_runs_shfmt_list_write(self, ctx: MagicMock, mocker: MockerFixture):
        mocker.patch.object(fmt, "shell_sources", return_value=["a.sh"])
        fmt.fix(ctx)
        assert _command(ctx).startswith("shfmt -l -w ")


class TestFormatCliCheck:
    def test_runs_cargo_fmt_all_check(self, ctx: MagicMock):
        fmt_cli.check(ctx)
        assert _command(ctx) == "cargo fmt --all --check"

    def test_raises_on_drift(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            fmt_cli.check(ctx)


class TestFormatCliFix:
    def test_runs_cargo_fmt_all(self, ctx: MagicMock):
        fmt_cli.fix(ctx)
        assert _command(ctx) == "cargo fmt --all"
