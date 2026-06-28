from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks import pup
from tasks.shared import rust
from tasks.shared.rust import PUP_NIGHTLY


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestPupCheck:
    def test_runs_pup_on_the_pinned_nightly(self, ctx: MagicMock):
        pup.check(ctx)
        assert _command(ctx) == f"cargo +{PUP_NIGHTLY} pup"

    def test_deny_mode_raises_on_findings(
        self, ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_PUP_MODE", raising=False)
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            pup.check(ctx)

    def test_warn_mode_logs_and_returns_cleanly(
        self,
        ctx: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ):
        monkeypatch.setenv("LUMINOSITY_PUP_MODE", "warn")
        ctx.run.return_value = MagicMock(exited=1)
        pup.check(ctx)
        assert "WARNING" in capsys.readouterr().out


class TestPupMode:
    def test_defaults_to_deny_when_env_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.delenv("LUMINOSITY_PUP_MODE", raising=False)
        assert rust.pup_mode() == "deny"

    @pytest.mark.parametrize("value", ["warn", "Warn", " warn ", "WARN"])
    def test_normalises_warn(self, monkeypatch: pytest.MonkeyPatch, value: str):
        monkeypatch.setenv("LUMINOSITY_PUP_MODE", value)
        assert rust.pup_mode() == "warn"

    def test_unrecognised_value_fails_closed_with_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ):
        monkeypatch.setenv("LUMINOSITY_PUP_MODE", "lenient")
        assert rust.pup_mode() == "deny"
        assert "WARNING" in capsys.readouterr().out
