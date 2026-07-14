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

const SKILL_HEADER: &str = "## Skill-Specific Context\n\n\
The following context is specific to the configure skill. Apply this\n\
context in addition to any project-wide context above.\n\n";

const SKILL: &str = "--skill=configure";

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

fn seed_project(dir: &Path, name: &str, content: &str) -> TestResult {
    fs::create_dir_all(dir.join(".luminosity"))?;
    fs::write(dir.join(".luminosity").join(name), content)?;
    Ok(())
}

fn seed_skill(dir: &Path, name: &str, content: &str) -> TestResult {
    let skill_dir = dir.join(".luminosity/skills/configure");
    fs::create_dir_all(&skill_dir)?;
    fs::write(skill_dir.join(name), content)?;
    Ok(())
}

#[test]
fn a_team_body_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn a_personal_body_prints_the_block() -> TestResult {
    let dir = workspace()?;
    seed_project(
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
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    seed_project(
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
    seed_project(&dir, "config.md", "---\ncore: v\n---\n")?;
    seed_project(&dir, "config.local.md", "---\ncore: v\n---\n")?;

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
    seed_project(&dir, "config.md", "---\ncore: v\n---\n\n\n  team\n\n\n")?;

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
    seed_project(&dir, "config.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("config.md"));
    Ok(())
}

#[test]
fn explain_prints_the_block_and_per_level_diagnostics() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--explain"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    let err = stderr(&output);
    assert!(err.starts_with("root: "));
    assert!(err.contains("team (.luminosity/config.md)"));
    assert!(err.contains("personal (.luminosity/config.local.md)"));
    Ok(())
}

#[test]
fn explain_distinguishes_absent_from_present_but_empty() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.local.md", "---\ncore: v\n---\n")?;

    let output = run(&dir, &["context", "--explain"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    let err = stderr(&output);
    assert!(err.contains("team (.luminosity/config.md): not found"));
    assert!(err.contains(
        "personal (.luminosity/config.local.md): discovered, empty body"
    ));
    Ok(())
}

#[test]
fn fail_safe_renders_a_malformed_body_as_a_stdout_notice() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with("## Project Context Unavailable\n"));
    assert!(out.contains("config.md"));
    assert!(out.contains("malformed frontmatter"));
    Ok(())
}

#[test]
fn fail_safe_leaves_a_healthy_read_byte_identical() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let plain = run(&dir, &["context"])?;
    let safe = run(&dir, &["context", "--fail-safe"])?;
    assert_eq!(safe.stdout, plain.stdout);
    assert_eq!(stdout(&safe), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn fail_safe_still_prints_nothing_when_both_bodies_are_empty() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\n")?;

    let output = run(&dir, &["context", "--fail-safe"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn without_fail_safe_a_malformed_body_still_fails_loudly() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context"])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("config.md"));
    Ok(())
}

#[test]
fn resolves_the_block_from_a_subdirectory() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
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

#[test]
fn help_describes_the_skill_flag() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["context", "--help"])?;
    assert!(output.status.success());
    assert!(stdout(&output).contains("--skill"));
    Ok(())
}

#[test]
fn a_team_skill_context_prints_the_skill_block() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{SKILL_HEADER}skill team\n"));
    Ok(())
}

#[test]
fn a_personal_skill_context_prints_the_skill_block() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.local.md", "skill personal\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{SKILL_HEADER}skill personal\n"));
    Ok(())
}

#[test]
fn both_skill_levels_join_team_first_with_one_blank_line() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "skill team\n")?;
    seed_skill(&dir, "context.local.md", "skill personal\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert_eq!(
        stdout(&output),
        format!("{SKILL_HEADER}skill team\n\nskill personal\n")
    );
    Ok(())
}

#[test]
fn the_skill_block_follows_the_project_block_with_one_blank_line() -> TestResult
{
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert_eq!(
        stdout(&output),
        format!("{BLOCK_HEADER}team context\n\n{SKILL_HEADER}skill team\n")
    );
    Ok(())
}

#[test]
fn a_skill_block_with_no_project_context_is_the_only_block() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{SKILL_HEADER}skill team\n"));
    assert!(out.starts_with("## Skill-Specific Context\n"));
    Ok(())
}

#[test]
fn a_skill_context_with_no_skill_flag_is_not_printed() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn an_absent_skill_context_prints_only_the_project_block() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn an_empty_skill_context_prints_only_the_project_block() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    seed_skill(&dir, "context.md", "\n  \n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn both_sources_absent_prints_nothing_and_exits_zero() -> TestResult {
    let dir = workspace()?;
    let output = run(&dir, &["context", SKILL])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), "");
    Ok(())
}

#[test]
fn skill_surrounding_blank_lines_leave_no_leading_or_trailing_blanks(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "\n\n  skill\n\n\n")?;

    let output = run(&dir, &["context", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{SKILL_HEADER}  skill\n"));
    assert!(!out.ends_with("\n\n"));
    Ok(())
}

#[test]
fn a_skill_context_frontmatter_mapping_is_not_injected() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "---\ntitle: x\n---\nskill body\n")?;

    let output = run(&dir, &["context", SKILL])?;
    let out = stdout(&output);
    assert_eq!(out, format!("{SKILL_HEADER}skill body\n"));
    assert!(!out.contains("title: x"));
    Ok(())
}

