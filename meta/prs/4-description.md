---
type: pr-description
id: "4"
title: "Scaffold the hexagonal Rust workspace with a version subcommand (0007)"
date: "2026-07-02T00:10:04+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "0007"
parent: "work-item:0007"
relates_to: ["work-item:0013"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/4"
pr_number: 4
tags: [rust, cli, hexagonal, scaffold, cargo-pup, vergen, kernel]
revision: "8e05e3f801a8e735c37f7111df284277873d4516"
repository: "luminosity"
last_updated: "2026-07-02T00:10:04+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Scaffold the hexagonal Rust workspace with a version subcommand (0007)

## Summary

Implements work item 0007: replaces the throwaway `describe_release` bootstrap
with a genuine, minimal hexagon for `luminosity version`, adds a
dependency-light `kernel` crate, and turns cargo-pup into the live, sole
enforcer of the inward dependency rule. The value is structural — a real
ports-and-adapters skeleton later stories build on — not the feature itself.
Built test-first, in three independently-mergeable phases.

## Changes

**Phase 1 — `kernel` crate + task-tree wiring**
- New `kernel` library crate holding the cross-cutting error taxonomy (an
  uninhabited `Error` today, with a contract test asserting it satisfies
  `std::error::Error`).
- Per-crate `format`/`lint`/`test` task modules and a `kernel:check` roll-up,
  deliberately excluded from the aggregate `check` (the workspace-wide
  `cli:check` pass already covers it); `test:unit:kernel` threaded into
  `test:unit`.

**Phase 2 — the `version` hexagon inside `cli`**
- A presentation-free core defining both ports (inbound `ReportVersion`,
  outbound `BuildMetadata`), a clap inbound adapter, a vergen outbound adapter,
  and a composition root in `main.rs` that maps `kernel::Error` to an exit code.
- `cli/build.rs` injects commit SHA, build timestamp, and target triple via
  vergen. Dependencies are pinned MSRV-first (≤ 1.90) and frozen in
  `Cargo.lock`; both crates are `publish = false`.

**Phase 3 — cargo-pup inward-direction enforcement**
- A fail-closed `RestrictImports` rule in `pup.ron` constraining what
  `version::core` may import, proven live by behavioural tests (a
  domain→adapter import is rejected; its removal goes green) and a binding test
  that confirms the rule is attached to the real core module.

## Context

Implements work item 0007 per its implementation plan
(`meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md`). The
hexagonal ports-and-adapters structure and the inward-dependency rule follow
ADR-0009; the `kernel`/`cli` split and `version`-as-built-in follow ADR-0010.
Stacked on #3 (the planning/research PR).

## Testing

- [x] `mise run check` — format/lint/types + cargo-deny + cargo-pup, green.
- [x] `mise run test` — 161 task tests, the cli core-against-fake unit test, the
      black-box `version` binary test, and the kernel contract test all pass.
- [x] `mise run build:cli` and the full `mise run` mirror verified green during
      implementation.
- [x] cargo-pup enforcement proven live: injecting a `use
      crate::version::outbound::…` into the core fails `pup:check`; removing it
      restores green.
- [x] Degraded-build path handled: the vergen adapter reads git facts via
      `option_env!(…).unwrap_or("unknown")`, so a git-less build still compiles.

## Notes for Reviewers

- **Dependency pinning is the subtle bit.** `vergen` is pinned *exactly* to
  `=9.0.6`: a floating caret reaches 9.1.0, whose `vergen-lib` bump is
  incompatible with `vergen-gitcl 1.0.8` and drags in two `vergen-lib` versions
  that break the `Emitter` bound. vergen 10.x is off-limits (needs Rust 1.95).
  The follow-up to revisit the Rust pin is captured as work item 0013.
- `deny.toml` gains `allow-wildcard-paths` and both crates are `publish = false`
  so the `cli → kernel` path dependency isn't flagged as a wildcard.
- The cargo-pup rule's `matches` uses the resolved module path while
  `allowed_only` matches literal `use`-path text — a cargo-pup v0.1.8 quirk
  worth knowing when editing the rule.
- Stacked PR: based on #3; followed by #5 (work item 0013) and #6 (tooling).
