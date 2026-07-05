import json
import shlex
import subprocess
import tempfile
from pathlib import Path

import semver
from invoke import Context, task

from . import version
from .shared import minisign
from .shared.errors import InvalidVersionError, MinisignError
from .shared.hashing import compute_sha256
from .shared.paths import (
    CHECKSUMS,
    MANIFEST,
    MANIFEST_SIGNATURE,
    RELEASE_PUBLIC_KEY,
    binary_path,
    debug_archive_path,
    signature_path,
)
from .shared.targets import TARGETS


def is_prerelease_version(version: str) -> bool:
    try:
        parsed = semver.Version.parse(version)
    except (ValueError, TypeError) as exc:
        raise InvalidVersionError(f"not a valid semver: {version!r}") from exc
    return bool(parsed.prerelease)


def _emit_forensic_alert(context: Context, tag: str, message: str) -> None:
    print(f"::error title=Release {tag}::{message}", flush=True)


class AssetVerificationError(Exception):
    pass


@task
def check_auth(context: Context) -> None:
    """Verify the GitHub CLI is authenticated."""
    result = context.run("gh auth status", warn=True, hide=True)
    if result.return_code != 0:
        raise RuntimeError(
            "gh auth status failed — run 'gh auth login' or set GH_TOKEN"
        )


@task
def create_release(context: Context, target_version: str | None = None) -> None:
    """Create a draft GitHub release for the current version.

    Passes --prerelease for pre-release versions; always --draft so nothing is
    visible until upload_and_verify has verified every binary and published.
    """
    resolved_version = str(
        target_version or version.read(context, print_to_stdout=False)
    )
    tag = f"v{resolved_version}"
    cmd = [
        "gh",
        "release",
        "create",
        tag,
        "--draft",
        "--generate-notes",
        "--title",
        tag,
    ]
    if is_prerelease_version(resolved_version):
        cmd.append("--prerelease")
    context.run(shlex.join(cmd), pty=True)


@task
def upload_release_asset(context: Context, tag: str, path: Path) -> None:
    """Upload a single asset file to a GitHub release."""
    context.run(f"gh release upload {tag} {path}", pty=True)


@task
def download_release_asset(
    context: Context, tag: str, asset_name: str, output_path: Path
) -> None:
    """Download a single asset from a GitHub release to output_path."""
    result = subprocess.run(
        [
            "gh",
            "release",
            "download",
            tag,
            "--pattern",
            asset_name,
            "--output",
            str(output_path),
            "--clobber",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        raise AssetVerificationError(
            f"gh release download failed: {result.stderr.strip()}"
        )


@task
def verify_release_asset(
    context: Context, path: Path, expected_hex: str
) -> None:
    """Verify the SHA-256 of a local file matches expected_hex."""
    actual = compute_sha256(path)
    if actual != expected_hex:
        raise AssetVerificationError(
            f"{path.name}: expected sha256:{expected_hex}, got sha256:{actual}"
        )


@task
def download_and_verify(
    context: Context, release_tag: str, asset_name: str, expected_hex: str
) -> None:
    """Download a release asset to a temp file and verify its SHA-256."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        try:
            download_release_asset(context, release_tag, asset_name, tmp_path)
        except subprocess.TimeoutExpired as exc:
            raise AssetVerificationError(
                f"gh release download timed out for {asset_name}"
            ) from exc
        verify_release_asset(context, tmp_path, expected_hex)
    finally:
        tmp_path.unlink(missing_ok=True)


@task
def download_and_verify_signature(
    context: Context,
    release_tag: str,
    asset_name: str,
    signature_name: str,
    public_key: Path,
) -> None:
    """Re-download an asset + `.minisig` and minisign-verify against a key.

    Every failure mode — a genuine signature mismatch or any tool hiccup —
    surfaces as `AssetVerificationError`, so no transient tooling failure
    escapes into the generic branch that destroys the pushed tag.
    """
    with tempfile.NamedTemporaryFile(delete=False) as target_tmp:
        target_path = Path(target_tmp.name)
    with tempfile.NamedTemporaryFile(delete=False) as sig_tmp:
        sig_path = Path(sig_tmp.name)
    try:
        try:
            download_release_asset(
                context, release_tag, asset_name, target_path
            )
            download_release_asset(
                context, release_tag, signature_name, sig_path
            )
        except subprocess.TimeoutExpired as exc:
            raise AssetVerificationError(
                f"gh release download timed out for {asset_name}"
            ) from exc
        try:
            minisign.verify(target_path, sig_path, public_key)
        except MinisignError as exc:
            raise AssetVerificationError(str(exc)) from exc
    finally:
        target_path.unlink(missing_ok=True)
        sig_path.unlink(missing_ok=True)


@task
def upload_and_verify(context: Context, version: str) -> None:
    """Upload artefacts, verify SHA-256 + minisign + manifest, then publish."""
    tag = f"v{version}"
    checksums = json.loads(CHECKSUMS.read_text())
    hashes = {
        platform: digest.removeprefix("sha256:")
        for platform, digest in checksums["binaries"].items()
    }
    binaries = {platform: binary_path(platform) for _, platform in TARGETS}
    archives = {
        platform: debug_archive_path(platform) for _, platform in TARGETS
    }
    signatures = {platform: signature_path(platform) for _, platform in TARGETS}
    required = (
        list(binaries.values())
        + list(archives.values())
        + list(signatures.values())
        + [MANIFEST, MANIFEST_SIGNATURE]
    )
    missing = [p for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"Expected release artefacts not found: {[str(p) for p in missing]}"
        )
    try:
        for platform, path in binaries.items():
            upload_release_asset(context, tag, path)
            upload_release_asset(context, tag, archives[platform])
            upload_release_asset(context, tag, signatures[platform])
        upload_release_asset(context, tag, MANIFEST)
        upload_release_asset(context, tag, MANIFEST_SIGNATURE)
        for platform, asset_path in binaries.items():
            download_and_verify(context, tag, asset_path.name, hashes[platform])
            download_and_verify_signature(
                context,
                tag,
                asset_path.name,
                signatures[platform].name,
                RELEASE_PUBLIC_KEY,
            )
        download_and_verify_signature(
            context,
            tag,
            MANIFEST.name,
            MANIFEST_SIGNATURE.name,
            RELEASE_PUBLIC_KEY,
        )
        context.run(f"gh release edit {tag} --draft=false", pty=True)
    except AssetVerificationError:
        _emit_forensic_alert(
            context,
            tag,
            "AssetVerificationError — draft + tag PRESERVED for triage",
        )
        raise
    except Exception:
        context.run(
            f"gh release delete {tag} --cleanup-tag --yes",
            warn=True,
            timeout=120,
        )
        raise
