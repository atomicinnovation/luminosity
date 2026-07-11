//! The clap inbound (driving) adapter — the top-level command tree.

use std::ffi::OsString;

use clap::{Parser, Subcommand, ValueEnum};

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
    /// Read or write configuration values.
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },
    /// Print the project-context block assembled from the config-file bodies
    /// (prints nothing when both bodies are empty or absent).
    Context {
        /// Also print a per-level discovery diagnostic to stderr.
        #[arg(long)]
        explain: bool,
    },
    /// Any unknown subcommand + its args, forwarded verbatim. `Vec<OsString>`
    /// (not `Vec<String>`) preserves non-UTF-8 arguments through to the child.
    #[command(external_subcommand)]
    External(Vec<OsString>),
}

/// Read or write a configuration value.
///
/// Configuration is a dotted `section.key` tree resolved across two levels:
/// `team` is the committed, shared `.luminosity/config.md`, and `personal` is
/// the git-ignored, local `.luminosity/config.local.md` that overrides it.
#[derive(Subcommand)]
pub enum ConfigAction {
    /// Print a configuration value. Without `--level` the value resolves
    /// personal-over-team; with `--level` only that level is read. Exits
    /// non-zero if the key is not set.
    Get {
        /// The dotted `section.key` to read (e.g. `core.example`).
        key: String,
        /// Read only this level instead of resolving across both.
        #[arg(long)]
        level: Option<Level>,
    },
    /// Write a configuration value. Defaults to the git-ignored personal level;
    /// pass `--level team` to write the committed, shared file. Creates
    /// `.luminosity/` and the level's file on first write.
    Set {
        /// The dotted `section.key` to write (e.g. `core.example`).
        key: String,
        /// The value to store.
        value: String,
        /// Write this level instead of the personal default.
        #[arg(long)]
        level: Option<Level>,
    },
}

/// Which configuration level a command reads or writes.
#[derive(Clone, Copy, ValueEnum)]
pub enum Level {
    /// The committed, shared `.luminosity/config.md`.
    Team,
    /// The git-ignored, local `.luminosity/config.local.md` (overrides team).
    Personal,
}

impl From<Level> for config::Level {
    fn from(level: Level) -> Self {
        match level {
            Level::Team => Self::Team,
            Level::Personal => Self::Personal,
        }
    }
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
            Command::Version
            | Command::Config { .. }
            | Command::Context { .. } => {
                return Err("routed away from External".into())
            }
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
