//! A resolver that resolves every subcommand to the executable named by
//! `LUMINOSITY_RESOLVE_FIXTURE`.
//!
//! Lets dispatch and exec be exercised against a test fixture without the
//! network; with the variable unset it reports an "unresolved" diagnostic.

use std::path::PathBuf;

use crate::launch::core::{ExternalCommand, ResolutionError, ResolveBinary};

/// The environment variable naming the executable to resolve to.
pub const FIXTURE_ENV: &str = "LUMINOSITY_RESOLVE_FIXTURE";

/// Resolves every subcommand to the path in [`FIXTURE_ENV`].
pub struct FixtureResolver;

impl ResolveBinary for FixtureResolver {
    fn resolve(
        &self,
        command: &ExternalCommand,
    ) -> Result<PathBuf, ResolutionError> {
        match std::env::var_os(FIXTURE_ENV) {
            Some(path) if !path.is_empty() => Ok(PathBuf::from(path)),
            _ => Err(ResolutionError::Unresolved {
                name: command.name.clone(),
            }),
        }
    }
}
