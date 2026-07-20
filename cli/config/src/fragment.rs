//! Assembling a two-level `.luminosity` document into a single prompt fragment
//! from its team and personal bodies.
//!
//! A *prompt fragment* is a two-level-combined, frontmatter-stripped piece of
//! userspace-authored content bound for a skill's prompt. The document is named
//! by a [`FragmentSource`]; the assembly rule is the same whichever one it is.
//! The two bodies are trimmed independently, the empty ones dropped, and the
//! survivors joined team-then-personal with a single blank line — so an empty
//! combined result means no fragment at all. The assembler also reports what each
//! level contributed in the same read pass, using the same trim predicate as the
//! merge, so a level's `has_body` can never disagree with whether it appears in
//! the fragment.

use crate::error::ConfigError;
use crate::level::Level;
use crate::source::FragmentSource;

/// A trimmed, combined team-then-personal body ready to wrap in a block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Fragment {
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

/// The outcome of a single assembly pass: the optional combined fragment plus a
/// per-level record, ordered `[team, personal]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    pub fragment: Option<Fragment>,
    pub levels: [LevelContribution; 2],
}

/// One level's read: the path it was read from, and its body when the file was
/// present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelBody {
    pub path: String,
    pub body: Option<String>,
}

/// Where a source's two levels live: the project root, and each level's path
/// relative to it, ordered `[team, personal]`.
///
/// Answers "which files would have been read" for a diagnostic that must name
/// them even when the read failed and yielded no [`Assembly`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceLocation {
    pub root: String,
    pub paths: [String; 2],
}

/// Reads a single level of a single document — a driven port.
pub trait ReadFragmentBody {
    /// Returns `source`'s body at `level` (absent when the file is), and the
    /// path it read.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when a present file cannot be read, cannot be split,
    /// or resolves outside the `.luminosity` directory.
    fn read_body(
        &self,
        source: &FragmentSource,
        level: Level,
    ) -> Result<LevelBody, ConfigError>;

    /// Reports where `source`'s levels live, without reading them.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when the project root cannot be discovered.
    fn locate(
        &self,
        source: &FragmentSource,
    ) -> Result<SourceLocation, ConfigError>;
}

/// The operations the assembler offers callers — the driving port.
pub trait AssembleFragment {
    /// Reads both of `source`'s levels once and combines their bodies.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when either level cannot be read.
    fn assemble(
        &self,
        source: &FragmentSource,
    ) -> Result<Assembly, ConfigError>;

    /// Reports where `source`'s levels live, without reading them.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when the project root cannot be discovered.
    fn locate(
        &self,
        source: &FragmentSource,
    ) -> Result<SourceLocation, ConfigError>;
}

/// The application service. Depends only on the [`ReadFragmentBody`] driven port.
pub struct FragmentAssembler<R> {
    reader: R,
}

impl<R> FragmentAssembler<R> {
    pub const fn new(reader: R) -> Self {
        Self { reader }
    }
}

impl<R: ReadFragmentBody> AssembleFragment for FragmentAssembler<R> {
    fn assemble(
        &self,
        source: &FragmentSource,
    ) -> Result<Assembly, ConfigError> {
        let team = self.reader.read_body(source, Level::Team)?;
        let personal = self.reader.read_body(source, Level::Personal)?;
        let team_body = team.body.as_deref().unwrap_or_default();
        let personal_body = personal.body.as_deref().unwrap_or_default();
        let fragment =
            combine(team_body, personal_body).map(|body| Fragment { body });
        let levels = [
            contribution(Level::Team, &team),
            contribution(Level::Personal, &personal),
        ];
        Ok(Assembly { fragment, levels })
    }

    fn locate(
        &self,
        source: &FragmentSource,
    ) -> Result<SourceLocation, ConfigError> {
        self.reader.locate(source)
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
        AssembleFragment, Assembly, Fragment, FragmentAssembler, LevelBody,
        LevelContribution, ReadFragmentBody, SourceLocation,
    };
    use crate::error::ConfigError;
    use crate::level::Level;
    use crate::source::{FragmentSource, SkillName};

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

    fn path_of(source: &FragmentSource, level: Level) -> String {
        let base = match source {
            FragmentSource::Project => ".luminosity/config".to_owned(),
            FragmentSource::Skill(name) => {
                format!(".luminosity/skills/{name}/context")
            }
        };
        format!("{base}{}.md", level.qualifier())
    }

