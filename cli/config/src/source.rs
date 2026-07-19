//! Which two-level `.luminosity` document an assembly reads, and the validated
//! skill name that identifies a per-skill one.
//!
//! A skill name is parsed under an allow-list rather than a deny-list: a
//! deny-list of the separators and traversal sequences known today invites the
//! next one, whereas the allow-list rejects path separators, `.`, `..`, Unicode
//! lookalikes, and NUL bytes by construction — so a name is always safe to place
//! in a filesystem path.

use std::fmt::{self, Display, Formatter};

use crate::error::ConfigError;

/// A validated skill name — the identity a skill is invoked by, safe to place
/// in a filesystem path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SkillName(String);

impl SkillName {
    /// Parses a skill name under an allow-list: non-empty, ASCII alphanumeric,
    /// `-`, or `_`.
    ///
    /// # Errors
    ///
    /// [`ConfigError::InvalidSkillName`] when `raw` is empty or carries any
    /// character outside the allow-list.
    pub fn parse(raw: &str) -> Result<Self, ConfigError> {
        let permitted = |character: char| {
            character.is_ascii_alphanumeric()
                || character == '-'
                || character == '_'
        };
        if raw.is_empty() || !raw.chars().all(permitted) {
            return Err(ConfigError::InvalidSkillName {
                name: raw.to_owned(),
            });
        }
        Ok(Self(raw.to_owned()))
    }

    /// The validated name, for an adapter composing it into a path.
    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl Display for SkillName {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.0)
    }
}

/// Which two-level `.luminosity` document is being assembled.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContextSource {
    Project,
    Skill(SkillName),
}

#[cfg(test)]
mod tests {
    use super::SkillName;
    use crate::error::ConfigError;

    fn rejected(raw: &str) -> bool {
        matches!(
            SkillName::parse(raw),
            Err(ConfigError::InvalidSkillName { name }) if name == raw
        )
    }

    #[test]
    fn a_bare_name_parses() -> Result<(), ConfigError> {
        assert_eq!(SkillName::parse("configure")?.as_str(), "configure");
        Ok(())
    }

    #[test]
    fn a_hyphenated_name_parses() -> Result<(), ConfigError> {
        assert_eq!(SkillName::parse("create-plan")?.as_str(), "create-plan");
        Ok(())
    }

    #[test]
    fn an_underscored_name_parses() -> Result<(), ConfigError> {
        assert_eq!(SkillName::parse("create_plan9")?.as_str(), "create_plan9");
        Ok(())
    }

    #[test]
    fn an_empty_name_is_rejected() {
        assert!(rejected(""));
    }

    #[test]
    fn a_name_with_a_path_separator_is_rejected() {
        assert!(rejected("a/b"));
        assert!(rejected("a\\b"));
    }

    #[test]
    fn a_parent_directory_traversal_is_rejected() {
        assert!(rejected(".."));
        assert!(rejected("../../etc"));
    }

    #[test]
    fn a_name_with_a_dot_is_rejected() {
        assert!(rejected("."));
        assert!(rejected("configure.local"));
    }

    #[test]
    fn a_name_with_a_brace_is_rejected() {
        assert!(rejected("{skill}"));
    }

    #[test]
    fn a_name_with_whitespace_is_rejected() {
        assert!(rejected("my skill"));
    }

    #[test]
    fn a_unicode_lookalike_is_rejected() {
        assert!(rejected("conﬁgure"));
    }

    #[test]
    fn display_round_trips_the_name() -> Result<(), ConfigError> {
        assert_eq!(SkillName::parse("configure")?.to_string(), "configure");
        Ok(())
    }
}
