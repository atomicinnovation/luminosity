//! Maps the parsed `context` command onto the injected assembler.
//!
//! It owns the byte-exact `## Project Context` block, prints nothing when no
//! context survives assembly, and formats the per-level `--explain` diagnostic
//! to stderr without touching stdout.

use config::{
    AssembleProjectContext, ConfigError, LevelContribution, ProjectContext,
};

const PROSE: &str = "\
The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.";

#[must_use]
pub fn render(context: &ProjectContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

/// Prints the assembled block, or nothing when both bodies are empty or absent.
///
/// # Errors
///
/// A [`ConfigError`] when a config body cannot be read.
pub fn report(
    assembler: &impl AssembleProjectContext,
) -> Result<(), ConfigError> {
    if let Some(context) = assembler.assemble()?.context {
        println!("{}", render(&context));
    }
    Ok(())
}

/// Prints the assembled block on stdout (when any) and a per-level discovery
/// diagnostic on stderr.
///
/// # Errors
///
/// A [`ConfigError`] when a config body cannot be read — reported before any
/// per-level line, so the offending filename is what the user sees.
pub fn report_explain(
    assembler: &impl AssembleProjectContext,
) -> Result<(), ConfigError> {
    let assembly = assembler.assemble()?;
    if let Some(context) = &assembly.context {
        println!("{}", render(context));
    }
    for line in explain_lines(&assembly.levels) {
        eprintln!("{line}");
    }
    Ok(())
}

#[must_use]
pub fn explain_lines(levels: &[LevelContribution]) -> Vec<String> {
    levels.iter().map(explain_line).collect()
}

fn explain_line(contribution: &LevelContribution) -> String {
    let level = contribution.level;
    let file = level.file_name();
    if !contribution.discovered {
        format!("{level} ({file}): not found")
    } else if contribution.has_body {
        format!("{level} ({file}): discovered, body present")
    } else {
        format!("{level} ({file}): discovered, empty body")
    }
}

#[cfg(test)]
mod tests {
    use config::{Level, LevelContribution, ProjectContext};

    use super::{explain_lines, render};

    #[test]
    fn renders_the_byte_exact_block() {
        let context = ProjectContext {
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
        let context = ProjectContext {
            body: "only".to_owned(),
        };
        assert!(render(&context).ends_with("output.\n\nonly"));
    }

    #[test]
    fn each_contribution_shape_renders_a_distinct_line() {
        let absent = LevelContribution {
            level: Level::Team,
            discovered: false,
            has_body: false,
        };
        let empty = LevelContribution {
            level: Level::Team,
            discovered: true,
            has_body: false,
        };
        let present = LevelContribution {
            level: Level::Team,
            discovered: true,
            has_body: true,
        };
        let lines = explain_lines(&[absent, empty, present]);
        assert_eq!(
            lines,
            vec![
                "team (config.md): not found".to_owned(),
                "team (config.md): discovered, empty body".to_owned(),
                "team (config.md): discovered, body present".to_owned(),
            ]
        );
    }
}
