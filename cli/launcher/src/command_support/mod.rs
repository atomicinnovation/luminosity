//! Shared inbound scaffolding for the fragment-rendering commands (`context`
//! and `instructions`).
//!
//! Not a subcommand — it holds the whole fail-safe boundary both commands must
//! implement identically: the failure policy, the assemble-then-degrade wrapper,
//! the raw-`--skill`-name parse kept inside the boundary, and the `--explain`
//! line grammar. A non-zero exit from either command discards the prompt a
//! caller splices its stdout into, so this boundary has one implementation, not
//! two that can drift.

use config::{
    AssembleFragment, ConfigError, FragmentSource, Level, LevelContribution,
    SkillName,
};

/// How a read failure is surfaced.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OnFailure {
    /// Exit non-zero with the error on stderr.
    Fail,
    /// Exit zero, rendering the error as a notice on stdout. For a caller that
    /// splices this command's stdout into a prompt: a non-zero exit there
    /// discards the whole prompt, so failing loudly would disable the caller
    /// rather than inform it.
    Degrade,
}

/// What assembling one source yielded: its levels, or the error a `--fail-safe`
/// run absorbed.
pub enum Outcome {
    Assembled(config::Assembly),
    Degraded(ConfigError),
}

/// Assembles one source, absorbing a read failure into [`Outcome::Degraded`]
/// under [`OnFailure::Degrade`] and propagating it under [`OnFailure::Fail`].
///
/// # Errors
///
/// The underlying [`ConfigError`] when assembly fails and `on_failure` is
/// [`OnFailure::Fail`].
pub fn assemble(
    assembler: &impl AssembleFragment,
    source: &FragmentSource,
    on_failure: OnFailure,
) -> Result<Outcome, ConfigError> {
    match assembler.assemble(source) {
        Ok(assembly) => Ok(Outcome::Assembled(assembly)),
        Err(error) if on_failure == OnFailure::Degrade => {
            Ok(Outcome::Degraded(error))
        }
        Err(error) => Err(error),
    }
}

/// A raw `--skill` name resolved inside the fail-safe boundary.
pub enum SkillResolution {
    /// The name parsed to a valid [`SkillName`].
    Parsed(SkillName),
    /// The name did not parse, and `--fail-safe` absorbed the rejection.
    Invalid(ConfigError),
}

/// Parses a raw `--skill` name inside the fail-safe boundary.
///
/// An invalid name degrades to [`SkillResolution::Invalid`] under
/// [`OnFailure::Degrade`] rather than exiting before the boundary, as a clap
/// `value_parser` would.
///
/// # Errors
///
/// [`ConfigError::InvalidSkillName`] when the name does not parse and
/// `on_failure` is [`OnFailure::Fail`].
pub fn resolve_skill_name(
    raw: &str,
    on_failure: OnFailure,
) -> Result<SkillResolution, ConfigError> {
    match SkillName::parse(raw) {
        Ok(name) => Ok(SkillResolution::Parsed(name)),
        Err(error) if on_failure == OnFailure::Degrade => {
            Ok(SkillResolution::Invalid(error))
        }
        Err(error) => Err(error),
    }
}

/// Degrades a `--explain` build failure to a single notice line under
/// [`OnFailure::Degrade`].
///
/// So `--explain` is never a hole in the fail-safe boundary — the one error that
/// would still exit non-zero and discard the prompt the flag was only meant to
/// describe.
///
/// # Errors
///
/// The underlying [`ConfigError`] when the lines could not be built and
/// `on_failure` is [`OnFailure::Fail`].
pub fn degrade_explain(
    lines: Result<Vec<String>, ConfigError>,
    on_failure: OnFailure,
) -> Result<Vec<String>, ConfigError> {
    match lines {
        Ok(lines) => Ok(lines),
        Err(error) if on_failure == OnFailure::Degrade => {
            Ok(vec![format!("explain unavailable: {error}")])
        }
        Err(error) => Err(error),
    }
}

/// The per-level `--explain` lines for an assembled source.
#[must_use]
pub fn explain_lines(levels: &[LevelContribution]) -> Vec<String> {
    levels.iter().map(explain_line).collect()
}

