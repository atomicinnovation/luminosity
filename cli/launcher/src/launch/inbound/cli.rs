//! The clap inbound (driving) adapter — the top-level command tree.

use std::ffi::OsString;

use clap::{Parser, Subcommand};

/// The `luminosity` command-line surface.
#[derive(Parser)]
#[command(name = "luminosity", disable_version_flag = true)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Print the version, commit SHA, build date, and target triple.
    Version,
    /// Any unknown subcommand + its args, forwarded verbatim. `Vec<OsString>`
    /// (not `Vec<String>`) preserves non-UTF-8 arguments through to the child.
    #[command(external_subcommand)]
    External(Vec<OsString>),
}

#[cfg(test)]
mod tests {
    use std::error::Error;
    use std::ffi::OsString;

    use clap::Parser as _;

    use super::{Cli, Command};

    #[test]
    fn an_unknown_subcommand_routes_to_external_with_its_args(
    ) -> Result<(), Box<dyn Error>> {
        let cli = Cli::try_parse_from(["luminosity", "frobnicate", "--flag"])?;
        match cli.command {
            Command::External(raw) => assert_eq!(
                raw,
                vec![OsString::from("frobnicate"), OsString::from("--flag")]
            ),
            Command::Version => return Err("routed to Version".into()),
        }
        Ok(())
    }

    #[test]
    fn a_known_subcommand_routes_to_its_builtin() -> Result<(), Box<dyn Error>>
    {
        let cli = Cli::try_parse_from(["luminosity", "version"])?;
        assert!(matches!(cli.command, Command::Version));
        Ok(())
    }
}
