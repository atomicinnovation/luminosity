from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_ROOT = REPO_ROOT / "cli"
WORKSPACE_MANIFEST = WORKSPACE_ROOT / "Cargo.toml"
LAUNCHER_DIR = WORKSPACE_ROOT / "launcher"
BIN_DIR = LAUNCHER_DIR / "bin"
CHECKSUMS = BIN_DIR / "checksums.json"
MANIFEST = BIN_DIR / "manifest.json"
MANIFEST_SIGNATURE = BIN_DIR / "manifest.minisig"
CARGO_TOML = LAUNCHER_DIR / "Cargo.toml"
# The release public key rides two committed copies kept byte-identical by
# version:check: one shipped in the plugin package (for the bootstrap's
# root-of-trust shim) and one the launcher embeds via include_str!.
RELEASE_PUBLIC_KEY = REPO_ROOT / "keys" / "luminosity-release.pub"
LAUNCHER_EMBEDDED_PUBLIC_KEY = LAUNCHER_DIR / "keys" / "release.pub"
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


def signature_path(platform: str, bin_dir: Path = BIN_DIR) -> Path:
    return bin_dir / f"luminosity-{platform}.minisig"
