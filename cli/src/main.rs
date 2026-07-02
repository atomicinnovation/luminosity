//! The luminosity launcher binary — the composition root: it builds the vergen
//! adapter, injects it into the `version` core, parses the CLI, and dispatches.

use std::process::ExitCode;

use clap::Parser;

use luminosity::version::core::VersionReporter;
use luminosity::version::inbound::cli::{dispatch, Cli};
use luminosity::version::outbound::build_metadata::VergenBuildMetadata;

fn main() -> ExitCode {
    let cli = Cli::parse();
    let reporter = VersionReporter::new(VergenBuildMetadata);
    match dispatch(&cli, &reporter) {
        Ok(()) => ExitCode::SUCCESS,
        // `kernel::Error` is uninhabited, so this arm is currently unreachable.
        Err(error) => match error {},
    }
}
