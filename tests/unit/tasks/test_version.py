import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from invoke import Context, Exit

import tasks.version as version_module
from tasks.version import check

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture
def ctx() -> MagicMock:
    return MagicMock(spec=Context)


@pytest.fixture
def coherent_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    """A tree where all four version anchors agree (the baseline)."""
    plugin = tmp_path / "plugin.json"
    plugin.write_text(json.dumps({"version": "0.1.0-pre.1"}))
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        '[package]\nname = "luminosity"\nversion = "0.1.0-pre.1"\n'
    )
    checksums = tmp_path / "checksums.json"
    checksums.write_text(json.dumps({"version": "0.1.0-pre.1", "binaries": {}}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"schema_version": 1, "version": "0.1.0-pre.1"})
    )

    monkeypatch.setattr(version_module, "PLUGIN_JSON", plugin)
    monkeypatch.setattr(version_module, "CARGO_TOML", cargo)
    monkeypatch.setattr(version_module, "CHECKSUMS", checksums)
    monkeypatch.setattr(version_module, "MANIFEST", manifest)
    return {
        "plugin.json": plugin,
        "cli/launcher/Cargo.toml": cargo,
        "cli/launcher/bin/checksums.json": checksums,
        "cli/launcher/bin/manifest.json": manifest,
    }


class TestVersionCheck:
    def test_passes_when_everything_agrees(
        self, ctx: MagicMock, coherent_tree: dict[str, Path]
    ):
        check(ctx)  # no raise

    @pytest.mark.parametrize(
        ("filename", "rewrite"),
        [
            (
                "cli/launcher/bin/checksums.json",
                lambda: json.dumps({"version": "9.9.9", "binaries": {}}),
            ),
            (
                "cli/launcher/bin/manifest.json",
                lambda: json.dumps({"schema_version": 1, "version": "9.9.9"}),
            ),
            ("plugin.json", lambda: json.dumps({"version": "9.9.9"})),
            (
                "cli/launcher/Cargo.toml",
                lambda: '[package]\nname = "luminosity"\nversion = "9.9.9"\n',
            ),
        ],
    )
    def test_names_the_desynced_anchor(
        self,
        ctx: MagicMock,
        coherent_tree: dict[str, Path],
        filename: str,
        rewrite: Callable[[], str],
    ):
        coherent_tree[filename].write_text(rewrite())
        with pytest.raises(Exit) as excinfo:
            check(ctx)
        assert filename in str(excinfo.value)

    def test_even_split_names_every_anchor(
        self, ctx: MagicMock, coherent_tree: dict[str, Path]
    ):
        # A 2-2 split has no majority to trust as the reference, so every
        # anchor must be named — not just the pair that loses a tiebreak.
        coherent_tree["cli/launcher/bin/checksums.json"].write_text(
            json.dumps({"version": "0.2.0", "binaries": {}})
        )
        coherent_tree["cli/launcher/bin/manifest.json"].write_text(
            json.dumps({"schema_version": 1, "version": "0.2.0"})
        )
        with pytest.raises(Exit) as excinfo:
            check(ctx)
        message = str(excinfo.value)
        for filename in coherent_tree:
            assert filename in message
