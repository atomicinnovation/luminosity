//! Maps the parsed `context` command onto the injected assembler.
//!
//! It owns the byte-exact `## Project Context` block, prints nothing when no
//! context survives assembly, formats the per-level `--explain` diagnostic to
//! stderr without touching stdout, and owns the fail-safe policy: a caller that
//! cannot survive a non-zero exit gets the read failure rendered as a visible
//! stdout notice instead.

use config::{
    AssembleContext, AssembledContext, ConfigError, ContextSource,
    LevelContribution,
};

const PROSE: &str = "\
The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.";

const UNAVAILABLE_PROSE: &str = "\
The project-specific context for this repository could not be read, so none has
been provided. Report the error below to the user and continue without project
context.";

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

/// What a single `context` invocation should print.
#[derive(Debug, Clone, Copy)]
pub struct Options {
    pub explain: bool,
    pub on_failure: OnFailure,
}

#[must_use]
pub fn render(context: &AssembledContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

#[must_use]
pub fn render_unavailable(error: &ConfigError) -> String {
    format!("## Project Context Unavailable\n\n{UNAVAILABLE_PROSE}\n\n{error}")
}

/// Prints the assembled block (nothing when both bodies are empty or absent),
/// plus a per-level stderr diagnostic under `--explain`.
///
/// # Errors
///
/// A [`ConfigError`] when a config body cannot be read and `on_failure` is
/// [`OnFailure::Fail`]; under [`OnFailure::Degrade`] the same error is rendered
/// to stdout and this succeeds.
pub fn run(
    assembler: &impl AssembleContext,
    options: Options,
) -> Result<(), ConfigError> {
    let assembly = match assembler.assemble(&ContextSource::Project) {
        Ok(assembly) => assembly,
        Err(error) if options.on_failure == OnFailure::Degrade => {
            println!("{}", render_unavailable(&error));
            return Ok(());
        }
        Err(error) => return Err(error),
    };
    if let Some(context) = &assembly.context {
        println!("{}", render(context));
    }
    if options.explain {
        for line in explain_lines(&assembly.levels) {
            eprintln!("{line}");
        }
    }
    Ok(())
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
    use config::{AssembledContext, ConfigError, Level, LevelContribution};

    use super::{explain_lines, render, render_unavailable};

    fn contribution(discovered: bool, has_body: bool) -> LevelContribution {
        LevelContribution {
            level: Level::Team,
            path: ".luminosity/config.md".to_owned(),
            discovered,
            has_body,
        }
    }

    #[test]
    fn the_unavailable_notice_names_the_offending_file() {
        let error = ConfigError::MalformedFrontmatter {
            path: ".luminosity/config.md".to_owned(),
            detail: "unterminated frontmatter block".to_owned(),
        };
        assert_eq!(
            render_unavailable(&error),
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
        let notice = render_unavailable(&error);
        assert!(!notice.starts_with("## Project Context\n"));
        assert!(notice.contains("permission denied"));
    }

    #[test]
    fn renders_the_byte_exact_block() {
        let context = AssembledContext {
            body: "team stuff\n\npersonal stuff".to_owned(),
        };
        assert_eq!(
            render(&context),
            "## Project Context\n\n\
             The following project-specific context has been provided. Take \
             this into\naccount when making decisions, selecting approaches, \
             and generating output.\n\n\
             team stuff\n\npersonal stuff"
        );
    }

    #[test]
    fn the_block_ends_at_the_last_body_byte() {
        let context = AssembledContext {
            body: "only".to_owned(),
        };
        assert!(render(&context).ends_with("output.\n\nonly"));
    }

    #[test]
    fn each_contribution_shape_renders_a_distinct_line() {
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
