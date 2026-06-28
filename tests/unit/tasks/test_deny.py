from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

from tasks import deny


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestDenyCheck:
    def test_runs_the_four_sections_in_order(self, ctx: MagicMock):
        deny.check(ctx)
        assert (
            _command(ctx) == "cargo deny check advisories licenses bans sources"
        )

    def test_raises_on_findings(self, ctx: MagicMock):
        ctx.run.return_value = MagicMock(exited=1)
        with pytest.raises(Exit):
            deny.check(ctx)
