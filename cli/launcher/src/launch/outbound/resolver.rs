//! A resolver that resolves every subcommand to a fixture executable.
//!
//! Resolves to the binary named by `LUMINOSITY_RESOLVE_FIXTURE`, exercising
//! dispatch and exec without the network; with the variable unset it reports an
//! "unresolved" diagnostic.

use std::path::PathBuf;

use crate::launch::core::{ExternalCommand, ResolutionError, ResolveBinary};

pub const FIXTURE_ENV: &str = "LUMINOSITY_RESOLVE_FIXTURE";

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
