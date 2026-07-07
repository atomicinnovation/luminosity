//! The luminosity launcher binary — the composition root: it installs the TLS
//! crypto provider, wires the concrete adapters to the ports, parses the CLI,
//! and dispatches (built-ins in-process, external subcommands via resolve+exec).

use std::path::PathBuf;
use std::process::ExitCode;

use clap::error::ErrorKind;
use clap::{CommandFactory as _, Parser as _};

use config::{ConfigAccess, ConfigError, ConfigService, Key, Level, Resolved};
use config_adapters::FileConfigStore;
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

/// Discovers the project root and builds the config service lazily on the first
/// `get`/`set`, so a built-in like `version` and external dispatch never pay the
/// project-root filesystem walk.
struct LazyConfigAccess;

impl ConfigAccess for LazyConfigAccess {
    fn get(
        &self,
        key: &Key,
        level: Option<Level>,
    ) -> Result<Resolved, ConfigError> {
        discover_config_service()?.get(key, level)
    }

    fn set(
        &self,
        key: &Key,
        value: &str,
        level: Level,
    ) -> Result<(), ConfigError> {
        discover_config_service()?.set(key, value, level)
    }
}

fn discover_config_service(
) -> Result<ConfigService<FileConfigStore, FileConfigStore>, ConfigError> {
    let start = std::env::current_dir().map_err(|error| ConfigError::Io {
        path: ".".to_owned(),
        detail: error.to_string(),
    })?;
    let store = FileConfigStore::discover(&start);
    Ok(ConfigService::new(store.clone(), store))
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

/// The augmentation lists external subcommands, which belong only in the root
/// help. A `DisplayHelp` whose first argument names a built-in subcommand is that
/// subcommand's own `--help` and is rendered by clap unchanged.
fn is_root_help(error: &clap::Error) -> bool {
    if error.kind() != ErrorKind::DisplayHelp {
        return false;
    }
    !matches!(
        std::env::args_os()
            .nth(1)
            .as_deref()
            .and_then(std::ffi::OsStr::to_str),
        Some("version" | "config" | "help")
    )
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
    let config = LazyConfigAccess;
    let executor = UnixExec;
    if std::env::var_os(FIXTURE_ENV).is_some_and(|value| !value.is_empty()) {
        dispatch(cli, &reporter, &config, &FixtureResolver, &executor)
    } else {
        dispatch(cli, &reporter, &config, &LazyProductionResolver, &executor)
    }
}

fn main() -> ExitCode {
    if let Err(error) = install_crypto_provider() {
        eprintln!("luminosity: {error}");
        return ExitCode::FAILURE;
    }

    // try_parse (not parse) so the root `--help` can be intercepted and
    // augmented with the external subcommands. A subcommand's own `--help`
    // (`config --help`) is left to clap so it prints that command's help.
    let cli = match Cli::try_parse() {
        Ok(cli) => cli,
        Err(error) if is_root_help(&error) => return render_augmented_help(),
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
