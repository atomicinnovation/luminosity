from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_DIR = REPO_ROOT / "cli"
BIN_DIR = CLI_DIR / "bin"
CHECKSUMS = BIN_DIR / "checksums.json"
CARGO_TOML = CLI_DIR / "Cargo.toml"
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
