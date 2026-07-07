from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks.eval import skills


@pytest.fixture
def ctx() -> MagicMock:
    return MagicMock(spec=Context)


def test_gates_closed_below_floor(
    ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LUMINOSITY_EVAL_LIVE", "on")
    monkeypatch.setattr(skills, "_run_configure_eval", lambda _c: 0.66)
    with pytest.raises(Exit):
        skills.configure(ctx)


def test_passes_open_at_or_above_floor(
    ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LUMINOSITY_EVAL_LIVE", "on")
    monkeypatch.setattr(skills, "_run_configure_eval", lambda _c: 1.0)
    skills.configure(ctx)


def test_skips_when_live_run_disabled(
    ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    # The seam raises NotImplementedError; a clean return proves the skip path
    # short-circuits before any live run is attempted.
    monkeypatch.setenv("LUMINOSITY_EVAL_LIVE", "off")
    skills.configure(ctx)
