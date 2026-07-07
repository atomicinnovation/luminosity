//! The production [`BuildMetadata`] adapter — serves the facts vergen baked
//! into the binary (via `cli/build.rs`) as `cargo:rustc-env` vars.

use crate::version::core::BuildMetadata;

/// Reads the build-baked metadata. Git/build facts use `option_env!` so a build
/// that could not resolve them degrades to `"unknown"` instead of failing to
/// compile.
pub struct VergenBuildMetadata;

impl BuildMetadata for VergenBuildMetadata {
    fn crate_version(&self) -> &'static str {
        env!("CARGO_PKG_VERSION")
    }

    fn commit_sha(&self) -> &'static str {
        option_env!("VERGEN_GIT_SHA").unwrap_or("unknown")
    }

    fn build_date(&self) -> &'static str {
        option_env!("VERGEN_BUILD_TIMESTAMP").unwrap_or("unknown")
    }

    fn target_triple(&self) -> &'static str {
        option_env!("VERGEN_CARGO_TARGET_TRIPLE").unwrap_or("unknown")
    }
}
