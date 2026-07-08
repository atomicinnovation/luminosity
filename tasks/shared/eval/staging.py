import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def stage_plugin(*, repo_root: Path, host_binary: Path, dest: Path) -> Path:
    # The shipped bin/luminosity is a release-fetching shim that cannot run for
    # an in-dev prerelease, so stage the real host-native launcher at that path.
    if dest.exists():
        shutil.rmtree(dest)
    (dest / ".claude-plugin").mkdir(parents=True)
    shutil.copy(
        repo_root / ".claude-plugin" / "plugin.json",
        dest / ".claude-plugin" / "plugin.json",
    )
    shutil.copytree(repo_root / "skills" / "config", dest / "skills" / "config")
    bin_dir = dest / "bin"
    bin_dir.mkdir()
    launcher = bin_dir / "luminosity"
    shutil.copy(host_binary, launcher)
    launcher.chmod(0o755)
    return dest
