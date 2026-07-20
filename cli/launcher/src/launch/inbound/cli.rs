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
    /// Print the project-context block assembled from the config-file bodies,
    /// and — with `--skill` — that skill's own `## Skill-Specific Context`
    /// block after it. Prints nothing when no block survives.
    Context {
        /// Also render this skill's own context block, assembled from
        /// `.luminosity/skills/<name>/context.md` and `context.local.md`.
        #[arg(long)]
        skill: Option<String>,
        /// Also print a per-level discovery diagnostic to stderr.
        #[arg(long)]
        explain: bool,
        /// Never exit non-zero: render an unreadable config as a notice on
        /// stdout instead. For callers that splice this command's stdout into
        /// a prompt, where a non-zero exit would discard the whole prompt.
        #[arg(long)]
        fail_safe: bool,
    },
    /// Print this skill's `## Additional Instructions` block, assembled from
    /// `.luminosity/skills/<name>/instructions.md` and `instructions.local.md`.
    /// Prints nothing when no block survives.
    Instructions {
        /// The skill whose instructions to assemble, named by its frontmatter
        /// `name`. Instructions are always skill-scoped; without it, nothing
        /// prints.
        #[arg(long)]
        skill: Option<String>,
        /// Also print a per-level discovery diagnostic to stderr.
        #[arg(long)]
        explain: bool,
        /// Never exit non-zero: render an unreadable file as a notice on stdout
        /// instead. For callers that splice this command's stdout into a
        /// prompt, where a non-zero exit would discard the whole prompt.
        #[arg(long)]
        fail_safe: bool,
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
            | Command::Context { .. }
            | Command::Instructions { .. } => {
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
