//! The two configuration levels and their precedence-independent identity.

use std::fmt::{self, Display, Formatter};

/// A configuration level. Personal wins over team when both resolve a key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level {
    Team,
    Personal,
}

impl Level {
    /// The base name of the level's file within the `.luminosity/` directory.
    #[must_use]
    pub const fn file_name(self) -> &'static str {
        match self {
            Self::Team => "config.md",
            Self::Personal => "config.local.md",
        }
    }
}

impl Display for Level {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::Team => write!(formatter, "team"),
            Self::Personal => write!(formatter, "personal"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Level;

    #[test]
    fn team_file_is_the_committed_config() {
        assert_eq!(Level::Team.file_name(), "config.md");
    }

    #[test]
    fn personal_file_is_the_git_ignored_config() {
        assert_eq!(Level::Personal.file_name(), "config.local.md");
    }
}
