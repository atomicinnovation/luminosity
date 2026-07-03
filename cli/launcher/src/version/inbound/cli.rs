//! The inbound (driving) adapter for `version` — renders the [`VersionReport`]
//! and drives the inbound port.
//!
//! No domain logic, and no CLI parsing: the command tree lives in
//! `launch::inbound::cli`; this owns only `version`.

use crate::version::core::{ReportVersion, VersionReport};

/// Renders a [`VersionReport`] as the human-facing `version` output.
#[must_use]
pub fn render(report: &VersionReport) -> String {
    format!(
        "luminosity {}\ncommit: {}\nbuilt:  {}\ntarget: {}",
        report.version,
        report.commit_sha,
        report.build_date,
        report.target_triple,
    )
}

/// Drives the inbound port and prints the rendered `version` output.
pub fn report(reporter: &impl ReportVersion) {
    println!("{}", render(&reporter.report()));
}
