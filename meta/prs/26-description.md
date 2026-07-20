---
type: pr-description
id: "26"
title: "[0018] Per-skill instructions"
date: "2026-07-20T14:30:58+00:00"
author: Toby Clemson
producer: describe-pr
status: complete
work_item_id: "work-item:0018"
parent: "work-item:0018"
pr_url: "https://github.com/atomicinnovation/luminosity/pull/26"
pr_number: 26
tags: [configuration, instructions-injection, rust-cli, skills, evals]
revision: "f376e492a20407c70451f39483376b6b8d1837ea"
repository: "luminosity"
last_updated: "2026-07-20T14:30:58+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# [0018] Per-skill instructions

## Summary

Teaches the launcher to inject per-skill **instructions** — directives a skill should *follow* — from `.luminosity/skills/<skill>/instructions.md` (team) and `instructions.local.md` (personal), rendered as a `## Additional Instructions` block at the **end** of a skill's prompt. This is the sibling of the per-skill *context* mechanism (story 0017): context lands near the top as information to *consider*, instructions land last as directives to *follow*. The two-level combination, frontmatter stripping, and symlink-containment kernel is reused verbatim — this change adds a third document kind flowing through it, not a new subsystem.

## Changes

- **Fragment kernel rename (Phase 0).** The `config` crate's context-assembly vocabulary is renamed to the neutral **`Fragment`** vocabulary (`context.rs` → `fragment.rs`; `ContextSource` → `FragmentSource`, `AssembledContext` → `Fragment`, `ContextAssembler` → `FragmentAssembler`, the `AssembleContext`/`ReadContextBody` ports, etc.) — a pure, behaviour-neutral rename so a second consumer no longer threads through symbols named for the first. The launcher's `context_command` edge stays deliberately context-named.
- **Instructions domain kind (Phase 1).** `FragmentSource` becomes kind-bearing (`ProjectContext`, `SkillContext(SkillName)`, `SkillInstructions(SkillName)`); the adapter's `fragment_path` grows the `instructions{qualifier}.md` arm via a shared `skill_dir` helper. Instructions are always skill-scoped, so a project-global instructions state is unrepresentable by construction.
- **`instructions` subcommand (Phase 2).** New `luminosity instructions --skill=<name>` command rendering the byte-exact `## Additional Instructions` block, omitted when empty, degrading under `--fail-safe`. The correctness-critical fail-safe boundary (including the raw-`--skill` parse) is factored into a shared `command_support` module so `context` and `instructions` share **one** implementation rather than two copies that can drift.
- **Skill wiring & configure surface (Phase 3).** A second end-of-body `!`-preprocessor line and the `instructions*` grant are added to the `configure` skill; a registry-walking contract test asserts the wiring in **every** registered skill; a `## Managing skill-specific instructions` section documents the mechanism; `.gitignore` gains the personal-file ignore+negation pair.
- **Eval coverage (Phases 4–5).** A new behavioural-only `instructions` eval capability (fixtures, dataset, scorer), the coordinated growth of the capability tripwires to `["context", "instructions", "values"]`, and a committed live `claude -p` log proving the block — and the context/instructions ordering — reach the model.

## Context

- Work item: `meta/work/0018-per-skill-instructions-injection.md`
- Plan: `meta/plans/2026-07-20-0018-per-skill-instructions-injection.md`
- Research: `meta/research/codebase/2026-07-19-0018-per-skill-instructions-injection.md`
- Validation: `meta/validations/2026-07-20-0018-per-skill-instructions-injection-validation.md` (result: **pass**)
- Governing decision: ADR-0012 (two-level per-skill model with frontmatter stripping), extended here from context to instructions. No new ADR is raised; the `Fragment` rename is a mechanical generalisation of the already-decided source-agnostic core.

## Testing

- [x] Full local CI mirror green end-to-end: `mise run` — exit 0 (formatters, all lints and type-checks, the full test suite with coverage, `build:launcher`, `deny:check` / `pup:check`)
- [x] Read-only CI set: `mise run check` — exit 0
- [x] Rust workspace + black-box suite with coverage: `mise run test:unit:cli` — exit 0 (`instructions_command/inbound/cli.rs` at 98.90% region)
- [x] Isolated instructions suites: `config-adapters` 10/10, `luminosity` 16/16
- [x] Contract test: `test_instructions_injection.py` — 11/11
- [x] Eval-logic tests: `mise run test:unit:evals` — 114 passed, 0 xfailed
- [x] Capability tripwires: `mise run test:unit:tasks` — 351 passed
- [x] `.gitignore` behaviour confirmed with `git check-ignore`: personal file ignored, team file tracked, fixture files tracked
- [x] Edge cases covered by the Rust black-box tier: invalid `--skill` under `--fail-safe` exits 0 with a notice (never discards the prompt); the mixed-empty drop-empty join and its symmetric twin; malformed-file degradation; thematic-break vs frontmatter-mapping first lines
- [x] Live eval: the committed ordering log carries both the context sentinel and the instructions sentinel, no host paths leaked

## Notes for Reviewers

- **Suggested review order follows the phases.** Phase 0 is a pure rename — a diff that changes any test's expected value there would be a mistake; the value is that Phases 1+ build on an already-neutral kernel.
- **Focus area: the fail-safe boundary** in `command_support/mod.rs`. A non-zero exit from an injected command discards the *entire* prompt, so an invalid `--skill` name is parsed *inside* the boundary (never a clap `value_parser`). This is the most correctness-sensitive code in the change; it now has one implementation shared by both commands.
- **No panicking macros were introduced.** The context command's render match stays total via a command-local two-variant projection rather than an `unreachable!` arm, honouring the workspace's panic-free convention.
- **Placement is a SKILL.md concern, not a Rust concern.** "Context early / instructions last" is realised by two `!`-lines in the SKILL.md body; the Rust tier asserts only each block's own bytes, and the relative ordering is pinned by the Python positional test and the behavioural eval.
- **Deliberate follow-up:** the `config` crate name and `ConfigError` taxonomy are intentionally left unrenamed (booked as a separate story once the `Fragment` vocabulary has settled); the `fragment.rs` module doc signposts the residual gap.
