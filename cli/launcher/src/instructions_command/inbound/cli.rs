//! Maps the parsed `instructions` command onto the injected assembler.
//!
//! It owns the byte-exact `## Additional Instructions` block, prints nothing
//! when no block survives, and formats the `--explain` diagnostic to stderr. The
//! fail-safe boundary it degrades through lives in [`crate::command_support`],
//! shared with the `context` command — a non-zero exit would discard the prompt
//! a caller splices this stdout into, which is why an invalid `--skill` name is
//! parsed inside that boundary rather than by a clap `value_parser`.
//!
//! Unlike `context`, instructions are always skill-scoped: there is no project
//! source. A bare invocation with no `--skill` prints nothing, and `--explain`
//! for an invalid name reports the name alone with no root to anchor it.

use config::{
    AssembleFragment, ConfigError, Fragment, FragmentSource, SkillName,
};

use crate::command_support::{self, OnFailure, Outcome, SkillResolution};

const UNAVAILABLE_HEADER: &str = "## Additional Instructions Unavailable";

const UNAVAILABLE_PROSE: &str = "\
The additional instructions for this skill could not be read, so none have been
provided. Report the error below to the user and continue without them.";

/// What a single `instructions` invocation should print.
///
/// `skill` is the raw, unvalidated name: parsing it inside the fail-safe
/// boundary rather than at the clap boundary keeps an invalid name inside the
/// fail-safe policy.
#[derive(Debug, Clone)]
pub struct Options {
    pub skill: Option<String>,
    pub explain: bool,
    pub on_failure: OnFailure,
}

/// A resolved `--skill`: a parsed name paired with its assembly outcome, or a
/// name that never parsed — degraded under `--fail-safe` before any path could
/// exist. Absent entirely when no `--skill` was given.
enum Section {
    Resolved(SkillName, Outcome),
    Unresolved(ConfigError),
}

fn instructions_prose(skill: &SkillName) -> String {
    format!(
        "\
The following additional instructions have been provided for the
{skill} skill. Follow these instructions in addition to all
instructions above."
    )
}

#[must_use]
pub fn render_instructions(skill: &SkillName, fragment: &Fragment) -> String {
    let prose = instructions_prose(skill);
    format!("## Additional Instructions\n\n{prose}\n\n{}", fragment.body)
}

/// The error already names the instructions file it failed on, so the notice
/// needs no skill-name parameter to be unambiguous.
#[must_use]
pub fn render_instructions_unavailable(error: &ConfigError) -> String {
    format!("{UNAVAILABLE_HEADER}\n\n{UNAVAILABLE_PROSE}\n\n{error}")
}

/// Prints the block (nothing when none survives), plus a per-level stderr
/// diagnostic under `--explain`.
///
/// # Errors
///
/// A [`ConfigError`] when the body cannot be read, or the `--skill` name is
/// invalid, and `on_failure` is [`OnFailure::Fail`]; under
/// [`OnFailure::Degrade`] the same error is rendered to stdout as a notice, and
/// this succeeds.
pub fn run(
    assembler: &impl AssembleFragment,
    options: &Options,
) -> Result<(), ConfigError> {
    let section = resolve(assembler, options)?;

    if let Some(block) = section.as_ref().and_then(section_block) {
        println!("{block}");
    }

    if options.explain {
        let lines = command_support::degrade_explain(
            explain(assembler, section.as_ref()),
            options.on_failure,
        )?;
        for line in lines {
            eprintln!("{line}");
        }
    }
    Ok(())
}

fn resolve(
    assembler: &impl AssembleFragment,
    options: &Options,
) -> Result<Option<Section>, ConfigError> {
    let Some(raw) = options.skill.as_deref() else {
        return Ok(None);
    };
    let name =
        match command_support::resolve_skill_name(raw, options.on_failure)? {
            SkillResolution::Parsed(name) => name,
            SkillResolution::Invalid(error) => {
                return Ok(Some(Section::Unresolved(error)))
            }
        };
    let outcome = command_support::assemble(
        assembler,
        &FragmentSource::SkillInstructions(name.clone()),
        options.on_failure,
    )?;
    Ok(Some(Section::Resolved(name, outcome)))
}

fn section_block(section: &Section) -> Option<String> {
    match section {
        Section::Resolved(name, outcome) => block(name, outcome),
        Section::Unresolved(error) => {
            Some(render_instructions_unavailable(error))
        }
    }
}

fn block(name: &SkillName, outcome: &Outcome) -> Option<String> {
    match outcome {
        Outcome::Assembled(assembly) => assembly
            .fragment
            .as_ref()
            .map(|fragment| render_instructions(name, fragment)),
        Outcome::Degraded(error) => {
            Some(render_instructions_unavailable(error))
        }
    }
}

