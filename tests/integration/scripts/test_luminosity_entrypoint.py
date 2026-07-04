"""Hermetic tests for bin/luminosity, the entry-point bootstrap.

No network: the bootstrap's fetch is pointed at a `file://` release directory
via `LUMINOSITY_RELEASE_BASE_URL`, so real `curl`/`wget` copy local files. The
launcher is a tiny signed stub. Skips cleanly if `minisign`, a fetcher, or the
host verify shim is unavailable.
"""

import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tasks.shared import minisign

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOTSTRAP = REPO_ROOT / "bin" / "luminosity"


def _platform_alias() -> str | None:
    arch = {
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86_64": "x64",
        "amd64": "x64",
    }
    system = {"Darwin": "darwin", "Linux": "linux"}
    machine = arch.get(platform.machine().lower())
    host = system.get(platform.system())
    if machine is None or host is None:
        return None
    return f"{host}-{machine}"


PLATFORM = _platform_alias()
HOST_SHIM = (
    REPO_ROOT / "bin" / f"luminosity-verify-{PLATFORM}" if PLATFORM else None
)

pytestmark = [
    pytest.mark.skipif(
        shutil.which(minisign.MINISIGN) is None, reason="minisign not on PATH"
    ),
    pytest.mark.skipif(
        shutil.which("curl") is None and shutil.which("wget") is None,
        reason="no curl or wget on PATH",
    ),
    pytest.mark.skipif(
        HOST_SHIM is None or not HOST_SHIM.exists(),
        reason="verify shim not built for this host",
    ),
]

_LAUNCHER_STUB = f"""#!{sys.executable}
import sys
arg = sys.argv[1] if len(sys.argv) > 1 else ""
if arg.startswith("exit-"):
    sys.exit(int(arg[len("exit-"):]))
print("LAUNCHER RAN:", *sys.argv[1:])
"""


def _make_keypair(directory: Path, name: str) -> tuple[Path, Path]:
    public = directory / f"{name}.pub"
    secret = directory / f"{name}.key"
    subprocess.run(
        [minisign.MINISIGN, "-G", "-W", "-f", "-p", public, "-s", secret],
        check=True,
        capture_output=True,
    )
    return public, secret


def _make_plugin_root(root: Path, public_key: Path) -> None:
    assert HOST_SHIM is not None  # narrowed; the module skips when it is None
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        '{\n  "version": "9.9.9-test"\n}\n'
    )
    (root / "bin").mkdir()
    (root / "keys").mkdir()
    shutil.copy(HOST_SHIM, root / "bin" / f"luminosity-verify-{PLATFORM}")
    shutil.copy(public_key, root / "keys" / "luminosity-release.pub")


def _make_release(release: Path, secret: Path) -> None:
    release.mkdir(parents=True)
    launcher = release / f"luminosity-{PLATFORM}"
    launcher.write_text(_LAUNCHER_STUB)
    launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    minisign.sign(secret, launcher, launcher.with_suffix(".minisig"))


