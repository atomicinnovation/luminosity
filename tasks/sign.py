import json
import os
import tempfile
from pathlib import Path
from typing import Any

from invoke import Context, Exit, task

from tasks.shared import minisign
from tasks.shared.files import atomic_write_text
from tasks.shared.paths import (
    CHECKSUMS,
    MANIFEST,
    MANIFEST_SIGNATURE,
    binary_path,
    signature_path,
)
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import TARGETS

# Manifest read-contract version; bumped only on a breaking shape change.
MANIFEST_SCHEMA_VERSION = 1
_LAUNCHER_DESCRIPTION = "The luminosity launcher"

_SECRET_KEY_ENV = "LUMINOSITY_RELEASE_SECRET_KEY"  # noqa: S105 — env var name


def build_manifest(
    version: str,
    digests: dict[str, str],
    signatures: dict[str, str],
) -> dict[str, Any]:
    """Assemble the launcher's read contract from per-platform artefacts.

    Keyed by binary name; `sha256` is the bare lowercase hex digest (no
    `sha256:` prefix), `signature` is the full `.minisig` contents.
    """
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "version": version,
        "binaries": {
            LAUNCHER_CRATE: {
                "description": _LAUNCHER_DESCRIPTION,
                "platforms": {
                    platform: {
                        "sha256": digests[platform],
                        "signature": signatures[platform],
                    }
                    for platform in digests
                },
            },
        },
    }


def _checksum_digests() -> dict[str, str]:
    checksums = json.loads(CHECKSUMS.read_text())
    return {
        platform: digest.removeprefix("sha256:")
        for platform, digest in checksums["binaries"].items()
    }


def _signatures() -> dict[str, str]:
    return {
        platform: signature_path(platform).read_text()
        for _, platform in TARGETS
    }


def sign_binaries(context: Context, secret_key: Path) -> None:
    """Detach-sign each staged binary as `luminosity-{platform}.minisig`."""
    for _, platform in TARGETS:
        minisign.sign(
            secret_key,
            binary_path(platform),
            signature_path(platform),
        )


def write_manifest() -> None:
    """Emit `manifest.json` from the staged checksums + emitted signatures.

    The inline `signature` is read back from the emitted `.minisig` so the
    inline copy and the detached asset cannot drift.
    """
    version = json.loads(CHECKSUMS.read_text())["version"]
    manifest = build_manifest(version, _checksum_digests(), _signatures())
    atomic_write_text(MANIFEST, json.dumps(manifest, indent=2) + "\n")


@task
def sign(context: Context) -> None:
    """Sign every binary, build the manifest, and sign the manifest.

    Reads the password-less release secret key from
    `LUMINOSITY_RELEASE_SECRET_KEY`, writing it to a private temp file to
    sign with.
    """
    key_material = os.environ.get(_SECRET_KEY_ENV)
    if not key_material:
        raise Exit(f"{_SECRET_KEY_ENV} is not set; cannot sign the release", 1)
    with tempfile.TemporaryDirectory() as tmp:
        secret_key = Path(tmp) / "release.key"
        secret_key.write_text(key_material)
        secret_key.chmod(0o600)
        sign_binaries(context, secret_key)
        write_manifest()
        minisign.sign(secret_key, MANIFEST, MANIFEST_SIGNATURE)
