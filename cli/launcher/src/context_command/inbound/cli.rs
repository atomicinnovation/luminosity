//! Maps the parsed `context` command onto the injected assembler.
//!
//! The kernel assembles each source into a neutral prompt *fragment*; this edge
//! is where a fragment is wrapped as a *context* block, hence the deliberately
//! context-named renderers and headers over `assembly.fragment`.
//!
//! It owns the byte-exact `## Project Context` and `## Skill-Specific Context`
//! blocks and the fixed project-then-skill order they compose in, prints nothing
//! when neither survives assembly, and formats the `--explain` diagnostic to
//! stderr without touching stdout. The fail-safe boundary it degrades each
//! source through — so an unreadable skill file still leaves the healthy project
//! block standing — lives in [`crate::command_support`], shared with the
//! `instructions` command.

use config::{
    AssembleFragment, ConfigError, Fragment, FragmentSource, SkillName,
};

use crate::command_support::{self, OnFailure, Outcome, SkillResolution};

const PROSE: &str = "\
The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.";

const UNAVAILABLE_PROSE: &str = "\
The project-specific context for this repository could not be read, so none has
been provided. Report the error below to the user and continue without project
context.";

const SKILL_UNAVAILABLE_HEADER: &str = "## Skill-Specific Context Unavailable";

const SKILL_UNAVAILABLE_PROSE: &str = "\
The context specific to this skill could not be read, so none has been provided.
Report the error below to the user and continue without skill-specific context.";

/// What a single `context` invocation should print.
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

/// The two context sources this command renders. Converted to the kernel's
/// [`FragmentSource`] only at the assembly boundary, so the render match stays
/// total without a `SkillInstructions` arm this command never assembles.
enum ContextSource {
    Project,
    Skill(SkillName),
}

impl ContextSource {
    fn fragment_source(&self) -> FragmentSource {
        match self {
            Self::Project => FragmentSource::ProjectContext,
            Self::Skill(name) => FragmentSource::SkillContext(name.clone()),
        }
    }
}

/// One section of the output. `Resolved` pairs a source with its assembly
/// outcome; `Unresolved` is a `--skill` name that never parsed — degraded under
/// `--fail-safe` before any source, and so any path, could exist.
enum Section {
    Resolved(ContextSource, Outcome),
    Unresolved(ConfigError),
}

/// The requested sections in their fixed output order: the project is always
/// requested; the skill only when `--skill` is given.
struct Resolution {
    project: Section,
    skill: Option<Section>,
}

fn skill_prose(skill: &SkillName) -> String {
    format!(
        "\
The following context is specific to the {skill} skill. Apply this
context in addition to any project-wide context above."
    )
}

#[must_use]
pub fn render_project(context: &Fragment) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

#[must_use]
pub fn render_skill(skill: &SkillName, context: &Fragment) -> String {
    let prose = skill_prose(skill);
    format!("## Skill-Specific Context\n\n{prose}\n\n{}", context.body)
}

#[must_use]
pub fn render_project_unavailable(error: &ConfigError) -> String {
    format!("## Project Context Unavailable\n\n{UNAVAILABLE_PROSE}\n\n{error}")
}

/// The error already names the skill file it failed on, so the notice needs no
/// skill-name parameter to be unambiguous.
#[must_use]
pub fn render_skill_unavailable(error: &ConfigError) -> String {
    format!(
        "{SKILL_UNAVAILABLE_HEADER}\n\n{SKILL_UNAVAILABLE_PROSE}\n\n{error}"
    )
}

/// Joins the surviving blocks with one blank line, in a fixed
/// project-then-skill order encoded by the parameters; `None` when neither
/// survives.
#[must_use]
pub fn join_blocks(
    project_block: Option<String>,
    skill_block: Option<String>,
) -> Option<String> {
    let blocks: Vec<String> =
        [project_block, skill_block].into_iter().flatten().collect();
    if blocks.is_empty() {
        None
    } else {
        Some(blocks.join("\n\n"))
    }
}

