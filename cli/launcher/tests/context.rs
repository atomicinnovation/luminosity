//! Black-box tests of the compiled `luminosity context` command.
//!
//! Each test spawns the real binary with a per-test working directory carrying
//! a `.git` boundary marker, so `FileConfigStore::discover` roots inside the
//! fixture and the upward walk can never escape into the real working tree.

use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicU64, Ordering};

const LAUNCHER: &str = env!("CARGO_BIN_EXE_luminosity");

const BLOCK_HEADER: &str = "## Project Context\n\n\
The following project-specific context has been provided. Take this into\n\
account when making decisions, selecting approaches, and generating output.\n\n";

static COUNTER: AtomicU64 = AtomicU64::new(0);

type TestResult = Result<(), Box<dyn Error>>;

fn workspace() -> Result<PathBuf, Box<dyn Error>> {
    let dir = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!(
        "context-{}-{}",
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
fn a_team_body_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn a_personal_body_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed(
        &dir,
        "config.local.md",
        "---\ncore: v\n---\npersonal context\n",
    )?;

    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}personal context\n"));
    Ok(())
}

#[test]
fn both_bodies_join_team_first_with_one_blank_line() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    seed(
        &dir,
        "config.local.md",
        "---\ncore: v\n---\npersonal context\n",
    )?;

    let output = run(&dir, &["context"])?;
    assert_eq!(
        stdout(&output),
        format!("{BLOCK_HEADER}team context\n\npersonal context\n")
    );
    Ok(())
}

#[test]
fn both_empty_prints_nothing_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\n")?;
    seed(&dir, "config.local.md", "---\ncore: v\n---\n")?;

    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn no_config_dir_prints_nothing_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn surrounding_blank_lines_leave_no_leading_or_trailing_blanks() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\n\n\n  team\n\n\n")?;

    let output = run(&dir, &["context"])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{BLOCK_HEADER}  team\n"));
    assert!(out.ends_with("  team\n"));
    assert!(!out.ends_with("\n\n"));
    Ok(())
}

#[test]
fn a_malformed_body_exits_non_zero_and_names_the_file() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("config.md"));
    Ok(())
}

#[test]
fn explain_prints_the_block_and_per_level_diagnostics() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--explain"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    let err = stderr(&output);
    assert!(err.contains("team (config.md)"));
    assert!(err.contains("personal (config.local.md)"));
    Ok(())
}

#[test]
fn explain_distinguishes_absent_from_present_but_empty() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.local.md", "---\ncore: v\n---\n")?;

    let output = run(&dir, &["context", "--explain"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    let err = stderr(&output);
    assert!(err.contains("team (config.md): not found"));
    assert!(err.contains("personal (config.local.md): discovered, empty body"));
    Ok(())
}

#[test]
fn resolves_the_block_from_a_subdirectory() -> TestResult {
    let dir = workspace()?;
    seed(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    let sub = dir.join("nested/deeper");
    fs::create_dir_all(&sub)?;

    let output = run(&sub, &["context"])?;
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn help_describes_the_context_command() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["context", "--help"])?;
    assert!(output.status.success());
    assert!(stdout(&output).to_lowercase().contains("project-context"));
    Ok(())
}
