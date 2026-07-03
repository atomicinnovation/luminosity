import json
from collections import Counter
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import semver
import tomlkit
from invoke import Context, Exit, task

if TYPE_CHECKING:
    from pathlib import Path

from .shared.files import atomic_write_text
from .shared.paths import (
    CARGO_TOML,
    CHECKSUMS,
    LAUNCHER_EMBEDDED_PUBLIC_KEY,
    MANIFEST,
    PLUGIN_JSON,
    RELEASE_PUBLIC_KEY,
)


class BumpType(StrEnum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRE = "pre"
    FINALISE = "finalise"
    NEXT_MINOR = "next-minor"


def read_plugin_metadata() -> dict[str, Any]:
    return json.loads(PLUGIN_JSON.read_text())


def _render_plugin_json(version: str) -> str:
    data = read_plugin_metadata()
    data["version"] = version
    return json.dumps(data, indent=2)


def _render_cargo_toml(version: str) -> str:
    data = tomlkit.parse(CARGO_TOML.read_text())
    data["package"]["version"] = version
    return tomlkit.dumps(data)


def _render_checksums_version(version: str) -> str:
    data = json.loads(CHECKSUMS.read_text())
    data["version"] = version
    return json.dumps(data, indent=2) + "\n"


def _render_manifest_version(version: str) -> str:
    data = json.loads(MANIFEST.read_text())
    data["version"] = version
    return json.dumps(data, indent=2) + "\n"


_PRERELEASE_IDENTIFIER = "pre"


def _bump_to_next_prerelease(version: semver.Version) -> semver.Version:
    """Advance to the next prerelease, opening a fresh line off a stable cut.

    Bumping a finalised release's prerelease directly would re-cut
    `<x.y.z>-pre.1`, colliding with the prerelease tags that led up to that
    release; advancing to the next minor's first prerelease avoids the clash.
    An in-progress prerelease simply increments.
    """
    already_in_prerelease = version.prerelease is not None
    if already_in_prerelease:
        return version.bump_prerelease(token=_PRERELEASE_IDENTIFIER)
    return version.bump_minor().bump_prerelease(token=_PRERELEASE_IDENTIFIER)


@task
def read(_context: Context, print_to_stdout: bool = True) -> semver.Version:
    """Read plugin version."""
    plugin_metadata = read_plugin_metadata()
    current_version = plugin_metadata["version"]
    if print_to_stdout:
        print(current_version)
    return semver.Version.parse(current_version)


@task
def write(_context: Context, version: str) -> None:
    """Write the version to every version-bearing file, coherently.

    Single writer for plugin.json, the launcher Cargo.toml, checksums.json, and
    the release manifest, so the four anchors version:check guards can never
    drift apart through a normal bump.
    """
    rendered_plugin_json = _render_plugin_json(version)
    rendered_cargo_toml = _render_cargo_toml(version)
    rendered_checksums = _render_checksums_version(version)
    rendered_manifest = _render_manifest_version(version)

    atomic_write_text(PLUGIN_JSON, rendered_plugin_json)
    atomic_write_text(CARGO_TOML, rendered_cargo_toml)
    atomic_write_text(CHECKSUMS, rendered_checksums)
    atomic_write_text(MANIFEST, rendered_manifest)


def _cargo_version() -> str:
    return tomlkit.parse(CARGO_TOML.read_text())["package"]["version"]


def _json_version(path: Path) -> str:
    return json.loads(path.read_text())["version"]


def _anchor_versions() -> dict[str, str]:
    """Return each guarded anchor's declared version, keyed by filename."""
    return {
        "plugin.json": read_plugin_metadata()["version"],
        "cli/launcher/Cargo.toml": _cargo_version(),
        "cli/launcher/bin/checksums.json": _json_version(CHECKSUMS),
        "cli/launcher/bin/manifest.json": _json_version(MANIFEST),
    }


def _mismatching_anchor_files(versions: dict[str, str]) -> list[str]:
    """Files whose version differs from the majority — empty when all agree."""
    majority, _ = Counter(versions.values()).most_common(1)[0]
    return sorted(name for name, value in versions.items() if value != majority)


def _key_coherence_error() -> str | None:
    """Non-None when the two committed release public keys diverge."""
    shipped = RELEASE_PUBLIC_KEY.read_text()
    embedded = LAUNCHER_EMBEDDED_PUBLIC_KEY.read_text()
    if shipped != embedded:
        return (
            "release public key diverges: keys/luminosity-release.pub differs "
            "from cli/launcher/keys/release.pub"
        )
    return None


@task
def check(_context: Context) -> None:
    """Fail (naming the culprits) if the release-contract anchors have drifted.

    Enforces version coherence across plugin.json, the launcher Cargo.toml,
    checksums.json, and manifest.json, plus a companion key-coherence check
    that the bootstrap-shipped public key is byte-identical to the one the
    launcher embeds. Wired into `mise run check` and re-run as a fail-closed
    precondition on the release path.
    """
    problems: list[str] = []

    mismatching = _mismatching_anchor_files(_anchor_versions())
    if mismatching:
        problems.append(
            "version mismatch across anchors: " + ", ".join(mismatching)
        )

    key_error = _key_coherence_error()
    if key_error is not None:
        problems.append(key_error)

    if problems:
        raise Exit("version:check failed:\n  " + "\n  ".join(problems), code=1)


@task(iterable=["bump_type"])
def bump(
    _context: Context, bump_type: list[BumpType] | None = None
) -> semver.Version:
    """Bump plugin version."""
    current_version = read(_context, print_to_stdout=False)
    new_version = current_version

    bump_types = bump_type or (BumpType.PRE,)
    for bt in bump_types:
        match bt:
            case BumpType.MAJOR:
                new_version = new_version.bump_major()
            case BumpType.MINOR:
                new_version = new_version.bump_minor()
            case BumpType.PATCH:
                new_version = new_version.bump_patch()
            case BumpType.PRE:
                new_version = _bump_to_next_prerelease(new_version)
            case BumpType.FINALISE:
                new_version = new_version.finalize_version()
            case BumpType.NEXT_MINOR:
                new_version = new_version.next_version(
                    part="minor", prerelease_token=_PRERELEASE_IDENTIFIER
                )

    write(_context, str(new_version))

    return new_version
