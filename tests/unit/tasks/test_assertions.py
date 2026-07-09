from unittest.mock import MagicMock

import pytest
from invoke import Context

from tasks.assertions import no_leaked_artifacts


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="", stderr="")
    return m


def test_aborts_when_a_secret_would_leak(ctx: MagicMock) -> None:
    ctx.run.return_value = MagicMock(stdout="?? keys/luminosity-release.key\n")
    with pytest.raises(RuntimeError):
        no_leaked_artifacts(ctx)


def test_aborts_when_a_staged_binary_would_leak(ctx: MagicMock) -> None:
    ctx.run.return_value = MagicMock(
        stdout="?? cli/launcher/bin/luminosity-darwin-arm64\n"
    )
    with pytest.raises(RuntimeError):
        no_leaked_artifacts(ctx)


def test_allows_clean_version_anchors(ctx: MagicMock) -> None:
    ctx.run.return_value = MagicMock(
        stdout=" M cli/launcher/bin/checksums.json\n"
        " M cli/launcher/bin/manifest.json\n"
    )
    no_leaked_artifacts(ctx)
