//! The clap inbound (driving) adapter for `version` — parses, renders the
//! [`VersionReport`], and drives the inbound port. No domain logic.

use clap::{Parser, Subcommand};

use crate::version::core::{ReportVersion, VersionReport};

/// The `luminosity` command-line surface.
#[derive(Parser)]
#[command(name = "luminosity", disable_version_flag = true)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

/// The built-in subcommands compiled into the launcher.
#[derive(Subcommand)]
pub enum Command {
    /// Print the version, commit SHA, build date, and target triple.
    Version,
}

/// Renders a [`VersionReport`] as the human-facing `version` output.
#[must_use]
pub fn render(report: &VersionReport) -> String {
    format!(
        "luminosity {}\ncommit: {}\nbuilt:  {}\ntarget: {}",
        report.version,
        report.commit_sha,
        report.build_date,
        report.target_triple,
    )
}

/// Drives the inbound port for the parsed command and prints the result.
///
/// # Errors
///
/// Currently never — `kernel::Error` is uninhabited. The fallible signature is
/// the deliberate seam where a future command's failure will surface.
pub fn dispatch(
    cli: &Cli,
    reporter: &impl ReportVersion,
) -> Result<(), kernel::Error> {
    match &cli.command {
        Command::Version => {
            println!("{}", render(&reporter.report()));
            Ok(())
        }
    }
}
