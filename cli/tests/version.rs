//! Black-box test of the compiled `luminosity version` output.
//!
//! Every field is asserted against the value baked into THIS package at build
//! time — `env!("CARGO_PKG_VERSION")` and the same `option_env!("VERGEN_*")`
//! expressions the adapter uses (cargo:rustc-env vars apply to the package's
//! integration tests too). So the assertions are deterministic and about the
//! built artefact, not about live git state or the wall clock: HEAD can move
//! between build and test, vergen may emit a short/`-dirty` SHA, and a git
//! binary may be absent on the test host. The authoritative per-source proof is
//! the core-against-fake unit test; this is a consistency + non-degradation
//! guard on the real, non-fakeable adapter.

use std::collections::HashSet;
use std::error::Error;
use std::process::Command;

use time::format_description::well_known::Rfc3339;
use time::OffsetDateTime;

const UNKNOWN: &str = "unknown";

fn version_output_lines() -> Result<Vec<String>, Box<dyn Error>> {
    let output = Command::new(env!("CARGO_BIN_EXE_luminosity"))
        .arg("version")
        .output()?;
    assert!(
        output.status.success(),
        "`luminosity version` exited non-zero: {:?}",
        output.status
    );
    let stdout = String::from_utf8(output.stdout)?;
    Ok(stdout.lines().map(str::to_owned).collect())
}

fn field(
    lines: &[String],
    index: usize,
    prefix: &str,
) -> Result<String, Box<dyn Error>> {
    let line = lines
        .get(index)
        .ok_or_else(|| format!("missing output line {index}"))?;
    let value = line
        .strip_prefix(prefix)
        .ok_or_else(|| format!("line {line:?} missing prefix {prefix:?}"))?;
    Ok(value.to_owned())
}

#[test]
fn version_reports_build_baked_metadata() -> Result<(), Box<dyn Error>> {
    let lines = version_output_lines()?;

    let version = field(&lines, 0, "luminosity ")?;
    let commit_sha = field(&lines, 1, "commit: ")?;
    let build_date = field(&lines, 2, "built:  ")?;
    let target_triple = field(&lines, 3, "target: ")?;

    // Each field equals the build-baked value, so plumbing through to stdout is
    // proven by construction in every build context.
    assert_eq!(version, env!("CARGO_PKG_VERSION"));
    assert_eq!(commit_sha, option_env!("VERGEN_GIT_SHA").unwrap_or(UNKNOWN));
    assert_eq!(
        build_date,
        option_env!("VERGEN_BUILD_TIMESTAMP").unwrap_or(UNKNOWN)
    );
    assert_eq!(
        target_triple,
        option_env!("VERGEN_CARGO_TARGET_TRIPLE").unwrap_or(UNKNOWN)
    );

    // Symmetry-breaking guards so the equalities are not tautologies: a dropped
    // or swapped field would otherwise move both sides together.
    for value in [&version, &commit_sha, &build_date, &target_triple] {
        assert!(!value.is_empty(), "a printed field was empty");
    }
    let distinct: HashSet<&str> = [
        version.as_str(),
        commit_sha.as_str(),
        build_date.as_str(),
        target_triple.as_str(),
    ]
    .into_iter()
    .collect();
    assert_eq!(distinct.len(), 4, "two printed fields are identical");

    // The local + CI build always runs inside a git working tree (the gitcl
    // rationale), so the SHA/date/triple are real values, not the degraded
    // sentinel — keeping the equality checks discriminating here.
    assert_ne!(commit_sha, UNKNOWN);
    assert_ne!(build_date, UNKNOWN);
    assert_ne!(target_triple, UNKNOWN);

    // The build date is a real RFC 3339 timestamp, not in the future. No lower
    // bound: a cache-honouring incremental build legitimately carries an earlier
    // (but real) timestamp, so a "recent window" assertion would be flaky.
    let parsed = OffsetDateTime::parse(&build_date, &Rfc3339)?;
    assert!(
        parsed <= OffsetDateTime::now_utc(),
        "build date is in the future: {build_date}"
    );

    Ok(())
}
