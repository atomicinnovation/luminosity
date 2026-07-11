//! Assembling the project-context block from the two config-file bodies.
//!
//! The team and personal bodies are trimmed independently, the empty ones
//! dropped, and the survivors joined team-then-personal with a single blank
//! line — so an empty combined result means no context at all. The assembler
//! also reports what each level contributed in the same read pass, using the
//! same trim predicate as the merge, so a level's `has_body` can never disagree
//! with whether it appears in the block.

use crate::error::ConfigError;
use crate::level::Level;
use crate::service::ReadConfigBody;

/// The trimmed, combined team-then-personal body ready to wrap in the block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectContext {
    pub body: String,
}

/// What a single level contributed to the assembly, for the `--explain`
/// diagnostic.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelContribution {
    pub level: Level,
    pub discovered: bool,
    pub has_body: bool,
}

/// The outcome of a single assembly pass: the optional combined context plus a
/// per-level record, ordered `[team, personal]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    pub context: Option<ProjectContext>,
    pub levels: [LevelContribution; 2],
}

/// The operation the assembler offers callers — the driving port.
pub trait AssembleProjectContext {
    /// Reads both levels once and combines their bodies.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when either level's body cannot be read.
    fn assemble(&self) -> Result<Assembly, ConfigError>;
}

/// The application service. Depends only on the [`ReadConfigBody`] driven port.
pub struct ProjectContextAssembler<R> {
    reader: R,
}

impl<R> ProjectContextAssembler<R> {
    pub const fn new(reader: R) -> Self {
        Self { reader }
    }
}

impl<R: ReadConfigBody> AssembleProjectContext for ProjectContextAssembler<R> {
    fn assemble(&self) -> Result<Assembly, ConfigError> {
        let team = self.reader.read_body(Level::Team)?;
        let personal = self.reader.read_body(Level::Personal)?;
        let team_body = team.as_deref().unwrap_or_default();
        let personal_body = personal.as_deref().unwrap_or_default();
        let context = combine(team_body, personal_body)
            .map(|body| ProjectContext { body });
        let levels = [
            contribution(Level::Team, team.is_some(), team_body),
            contribution(Level::Personal, personal.is_some(), personal_body),
        ];
        Ok(Assembly { context, levels })
    }
}

fn contribution(
    level: Level,
    discovered: bool,
    body: &str,
) -> LevelContribution {
    LevelContribution {
        level,
        discovered,
        has_body: !trim_blank_lines(body).is_empty(),
    }
}

fn combine(team: &str, personal: &str) -> Option<String> {
    let parts: Vec<&str> = [team, personal]
        .into_iter()
        .map(trim_blank_lines)
        .filter(|part| !part.is_empty())
        .collect();
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("\n\n"))
    }
}

fn trim_blank_lines(body: &str) -> &str {
    let mut offset = 0;
    let mut first = None;
    let mut last_end = 0;
    for segment in body.split_inclusive('\n') {
        let without_lf = segment.strip_suffix('\n').unwrap_or(segment);
        let content = without_lf.strip_suffix('\r').unwrap_or(without_lf);
        if !content.trim().is_empty() {
            first.get_or_insert(offset);
            last_end = offset + content.len();
        }
        offset += segment.len();
    }
    first.map_or("", |start| &body[start..last_end])
}

#[cfg(test)]
mod tests {
    use super::{
        AssembleProjectContext, Assembly, LevelContribution, ProjectContext,
        ProjectContextAssembler,
    };
    use crate::error::ConfigError;
    use crate::level::Level;
    use crate::service::ReadConfigBody;

    enum BodyState {
        Missing,
        Present(String),
        Failing,
    }

    struct FakeReader {
        team: BodyState,
        personal: BodyState,
    }

    impl FakeReader {
        fn new(team: BodyState, personal: BodyState) -> Self {
            Self { team, personal }
        }
    }

    impl ReadConfigBody for FakeReader {
        fn read_body(
            &self,
            level: Level,
        ) -> Result<Option<String>, ConfigError> {
            let state = match level {
                Level::Team => &self.team,
                Level::Personal => &self.personal,
            };
            match state {
                BodyState::Missing => Ok(None),
                BodyState::Present(body) => Ok(Some(body.clone())),
                BodyState::Failing => Err(ConfigError::Io {
                    path: "fake".to_owned(),
                    detail: "boom".to_owned(),
                }),
            }
        }
    }

