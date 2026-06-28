---
type: pr-description
id: "1"
title: "[0006] Add Rust guard rails"
date: "2026-06-28T14:02:03+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
parent: "work-item:0006"
relates_to: ["work-item:0002", "work-item:0007", "work-item:0009", "work-item:0012"]
work_item_id: "0006"
pr_url: "https://github.com/atomicinnovation/luminosity/pull/1"
pr_number: 1
tags: []
revision: "59850e0d06d8d0e34e173fd6e16bedbcf141c89d"
repository: "luminosity"
last_updated: "2026-06-28T14:02:03+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# [0006] Add Rust guard rails

## Summary

Establishes the full Rust quality toolchain (work item 0006) for Luminosity's
shipped CLI: a minimal buildable Cargo workspace plus the formatting, linting,
testing/coverage, supply-chain, and architecture-enforcement lanes — all wired
into the `mise` task tree and mirrored in CI. The `cli/` crate is an
intentional throwaway bootstrap so the toolchain has real code to run against;
story 0007 replaces its body with the hexagonal `version` subcommand.

## Changes

Delivered as five sequenced phases:

- **Phase 1 — Workspace + rustfmt + clippy.** Versionless `[package]`-free root
  workspace manifest with the product version homed in `cli/Cargo.toml`. Shared
  clippy lint *levels* live in `[workspace.lints.clippy]` (`-D warnings`,
  pedantic + nursery + cherry-picked restriction lints); `clippy.toml` holds
  config + `msrv`. A test-free `cli:check` (format + lint) roll-up joins
  `check`; an OS-aware host-native `build:cli` release build joins the bare
  `mise run` default.
- **Phase 2 — cargo-nextest + cargo-llvm-cov.** A `test:unit:cli` leaf folds
  into the existing `test:unit` → `test` roll-up. Coverage is folded into the
  test run (instrumented `cargo llvm-cov nextest`, report-only, no threshold),
  with `LUMINOSITY_COVERAGE=off` dropping to a plain `cargo nextest run` for a
  faster inner loop (read at call time, never frozen at import).
- **Phase 3 — cargo-deny supply-chain + architectural ban-lists.** `deny.toml`
  encodes the live workspace-wide native-tls/OpenSSL ban (ADR-0010, rustls
  only) plus scaffolded — and deliberately inert until the workspace splits —
  architectural infra-crate ban-lists (ADR-0009). `deny:check` is a
  workspace-scope static check joining both `check` and the default.
- **Phase 4 — cargo-pup architecture lane.** The sole inward-direction
  architecture enforcer (ADR-0009), blocking, on a pinned
  `nightly-2026-01-22` + cargo-pup 0.1.8 while everything else stays on stable.
  rustup-provisioned by an idempotent `deps:install:pup` task (mise cannot pin
  two rust toolchains); `pup:check` `depends` on it so a fresh checkout
  self-provisions. `pup.ron` is intentionally empty (story 0007 adds the
  layering rules). `LUMINOSITY_PUP_MODE=warn` downgrades the lane to advisory
  without a source edit.
- **Phase 5 — Aggregation, docs, runbook.** Reconciled `check`/`default` task
  descriptions, the `CLAUDE.md` "done means `mise run`" paragraph, and a
  durable `CONTRIBUTING.md` runbook for registering the new required-check
  names under branch protection.

Supporting work:

- **CI (`.github/workflows/main.yml`):** new `check-cli`, `build-cli` (dual-OS
  matrix), `check-supply-chain`, and `check-architecture` jobs, all in the
  release `needs:` list; workflow-wide least-privilege token default and
  SHA-pinning of every third-party action.
- **Tooling pins (`mise.toml`):** cargo-nextest, cargo-llvm-cov, cargo-deny,
  and the llvm-tools-preview component; cargo-pup + its nightly remain
  rustup-managed by design.
- **Build-system tests:** TDD task-module unit tests across format/lint/build/
  test/deny/pup/deps, a `tomllib`-parsed `test_mise_wiring.py` pinning the
  enumerated `check`/`default`/`test:unit` arrays and toolchain-version
  coherence, `test_workflows.py` asserting the four Rust CI jobs, and isolated
  integration regressions proving the cargo-deny ban and a cargo-pup rule
  violation actually fail their lanes.
- **Meta artifacts:** the 0006 research, plan, two plan reviews, and validation
  report; plus reconciliation of work items 0001–0005 and 0007/0009 and the
  new 0012 (cross-crate enforcement as the workspace grows).

## Context

- Implements work item **0006** — *Establish Rust toolchain guard rails in mise
  and CI* (`meta/work/0006-...md`).
- Plan: `meta/plans/2026-06-27-0006-establish-rust-toolchain-guard-rails.md`
  (reviewed in `meta/reviews/plans/...review-1.md` / `...review-2.md`).
- Validation: `meta/validations/2026-06-27-0006-...-validation.md`.
- Decisions enforced: **ADR-0009** (inward-direction architecture enforcement
  via cargo-pup) and **ADR-0010** (rustls-only / no native-tls).
- Follow-on work: **0007** (hexagonal workspace + `version` subcommand
  replacing the bootstrap crate), **0009** (first cross-crate ban-list
  enforcement), **0012** (workspace-growth enforcement).

## Testing

- [x] `mise run check` (read-only CI mirror: format + lint + types across all
      components, plus `deny:check` / `pup:check`) — exits 0, independently
      re-run for this description.
- [x] Full `mise run` default verified green end-to-end in the committed
      validation report: 133-test task unit suite, the cargo-deny and
      cargo-pup behavioural regressions, and the host-native `build:cli`
      release build all pass.
- [x] Both green-build acceptance criteria for 0006 verified against
      repository state (validation report).
- [ ] CI required-check registration under branch protection — must be done
      manually per the `CONTRIBUTING.md` runbook once the new jobs land (the
      `build-cli` matrix legs and the run-once-first gotcha apply).

## Notes for Reviewers

- **Bootstrap crate is throwaway by design** — `cli/src/{lib,main}.rs` is a
  trivial function + test purely so the toolchain has code to run against;
  story 0007 replaces it. Don't review it as product code.
- **Two intentionally-inert pieces:** `pup.ron` is empty and the cross-crate
  `deny.toml` architectural ban-lists stay dormant until the workspace splits
  into multiple crates — both are scaffolding for 0007/0009/0012, not dead
  config.
- **cargo-pup is the one toolchain on nightly** and is *blocking*. If a
  nightly/cargo-pup bump breaks it, `LUMINOSITY_PUP_MODE=warn` downgrades it
  per-environment without a source edit; a nightly-GC break instead fails in
  `deps:install:pup` and is recovered by bumping `PUP_NIGHTLY` + `PUP_VERSION`
  together.
- **Hand-synced mirrors to watch:** the 80-col line width (`.editorconfig` →
  `rustfmt.toml`) and `clippy.toml`'s `msrv` (mirrors the `mise.toml` rust
  pin); `test_mise_wiring.py` asserts the `msrv`/rust-pin coherence.
- The `deny:check` "license was not encountered" lines are non-fatal advisory
  warnings (`advisories ok, bans ok, licenses ok, sources ok`); the lane exits
  0.
- Branch-protection mergeability is **not** testable from the repo — the CI
  guard tests assert job topology only; the required-check registration step
  above is the manual follow-up.
