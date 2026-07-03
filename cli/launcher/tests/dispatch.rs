//! Black-box tests of external-subcommand dispatch + exec.
//!
//! `exec` replaces the current process, so these spawn the real `luminosity`
//! binary as a child (calling dispatch in-process would replace the test
//! runner). `LUMINOSITY_RESOLVE_FIXTURE` points the resolver at the in-crate
//! fixture, so the dispatch + exec path runs without any network.

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
fn per_command_help_is_delegated_to_the_child() -> Result<(), Box<dyn Error>> {
    // clap routes `foo --help` to External (not top-level help), so dispatch
    // re-execs the child with --help and the child emits its own help.
    let output = launcher().args(["frobnicate", "--help"]).output()?;
    assert!(output.status.success());
    let stdout = String::from_utf8(output.stdout)?;
    assert!(
        stdout.contains("LUMINOSITY_FIXTURE_HELP_SENTINEL"),
        "expected the child's help sentinel, got: {stdout}"
    );
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
