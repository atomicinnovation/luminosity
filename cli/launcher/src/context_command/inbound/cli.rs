//! Maps the parsed `context` command onto the injected assembler.
//!
//! It owns the byte-exact `## Project Context` and `## Skill-Specific Context`
//! blocks and the fixed project-then-skill order they compose in, prints nothing
//! when neither survives assembly, formats the `--explain` diagnostic to stderr
//! without touching stdout, and owns the fail-safe policy — which degrades each
//! source *independently*, so an unreadable skill file still leaves the healthy
//! project block standing, under a notice that names the skill file rather than
//! the config one.
//!
//! A caller that splices this stdout into a prompt cannot survive a non-zero
//! exit — it discards the whole prompt — which is why an invalid `--skill` name
//! is validated here, inside the fail-safe boundary, and not by a clap
//! `value_parser` that would exit before the boundary is reached.

use config::{
    AssembleContext, AssembledContext, ConfigError, ContextSource, Level,
    LevelContribution, SkillName,
};

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

/// What a single `context` invocation should print. `skill` is the raw,
/// unvalidated name: parsing it here rather than at the clap boundary keeps an
/// invalid name inside the fail-safe policy.
#[derive(Debug, Clone)]
pub struct Options {
    pub skill: Option<String>,
    pub explain: bool,
    pub on_failure: OnFailure,
}

/// What assembling one source yielded: its levels, or the error a `--fail-safe`
/// run absorbed.
enum Outcome {
    Assembled(config::Assembly),
    Degraded(ConfigError),
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
pub fn render_project(context: &AssembledContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

#[must_use]
pub fn render_skill(skill: &SkillName, context: &AssembledContext) -> String {
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
    assembler: &impl AssembleContext,
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
        for line in explain(assembler, &project, skill.as_ref())? {
            eprintln!("{line}");
        }
    }
    Ok(())
}

fn assemble(
    assembler: &impl AssembleContext,
    source: &ContextSource,
    options: &Options,
) -> Result<Outcome, ConfigError> {
    match assembler.assemble(source) {
        Ok(assembly) => Ok(Outcome::Assembled(assembly)),
        Err(error) if options.on_failure == OnFailure::Degrade => {
            Ok(Outcome::Degraded(error))
        }
        Err(error) => Err(error),
    }
}

fn resolve(
    assembler: &impl AssembleContext,
    options: &Options,
) -> Result<Resolution, ConfigError> {
    Ok(Resolution {
        project: resolve_project(assembler, options)?,
        skill: resolve_skill(assembler, options)?,
    })
}

fn resolve_project(
    assembler: &impl AssembleContext,
    options: &Options,
) -> Result<Section, ConfigError> {
    let source = ContextSource::Project;
    let outcome = assemble(assembler, &source, options)?;
    Ok(Section::Resolved(source, outcome))
}

/// Resolving the skill request adds the one step [`resolve_project`] has no
/// analogue for: parsing the raw `--skill` name, whose failure degrades to a
/// [`Section::Unresolved`] under `--fail-safe`. A parsed name then assembles
/// through the same [`assemble`] path as the project.
fn resolve_skill(
    assembler: &impl AssembleContext,
    options: &Options,
) -> Result<Option<Section>, ConfigError> {
    let Some(raw) = options.skill.as_deref() else {
        return Ok(None);
    };
    let name = match SkillName::parse(raw) {
        Ok(name) => name,
        Err(error) if options.on_failure == OnFailure::Degrade => {
            return Ok(Some(Section::Unresolved(error)))
        }
        Err(error) => return Err(error),
    };
    let source = ContextSource::Skill(name);
    let outcome = assemble(assembler, &source, options)?;
    Ok(Some(Section::Resolved(source, outcome)))
}

fn block(source: &ContextSource, outcome: &Outcome) -> Option<String> {
    match outcome {
        Outcome::Assembled(assembly) => {
            assembly.context.as_ref().map(|context| match source {
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
    assembler: &impl AssembleContext,
    project: &Section,
    skill: Option<&Section>,
) -> Result<Vec<String>, ConfigError> {
    let root = assembler.locate(&ContextSource::Project)?.root;
    let mut lines = vec![format!("root: {root}")];
    lines.extend(section_lines(assembler, project)?);
    if let Some(skill) = skill {
        lines.extend(section_lines(assembler, skill)?);
    }
    Ok(lines)
}

fn section_lines(
    assembler: &impl AssembleContext,
    section: &Section,
) -> Result<Vec<String>, ConfigError> {
    match section {
        Section::Resolved(source, outcome) => {
            source_lines(assembler, source, outcome)
        }
        // No path was ever constructed for a name that did not parse, and
        // fabricating one would be the very path-rebuild the design forbids.
        Section::Unresolved(error) => Ok(vec![error.to_string()]),
    }
}

fn source_lines(
    assembler: &impl AssembleContext,
    source: &ContextSource,
    outcome: &Outcome,
) -> Result<Vec<String>, ConfigError> {
    match outcome {
        Outcome::Assembled(assembly) => Ok(explain_lines(&assembly.levels)),
        Outcome::Degraded(error) => {
            let state = degraded_state(error);
            let paths = assembler.locate(source)?.paths;
            Ok([Level::Team, Level::Personal]
                .into_iter()
                .zip(paths)
                .map(|(level, path)| format!("{level} ({path}): {state}"))
                .collect())
        }
    }
}

const fn degraded_state(error: &ConfigError) -> &'static str {
    match error {
        ConfigError::UnsafePath { .. } => "unsafe",
        _ => "unreadable",
    }
}

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

#[cfg(test)]
mod tests {
    use config::{
        AssembledContext, ConfigError, Level, LevelContribution, SkillName,
    };

    use super::{
        explain_lines, join_blocks, render_project, render_project_unavailable,
        render_skill, render_skill_unavailable,
    };

    fn contribution(discovered: bool, has_body: bool) -> LevelContribution {
        LevelContribution {
            level: Level::Team,
            path: ".luminosity/config.md".to_owned(),
            discovered,
            has_body,
        }
    }

    fn context(body: &str) -> AssembledContext {
        AssembledContext {
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
}
