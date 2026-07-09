---
type: work-item
id: "0010"
title: "Apply the Eval Framework to the configure Skill"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: high
parent: "work-item:0001"
blocked_by: ["work-item:0003", "work-item:0009"]
tags: [story, evaluation, skills, configure]
last_updated: "2026-07-06T21:45:07+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0010: Apply the Eval Framework to the configure Skill

**Kind**: Story
**Status**: Ready
**Priority**: High
**Author**: Toby Clemson

## Summary

Apply the eval framework chosen by spike 0003 — **Inspect** (UK AI Safety
Institute, AISI) — to the `configure` skill as the first evaluation target. The eval runs on demand during
development via `mise run eval:skills:configure` (deliberately excluded from CI to
control token cost), with the Inspect eval log committed to the repository as
the durable quality signal. This proves the eval approach end-to-end on the skill
that is the proof-of-architecture for the skills-vs-CLI division.

## Context

The eval-framework spike (0003) recommends an approach; this story applies it
(epic 0001, assumption A4). The `configure` skill is the first target because it
is the proof-of-architecture for the skills-vs-CLI division. Skill evals consume
significant tokens per trial, so they run on demand during development rather than
on every CI run; the recorded eval log is version-controlled as the durable
quality signal for the skill maintainers who rely on it to catch `configure`
regressions.

Spike 0003 concluded on 2026-06-24, selecting **Inspect** over the epic's leading
`skill-creator` hypothesis: only a headless, threshold-gating harness run from a
`mise`+invoke task meets the automation requirement, which `skill-creator`'s
interactive in-session loop cannot. `skill-creator` is retained as an optional
interactive authoring aid; promptfoo is the pre-vetted fallback.

## Requirements

- Stand up an Inspect eval suite for the `configure` skill under
  `tests/evals/skills/configure/`: an Inspect `@task` in `configure_eval.py`
  (with-skill vs baseline solvers over one dataset), the tasks in `dataset.jsonl`,
  and committed logs under `results/`. Name eval files as Inspect `@task` files
  (not `test_*`) so pytest does not collect them — the eval tier runs on the
  Inspect runner while sharing the `tests/` root.
- Run the eval on demand during development via `mise run eval:skills:configure`
  (leaf) / `mise run eval` (tier roll-up): an invoke task that calls Inspect's
  `eval()` in-process with `epochs=Epochs(k, pass_k(k))` (k = the trial count),
  reads `pass_k` off `log.results`, and exits non-zero below the floor. Exclude
  the eval tier from the default `mise run` / `check` sweep so it never runs in CI
  (token-cost control).
- Commit the Inspect eval log as JSON (`--log-format json`, so it diffs in VCS)
  under `tests/evals/skills/configure/results/<timestamp>.json`, by hand during
  development.
- Gate at the spike's bootstrap floor — its decided gate for this epic:
  **≥ 3 tasks**, **pass^k ≥ 0.8 over k = 3 trials** (Inspect's `pass_k` —
  all-k-succeed, not a mean pass-rate). The ramp commitment to grow the suite
  toward 20–50 real-failure-derived tasks (raising k toward 5–10 as token budget
  allows) as the skill matures is captured in Technical Notes as background — it
  is not an outstanding deliverable for this story.

## Acceptance Criteria

- [ ] The `configure` eval suite is defined as an Inspect `@task` under
      `tests/evals/skills/configure/`, with ≥ 3 tasks in `dataset.jsonl` covering
      at least the get, set/precedence, and missing-or-malformed-key scenarios,
      and is runnable on demand via `mise run eval:skills:configure`.
- [ ] Each task is graded by outcome against the CLI stdout and exit code the
      skill emits, with an explicit and deterministic per-task pass rule recorded
      in `configure_eval.py`: for value-producing tasks (get, set/precedence) the
      resolved config value the skill produces equals the task's expected value;
      for missing-or-malformed-key tasks the pass condition is that the skill
      surfaces the expected error / non-zero exit rather than a value.
- [ ] The committed results log records both the with-skill and baseline solvers
      over the same dataset. The baseline arm is recorded for attribution only —
      the gate (below) is on the with-skill `pass_k` alone — but a with-skill
      result that does not exceed the baseline is flagged in the commit as a
      signal to investigate rather than treated as a failing outcome.
- [ ] Given the eval is run during development, when it completes, then an Inspect
      eval log (`--log-format json`) is committed under
      `tests/evals/skills/configure/results/`.
- [ ] The committed `configure` eval log records a `pass_k` result meeting the
      spike's bootstrap floor (its decided gate for this epic). The floor has two
      independent dimensions: the
      **trial count** k = 3 (each task is run 3 times) and the **task count**
      ≥ 3. Inspect's `pass_k` scores a task as passing only if all k of its trials
      pass, then reports the fraction of tasks that pass; the gate is that
      fraction ≥ 0.8. At the minimum of 3 tasks the achievable fractions are 0,
      ⅓, ⅔, or 1, so ≥ 0.8 is met only at 1.0 — i.e. all 3 tasks must pass all 3
      of their trials. As the suite grows past 3 tasks the 0.8 fraction admits
      some failures.
