---
type: work-item
id: "0006"
title: "Establish Rust Toolchain Guard Rails in mise + CI"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
relates_to: ["work-item:0007"]
tags: [story, rust, tooling, ci, guard-rails]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0006: Establish Rust Toolchain Guard Rails in mise + CI

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Stand up the Rust toolchain — format, lint, test, coverage, supply-chain — wired
into `mise run` tasks and enforced in CI, so Rust code is held to the same
automated quality bar as the existing Python and shell components.

## Context

The epic (0001) interprets "guard rails" as primarily the Rust toolchain. The
repo already runs Python and shell checks through `mise run`; this story adds the
Rust equivalents so the first Rust code (from the scaffold story) lands behind
enforced checks. The toolchain and scaffold stories are paired: there is nothing
to lint or test until Rust code exists, and the scaffold should not merge ahead
of the guard rails meant to enforce its quality.

## Requirements

Wire the following into `mise run` tasks and the existing `.github` CI workflows:

- **Formatting**: rustfmt via `cargo fmt --check`.
- **Linting**: clippy with pedantic + nursery + cherry-picked restriction lints,
  `-D warnings`.
- **Testing**: cargo-nextest (with proptest / insta adopted where they earn their
  place, not by default).
- **Coverage**: cargo-llvm-cov.
- **Supply-chain**: cargo-deny checking advisories, licenses, bans, and sources.

Integrate the Rust checks into the existing component-based mise task tree,
prefixed by component/crate — joining the existing `build-system` and `scripts`
components rather than introducing a generic `rust:` prefix:

- Per-crate check tasks scoped to each crate via `-p`: `core:check`,
  `adapters:check`, `cli:check` (and their `format:<crate>` / `lint:<crate>` /
  `test:<crate>` leaves), each running rustfmt, clippy, nextest, and coverage
  for that crate only.
- Supply-chain (cargo-deny) runs at workspace scope — it operates on the whole
  dependency graph — as its own task rather than per-crate.

The per-crate check tasks and the workspace cargo-deny task are included in
`mise run check` and the bare `mise run` default.

## Acceptance Criteria

- [ ] Given the Rust toolchain tasks, when `mise run check` is run, then it
      includes the per-crate checks (format-check, clippy `-D warnings`, tests,
      coverage for `core`, `adapters`, `cli`) and the workspace `cargo deny
      check`, and exits 0.
- [ ] Given a Rust change that fails format-check or clippy, when CI runs on a
      pull request, then the workflow fails and the PR is non-mergeable.
- [ ] `mise run` (the bare default task) exits 0 end-to-end with the Rust
      component included.
- [ ] The clippy configuration enables pedantic + nursery and the cherry-picked
      restriction lints, with `-D warnings` so any lint fails the build.
- [ ] cargo-deny is configured with advisories, licenses, bans, and sources
      sections and runs in both `mise run` and CI.

## Open Questions

- Which specific restriction lints are cherry-picked? To be decided during
  implementation (the epic says "cherry-picked", not a fixed list).

## Dependencies

- Paired with: the scaffold story (0007) — needs Rust code to lint/test; both
  land before the two `mise run` green-build criteria can pass.
- Blocked by: none hard, but only meaningful once the scaffold provides Rust
  code.
- Parent: epic 0001.

## Assumptions

- The specific Rust tool choices are ratified as ADRs (A3) — this story
  implements them; the rationale lives in the corresponding ADRs.
- Tool versions are pinned in `mise.toml` consistent with the existing toolchain
  pinning convention.

## Technical Notes

- Line width is 80 everywhere; rustfmt's width is duplicated by hand into
  `rustfmt.toml` (it does not read `.editorconfig`) — keep in sync with the
  other components.
- cargo-llvm-cov and cargo-nextest compose (`cargo llvm-cov nextest`).
- Per-crate scoping uses `cargo <tool> -p <crate>`; cargo-deny has no per-crate
  notion and runs once over the workspace dependency graph.
- Component task naming follows the existing `<component>:check` convention
  (see `tasks/README.md` for the task-tree shape); the crates are the new
  components.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (the toolchain wiring).
- Pairing with the scaffold story carried from the epic's Intra-epic ordering
  (recorded as `relates_to`, not a strict block, since the order is mutual).
- The exact restriction-lint set is left open deliberately, matching the epic's
  "cherry-picked" language.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
