//! Cross-cutting contracts shared across luminosity subdomains.

use std::fmt::{self, Display, Formatter};

/// The error taxonomy luminosity subcommands report through.
///
/// Deliberately small and dependency-light (std only): it is the shared
/// boundary type, not a dumping ground for every subdomain's private failure
/// modes. A subdomain keeps its own rich error enum (e.g. the launcher's
/// resolution taxonomy) and maps it into this at the dispatch boundary, so a
/// subdomain never compiles against variants it cannot produce.
#[derive(Debug)]
pub enum Error {
    /// A subcommand could not complete; the string is a ready-to-print,
    /// user-facing diagnostic already assembled by the failing subdomain.
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

    // Compile-time contract: kernel::Error is usable as a std error (for `?` /
    // `dyn Error`).
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
