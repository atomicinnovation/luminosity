---
type: work-item
id: "0009"
title: "Multi-Level Configuration System — CLI Command + Thin configure Skill"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
blocks: ["work-item:0010", "work-item:0011"]
relates_to: ["work-item:0006", "work-item:0011", "adr:ADR-0003", "adr:ADR-0010"]
tags: [story, configuration, cli, skills, architecture-enforcement]
last_updated: "2026-06-27T11:51:56+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0009: Multi-Level Configuration System — CLI Command + Thin configure Skill

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Implement a multi-level configuration system (team and personal precedence)
exposed as a CLI command and driven by a thin `configure` skill, proving the
skills-vs-CLI division of labour end-to-end: the skill orchestrates while the
CLI executes the deterministic configuration logic.

## Context

The `configure` skill is the first concrete instance of the skills-vs-CLI
division — a skill driving deterministic configuration logic that lives in the
CLI — so it doubles as the proof-of-architecture for the whole approach. It also
becomes the first eval target (the eval-application story). Configuration scope is
deliberately minimal: enough to prove the multi-level model end-to-end, not a
complete schema for as-yet-unbuilt features. The multi-level model is adapted
from the accelerator's userspace configuration approach.

## Requirements

- Implement configuration resolution across two levels, mirroring the
  accelerator's scheme: a team level at `.luminosity/config.md` (committed) and a
  personal level at `.luminosity/config.local.md` (project-local, gitignored),
  both carrying YAML frontmatter. Personal precedence wins on conflict.
- The CLI is the reader: it parses the YAML frontmatter natively (no shell YAML
  parsing — this is exactly the deterministic work the CLI owns). The resolution
  logic lives in the hexagonal core and is exposed through a CLI command (e.g.
  `luminosity config get` / `set`).
- Realise the config hexagon as the `config` / `config-adapters` crate split
  (ADR-0010): the `config` core holds resolution (domain + application + ports)
  and depends on no serde / toml / filesystem crate; those concerns live in
  `config-adapters`, wired at the composition root. This is the workspace's first
  multi-crate hexagon, so the inward dependency direction is enforced here for the
  first time — by the Cargo graph and the cargo-deny ban-list from the toolchain
  story (0006).
- Ensure `.luminosity/config.local.md` is gitignored so personal config is never
  committed (mirroring how the accelerator's `init` handles `.local.md`).
- Provide a thin `configure` skill that orchestrates by invoking the CLI command;
  the skill carries no configuration logic of its own.
- Build test-first, with the precedence logic covered by core tests.

## Acceptance Criteria

- [ ] Given key `core.example` set to `team-value` in `.luminosity/config.md` and
      `personal-value` in `.luminosity/config.local.md`, when read via the CLI
      command (e.g. `luminosity config get core.example`), then it returns
      `personal-value`.
- [ ] Setting and inspecting the same key via the `configure` skill yields the
      same result as the CLI command (the skill drives the CLI).
- [ ] `.luminosity/config.local.md` is gitignored; the team file is committed.
- [ ] The precedence resolution lives in the `config` core crate and is covered by
      tests written test-first.
- [ ] The `config` core crate has no serde / toml / filesystem crate in its
      dependency closure (those live in `config-adapters`); a violation fails to
      compile and/or trips the cargo-deny ban-list.
- [ ] The `configure` skill contains orchestration only — no configuration logic
      that belongs in the CLI.

## Open Questions

- The configuration key namespace/schema beyond the single proof value is out of
  scope (A2); only what proves the two-level model is implemented now.

## Dependencies

- Blocked by: the scaffold story (0007, the config command lives in the
  workspace).
- Relies on: the toolchain story (0006) for the cargo-deny ban-list that enforces
  the `config` core's clean dependency closure — this is the first crate split
  where that ban-list does real work.
- Blocks: the eval-application story (0010, the `configure` skill is its eval
  target); the configuration-parity epic (0011, builds on this base model).
- Relates to: the configuration-parity epic (0011).
- Parent: epic 0001.

## Assumptions

- "Some degree of configuration" means enough to prove the multi-level model
  end-to-end (A2), not a complete configuration schema.
- The multi-level configuration model is recorded as an ADR (decision 3),
  now ADR-0003.

## Technical Notes

- This story is the canonical demonstration of the skills-vs-CLI division
  (decision 1); keep the skill thin and the logic in the CLI/core.
- Format/location mirrors the accelerator's consolidated layout
  (`.luminosity/config.md` + `.luminosity/config.local.md` under a dedicated
  plugin directory, YAML frontmatter), but the reader is the Rust CLI parsing
  YAML natively — not the accelerator's bash-3.2 line-by-line parser. The
  directory location and the model are fixed by ADR-0003.
- Precedence is personal-over-team (last-writer-wins, personal last), matching the
  accelerator's two-tier model.
- Per ADR-0010 the config domain is the `config` crate and its outbound readers
  (serde/toml/fs) are the `config-adapters` crate; "core" in this story means the
  `config` crate. Keeping infrastructure out of `config`'s closure is enforced by
  the cargo-deny ban-list (toolchain story 0006), and this is the first place that
  cross-crate enforcement is exercised.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (config resolution + CLI
  command + thin skill).
- Scope deliberately minimal per A2 — one resolvable value across two levels, not
  a full schema.
- Config format/location set to mirror the accelerator's consolidated
  `.luminosity/config*.md` directory (.md + YAML frontmatter) for familiarity,
  with the CLI as the native reader; personal level is project-local and
  gitignored, per the author. The directory location was settled by ADR-0003
  (originally drafted as `.claude/luminosity*.md`, then consolidated).
- Fuller accelerator config features (plugin-global body context, per-skill
  `context.md` / `instructions.md`, template-management subcommands) are
  explicitly out of scope here per A2, and captured as a separate future work
  item (0011, "Configuration Feature Parity with Accelerator") rather than
  expanding this proof slice.

- Added 2026-06-27 (from codebase research
  `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`): the
  `config` / `config-adapters` split is the workspace's first multi-crate hexagon,
  so the inward-dependency cargo-deny ban-list enforcement (designed in ADR-0009,
  mechanism in 0006) first becomes live and verifiable here — captured as an
  explicit requirement and acceptance criterion. Later per-subdomain enforcement
  is tracked in work item 0012.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
- Toolchain: `meta/work/0006-establish-rust-toolchain-guard-rails-in-mise-and-ci.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
