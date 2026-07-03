//! The luminosity launcher binary — the composition root: it installs the TLS
//! crypto provider, wires the concrete adapters to the ports, parses the CLI,
//! and dispatches (built-ins in-process, external subcommands via resolve+exec).

use std::process::ExitCode;

use clap::Parser as _;

use luminosity::launch::dispatch;
use luminosity::launch::inbound::cli::Cli;
use luminosity::launch::outbound::exec::UnixExec;
use luminosity::launch::outbound::resolver::FixtureResolver;
use luminosity::launch::outbound::tls::install_crypto_provider;
use luminosity::version::core::VersionReporter;
use luminosity::version::outbound::build_metadata::VergenBuildMetadata;

fn main() -> ExitCode {
    if let Err(error) = install_crypto_provider() {
        eprintln!("luminosity: {error}");
        return ExitCode::FAILURE;
    }
    let cli = Cli::parse();
    let reporter = VersionReporter::new(VergenBuildMetadata);
    let resolver = FixtureResolver;
    let executor = UnixExec;
    match dispatch(&cli, &reporter, &resolver, &executor) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("luminosity: {error}");
            ExitCode::FAILURE
        }
    }
}
