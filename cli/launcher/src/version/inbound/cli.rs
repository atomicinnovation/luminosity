//! The inbound (driving) adapter for `version`. No CLI parsing: the command
//! tree lives in `launch::inbound::cli`; this owns only `version`.

use crate::version::core::{ReportVersion, VersionReport};

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

pub fn report(reporter: &impl ReportVersion) {
    println!("{}", render(&reporter.report()));
}
