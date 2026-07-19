//! The two configuration levels and their precedence-independent identity.

use std::fmt::{self, Display, Formatter};

/// A configuration level. Personal wins over team when both resolve a key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Level {
    Team,
    Personal,
}

impl Level {
    /// The filename qualifier for this level: empty for team, `.local` for
    /// personal. A document's base name is composed with it by the adapter that
    /// owns the document's path rule.
    #[must_use]
    pub const fn qualifier(self) -> &'static str {
        match self {
            Self::Team => "",
            Self::Personal => ".local",
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
    fn the_team_level_qualifies_nothing() {
        assert_eq!(Level::Team.qualifier(), "");
    }

    #[test]
    fn the_personal_level_qualifies_a_local_file() {
        assert_eq!(Level::Personal.qualifier(), ".local");
    }
}
