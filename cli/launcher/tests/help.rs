//! Black-box tests that built-in commands stay decoupled from the release
//! manifest: `version` runs without it, and top-level `--help` degrades to the
//! built-in help when the manifest cannot be fetched.

use std::error::Error;
use std::process::Command;

const LAUNCHER: &str = env!("CARGO_BIN_EXE_luminosity");

// An https endpoint that refuses connections, so a manifest fetch fails fast;
// the fetcher pins https, so the scheme cannot be http.
const DEAD_RELEASE_URL: &str = "https://127.0.0.1:1";

#[test]
fn version_succeeds_with_no_manifest_available() -> Result<(), Box<dyn Error>> {
    let output = Command::new(LAUNCHER)
        .arg("version")
        .env("LUMINOSITY_RELEASE_BASE_URL", DEAD_RELEASE_URL)
        .output()?;
    assert!(output.status.success(), "version did not succeed");
    let stdout = String::from_utf8(output.stdout)?;
    assert!(
        stdout.contains("luminosity "),
        "expected version output, got: {stdout}"
    );
    Ok(())
}

#[test]
fn top_level_help_prints_builtins_when_manifest_unavailable(
) -> Result<(), Box<dyn Error>> {
    let output = Command::new(LAUNCHER)
        .arg("--help")
        .env("LUMINOSITY_RELEASE_BASE_URL", DEAD_RELEASE_URL)
        .output()?;
    assert!(output.status.success(), "--help did not exit 0");
    let stdout = String::from_utf8(output.stdout)?;
    assert!(
        stdout.contains("version"),
        "expected built-in help listing `version`, got: {stdout}"
    );
    Ok(())
}
