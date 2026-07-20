//! Black-box tests of the compiled `luminosity instructions` command.
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

const HEADER: &str = "## Additional Instructions\n\n\
The following additional instructions have been provided for the\n\
configure skill. Follow these instructions in addition to all\n\
instructions above.\n\n";

const SKILL: &str = "--skill=configure";

static COUNTER: AtomicU64 = AtomicU64::new(0);

type TestResult = Result<(), Box<dyn Error>>;

fn workspace() -> Result<PathBuf, Box<dyn Error>> {
    let dir = PathBuf::from(env!("CARGO_TARGET_TMPDIR")).join(format!(
        "instructions-{}-{}",
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

fn seed_skill(dir: &Path, name: &str, content: &str) -> TestResult {
    let skill_dir = dir.join(".luminosity/skills/configure");
    fs::create_dir_all(&skill_dir)?;
    fs::write(skill_dir.join(name), content)?;
    Ok(())
}

#[test]
fn a_team_skill_instructions_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "team instructions\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{HEADER}team instructions\n"));
    Ok(())
}

#[test]
fn a_personal_skill_instructions_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.local.md", "personal instructions\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{HEADER}personal instructions\n"));
    Ok(())
}

#[test]
fn both_levels_join_team_first_with_one_blank_line() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "team\n")?;
    seed_skill(&dir, "instructions.local.md", "personal\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert_eq!(stdout(&output), format!("{HEADER}team\n\npersonal\n"));
    Ok(())
}

#[test]
fn a_present_but_empty_personal_level_is_dropped_with_no_doubled_blank(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "team\n")?;
    seed_skill(&dir, "instructions.local.md", "\n  \n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{HEADER}team\n"));
    assert!(!out.ends_with("\n\n"));
    Ok(())
}

#[test]
fn a_present_but_empty_team_level_is_dropped_with_no_leading_blank(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "\n  \n")?;
    seed_skill(&dir, "instructions.local.md", "personal\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{HEADER}personal\n"));
    assert!(!out.contains("above.\n\n\npersonal"));
    Ok(())
}

#[test]
fn an_absent_instructions_file_prints_nothing_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["instructions", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn an_empty_instructions_file_prints_nothing() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "\n  \n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn a_frontmatter_mapping_is_not_injected() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "---\ntitle: x\n---\nthe body\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{HEADER}the body\n"));
    assert!(!out.contains("title: x"));
    Ok(())
}

#[test]
fn a_thematic_break_body_is_injected_whole() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "---\nSection A\n---\nSection B\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert_eq!(
        stdout(&output),
        format!("{HEADER}---\nSection A\n---\nSection B\n")
    );
    Ok(())
}

#[test]
fn surrounding_blank_lines_leave_no_leading_or_trailing_blanks() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "\n\n  do this\n\n\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{HEADER}  do this\n"));
    assert!(!out.ends_with("\n\n"));
    Ok(())
}

#[test]
fn no_skill_flag_prints_nothing_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "team instructions\n")?;

    let output = run(&dir, &["instructions"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn an_unknown_skill_name_prints_nothing() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["instructions", "--skill=nonexistent"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn an_invalid_skill_name_under_fail_safe_exits_zero_with_a_notice() -> TestResult
{
    let dir = workspace()?;
    let output =
        run(&dir, &["instructions", "--skill=../../etc", "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with("## Additional Instructions Unavailable\n"));
    assert!(out.contains("invalid skill name '../../etc'"));
    assert!(!out.contains("skills/"));
    Ok(())
}

#[test]
fn an_invalid_skill_name_without_fail_safe_exits_non_zero() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["instructions", "--skill=../../etc"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("invalid skill name"));
    Ok(())
}

#[test]
fn a_malformed_instructions_under_fail_safe_exits_zero_with_a_notice(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "---\nkey: value\n")?;

    let output = run(&dir, &["instructions", SKILL, "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with("## Additional Instructions Unavailable\n"));
    assert!(out.contains("skills/configure/instructions.md"));
    assert!(out.contains("malformed frontmatter"));
    Ok(())
}

#[test]
fn a_malformed_instructions_without_fail_safe_fails_loudly() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "---\nkey: value\n")?;

    let output = run(&dir, &["instructions", SKILL])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("skills/configure/instructions.md"));
    Ok(())
}

#[test]
fn explain_reports_the_root_and_both_instructions_levels() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "team instructions\n")?;

    let output = run(&dir, &["instructions", SKILL, "--explain"])?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.starts_with("root: "));
    assert!(err.contains(
        "team (.luminosity/skills/configure/instructions.md): discovered, \
         body present"
    ));
    assert!(err.contains(
        "personal (.luminosity/skills/configure/instructions.local.md): \
         not found"
    ));
    Ok(())
}

#[test]
fn explain_surfaces_the_attempted_paths_when_a_valid_named_source_degrades(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "instructions.md", "---\nkey: value\n")?;

    let output =
        run(&dir, &["instructions", SKILL, "--fail-safe", "--explain"])?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.contains(
        "team (.luminosity/skills/configure/instructions.md): unreadable"
    ));
    assert!(err.contains(
        "personal (.luminosity/skills/configure/instructions.local.md): \
         unreadable"
    ));
    Ok(())
}

#[test]
fn explain_reports_an_invalid_skill_name_as_a_single_name_only_line(
) -> TestResult {
    let dir = workspace()?;
    let output = run(
        &dir,
        &[
            "instructions",
            "--skill=../../etc",
            "--fail-safe",
            "--explain",
        ],
    )?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.contains("invalid skill name '../../etc'"));
    assert!(!err.contains("skills/"));
    assert!(!err.contains("root:"));
    Ok(())
}

#[test]
fn explain_without_a_skill_prints_nothing() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["instructions", "--explain"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    assert_eq!(stderr(&output), "");
    Ok(())
}

#[test]
fn help_describes_the_instructions_command() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["instructions", "--help"])?;
    assert!(output.status.success());
    let out = stdout(&output).to_lowercase();
    assert!(out.contains("additional instructions"));
    assert!(out.contains("--skill"));
    Ok(())
}