#[test]
fn a_skill_context_thematic_break_body_is_injected_whole() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "---\nSection A\n---\nSection B\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert_eq!(
        stdout(&output),
        format!("{SKILL_HEADER}---\nSection A\n---\nSection B\n")
    );
    Ok(())
}

#[test]
fn an_unknown_skill_name_prints_only_the_project_block() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--skill=nonexistent"])?;
    assert!(output.status.success());
    assert_eq!(stdout(&output), format!("{BLOCK_HEADER}team context\n"));
    Ok(())
}

#[test]
fn an_invalid_skill_name_under_fail_safe_still_prints_the_project_block(
) -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--skill=../../etc", "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with(&format!("{BLOCK_HEADER}team context\n\n")));
    assert!(out.contains("## Skill-Specific Context Unavailable\n"));
    assert!(out.contains("invalid skill name '../../etc'"));
    Ok(())
}

#[test]
fn an_invalid_skill_name_without_fail_safe_exits_non_zero() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--skill=../../etc"])?;
    assert!(!output.status.success());
    assert!(stderr(&output).contains("invalid skill name"));
    Ok(())
}

#[test]
fn a_malformed_skill_context_under_fail_safe_still_prints_the_project_block(
) -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;
    seed_skill(&dir, "context.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", SKILL, "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with(&format!("{BLOCK_HEADER}team context\n\n")));
    assert!(out.contains("## Skill-Specific Context Unavailable\n"));
    Ok(())
}

#[test]
fn a_malformed_skill_context_names_the_skill_file_in_its_notice() -> TestResult
{
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", SKILL, "--fail-safe"])?;
    let out = stdout(&output);
    assert!(out.contains("skills/configure/context.md"));
    assert!(out.contains("malformed frontmatter"));
    assert!(!out.contains("## Project Context Unavailable"));
    Ok(())
}

#[test]
fn a_malformed_config_under_fail_safe_still_prints_the_skill_block(
) -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\nkey: value\n")?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context", SKILL, "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with("## Project Context Unavailable\n"));
    assert!(out.ends_with(&format!("{SKILL_HEADER}skill team\n")));
    Ok(())
}

#[test]
fn both_sources_malformed_under_fail_safe_print_both_notices() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\nkey: value\n")?;
    seed_skill(&dir, "context.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", SKILL, "--fail-safe"])?;
    assert!(output.status.success());
    let out = stdout(&output);
    assert!(out.starts_with("## Project Context Unavailable\n"));
    assert!(out.contains("## Skill-Specific Context Unavailable\n"));
    Ok(())
}

#[test]
fn a_malformed_skill_context_without_fail_safe_fails_loudly() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", SKILL])?;
    assert!(!output.status.success());
    assert_eq!(stdout(&output), "");
    assert!(stderr(&output).contains("skills/configure/context.md"));
    Ok(())
}

#[test]
fn explain_reports_the_root_and_both_skill_levels() -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "skill team\n")?;

    let output = run(&dir, &["context", SKILL, "--explain"])?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.starts_with("root: "));
    assert!(err.contains(
        "team (.luminosity/skills/configure/context.md): discovered, \
         body present"
    ));
    assert!(err.contains(
        "personal (.luminosity/skills/configure/context.local.md): not found"
    ));
    Ok(())
}

#[test]
fn explain_surfaces_the_attempted_paths_when_a_valid_named_source_degrades(
) -> TestResult {
    let dir = workspace()?;
    seed_skill(&dir, "context.md", "---\nkey: value\n")?;

    let output = run(&dir, &["context", SKILL, "--fail-safe", "--explain"])?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.contains(
        "team (.luminosity/skills/configure/context.md): unreadable"
    ));
    assert!(err.contains(
        "personal (.luminosity/skills/configure/context.local.md): unreadable"
    ));
    Ok(())
}

#[test]
fn explain_reports_an_invalid_skill_name_as_a_single_name_only_line(
) -> TestResult {
    let dir = workspace()?;
    let output = run(
        &dir,
        &["context", "--skill=../../etc", "--fail-safe", "--explain"],
    )?;
    assert!(output.status.success());
    let err = stderr(&output);
    assert!(err.contains("invalid skill name '../../etc'"));
    assert!(!err.contains("skills/"));
    Ok(())
}

#[test]
fn explain_without_a_skill_reports_only_the_config_levels() -> TestResult {
    let dir = workspace()?;
    seed_project(&dir, "config.md", "---\ncore: v\n---\nteam context\n")?;

    let output = run(&dir, &["context", "--explain"])?;
    let err = stderr(&output);
    assert!(!err.contains("skills/"));
    assert_eq!(err.lines().count(), 3);
    Ok(())
}
