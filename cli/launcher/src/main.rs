//! The luminosity launcher binary — the composition root: it installs the TLS
//! crypto provider, wires the concrete adapters to the ports, parses the CLI,
//! and dispatches (built-ins in-process, external subcommands via resolve+exec).

use std::path::PathBuf;
use std::process::ExitCode;

use clap::Parser as _;

use luminosity::launch::core::{
    ExternalCommand, ResolutionError, ResolveBinary,
};
use luminosity::launch::dispatch;
use luminosity::launch::inbound::cli::Cli;
use luminosity::launch::outbound::exec::UnixExec;
use luminosity::launch::outbound::resolve::cache_root::{
    self, CacheRootConfig,
};
use luminosity::launch::outbound::resolve::keys::TrustedKeys;
use luminosity::launch::outbound::resolve::{
    FetchVerifyCacheResolver, ResolverConfig,
};
use luminosity::launch::outbound::resolver::{FixtureResolver, FIXTURE_ENV};
use luminosity::launch::outbound::tls::install_crypto_provider;
use luminosity::version::core::VersionReporter;
use luminosity::version::outbound::build_metadata::VergenBuildMetadata;

/// The release-download base URL the real resolver fetches from, pinned to the
/// plugin's own `v{version}` tag. Overridable by `LUMINOSITY_RELEASE_BASE_URL`
/// (the hermetic tests point it at a local mock server).
fn release_base_url() -> String {
    if let Some(override_url) = std::env::var_os("LUMINOSITY_RELEASE_BASE_URL")
    {
        return override_url.to_string_lossy().into_owned();
    }
    let version = env!("CARGO_PKG_VERSION");
    format!(
        "https://github.com/atomicinnovation/luminosity/releases/download/v{version}"
    )
}

/// Builds the real resolver lazily, on the first `resolve` call, so a built-in
/// like `version` never touches the cache root, TLS, or the network — its
/// construction (and its failure modes) are confined to external dispatch.
struct LazyProductionResolver;

impl ResolveBinary for LazyProductionResolver {
    fn resolve(
        &self,
        command: &ExternalCommand,
    ) -> Result<PathBuf, ResolutionError> {
        let cache = cache_root::resolve(&CacheRootConfig::from_env())?;
        let keys = TrustedKeys::embedded()?;
        let config = ResolverConfig::production(release_base_url(), cache);
        FetchVerifyCacheResolver::new(config, keys)?.resolve(command)
    }
}

fn main() -> ExitCode {
    if let Err(error) = install_crypto_provider() {
        eprintln!("luminosity: {error}");
        return ExitCode::FAILURE;
    }
    let cli = Cli::parse();
    let reporter = VersionReporter::new(VergenBuildMetadata);
    let executor = UnixExec;

    // The fixture seam (tests only): when set, external dispatch runs against
    // the in-crate fixture without the network. Production never sets it and
    // always takes the real, lazily-built fetch → verify → cache resolver.
    let outcome = if std::env::var_os(FIXTURE_ENV)
        .is_some_and(|value| !value.is_empty())
    {
        dispatch(&cli, &reporter, &FixtureResolver, &executor)
    } else {
        dispatch(&cli, &reporter, &LazyProductionResolver, &executor)
    };

    match outcome {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("luminosity: {error}");
            ExitCode::FAILURE
        }
    }
}
