//! Black-box tests of the compiled `luminosity config` command.
//!
//! Each test spawns the real binary with a per-test working directory carrying
//! a `.git` boundary marker, so `FileConfigStore::discover` roots inside the
//! fixture and the upward walk can never escape into the real working tree
//! (`CARGO_TARGET_TMPDIR` lives under `cli/target/`, inside this repo).

use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

const LAUNCHER: &str = env!("CARGO_BIN_EXE_luminosity");

static COUNTER: AtomicU64 = AtomicU64::new(0);

type TestResult = Result<(), Box<dyn Error>>;

fn workspace() -> Result<PathBuf, Box<dyn Error>> {
    let dir = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!(
        "config-{}-{}",
        std::process::id(),
        COUNTER.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(dir.join(".git"))?;
    Ok(dir)
}

fn run(dir: &Path, args: &[&str]) -> Result<Output, Box<dyn Error>> {
    Ok(Command::new(LAUNCHER)
        .current_dir(dir)
        .args(args)
        .output()?)
}

fn stdout(output: &Output) -> String {
    String::from_utf8_lossy(&output.stdout).into_owned()
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn seed(dir: &Path, name: &str, content: &str) -> TestResult {
    fs::create_dir_all(dir.join(".luminosity"))?;
    fs::write(dir.join(".luminosity").join(name), content)?;
    Ok(())
}

#[test]
fn full_stack_resolution_returns_the_personal_value() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "team-v", "--level", "team"],
    )?;
    run(&dir, &["config", "set", "core.example", "personal-v"])?;

    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "personal-v\n");
    Ok(())
}

#[test]
fn team_only_falls_through() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "team-v", "--level", "team"],
    )?;

    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "team-v\n");
    Ok(())
}

#[test]
fn level_scoped_reads_target_a_single_level() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "team-v", "--level", "team"],
    )?;
    run(&dir, &["config", "set", "core.example", "personal-v"])?;

    let team =
        run(&dir, &["config", "get", "core.example", "--level", "team"])?;
    assert_eq!(stdout(&team), "team-v\n");
    let personal = run(
        &dir,
        &["config", "get", "core.example", "--level", "personal"],
    )?;
    assert_eq!(stdout(&personal), "personal-v\n");
    Ok(())
}

#[test]
fn set_defaults_to_the_personal_file_and_team_writes_the_team_file(
) -> TestResult {
    let dir = workspace()?;
    run(&dir, &["config", "set", "core.example", "p"])?;
    assert!(dir.join(".luminosity/config.local.md").is_file());
    assert!(!dir.join(".luminosity/config.md").exists());

    run(
        &dir,
        &["config", "set", "core.example", "t", "--level", "team"],
    )?;
    assert!(dir.join(".luminosity/config.md").is_file());
    Ok(())
}

#[test]
fn get_and_set_resolve_the_ancestor_from_a_subdirectory() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "v", "--level", "team"],
    )?;
    let sub = dir.join("nested/deeper");
    fs::create_dir_all(&sub)?;

    let output = run(&sub, &["config", "get", "core.example"])?;
    assert_eq!(stdout(&output), "v\n");

    run(&sub, &["config", "set", "other.key", "x"])?;
    assert!(!sub.join(".luminosity").exists(), "scaffolded a stray dir");
    assert!(dir.join(".luminosity/config.local.md").is_file());
    Ok(())
}

#[test]
fn set_personal_then_full_stack_get_round_trips() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "v", "--level", "personal"],
    )?;
    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "v\n");
    Ok(())
}

#[test]
fn a_missing_key_exits_non_zero_and_names_the_key() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["config", "get", "missing.key"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("missing.key"));
    assert!(stderr(&output).contains("is not set"));
    Ok(())
}

#[test]
fn an_empty_string_value_prints_an_empty_line_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "", "--level", "team"],
    )?;
    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "\n");
    Ok(())
}

#[test]
fn a_null_value_prints_an_empty_line_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore:\n  example:\n---\n")?;
    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "\n");
    Ok(())
}

#[test]
fn a_conflicting_set_exits_non_zero_and_leaves_files_unchanged() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "v", "--level", "team"],
    )?;
    let before = fs::read_to_string(dir.join(".luminosity/config.md"))?;

    let output = run(&dir, &["config", "set", "core", "x", "--level", "team"])?;
    assert!(!output.status.success());
    assert!(stderr(&output).contains("core"));
    assert!(stderr(&output).contains("section"));
    assert_eq!(
        fs::read_to_string(dir.join(".luminosity/config.md"))?,
        before
    );
    Ok(())
}

#[test]
fn a_malformed_personal_file_fails_a_full_stack_get_loudly() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore:\n  example: team-v\n---\n")?;
    seed(&dir, "config.local.md", "---\nkey: value\n")?;

    let output = run(&dir, &["config", "get", "core.example"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("config.local.md"));
    assert!(!stderr(&output).contains("personal"));
    Ok(())
}

#[test]
fn a_bogus_level_is_rejected_and_touches_no_file() -> TestResult {
    let dir = workspace()?;
    let get = run(&dir, &["config", "get", "core.example", "--level", "bad"])?;
    assert!(!get.status.success());
    assert!(stderr(&get).contains("bad"));

    let set = run(
        &dir,
        &["config", "set", "core.example", "v", "--level", "bad"],
    )?;
    assert!(!set.status.success());
    assert!(!dir.join(".luminosity").exists());
    Ok(())
}

#[test]
fn a_degenerate_key_is_rejected_before_any_scaffolding() -> TestResult {
    let dir = workspace()?;
    let get = run(&dir, &["config", "get", ""])?;
    assert!(!get.status.success());
    assert_eq!(stdout(&get), "");
    assert!(stderr(&get).contains("invalid config key"));

    let set = run(&dir, &["config", "set", "core..example", "v"])?;
    assert!(!set.status.success());
    assert_eq!(stdout(&set), "");
    assert!(stderr(&set).contains("core..example"));
    assert!(!dir.join(".luminosity").exists());
    Ok(())
}

#[test]
fn a_resolved_value_prints_with_one_trailing_newline() -> TestResult {
    let dir = workspace()?;
    run(
        &dir,
        &["config", "set", "core.example", "v", "--level", "team"],
    )?;
    let output = run(&dir, &["config", "get", "core.example"])?;
    assert_eq!(output.stdout, b"v\n");
    Ok(())
}

#[test]
fn help_describes_the_config_commands_and_levels() -> TestResult {
    let dir = workspace()?;
    let config = run(&dir, &["config", "--help"])?;
    assert!(config.status.success());
    assert!(stdout(&config).to_lowercase().contains("configuration"));

    let get = run(&dir, &["config", "get", "--help"])?;
    assert!(get.status.success());
    assert!(stdout(&get).contains("--level"));
    assert!(stdout(&get).contains("section.key"));

    let set = run(&dir, &["config", "set", "--help"])?;
    assert!(set.status.success());
    let set_help = stdout(&set);
    assert!(set_help.contains("--level"));
    assert!(set_help.contains("team"));
    assert!(set_help.contains("personal"));
    Ok(())
}
