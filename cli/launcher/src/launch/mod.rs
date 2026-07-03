//! The launcher's imperative shell: the dispatch boundary that routes the
//! parsed command tree to a built-in handler or to external resolution + exec.
//!
//! This is the named inward-only boundary the plan calls for — `version` stays a
//! clean hexagon under `version::`, and no launcher dispatch code sits under
//! `version::core` (which cargo-pup would reject).

pub mod core;
pub mod inbound;
pub mod outbound;

use crate::launch::core::{
    run_external, ExecBinary, ExternalCommand, ResolveBinary,
};
use crate::launch::inbound::cli::{Cli, Command};
use crate::version::core::ReportVersion;
use crate::version::inbound::cli as version_cli;

/// Route the parsed command: built-ins run in-process; an external subcommand
/// resolves + execs (replacing this process on success).
///
/// # Errors
///
/// A [`kernel::Error`] when an external subcommand cannot be resolved or exec'd.
/// The `Version` built-in never fails. A successful external exec never returns.
pub fn dispatch(
    cli: &Cli,
    reporter: &impl ReportVersion,
    resolver: &impl ResolveBinary,
    executor: &impl ExecBinary,
) -> Result<(), kernel::Error> {
    match &cli.command {
        Command::Version => {
            version_cli::report(reporter);
            Ok(())
        }
        Command::External(raw) => {
            let command = ExternalCommand::from_raw(raw.clone())?;
            // run_external only returns on failure — a successful exec replaces
            // the process — so reaching here always means an error.
            Err(run_external(resolver, executor, &command).into())
        }
    }
}
