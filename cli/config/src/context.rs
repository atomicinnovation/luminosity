//! Assembling any two-level `.luminosity` document's context block from its
//! team and personal bodies.
//!
//! The document is named by a [`ContextSource`]; the assembly rule is the same
//! whichever one it is. The two bodies are trimmed independently, the empty ones
//! dropped, and the survivors joined team-then-personal with a single blank
//! line — so an empty combined result means no context at all. The assembler
//! also reports what each level contributed in the same read pass, using the
//! same trim predicate as the merge, so a level's `has_body` can never disagree
//! with whether it appears in the block.

use crate::error::ConfigError;
use crate::level::Level;
use crate::source::ContextSource;

/// A trimmed, combined team-then-personal body ready to wrap in a block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssembledContext {
    pub body: String,
}

/// What a single level contributed to the assembly, and the path it was read
/// from, for the `--explain` diagnostic.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelContribution {
    pub level: Level,
    pub path: String,
    pub discovered: bool,
    pub has_body: bool,
}

/// The outcome of a single assembly pass: the optional combined context plus a
/// per-level record, ordered `[team, personal]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    pub context: Option<AssembledContext>,
    pub levels: [LevelContribution; 2],
}

/// One level's read: the path it was read from, and its body when the file was
/// present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelBody {
    pub path: String,
    pub body: Option<String>,
}

/// Reads a single level of a single document — a driven port.
pub trait ReadContextBody {
    /// Returns `source`'s body at `level` (absent when the file is), and the
    /// path it read.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when a present file cannot be read, cannot be split,
    /// or resolves outside the `.luminosity` directory.
    fn read_body(
        &self,
        source: &ContextSource,
        level: Level,
    ) -> Result<LevelBody, ConfigError>;
}

/// The operation the assembler offers callers — the driving port.
pub trait AssembleContext {
    /// Reads both of `source`'s levels once and combines their bodies.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when either level cannot be read.
    fn assemble(&self, source: &ContextSource)
        -> Result<Assembly, ConfigError>;
}

/// The application service. Depends only on the [`ReadContextBody`] driven port.
pub struct ContextAssembler<R> {
    reader: R,
}

impl<R> ContextAssembler<R> {
    pub const fn new(reader: R) -> Self {
        Self { reader }
    }
}

impl<R: ReadContextBody> AssembleContext for ContextAssembler<R> {
    fn assemble(
        &self,
        source: &ContextSource,
    ) -> Result<Assembly, ConfigError> {
        let team = self.reader.read_body(source, Level::Team)?;
        let personal = self.reader.read_body(source, Level::Personal)?;
        let team_body = team.body.as_deref().unwrap_or_default();
        let personal_body = personal.body.as_deref().unwrap_or_default();
        let context = combine(team_body, personal_body)
            .map(|body| AssembledContext { body });
        let levels = [
            contribution(Level::Team, &team),
            contribution(Level::Personal, &personal),
        ];
        Ok(Assembly { context, levels })
    }
}