fn explain_line(contribution: &LevelContribution) -> String {
    let LevelContribution {
        level,
        path,
        discovered,
        has_body,
    } = contribution;
    if !discovered {
        format!("{level} ({path}): not found")
    } else if *has_body {
        format!("{level} ({path}): discovered, body present")
    } else {
        format!("{level} ({path}): discovered, empty body")
    }
}

/// The per-level `--explain` lines for a source that degraded under
/// `--fail-safe`: the two attempted paths, each tagged with why the read failed.
#[must_use]
pub fn degraded_source_lines(
    error: &ConfigError,
    paths: [String; 2],
) -> Vec<String> {
    let state = degraded_state(error);
    [Level::Team, Level::Personal]
        .into_iter()
        .zip(paths)
        .map(|(level, path)| format!("{level} ({path}): {state}"))
        .collect()
}

const fn degraded_state(error: &ConfigError) -> &'static str {
    match error {
        ConfigError::UnsafePath { .. } => "unsafe",
        _ => "unreadable",
    }
}

/// Names an invalid `--skill` source without naming a file: no path was ever
/// constructed for a name that did not parse, and fabricating one would be the
/// very path-rebuild the design forbids.
#[must_use]
pub fn invalid_skill_line(error: &ConfigError) -> String {
    format!("skill: {error}")
}

#[cfg(test)]
mod tests {
    use config::{ConfigError, Level, LevelContribution};

    use super::{
        degraded_source_lines, explain_lines, invalid_skill_line,
        resolve_skill_name, OnFailure, SkillResolution,
    };

    fn contribution(discovered: bool, has_body: bool) -> LevelContribution {
        LevelContribution {
            level: Level::Team,
            path: ".luminosity/config.md".to_owned(),
            discovered,
            has_body,
        }
    }

    #[test]
    fn each_contribution_shape_renders_a_distinct_explain_line() {
        let lines = explain_lines(&[
            contribution(false, false),
            contribution(true, false),
            contribution(true, true),
        ]);
        assert_eq!(
            lines,
            vec![
                "team (.luminosity/config.md): not found".to_owned(),
                "team (.luminosity/config.md): discovered, empty body"
                    .to_owned(),
                "team (.luminosity/config.md): discovered, body present"
                    .to_owned(),
            ]
        );
    }

    #[test]
    fn a_degraded_source_tags_each_attempted_path_with_a_reason() {
        let error = ConfigError::UnsafePath {
            path: ".luminosity/skills/x/instructions.md".to_owned(),
        };
        let lines = degraded_source_lines(
            &error,
            [
                ".luminosity/skills/x/instructions.md".to_owned(),
                ".luminosity/skills/x/instructions.local.md".to_owned(),
            ],
        );
        assert_eq!(
            lines,
            vec![
                "team (.luminosity/skills/x/instructions.md): unsafe"
                    .to_owned(),
                "personal (.luminosity/skills/x/instructions.local.md): unsafe"
                    .to_owned(),
            ]
        );
    }

    #[test]
    fn an_invalid_skill_name_explains_under_a_skill_prefix() {
        let error = ConfigError::InvalidSkillName {
            name: "../../etc".to_owned(),
        };
        let line = invalid_skill_line(&error);
        assert!(line.starts_with("skill: "));
        assert!(line.contains("../../etc"));
        assert!(!line.contains("skills/"));
    }

    #[test]
    fn a_valid_skill_name_parses_inside_the_boundary() -> Result<(), ConfigError>
    {
        assert!(matches!(
            resolve_skill_name("configure", OnFailure::Fail)?,
            SkillResolution::Parsed(name) if name.as_str() == "configure"
        ));
        Ok(())
    }

    #[test]
    fn an_invalid_skill_name_degrades_inside_the_boundary(
    ) -> Result<(), ConfigError> {
        assert!(matches!(
            resolve_skill_name("../../etc", OnFailure::Degrade)?,
            SkillResolution::Invalid(_)
        ));
        Ok(())
    }

    #[test]
    fn an_invalid_skill_name_fails_loudly_without_fail_safe() {
        assert!(resolve_skill_name("../../etc", OnFailure::Fail).is_err());
    }
}
