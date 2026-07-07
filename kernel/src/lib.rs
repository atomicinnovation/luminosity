//! Cross-cutting contracts shared across luminosity subdomains.

use std::fmt::{self, Display, Formatter};

/// The error taxonomy luminosity subcommands report through.
///
/// Uninhabited until a command can actually fail.
#[derive(Debug)]
pub enum Error {}

impl Display for Error {
    fn fmt(&self, _formatter: &mut Formatter<'_>) -> fmt::Result {
        // Statically unreachable; the expect self-cleans when a variant lands.
        #[expect(clippy::uninhabited_references)]
        match *self {}
    }
}

impl std::error::Error for Error {}

#[cfg(test)]
mod tests {
    use super::Error;

    // Compile-time contract: kernel::Error is usable as a std error (for `?` /
    // `dyn Error`). Uninhabited today, so it only needs to type-check.
    #[test]
    fn error_satisfies_the_std_error_contract() {
        fn assert_std_error<E: std::error::Error>() {}
        assert_std_error::<Error>();
    }
}
