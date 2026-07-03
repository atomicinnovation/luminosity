//! Black-box tests of external-subcommand dispatch + exec.
//!
//! `exec` REPLACES the current process, so these must spawn the real
//! `luminosity` binary as a child (never call dispatch in-process — that would
//! replace the test runner). The Phase 3 resolver reads `LUMINOSITY_RESOLVE_FIXTURE`
//! and returns it for any subcommand, so these exercise the real dispatch + exec
//! path against the in-crate fixture without any network.

use std::error::Error;
use std::ffi::OsString;
use std::io::{BufRead as _, BufReader};
use std::os::unix::ffi::OsStringExt as _;
use std::os::unix::process::ExitStatusExt as _;
use std::process::{Command, Stdio};

const FIXTURE_ENV: &str = "LUMINOSITY_RESOLVE_FIXTURE";
const LAUNCHER: &str = env!("CARGO_BIN_EXE_luminosity");
const FIXTURE: &str = env!("CARGO_BIN_EXE_luminosity-fixture");

fn launcher() -> Command {
    let mut command = Command::new(LAUNCHER);
    command.env(FIXTURE_ENV, FIXTURE);
    command
}

#[test]
fn external_subcommand_exit_code_propagates() -> Result<(), Box<dyn Error>> {
    // A resolved sub-binary exiting 42 makes `luminosity <sub>` exit 42 (AC5).
    let status = launcher().args(["frobnicate", "exit-42"]).status()?;
    assert_eq!(status.code(), Some(42));
    Ok(())
}

#[test]
fn external_subcommand_terminating_signal_propagates(
) -> Result<(), Box<dyn Error>> {
    // A sub-binary killed by SIGTERM makes the caller observe 128+15 — because
    // `exec` replaced the launcher, the fixture IS the launcher's PID.
    let mut child = launcher()
        .args(["frobnicate", "block-on-sigterm"])
        .stdout(Stdio::piped())
        .spawn()?;

    // Readiness handshake: wait for the sentinel line before signalling, so the
    // test is not racy against a not-yet-blocking child.
    let stdout = child.stdout.take().ok_or("child stdout missing")?;
    let mut line = String::new();
    BufReader::new(stdout).read_line(&mut line)?;
    assert!(
        line.contains("LUMINOSITY_FIXTURE_READY"),
        "no readiness line"
    );

    // std only sends SIGKILL via Child::kill; send SIGTERM via `kill(1)`.
    let killed = Command::new("kill")
        .args(["-TERM", &child.id().to_string()])
        .status()?;
    assert!(killed.success(), "kill -TERM failed");

    let status = child.wait()?;
    assert_eq!(status.signal(), Some(15), "expected SIGTERM (128+15=143)");
    Ok(())
}

#[test]
fn non_utf8_arguments_survive_verbatim_to_the_child(
) -> Result<(), Box<dyn Error>> {
    // The reason External is Vec<OsString>, not Vec<String>: a non-UTF-8 arg
    // must reach the exec'd child byte-for-byte.
    let destination =
        std::path::Path::new(env!("CARGO_TARGET_TMPDIR")).join("nonutf8-args");
    let non_utf8 = OsString::from_vec(vec![0x66, 0x80, 0x6f]); // "f\x80o"

    let status = launcher()
        .arg("frobnicate")
        .arg("write-args-to")
        .arg(&destination)
        .arg(&non_utf8)
        .status()?;
    assert!(status.success(), "fixture did not write the args");

    let written = std::fs::read(&destination)?;
    assert_eq!(written, vec![0x66, 0x80, 0x6f, 0]); // arg bytes + NUL separator
    Ok(())
}
