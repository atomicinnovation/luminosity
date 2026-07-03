//! A transitional resolver adapter for Phase 3.
//!
//! Real resolution — fetch → verify (sha256 + minisign) → cache → return path —
//! lands in Phase 4 as the adapter that replaces this one at the composition
//! root. Until then, external dispatch and exec are proven against the in-crate
//! test fixture via an explicit environment seam: `LUMINOSITY_RESOLVE_FIXTURE`
//! names the executable to resolve every subcommand to. With the seam unset,
//! external subcommands report an honest "unresolved" diagnostic (real
//! resolution is not wired yet), so this ships harmlessly in the Phase 3
//! intermediate state.

use std::path::PathBuf;

use crate::launch::core::{ExternalCommand, ResolutionError, ResolveBinary};

/// The environment seam naming the fixture executable Phase 3 resolves to.
pub const FIXTURE_ENV: &str = "LUMINOSITY_RESOLVE_FIXTURE";

/// Resolves every subcommand to the path in [`FIXTURE_ENV`] (Phase 3 only).
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
