//! The configuration error taxonomy.
//!
//! Each variant carries the context its message needs — messages name concrete
//! keys and file paths, never an internal level word alone — and the taxonomy
//! maps into the shared boundary error via `From`.

use std::fmt::{self, Display, Formatter};

use crate::key::Key;
use crate::level::Level;

/// What a conflicting segment already holds, from the perspective of the write
/// that was blocked.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Existing {
    Value,
    Section,
}

impl Existing {
    const fn opposite(self) -> &'static str {
        match self {
            Self::Value => "section",
            Self::Section => "value",
        }
    }
}

impl Display for Existing {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::Value => write!(formatter, "value"),
            Self::Section => write!(formatter, "section"),
        }
    }
}

/// A configuration operation failure.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConfigError {
    NotFound {
        key: Key,
        level: Option<Level>,
    },
    PathConflict {
        key: Key,
        at: String,
        existing: Existing,
    },
    MalformedFrontmatter {
        path: String,
        detail: String,
    },
    Io {
        path: String,
        detail: String,
    },
    InvalidKey {
        key: String,
    },
    InvalidSkillName {
        name: String,
    },
    UnsafePath {
        path: String,
    },
}

impl Display for ConfigError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::NotFound { key, level: None } => {
                write!(formatter, "config key '{key}' is not set")
            }
            Self::NotFound {
                key,
                level: Some(level),
            } => write!(
                formatter,
                "config key '{key}' is not set at level '{level}'"
            ),
            Self::PathConflict { key, at, existing } => write!(
                formatter,
                "cannot set '{key}': '{at}' is a {existing}, not a {}",
                existing.opposite()
            ),
            Self::MalformedFrontmatter { path, detail } => write!(
                formatter,
                "config file '{path}' has malformed frontmatter: {detail}"
            ),
            Self::Io { path, detail } => {
                write!(formatter, "I/O error on config file '{path}': {detail}")
            }
            Self::InvalidKey { key } => write!(
                formatter,
                "invalid config key '{key}': expected dot-separated \
                 non-empty segments"
            ),
            Self::InvalidSkillName { name } => write!(
                formatter,
                "invalid skill name '{name}': expected non-empty \
                 alphanumeric, '-', or '_'"
            ),
            Self::UnsafePath { path } => write!(
                formatter,
                "refused to read '{path}': it resolves outside the \
                 .luminosity directory"
            ),
        }
    }
}

impl std::error::Error for ConfigError {}

impl From<ConfigError> for kernel::Error {
    fn from(error: ConfigError) -> Self {
        Self::Failed(error.to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::{ConfigError, Existing};
    use crate::key::Key;
    use crate::level::Level;

    #[test]
    fn not_found_names_the_key() -> Result<(), ConfigError> {
        let error = ConfigError::NotFound {
            key: Key::parse("core.example")?,
            level: None,
        };
        assert_eq!(error.to_string(), "config key 'core.example' is not set");
        Ok(())
    }

    #[test]
    fn level_scoped_not_found_names_the_level() -> Result<(), ConfigError> {
        let error = ConfigError::NotFound {
            key: Key::parse("core.example")?,
            level: Some(Level::Team),
        };
        assert_eq!(
            error.to_string(),
            "config key 'core.example' is not set at level 'team'"
        );
        Ok(())
    }

    #[test]
    fn descent_conflict_reads_value_not_section() -> Result<(), ConfigError> {
        let error = ConfigError::PathConflict {
            key: Key::parse("core.example")?,
            at: "core".to_owned(),
            existing: Existing::Value,
        };
        assert_eq!(
            error.to_string(),
            "cannot set 'core.example': 'core' is a value, not a section"
        );
        Ok(())
    }

    #[test]
    fn container_conflict_reads_section_not_value() -> Result<(), ConfigError> {
        let error = ConfigError::PathConflict {
            key: Key::parse("net")?,
            at: "net".to_owned(),
            existing: Existing::Section,
        };
        assert_eq!(
            error.to_string(),
            "cannot set 'net': 'net' is a section, not a value"
        );
        Ok(())
    }

    #[test]
    fn malformed_frontmatter_names_the_path_and_detail() {
        let error = ConfigError::MalformedFrontmatter {
            path: ".luminosity/config.local.md".to_owned(),
            detail: "line 3, column 1: did not find expected key".to_owned(),
        };
        assert_eq!(
            error.to_string(),
            "config file '.luminosity/config.local.md' has malformed \
             frontmatter: line 3, column 1: did not find expected key"
        );
    }

    #[test]
    fn io_names_the_path_and_detail() {
        let error = ConfigError::Io {
            path: ".luminosity/config.md".to_owned(),
            detail: "permission denied".to_owned(),
        };
        assert_eq!(
            error.to_string(),
            "I/O error on config file '.luminosity/config.md': \
             permission denied"
        );
    }

    #[test]
    fn invalid_key_names_the_offending_key() {
        let error = ConfigError::InvalidKey { key: String::new() };
        assert_eq!(
            error.to_string(),
            "invalid config key '': expected dot-separated non-empty segments"
        );
    }

    #[test]
    fn invalid_skill_name_names_the_offending_name() {
        let error = ConfigError::InvalidSkillName {
            name: "../../etc".to_owned(),
        };
        assert_eq!(
            error.to_string(),
            "invalid skill name '../../etc': expected non-empty \
             alphanumeric, '-', or '_'"
        );
    }

    #[test]
    fn unsafe_path_names_the_offending_path() {
        let error = ConfigError::UnsafePath {
            path: ".luminosity/skills/configure/context.md".to_owned(),
        };
        assert_eq!(
            error.to_string(),
            "refused to read '.luminosity/skills/configure/context.md': \
             it resolves outside the .luminosity directory"
        );
    }

    #[test]
    fn maps_into_the_kernel_boundary_error() -> Result<(), ConfigError> {
        let error = ConfigError::NotFound {
            key: Key::parse("core.example")?,
            level: None,
        };
        let boundary: kernel::Error = error.into();
        assert_eq!(
            boundary.to_string(),
            "config key 'core.example' is not set"
        );
        Ok(())
    }
}
