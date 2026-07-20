//! The dispatch boundary: routes the parsed command tree to a built-in handler
//! or to external resolution + exec.

pub mod core;
pub mod help;
pub mod inbound;
pub mod outbound;

use config::{AssembleFragment, ConfigAccess};

use crate::command_support::OnFailure;
use crate::config_command::inbound::cli as config_cli;
use crate::context_command::inbound::cli as context_cli;
use crate::instructions_command::inbound::cli as instructions_cli;
use crate::launch::core::{
    run_external, ExecBinary, ExternalCommand, ResolveBinary,
};
use crate::launch::inbound::cli::{Cli, Command};
use crate::version::core::ReportVersion;
use crate::version::inbound::cli as version_cli;

const fn on_failure(fail_safe: bool) -> OnFailure {
    if fail_safe {
        OnFailure::Degrade
    } else {
        OnFailure::Fail
    }
}

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
    context: &impl AssembleFragment,
    resolver: &impl ResolveBinary,
    executor: &impl ExecBinary,
) -> Result<(), kernel::Error> {
    match &cli.command {
        Command::Version => {
            version_cli::report(reporter);
            Ok(())
        }
        Command::Config { action } => Ok(config_cli::run(config, action)?),
        Command::Context {
            skill,
            explain,
            fail_safe,
        } => {
            let options = context_cli::Options {
                skill: skill.clone(),
                explain: *explain,
                on_failure: on_failure(*fail_safe),
            };
            Ok(context_cli::run(context, &options)?)
        }
        Command::Instructions {
            skill,
            explain,
            fail_safe,
        } => {
            let options = instructions_cli::Options {
                skill: skill.clone(),
                explain: *explain,
                on_failure: on_failure(*fail_safe),
            };
            Ok(instructions_cli::run(context, &options)?)
        }
        Command::External(raw) => {
            let command = ExternalCommand::from_raw(raw.clone())?;
            Err(run_external(resolver, executor, &command).into())
        }
    }
}