    impl ReadFragmentBody for FakeReader {
        fn read_body(
            &self,
            source: &FragmentSource,
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

        fn locate(
            &self,
            source: &FragmentSource,
        ) -> Result<SourceLocation, ConfigError> {
            Ok(SourceLocation {
                root: "/root".to_owned(),
                paths: [Level::Team, Level::Personal]
                    .map(|level| path_of(source, level)),
            })
        }
    }

    fn present(body: &str) -> BodyState {
        BodyState::Present(body.to_owned())
    }

    fn skill() -> Result<FragmentSource, ConfigError> {
        Ok(FragmentSource::Skill(SkillName::parse("configure")?))
    }

    fn assemble_source(
        source: &FragmentSource,
        team: BodyState,
        personal: BodyState,
    ) -> Result<Assembly, ConfigError> {
        FragmentAssembler::new(FakeReader::new(team, personal)).assemble(source)
    }

    fn assemble(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Assembly, ConfigError> {
        assemble_source(&FragmentSource::Project, team, personal)
    }

    fn fragment(
        team: BodyState,
        personal: BodyState,
    ) -> Result<Option<Fragment>, ConfigError> {
        Ok(assemble(team, personal)?.fragment)
    }

    #[test]
    fn both_levels_absent_is_no_fragment() -> Result<(), ConfigError> {
        assert_eq!(fragment(BodyState::Missing, BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn both_levels_empty_is_no_fragment() -> Result<(), ConfigError> {
        assert_eq!(fragment(present(""), present(""))?, None);
        Ok(())
    }

    #[test]
    fn a_whitespace_only_level_is_no_fragment() -> Result<(), ConfigError> {
        assert_eq!(fragment(present("  \n\t\n \n"), BodyState::Missing)?, None);
        Ok(())
    }

    #[test]
    fn team_only_yields_the_team_body() -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("team stuff\n"), BodyState::Missing)?,
            Some(Fragment {
                body: "team stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn personal_only_yields_the_personal_body() -> Result<(), ConfigError> {
        assert_eq!(
            fragment(BodyState::Missing, present("personal stuff\n"))?,
            Some(Fragment {
                body: "personal stuff".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn both_levels_join_team_first_with_one_blank_line(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("\nteam\n\n"), present("\n\npersonal\n"))?,
            Some(Fragment {
                body: "team\n\npersonal".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn surrounding_blank_lines_are_trimmed() -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("\n\n  hello\n"), BodyState::Missing)?,
            Some(Fragment {
                body: "  hello".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn interior_blank_lines_and_indentation_are_preserved(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("\n  a\n\n    b\n\n"), BodyState::Missing)?,
            Some(Fragment {
                body: "  a\n\n    b".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn a_crlf_body_strips_its_terminator_and_keeps_interiors(
    ) -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("line1\r\nline2\r\n"), BodyState::Missing)?,
            Some(Fragment {
                body: "line1\r\nline2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn joining_crlf_bodies_uses_an_lf_separator() -> Result<(), ConfigError> {
        assert_eq!(
            fragment(present("t1\r\nt2\r\n"), present("p1\r\np2\r\n"))?,
            Some(Fragment {
                body: "t1\r\nt2\n\np1\r\np2".to_owned()
            })
        );
        Ok(())
    }

    #[test]
    fn the_combined_body_ends_without_a_terminator() -> Result<(), ConfigError>
    {
        let Fragment { body } =
            fragment(present("team\n"), present("personal\n"))?.ok_or_else(
                || ConfigError::Io {
                    path: "test".to_owned(),
                    detail: "expected a fragment".to_owned(),
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
            assembly.fragment,
            Some(Fragment {
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
        for source in [FragmentSource::Project, skill()?] {
            let assembly = assemble_source(
                &source,
                present("\nteam\n\n"),
                present("\n\npersonal\n"),
            )?;
            assert_eq!(
                assembly.fragment,
                Some(Fragment {
                    body: "team\n\npersonal".to_owned()
                })
            );
            assert_eq!(assembly.levels[0].level, Level::Team);
            assert_eq!(assembly.levels[1].level, Level::Personal);
        }
        Ok(())
    }

    #[test]
    fn locating_a_source_reports_its_root_and_both_paths(
    ) -> Result<(), ConfigError> {
        let assembler = FragmentAssembler::new(FakeReader::new(
            BodyState::Missing,
            BodyState::Missing,
        ));
        assert_eq!(
            assembler.locate(&skill()?)?,
            SourceLocation {
                root: "/root".to_owned(),
                paths: [
                    ".luminosity/skills/configure/context.md".to_owned(),
                    ".luminosity/skills/configure/context.local.md".to_owned(),
                ],
            }
        );
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
