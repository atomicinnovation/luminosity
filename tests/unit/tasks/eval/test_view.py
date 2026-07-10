import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from invoke import Context

from tasks.eval import view as view_task
from tasks.shared.eval.locations import EVALS_SKILLS_DIR, results_dir


@pytest.fixture
def ctx() -> MagicMock:
    return MagicMock(spec=Context)


@pytest.fixture
def captured_view(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {}
    fake = SimpleNamespace(view=lambda **kwargs: calls.update(kwargs))
    monkeypatch.setitem(sys.modules, "inspect_ai", fake)
    return calls


class TestView:
    def test_serves_every_skill_recursively_by_default(
        self, ctx: MagicMock, captured_view: dict[str, Any]
    ):
        view_task.view(ctx)
        assert captured_view["log_dir"] == str(EVALS_SKILLS_DIR)
        assert captured_view["recursive"] is True

    def test_serves_a_single_skill_when_named(
        self, ctx: MagicMock, captured_view: dict[str, Any]
    ):
        view_task.view(ctx, skill="configure")
        assert captured_view["log_dir"] == str(results_dir("configure"))

    def test_forwards_the_host_and_port(
        self, ctx: MagicMock, captured_view: dict[str, Any]
    ):
        view_task.view(ctx, host="0.0.0.0", port=8080)
        assert captured_view["host"] == "0.0.0.0"
        assert captured_view["port"] == 8080
