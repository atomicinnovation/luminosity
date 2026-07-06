//! The luminosity launcher binary — the composition root: it installs the TLS
//! crypto provider, wires the concrete adapters to the ports, parses the CLI,
//! and dispatches (built-ins in-process, external subcommands via resolve+exec).

use std::path::PathBuf;
use std::process::ExitCode;

use clap::error::ErrorKind;
use clap::{CommandFactory as _, Parser as _};

use luminosity::launch::core::{
    ExternalCommand, ResolutionError, ResolveBinary,
};
use luminosity::launch::dispatch;
use luminosity::launch::help::external_subcommands_section;
use luminosity::launch::inbound::cli::Cli;
use luminosity::launch::outbound::exec::UnixExec;
use luminosity::launch::outbound::resolve::cache_root::{
    self, CacheRootConfig,
};
use luminosity::launch::outbound::resolve::fetcher::Fetcher;
use luminosity::launch::outbound::resolve::keys::TrustedKeys;
use luminosity::launch::outbound::resolve::{
    FetchVerifyCacheResolver, ResolverConfig,
};
use luminosity::launch::outbound::resolver::{FixtureResolver, FIXTURE_ENV};
use luminosity::launch::outbound::tls::install_crypto_provider;
use luminosity::version::core::VersionReporter;
use luminosity::version::outbound::build_metadata::VergenBuildMetadata;

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

/// Builds the real resolver lazily on the first `resolve` call, so a built-in
/// like `version` never touches the cache root, TLS, or the network.
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

/// Best-effort and offline-tolerant: any failure yields `None` so `--help`
/// still prints the built-in help rather than erroring.
fn help_section() -> Option<String> {
    let keys = TrustedKeys::embedded().ok()?;
    let fetcher = Fetcher::new().ok()?;
    let config = ResolverConfig::production(release_base_url(), PathBuf::new());
    let resolver =
        FetchVerifyCacheResolver::with_fetcher(config, keys, fetcher);
    let manifest = resolver.load_manifest().ok()?;
    external_subcommands_section(&manifest)
}

fn render_augmented_help() -> ExitCode {
    let mut command = Cli::command();
    if let Some(section) = help_section() {
        command = command.after_help(section);
    }
    let _ = command.print_help();
    println!();
    ExitCode::SUCCESS
}

fn run(cli: &Cli) -> Result<(), kernel::Error> {
    let reporter = VersionReporter::new(VergenBuildMetadata);
    let executor = UnixExec;
    if std::env::var_os(FIXTURE_ENV).is_some_and(|value| !value.is_empty()) {
        dispatch(cli, &reporter, &FixtureResolver, &executor)
    } else {
        dispatch(cli, &reporter, &LazyProductionResolver, &executor)
    }
}

fn main() -> ExitCode {
    if let Err(error) = install_crypto_provider() {
        eprintln!("luminosity: {error}");
        return ExitCode::FAILURE;
    }

    // try_parse (not parse) so top-level `--help` can be intercepted and
    // augmented rather than printed by clap.
    let cli = match Cli::try_parse() {
        Ok(cli) => cli,
        Err(error) if error.kind() == ErrorKind::DisplayHelp => {
            return render_augmented_help();
        }
        Err(error) => error.exit(),
    };

    match run(&cli) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("luminosity: {error}");
            ExitCode::FAILURE
        }
    }
}