def _run(
    plugin_root: Path,
    release: Path,
    cache: Path,
    *args: str,
    extra_path: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **_base_env(),
        "CLAUDE_PLUGIN_ROOT": str(plugin_root),
        "LUMINOSITY_CACHE_DIR": str(cache),
        "LUMINOSITY_RELEASE_BASE_URL": release.as_uri(),
    }
    if extra_path is not None:
        env["PATH"] = f"{extra_path}:{env['PATH']}"
    return subprocess.run(
        [BOOTSTRAP, *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def _base_env() -> dict[str, str]:
    return dict(os.environ)


def test_unset_plugin_root_is_a_named_error() -> None:
    result = subprocess.run(
        [BOOTSTRAP, "version"],
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": ""},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode != 0
    assert "CLAUDE_PLUGIN_ROOT" in result.stderr


def test_invalid_plugin_root_is_a_named_error(tmp_path: Path) -> None:
    # A set-but-non-directory CLAUDE_PLUGIN_ROOT must fail closed with the named
    # diagnostic, not a raw shell error.
    missing = tmp_path / "does-not-exist"
    result = subprocess.run(
        [BOOTSTRAP, "version"],
        env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(missing)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode != 0
    assert "not a directory" in result.stderr


def test_unrunnable_verify_shim_is_a_fail_closed_named_error(
    tmp_path: Path,
) -> None:
    # The shim is the root of trust. If it is present but cannot run, the
    # bootstrap must fail closed with a named diagnostic and never exec the
    # launcher — not silently downgrade to a TLS-only trust model.
    public, secret = _make_keypair(tmp_path, "release")
    root = tmp_path / "root"
    _make_plugin_root(root, public)
    _make_release(tmp_path / "rel", secret)  # a validly signed launcher
    broken = root / "bin" / f"luminosity-verify-{PLATFORM}"
    broken.write_text("not a runnable program\n")
    broken.chmod(broken.stat().st_mode | stat.S_IEXEC)
    result = _run(root, tmp_path / "rel", tmp_path / "cache", "go")
    assert result.returncode != 0
    assert "LAUNCHER RAN" not in result.stdout
    assert "luminosity:" in result.stderr


def test_happy_path_fetches_verifies_execs_and_forwards_args(
    tmp_path: Path,
) -> None:
    public, secret = _make_keypair(tmp_path, "release")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", secret)
    result = _run(
        tmp_path / "root",
        tmp_path / "rel",
        tmp_path / "cache",
        "hello",
        "world",
    )
    assert result.returncode == 0, result.stderr
    assert "LAUNCHER RAN: hello world" in result.stdout


def test_launcher_exit_code_propagates(tmp_path: Path) -> None:
    public, secret = _make_keypair(tmp_path, "release")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", secret)
    result = _run(
        tmp_path / "root", tmp_path / "rel", tmp_path / "cache", "exit-7"
    )
    assert result.returncode == 7


def test_cached_launcher_is_reused_without_refetching(tmp_path: Path) -> None:
    public, secret = _make_keypair(tmp_path, "release")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", secret)
    cache = tmp_path / "cache"
    first = _run(tmp_path / "root", tmp_path / "rel", cache, "first")
    assert first.returncode == 0, first.stderr
    # Remove the release so a refetch would fail; a cache hit must not fetch.
    shutil.rmtree(tmp_path / "rel")
    second = _run(tmp_path / "root", tmp_path / "rel", cache, "second")
    assert second.returncode == 0, second.stderr
    assert "LAUNCHER RAN: second" in second.stdout


def test_poisoned_cache_entry_is_refused(tmp_path: Path) -> None:
    public, secret = _make_keypair(tmp_path, "release")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", secret)
    cache = tmp_path / "cache"
    _run(tmp_path / "root", tmp_path / "rel", cache, "first")
    cached = cache / f"luminosity-launcher-9.9.9-test-{PLATFORM}"
    cached.write_text("poisoned")
    shutil.rmtree(tmp_path / "rel")  # no clean refetch available
    result = _run(tmp_path / "root", tmp_path / "rel", cache, "go")
    assert result.returncode != 0
    assert "LAUNCHER RAN" not in result.stdout


def test_non_release_key_launcher_is_refused(tmp_path: Path) -> None:
    public, _ = _make_keypair(tmp_path, "release")
    _, attacker_secret = _make_keypair(tmp_path, "attacker")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", attacker_secret)  # signed by attacker
    result = _run(tmp_path / "root", tmp_path / "rel", tmp_path / "cache", "go")
    assert result.returncode != 0
    assert "LAUNCHER RAN" not in result.stdout


def test_path_planted_decoy_shim_is_not_used(tmp_path: Path) -> None:
    public, _ = _make_keypair(tmp_path, "release")
    _, attacker_secret = _make_keypair(tmp_path, "attacker")
    _make_plugin_root(tmp_path / "root", public)
    _make_release(tmp_path / "rel", attacker_secret)
    # A decoy `luminosity-verify` earlier on PATH that always succeeds; the
    # bootstrap must invoke the real shim by absolute path, so this is ignored.
    decoy_dir = tmp_path / "decoy"
    decoy_dir.mkdir()
    decoy = decoy_dir / "luminosity-verify"
    decoy.write_text(f"#!{sys.executable}\nimport sys\nsys.exit(0)\n")
    decoy.chmod(decoy.stat().st_mode | stat.S_IEXEC)
    result = _run(
        tmp_path / "root",
        tmp_path / "rel",
        tmp_path / "cache",
        "go",
        extra_path=decoy_dir,
    )
    assert result.returncode != 0
    assert "LAUNCHER RAN" not in result.stdout


def test_read_only_plugin_root_falls_back_to_xdg(tmp_path: Path) -> None:
    public, secret = _make_keypair(tmp_path, "release")
    root = tmp_path / "root"
    _make_plugin_root(root, public)
    _make_release(tmp_path / "rel", secret)
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    (root / "bin").chmod(0o555)
    try:
        result = subprocess.run(
            [BOOTSTRAP, "ok"],
            env={
                **os.environ,
                "CLAUDE_PLUGIN_ROOT": str(root),
                "XDG_CACHE_HOME": str(xdg),
                "LUMINOSITY_RELEASE_BASE_URL": (tmp_path / "rel").as_uri(),
            },
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    finally:
        (root / "bin").chmod(0o755)  # let tmp cleanup remove it
    assert result.returncode == 0, result.stderr
    assert "LAUNCHER RAN: ok" in result.stdout
    cached = xdg / "luminosity" / f"luminosity-launcher-9.9.9-test-{PLATFORM}"
    assert cached.exists()
