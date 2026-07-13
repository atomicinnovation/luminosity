//! The dispatch boundary: routes the parsed command tree to a built-in handler
//! or to external resolution + exec.

pub mod core;
pub mod help;
pub mod inbound;
pub mod outbound;

use config::{AssembleContext, ConfigAccess};

use crate::config_command::inbound::cli as config_cli;
use crate::context_command::inbound::cli as context_cli;
use crate::launch::core::{
    run_external, ExecBinary, ExternalCommand, ResolveBinary,
};
use crate::launch::inbound::cli::{Cli, Command};
use crate::version::core::ReportVersion;
use crate::version::inbound::cli as version_cli;

/// A successful external exec never returns (it replaces this process).
///
/// # Errors
///
/// A [`kernel::Error`] when a built-in fails or an external subcommand cannot
/// be resolved or exec'd.
pub fn dispatch(
    cli: &Cli,
    reporter: &impl ReportVersion,
    config: &impl ConfigAccess,
    context: &impl AssembleContext,
    resolver: &impl ResolveBinary,
    executor: &impl ExecBinary,
) -> Result<(), kernel::Error> {
    match &cli.command {
        Command::Version => {
            version_cli::report(reporter);
            Ok(())
        }
        Command::Config { action } => Ok(config_cli::run(config, action)?),
        Command::Context { explain, fail_safe } => {
            let options = context_cli::Options {
                explain: *explain,
                on_failure: if *fail_safe {
                    context_cli::OnFailure::Degrade
                } else {
                    context_cli::OnFailure::Fail
                },
            };
            Ok(context_cli::run(context, options)?)
        }
        Command::External(raw) => {
            let command = ExternalCommand::from_raw(raw.clone())?;
            Err(run_external(resolver, executor, &command).into())
        }
    }
}