/// Prints the surviving blocks (nothing when neither survives), plus a
/// per-level stderr diagnostic under `--explain`.
///
/// # Errors
///
/// A [`ConfigError`] when a body cannot be read, or a `--skill` name is
/// invalid, and `on_failure` is [`OnFailure::Fail`]; under
/// [`OnFailure::Degrade`] the same error is rendered to stdout as a notice for
/// that source alone, and this succeeds.
pub fn run(
    assembler: &impl AssembleFragment,
    options: &Options,
) -> Result<(), ConfigError> {
    let Resolution { project, skill } = resolve(assembler, options)?;

    let output = join_blocks(
        section_block(&project),
        skill.as_ref().and_then(section_block),
    );
    if let Some(output) = output {
        println!("{output}");
    }

    if options.explain {
        let lines = command_support::degrade_explain(
            explain(assembler, &project, skill.as_ref()),
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
) -> Result<Resolution, ConfigError> {
    Ok(Resolution {
        project: resolve_project(assembler, options)?,
        skill: resolve_skill(assembler, options)?,
    })
}

fn resolve_project(
    assembler: &impl AssembleFragment,
    options: &Options,
) -> Result<Section, ConfigError> {
    let source = ContextSource::Project;
    let outcome = command_support::assemble(
        assembler,
        &source.fragment_source(),
        options.on_failure,
    )?;
    Ok(Section::Resolved(source, outcome))
}

/// Resolving the skill request adds the one step [`resolve_project`] has no
/// analogue for: parsing the raw `--skill` name, whose failure degrades to a
/// [`Section::Unresolved`] under `--fail-safe`. A parsed name then assembles
/// through the same path as the project.
fn resolve_skill(
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
    let source = ContextSource::Skill(name);
    let outcome = command_support::assemble(
        assembler,
        &source.fragment_source(),
        options.on_failure,
    )?;
    Ok(Some(Section::Resolved(source, outcome)))
}

fn block(source: &ContextSource, outcome: &Outcome) -> Option<String> {
    match outcome {
        Outcome::Assembled(assembly) => {
            assembly.fragment.as_ref().map(|context| match source {
                ContextSource::Project => render_project(context),
                ContextSource::Skill(name) => render_skill(name, context),
            })
        }
        Outcome::Degraded(error) => Some(match source {
            ContextSource::Project => render_project_unavailable(error),
            ContextSource::Skill(_) => render_skill_unavailable(error),
        }),
    }
}

fn section_block(section: &Section) -> Option<String> {
    match section {
        Section::Resolved(source, outcome) => block(source, outcome),
        Section::Unresolved(error) => Some(render_skill_unavailable(error)),
    }
}

fn explain(
    assembler: &impl AssembleFragment,
    project: &Section,
    skill: Option<&Section>,
) -> Result<Vec<String>, ConfigError> {
    let root = assembler.locate(&FragmentSource::ProjectContext)?.root;
    let mut lines = vec![format!("root: {root}")];
    lines.extend(section_lines(assembler, project)?);
    if let Some(skill) = skill {
        lines.extend(section_lines(assembler, skill)?);
    }
    Ok(lines)
}

fn section_lines(
    assembler: &impl AssembleFragment,
    section: &Section,
) -> Result<Vec<String>, ConfigError> {
    match section {
        Section::Resolved(source, outcome) => {
            source_lines(assembler, source, outcome)
        }
        Section::Unresolved(error) => {
            Ok(vec![command_support::invalid_skill_line(error)])
        }
    }
}

fn source_lines(
    assembler: &impl AssembleFragment,
    source: &ContextSource,
    outcome: &Outcome,
) -> Result<Vec<String>, ConfigError> {
    match outcome {
        Outcome::Assembled(assembly) => {
            Ok(command_support::explain_lines(&assembly.levels))
        }
        Outcome::Degraded(error) => {
            let paths = assembler.locate(&source.fragment_source())?.paths;
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
        join_blocks, render_project, render_project_unavailable, render_skill,
        render_skill_unavailable, run, OnFailure, Options,
    };

    fn context(body: &str) -> Fragment {
        Fragment {
            body: body.to_owned(),
        }
    }

    #[test]
    fn the_unavailable_notice_names_the_offending_file() {
        let error = ConfigError::MalformedFrontmatter {
            path: ".luminosity/config.md".to_owned(),
            detail: "unterminated frontmatter block".to_owned(),
        };
        assert_eq!(
            render_project_unavailable(&error),
            "## Project Context Unavailable\n\n\
             The project-specific context for this repository could not be \
             read, so none has\nbeen provided. Report the error below to the \
             user and continue without project\ncontext.\n\n\
             config file '.luminosity/config.md' has malformed frontmatter: \
             unterminated frontmatter block"
        );
    }

    #[test]
    fn the_unavailable_notice_does_not_pose_as_a_context_block() {
        let error = ConfigError::Io {
            path: ".luminosity/config.md".to_owned(),
            detail: "permission denied".to_owned(),
        };
        let notice = render_project_unavailable(&error);
        assert!(!notice.starts_with("## Project Context\n"));
        assert!(notice.contains("permission denied"));
    }

    #[test]
    fn the_skill_unavailable_notice_names_the_skill_file_and_not_project() {
        let error = ConfigError::MalformedFrontmatter {
            path: ".luminosity/skills/configure/context.md".to_owned(),
            detail: "unterminated frontmatter block".to_owned(),
        };
        let notice = render_skill_unavailable(&error);
        assert!(notice.starts_with("## Skill-Specific Context Unavailable\n"));
        assert!(notice.contains("skills/configure/context.md"));
        assert!(!notice.contains("## Project Context"));
    }

    #[test]
    fn renders_the_byte_exact_project_block() {
        assert_eq!(
            render_project(&context("team stuff\n\npersonal stuff")),
            "## Project Context\n\n\
             The following project-specific context has been provided. Take \
             this into\naccount when making decisions, selecting approaches, \
             and generating output.\n\n\
             team stuff\n\npersonal stuff"
        );
    }

    #[test]
    fn renders_the_byte_exact_skill_block() -> Result<(), ConfigError> {
        assert_eq!(
            render_skill(
                &SkillName::parse("configure")?,
                &context("team stuff\n\npersonal stuff")
            ),
            "## Skill-Specific Context\n\n\
             The following context is specific to the configure skill. Apply \
             this\ncontext in addition to any project-wide context above.\n\n\
             team stuff\n\npersonal stuff"
        );
        Ok(())
    }

    #[test]
    fn the_skill_block_interpolates_the_skill_name() -> Result<(), ConfigError>
    {
        let block =
            render_skill(&SkillName::parse("create-plan")?, &context("body"));
        assert!(block.contains("specific to the create-plan skill"));
        Ok(())
    }

    #[test]
    fn the_project_block_ends_at_the_last_body_byte() {
        assert!(render_project(&context("only")).ends_with("output.\n\nonly"));
    }

    #[test]
    fn the_skill_block_ends_at_the_last_body_byte() -> Result<(), ConfigError> {
        let block =
            render_skill(&SkillName::parse("configure")?, &context("only"));
        assert!(block.ends_with("above.\n\nonly"));
        Ok(())
    }

    #[test]
    fn join_blocks_orders_project_before_skill_with_one_blank_line() {
        assert_eq!(
            join_blocks(Some("PROJECT".to_owned()), Some("SKILL".to_owned())),
            Some("PROJECT\n\nSKILL".to_owned())
        );
    }

    #[test]
    fn join_blocks_of_a_single_survivor_is_that_block() {
        assert_eq!(
            join_blocks(Some("PROJECT".to_owned()), None),
            Some("PROJECT".to_owned())
        );
        assert_eq!(
            join_blocks(None, Some("SKILL".to_owned())),
            Some("SKILL".to_owned())
        );
    }

    #[test]
    fn join_blocks_of_neither_is_none() {
        assert_eq!(join_blocks(None, None), None);
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
