from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = REPO_ROOT / "cli"
WORKSPACE_MANIFEST = WORKSPACE_ROOT / "Cargo.toml"
LAUNCHER_DIR = WORKSPACE_ROOT / "launcher"
BIN_DIR = LAUNCHER_DIR / "bin"
CHECKSUMS = BIN_DIR / "checksums.json"
CARGO_TOML = LAUNCHER_DIR / "Cargo.toml"
PLUGIN_JSON = REPO_ROOT / ".claude-plugin/plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin/marketplace.json"
PRERELEASE_MARKETPLACE_JSON = (
    REPO_ROOT / ".claude-plugin/marketplace-prerelease.json"
)
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def binary_path(platform: str, bin_dir: Path = BIN_DIR) -> Path:
    return bin_dir / f"luminosity-{platform}"


def debug_archive_path(platform: str, bin_dir: Path = BIN_DIR) -> Path:
    return bin_dir / f"luminosity-{platform}.debug.tar.gz"
