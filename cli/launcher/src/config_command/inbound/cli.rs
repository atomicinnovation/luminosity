//! Maps the parsed `config` action onto the injected core service.
//!
//! It renders a resolved value to stdout, and owns the not-found→error policy:
//! the core returns `Resolved::Absent`, and this adapter maps it to
//! `ConfigError::NotFound` with the key and any `--level`.

use config::{ConfigAccess, ConfigError, Key, Level, Resolved, Scalar};

use crate::launch::inbound::cli::ConfigAction;

/// # Errors
///
/// A [`ConfigError`] when the key is invalid, a level cannot be read, the
/// requested value is not set, or a write conflicts or fails.
pub fn run(
    access: &impl ConfigAccess,
    action: &ConfigAction,
) -> Result<(), ConfigError> {
    match action {
        ConfigAction::Get { key, level } => {
            get(access, key, level.map(Into::into))
        }
        ConfigAction::Set { key, value, level } => {
            set(access, key, value, level.map(Into::into))
        }
    }
}

fn get(
    access: &impl ConfigAccess,
    raw_key: &str,
    level: Option<Level>,
) -> Result<(), ConfigError> {
    let key = Key::parse(raw_key)?;
    match access.get(&key, level)? {
        Resolved::Found(scalar) => {
            println!("{}", render(&scalar));
            Ok(())
        }
        Resolved::Absent => Err(ConfigError::NotFound { key, level }),
    }
}

fn set(
    access: &impl ConfigAccess,
    raw_key: &str,
    value: &str,
    level: Option<Level>,
) -> Result<(), ConfigError> {
    let key = Key::parse(raw_key)?;
    access.set(&key, value, level.unwrap_or(Level::Personal))
}

#[must_use]
pub fn render(scalar: &Scalar) -> String {
    match scalar {
        Scalar::String(value) => value.clone(),
        Scalar::Bool(value) => value.to_string(),
        Scalar::Int(value) => value.to_string(),
        Scalar::Float(value) => value.to_string(),
        Scalar::Null => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use config::Scalar;

    use super::render;

    #[test]
    fn renders_a_string_verbatim() {
        assert_eq!(render(&Scalar::String("hello".to_owned())), "hello");
    }

    #[test]
    fn renders_a_bool() {
        assert_eq!(render(&Scalar::Bool(true)), "true");
        assert_eq!(render(&Scalar::Bool(false)), "false");
    }

    #[test]
    fn renders_an_int_as_decimal() {
        assert_eq!(render(&Scalar::Int(42)), "42");
        assert_eq!(render(&Scalar::Int(-7)), "-7");
    }

    #[test]
    fn renders_a_float_in_canonical_form() {
        assert_eq!(render(&Scalar::Float(1.5)), "1.5");
    }

    #[test]
    fn renders_null_as_the_empty_string() {
        assert_eq!(render(&Scalar::Null), "");
    }
}
