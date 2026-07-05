//! Cross-cutting contracts shared across luminosity subdomains.

use std::fmt::{self, Display, Formatter};

/// The shared boundary error type. A subdomain keeps its own rich error enum
/// and maps into this at the dispatch boundary, so it never compiles against
/// variants it cannot produce.
#[derive(Debug)]
pub enum Error {
    /// A ready-to-print, user-facing diagnostic assembled by the failing
    /// subdomain.
    Failed(String),
}

impl Display for Error {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match self {
            Self::Failed(message) => write!(formatter, "{message}"),
        }
    }
}

impl std::error::Error for Error {}

#[cfg(test)]
mod tests {
    use super::Error;

    #[test]
    fn error_satisfies_the_std_error_contract() {
        fn assert_std_error<E: std::error::Error>() {}
        assert_std_error::<Error>();
    }

    #[test]
    fn failed_displays_its_diagnostic_verbatim() {
        let error =
            Error::Failed("no asset for aarch64-apple-darwin".to_owned());
        assert_eq!(error.to_string(), "no asset for aarch64-apple-darwin");
    }
}