- [ ] The threshold gate is verified two-sided by unit tests independent of live
      runs: a synthetic `pass_k` below 0.8 asserts the `mise` task exits non-zero
      (fails closed), and a synthetic `pass_k` at or above 0.8 asserts it exits
      zero (passes open).
- [ ] The eval uses Inspect (the framework selected by spike 0003 / ADR
      decision 11), and the eval tier is excluded from the default `mise run` /
      `check` sweep — no eval runs on any CI build.
- [ ] Eval files are named so pytest does not collect them (Inspect `@task`
      files, not `test_*`).

## Open Questions

- None. The eval-refresh cadence — previously open — is resolved by spike
  0003: re-run and re-commit on the first material `configure` behaviour change,
  or the first real-world failure not covered by the bootstrap tasks (recorded in
  Technical Notes).

## Dependencies

- Blocked by: spike 0003 (**done** — chose Inspect, the pass^k floor, and the
  dev-time/committed workflow); configuration story 0009 (**ready** — provides the
  `configure` skill under test).
- Tooling: the Inspect library (UK AISI), added and version-pinned via `uv` per
  the repo's pinning convention — the framework of record decided by spike 0003.
- Runtime prerequisite: an authenticated, drivable Claude Code / model API plus
  the token budget available to whoever runs `mise run eval:skills:configure`
  (the same token cost that keeps the tier out of CI). The promptfoo fallback is
  the contingency if the external-agent A/B integration proves awkward. The
  committed `pass_k` result is coupled to the underlying model version, which can
  drift independently of the skill — see the eval-refresh triggers in Technical
  Notes.
- Discharges: the `configure` behavioural-equivalence validation that story 0009
  explicitly deferred to this eval-application story — closing 0010 also completes
  that outstanding 0009 acceptance obligation.
- Not a blocker: the eval-framework ADR (decision 11, work item 0005) is a
  parallel record — the authoritative framework decision already lives in the
  done spike 0003.
- Blocks: none; part of the epic's definition of done.
- Parent: epic 0001.

## Assumptions

- The eval-framework recommendation is applied within this epic (A4), not just
  decided.
- Running evals in CI is deliberately avoided due to token cost; the
  version-controlled Inspect eval log is the durable record instead.

## Technical Notes

- **Harness**: Inspect (UK AISI) — Python, installs via `uv`, runs in-process in
  an invoke task, so it adds no new language toolchain beyond the repo's
  Python/shell/Rust three. Inspect has no built-in score-threshold flag; the
  pass^k gate is wired by hand (~3 lines: read `pass_k` off `log.results`, raise
  `SystemExit(1)` below the bar).
- **A/B is hand-built**: with-skill vs baseline solver over one dataset, driving
  Claude Code as an external agent; skill-invocation detection is the author's
  responsibility (Inspect's main authoring cost versus promptfoo's turnkey skill
  A/B).
- **Residual risk (from spike)**: no live prototype was run — the first throwaway
  run in this story should validate the Inspect-driving-Claude-Code A/B
  integration. If the external-agent A/B proves awkward, promptfoo is the
  pre-vetted fallback.
- **Eval-refresh trigger** (resolves the former Open Question): re-run and
  re-commit on the first material `configure` behaviour change, the first
  real-world failure not covered by the bootstrap tasks, or a change in the
  underlying model version (the committed `pass_k` is coupled to it and can drift
  without any skill change).
- **Qualitative loop**: Inspect View / `read_eval_log` expose per-sample
  transcripts, tool calls, and grader rationales, so committed logs can be read
  back in a skill-writing session to propose improvements.
- Methodology follows the spike: multiple trials per task for variance,
  outcome-based grading, baseline comparison to attribute improvement.

## Drafting Notes

- Kind kept as `story`: a concrete, bounded deliverable (one eval suite applied to
  one skill).
- Execution model is dev-time + committed results, excluded from CI, to control
  token cost — this now **agrees with** spike 0003's operational model. The
  earlier note that 0010 "revises the eval spike's CI-gate framing" is superseded:
  the spike itself landed on the same dev-time/committed/no-CI model.
- Concretized against spike 0003 (2026-06-24): framework (Inspect), command
  (`mise run eval:skills:configure`), layout (`tests/evals/skills/configure/`),
  result format (JSON log), and gate (pass^k ≥ 0.8, k = 3) are lifted directly
  from the spike's Recommendation. If the spike is ever revised, re-sync these
  values here.
- Task sourcing: the bootstrap starts at the ≥ 3-task floor with realistic
  `configure` scenarios (get/set, precedence, missing/malformed key), ramping
  toward 20–50 real-failure-derived tasks later.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0003-skill-evaluation-framework-selection.md` (eval spike —
  framework, pass^k floor, operational model);
  `meta/work/0009-multi-level-configuration-system.md` (provides the `configure`
  skill under test); work item 0005 (eval-framework ADR, decision 11)
- Research: Anthropic, "Demystifying evals for AI agents" (Jan 2026); UK AISI
  Inspect (`inspect.aisi.org.uk`)
