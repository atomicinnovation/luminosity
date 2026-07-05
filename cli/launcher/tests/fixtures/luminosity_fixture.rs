//! A stand-in "sub-binary" the launcher resolves and execs in tests, selecting
//! a behaviour by argument. Located via `CARGO_BIN_EXE_luminosity-fixture`; the
//! release staging copies only the `luminosity` binary, so it never ships.
#![allow(
    clippy::exit,
    clippy::print_stdout,
    clippy::print_stderr,
    clippy::restriction
)]

use std::ffi::OsString;
use std::io::Write as _;
use std::os::unix::ffi::OsStrExt as _;
use std::process;

const HELP_SENTINEL: &str = "LUMINOSITY_FIXTURE_HELP_SENTINEL";
const READY_SENTINEL: &str = "LUMINOSITY_FIXTURE_READY";

fn main() {
    // args_os, not args: a non-UTF-8 forwarded argument must not panic here.
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();

    if args.iter().any(|arg| arg == "--help") {
        println!("{HELP_SENTINEL}");
        return;
    }

    match args.first().and_then(|arg| arg.to_str()) {
        Some("exit-42") => process::exit(42),
        Some("block-on-sigterm") => block_until_signalled(),
        Some("print-help-sentinel") => println!("{HELP_SENTINEL}"),
        Some("write-args-to") => write_forwarded_args(&args),
        other => {
            eprintln!("luminosity-fixture: unknown behaviour {other:?}");
            process::exit(1);
        }
    }
}

/// Print a readiness line (so a test can wait for it rather than guess timing),
/// then block forever — the caller kills us with SIGTERM and observes 128+15.
fn block_until_signalled() -> ! {
    println!("{READY_SENTINEL}");
    // Flush so the reader unblocks before we sleep; stdout is line-buffered to a
    // pipe, so an explicit flush avoids a deadlock on the handshake.
    let _ = std::io::stdout().flush();
    loop {
        std::thread::sleep(std::time::Duration::from_secs(3600));
    }
}

/// `write-args-to <file> <arg>...` — writes the args after the destination path,
/// NUL-separated as raw bytes, so a test can assert non-UTF-8 args survive exec.
fn write_forwarded_args(args: &[OsString]) {
    let Some(destination) = args.get(1) else {
        eprintln!("luminosity-fixture: write-args-to needs a destination");
        process::exit(1);
    };
    let mut bytes = Vec::new();
    for arg in &args[2..] {
        bytes.extend_from_slice(arg.as_bytes());
        bytes.push(0);
    }
    if let Err(error) = std::fs::write(destination, bytes) {
        eprintln!("luminosity-fixture: write failed: {error}");
        process::exit(1);
    }
}
