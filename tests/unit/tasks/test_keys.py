from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

import tasks.keys as keys_module
from tasks.keys import generate
from tasks.shared import minisign

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def ctx() -> MagicMock:
    m = MagicMock(spec=Context)
    m.run.return_value = MagicMock(exited=0, stdout="")
    return m


@pytest.fixture
def key_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pubkey = tmp_path / "luminosity-release.pub"
    monkeypatch.setattr(keys_module, "RELEASE_PUBLIC_KEY", pubkey)
    return tmp_path


def _command(ctx: MagicMock) -> str:
    return ctx.run.call_args.args[0]


class TestGenerate:
    def test_runs_minisign_generate_to_the_committed_paths(
        self, ctx: MagicMock, key_dir: Path
    ):
        generate(ctx)
        command = _command(ctx)
        assert command.startswith(f"{minisign.MINISIGN} -G")
        assert str(key_dir / "luminosity-release.pub") in command
        assert str(key_dir / "luminosity-release.key") in command

    def test_refuses_to_overwrite_an_existing_public_key(
        self, ctx: MagicMock, key_dir: Path
    ):
        (key_dir / "luminosity-release.pub").write_text("existing")
        with pytest.raises(Exit):
            generate(ctx)
        ctx.run.assert_not_called()

    def test_force_overwrites_an_existing_public_key(
        self, ctx: MagicMock, key_dir: Path
    ):
        (key_dir / "luminosity-release.pub").write_text("existing")
        generate(ctx, force=True)
        assert ctx.run.called

    def test_generates_a_password_less_key(self, ctx: MagicMock, key_dir: Path):
        generate(ctx)
        assert " -W" in _command(ctx)

    def test_generation_is_non_interactive(self, ctx: MagicMock, key_dir: Path):
        generate(ctx)
        assert "pty" not in ctx.run.call_args.kwargs