fn contribution(level: Level, read: &LevelBody) -> LevelContribution {
    let body = read.body.as_deref().unwrap_or_default();
    LevelContribution {
        level,
        path: read.path.clone(),
        discovered: read.body.is_some(),
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
        AssembleContext, AssembledContext, Assembly, ContextAssembler,
        LevelBody, LevelContribution, ReadContextBody,
    };
    use crate::error::ConfigError;
    use crate::level::Level;
    use crate::source::{ContextSource, SkillName};

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

    fn path_of(source: &ContextSource, level: Level) -> String {
        let base = match source {
            ContextSource::Project => ".luminosity/config".to_owned(),
            ContextSource::Skill(name) => {
                format!(".luminosity/skills/{name}/context")
            }
        };
        format!("{base}{}.md", level.qualifier())
    }

    impl ReadContextBody for FakeReader {
        fn read_body(
            &self,
            source: &ContextSource,
            level: Level,
        ) -> Result<LevelBody, ConfigError> {
            let state = match level {
                Level::Team => &self.team,
                Level::Personal => &self.personal,
            };
            let body = match state {
                BodyState::Missing => None,
                BodyState::Present(body) => Some(body.clone()),
                BodyState::Failing => {
                    return Err(ConfigError::Io {
                        path: "fake".to_owned(),
                        detail: "boom".to_owned(),
                    })
                }
            };
            Ok(LevelBody {
                path: path_of(source, level),
                body,
            })
        }
    }

    fn present(body: &str) -> BodyState {
        BodyState::Present(body.to_owned())
    }

    fn skill() -> Result<ContextSource, ConfigError> {
        Ok(ContextSource::Skill(SkillName::parse("configure")?))
    }

    fn assemble_source(
        source: &ContextSource,
        team: BodyState,
        personal: BodyState,
    ) -> Result<Assembly, ConfigError> {
        ContextAssembler::new(FakeReader::new(team, personal)).assemble(source)
    }

    fn assemble(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Assembly, ConfigError> {
        assemble_source(&ContextSource::Project, team, personal)
    }

    fn context(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Option<AssembledContext>, ConfigError> {
        Ok(assemble(team, personal)?.context)
    }

    #[test]
    fn both_levels_absent_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(BodyState::Missing, BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn both_levels_empty_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(present(""), present(""))?, None);
        Ok(())
    }

    #[test]
    fn a_whitespace_only_level_is_no_context() -> Result<(), ConfigError> {
        assert_eq!(context(present("  \n\t\n \n"), BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn team_only_yields_the_team_body() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("team stuff\n"), BodyState::Missing)?,
            Some(AssembledContext {
                body: "team stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn personal_only_yields_the_personal_body() -> Result<(), ConfigError> {
        assert_eq!(
            context(BodyState::Missing, present("personal stuff\n"))?,
            Some(AssembledContext {
                body: "personal stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn both_levels_join_team_first_with_one_blank_line(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            context(present("\nteam\n\n"), present("\n\npersonal\n"))?,
            Some(AssembledContext {
                body: "team\n\npersonal".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn surrounding_blank_lines_are_trimmed() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("\n\n  hello\n"), BodyState::Missing)?,
            Some(AssembledContext {
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
            Some(AssembledContext {
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
            Some(AssembledContext {
                body: "line1\r\nline2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn joining_crlf_bodies_uses_an_lf_separator() -> Result<(), ConfigError> {
        assert_eq!(
            context(present("t1\r\nt2\r\n"), present("p1\r\np2\r\n"))?,
            Some(AssembledContext {
                body: "t1\r\nt2\n\np1\r\np2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn the_combined_body_ends_without_a_terminator() -> Result<(), ConfigError>
    {
        let AssembledContext { body } =
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
    fn reports_discovered_has_body_and_path_per_level(
    ) -> Result<(), ConfigError> {
        let assembly = assemble(BodyState::Missing, present("personal\n"))?;
        assert_eq!(
            assembly.levels[0],
            LevelContribution {
                level: Level::Team,
                path: ".luminosity/config.md".to_owned(),
                discovered: false,
                has_body: false,
            }
        );
        assert_eq!(
            assembly.levels[1],
            LevelContribution {
                level: Level::Personal,
                path: ".luminosity/config.local.md".to_owned(),
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
            Some(AssembledContext {
                body: "team".to_owned()
            })
        );
        assert_eq!(
            assembly.levels[1],
            LevelContribution {
                level: Level::Personal,
                path: ".luminosity/config.local.md".to_owned(),
                discovered: true,
                has_body: false,
            }
        );
        Ok(())
    }

    #[test]
    fn assembles_a_skill_source_identically_to_a_project_source(
    ) -> Result<(), ConfigError> {
        for source in [ContextSource::Project, skill()?] {
            let assembly = assemble_source(
                &source,
                present("\nteam\n\n"),
                present("\n\npersonal\n"),
            )?;
            assert_eq!(
                assembly.context,
                Some(AssembledContext {
                    body: "team\n\npersonal".to_owned()
                })
            );
            assert_eq!(assembly.levels[0].level, Level::Team);
            assert_eq!(assembly.levels[1].level, Level::Personal);
        }
        Ok(())
    }

    #[test]
    fn reports_the_skill_paths_for_a_skill_source() -> Result<(), ConfigError> {
        let assembly =
            assemble_source(&skill()?, present("team\n"), BodyState::Missing)?;
        assert_eq!(
            assembly.levels[0].path,
            ".luminosity/skills/configure/context.md"
        );
        assert_eq!(
            assembly.levels[1].path,
            ".luminosity/skills/configure/context.local.md"
        );
        Ok(())
    }
}