    fn present(body: &str) -> BodyState {
        BodyState::Present(body.to_owned())
    }

    fn assemble(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Assembly, ConfigError> {
        ProjectContextAssembler::new(FakeReader::new(team, personal)).assemble()
    }

    fn context(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Option<ProjectContext>, ConfigError> {
        Ok(assemble(team, personal)?.context)
    }

    #[test]
    fn both_absent_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(BodyState::Missing, BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn both_empty_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(present(""), present(""))?, None);
        Ok(())
    }

    #[test]
    fn a_whitespace_only_body_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(present("  \n\t\n \n"), BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn team_only_yields_the_team_body() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("team stuff\n"), BodyState::Missing)?,
            Some(ProjectContext {
                body: "team stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn personal_only_yields_the_personal_body() -> Result<(), ConfigError> {
        assert_eq!(
            context(BodyState::Missing, present("personal stuff\n"))?,
            Some(ProjectContext {
                body: "personal stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn both_join_team_first_with_one_blank_line() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("\nteam\n\n"), present("\n\npersonal\n"))?,
            Some(ProjectContext {
                body: "team\n\npersonal".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn surrounding_blank_lines_are_trimmed() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("\n\n  hello\n"), BodyState::Missing)?,
            Some(ProjectContext {
                body: "  hello".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn interior_blank_lines_and_indentation_are_preserved(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            context(present("\n  a\n\n    b\n\n"), BodyState::Missing)?,
            Some(ProjectContext {
                body: "  a\n\n    b".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn a_crlf_body_strips_its_terminator_and_keeps_interiors(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            context(present("line1\r\nline2\r\n"), BodyState::Missing)?,
            Some(ProjectContext {
                body: "line1\r\nline2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn joining_crlf_bodies_uses_an_lf_separator() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("t1\r\nt2\r\n"), present("p1\r\np2\r\n"))?,
            Some(ProjectContext {
                body: "t1\r\nt2\n\np1\r\np2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn the_combined_body_ends_without_a_terminator() -> Result<(), ConfigError>
    {
        let ProjectContext { body } =
            context(present("team\n"), present("personal\n"))?.ok_or_else(
                || ConfigError::Io {
                    path: "test".to_owned(),
                    detail: "expected a context".to_owned(),
                },
            )?;
        assert!(!body.ends_with('\n'));
        Ok(())
    }

    #[test]
    fn a_team_read_error_propagates() {
        assert!(assemble(BodyState::Failing, present("personal\n")).is_err());
    }

    #[test]
    fn a_personal_read_error_propagates() {
        assert!(assemble(present("team\n"), BodyState::Failing).is_err());
    }

    #[test]
    fn reports_each_level_in_team_then_personal_order(
    ) -> Result<(), ConfigError> {
        let assembly = assemble(present("team\n"), present("personal\n"))?;
        assert_eq!(assembly.levels[0].level, Level::Team);
        assert_eq!(assembly.levels[1].level, Level::Personal);
        Ok(())
    }

    #[test]
    fn reports_discovered_and_has_body_per_level() -> Result<(), ConfigError> {
        let assembly = assemble(BodyState::Missing, present("personal\n"))?;
        assert_eq!(
            assembly.levels[0],
            LevelContribution {
                level: Level::Team,
                discovered: false,
                has_body: false,
            }
        );
        assert_eq!(
            assembly.levels[1],
            LevelContribution {
                level: Level::Personal,
                discovered: true,
                has_body: true,
            }
        );
        Ok(())
    }

    #[test]
    fn a_present_but_whitespace_level_is_discovered_without_a_body(
    ) -> Result<(), ConfigError> {
        let assembly = assemble(present("team\n"), present("   \n"))?;
        assert_eq!(
            assembly.context,
            Some(ProjectContext {
                body: "team".to_owned()
            })
        );
        assert_eq!(
            assembly.levels[1],
            LevelContribution {
                level: Level::Personal,
                discovered: true,
                has_body: false,
            }
        );
        Ok(())
    }
}
