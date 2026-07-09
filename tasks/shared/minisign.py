import subprocess
from typing import TYPE_CHECKING

from .errors import MinisignError

if TYPE_CHECKING:
    from pathlib import Path

MINISIGN = "minisign"
_TIMEOUT_SECONDS = 120


def sign(
    secret_key_path: Path,
    target: Path,
    signature_path: Path,
) -> None:
    """Detach-sign `target` with the password-less secret key.

    Writes `signature_path`; any failure raises `MinisignError`.
    """
    command = [
        MINISIGN,
        "-S",
        "-s",
        str(secret_key_path),
        "-x",
        str(signature_path),
        "-m",
        str(target),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MinisignError(
            f"minisign -S could not run for {target.name}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise MinisignError(
            f"minisign -S failed for {target.name}: {result.stderr.strip()}"
        )


def verify(target: Path, signature_path: Path, public_key_path: Path) -> None:
    """Verify `target` against its detached `signature_path` and `public_key`.

    Raises `MinisignError` on a verification failure or any tooling failure.
    """
    command = [
        MINISIGN,
        "-V",
        "-p",
        str(public_key_path),
        "-x",
        str(signature_path),
        "-m",
        str(target),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MinisignError(
            f"minisign -V could not run for {target.name}: {exc}"
        ) from exc
    if result.returncode != 0:
        raise MinisignError(
            f"minisign -V failed for {target.name}: {result.stderr.strip()}"
        )
