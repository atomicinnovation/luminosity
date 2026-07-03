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
    """A tree where all four anchors and both keys agree (the baseline)."""
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
    shipped_key = tmp_path / "shipped.pub"
    shipped_key.write_text("untrusted comment: k\nRWQKEY\n")
    embedded_key = tmp_path / "embedded.pub"
    embedded_key.write_text("untrusted comment: k\nRWQKEY\n")

    monkeypatch.setattr(version_module, "PLUGIN_JSON", plugin)
    monkeypatch.setattr(version_module, "CARGO_TOML", cargo)
    monkeypatch.setattr(version_module, "CHECKSUMS", checksums)
    monkeypatch.setattr(version_module, "MANIFEST", manifest)
    monkeypatch.setattr(version_module, "RELEASE_PUBLIC_KEY", shipped_key)
    monkeypatch.setattr(
        version_module, "LAUNCHER_EMBEDDED_PUBLIC_KEY", embedded_key
    )
    return {
        "plugin.json": plugin,
        "cli/launcher/Cargo.toml": cargo,
        "cli/launcher/bin/checksums.json": checksums,
        "cli/launcher/bin/manifest.json": manifest,
        "shipped_key": shipped_key,
        "embedded_key": embedded_key,
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

    def test_fails_when_the_release_keys_diverge(
        self, ctx: MagicMock, coherent_tree: dict[str, Path]
    ):
        coherent_tree["embedded_key"].write_text(
            "untrusted comment: k\nRWQDIFFERENT\n"
        )
        with pytest.raises(Exit) as excinfo:
            check(ctx)
        assert "public key" in str(excinfo.value)