fn explain(
    assembler: &impl AssembleFragment,
    section: Option<&Section>,
) -> Result<Vec<String>, ConfigError> {
    match section {
        None => Ok(Vec::new()),
        Some(Section::Unresolved(error)) => {
            Ok(vec![command_support::invalid_skill_line(error)])
        }
        Some(Section::Resolved(name, outcome)) => {
            let source = FragmentSource::SkillInstructions(name.clone());
            let root = assembler.locate(&source)?.root;
            let mut lines = vec![format!("root: {root}")];
            lines.extend(source_lines(assembler, &source, outcome)?);
            Ok(lines)
        }
    }
}

fn source_lines(
    assembler: &impl AssembleFragment,
    source: &FragmentSource,
    outcome: &Outcome,
) -> Result<Vec<String>, ConfigError> {
    match outcome {
        Outcome::Assembled(assembly) => {
            Ok(command_support::explain_lines(&assembly.levels))
        }
        Outcome::Degraded(error) => {
            let paths = assembler.locate(source)?.paths;
            Ok(command_support::degraded_source_lines(error, paths))
        }
    }
}

#[cfg(test)]
mod tests {
    use config::{
        AssembleFragment, Assembly, ConfigError, Fragment, FragmentSource,
        SkillName, SourceLocation,
    };

    use super::{
        explain, render_instructions, render_instructions_unavailable, run,
        Options, Section,
    };
    use crate::command_support::OnFailure;

    fn fragment(body: &str) -> Fragment {
        Fragment {
            body: body.to_owned(),
        }
    }

    #[test]
    fn renders_the_byte_exact_instructions_block() -> Result<(), ConfigError> {
        assert_eq!(
            render_instructions(
                &SkillName::parse("configure")?,
                &fragment("team\n\npersonal")
            ),
            "## Additional Instructions\n\n\
             The following additional instructions have been provided for \
             the\nconfigure skill. Follow these instructions in addition to \
             all\ninstructions above.\n\n\
             team\n\npersonal"
        );
        Ok(())
    }

    #[test]
    fn the_instructions_block_interpolates_the_skill_name(
    ) -> Result<(), ConfigError> {
        let block = render_instructions(
            &SkillName::parse("create-plan")?,
            &fragment("body"),
        );
        assert!(block.contains("for the\ncreate-plan skill. Follow"));
        Ok(())
    }

    #[test]
    fn the_instructions_block_ends_at_the_last_body_byte(
    ) -> Result<(), ConfigError> {
        let block = render_instructions(
            &SkillName::parse("configure")?,
            &fragment("only"),
        );
        assert!(block.ends_with("above.\n\nonly"));
        Ok(())
    }

    #[test]
    fn the_instructions_unavailable_notice_names_the_skill_file() {
        let error = ConfigError::MalformedFrontmatter {
            path: ".luminosity/skills/configure/instructions.md".to_owned(),
            detail: "unterminated frontmatter block".to_owned(),
        };
        let notice = render_instructions_unavailable(&error);
        assert!(notice.starts_with("## Additional Instructions Unavailable\n"));
        assert!(notice.contains("skills/configure/instructions.md"));
        assert!(!notice.contains("## Additional Instructions\n\n"));
    }

    #[test]
    fn an_invalid_skill_name_explains_as_a_name_only_line_with_no_root(
    ) -> Result<(), ConfigError> {
        let section = Section::Unresolved(ConfigError::InvalidSkillName {
            name: "../../etc".to_owned(),
        });
        let lines = explain(&Unlocatable, Some(&section))?;
        assert_eq!(lines.len(), 1);
        assert!(lines[0].starts_with("skill: "));
        assert!(!lines.iter().any(|line| line.starts_with("root:")));
        Ok(())
    }

    #[test]
    fn an_absent_skill_explain_reports_no_levels() -> Result<(), ConfigError> {
        assert!(explain(&Unlocatable, None)?.is_empty());
        Ok(())
    }

    /// Fails every port method, standing in for a broken working directory —
    /// the only way `locate` can fail, since `discover` itself is infallible.
    struct Unlocatable;

    impl Unlocatable {
        fn error() -> ConfigError {
            ConfigError::Io {
                path: ".".to_owned(),
                detail: "no such working directory".to_owned(),
            }
        }
    }

    impl AssembleFragment for Unlocatable {
        fn assemble(
            &self,
            _source: &FragmentSource,
        ) -> Result<Assembly, ConfigError> {
            Err(Self::error())
        }

        fn locate(
            &self,
            _source: &FragmentSource,
        ) -> Result<SourceLocation, ConfigError> {
            Err(Self::error())
        }
    }

    fn options(explain: bool, on_failure: OnFailure) -> Options {
        Options {
            skill: Some("configure".to_owned()),
            explain,
            on_failure,
        }
    }

    #[test]
    fn explain_degrades_with_the_rest_under_fail_safe() {
        assert!(
            run(&Unlocatable, &options(true, OnFailure::Degrade)).is_ok(),
            "an unlocatable root under --explain --fail-safe must exit zero"
        );
    }

    #[test]
    fn explain_still_fails_loudly_without_fail_safe() {
        assert!(run(&Unlocatable, &options(true, OnFailure::Fail)).is_err());
    }
}
