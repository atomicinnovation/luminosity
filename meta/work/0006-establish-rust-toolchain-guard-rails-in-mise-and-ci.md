---
type: work-item
id: "0006"
title: "Establish Rust Toolchain Guard Rails in mise + CI"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: in-progress
kind: story
priority: high
parent: "work-item:0001"
relates_to: ["work-item:0002", "work-item:0007", "work-item:0009", "work-item:0012"]
tags: [story, rust, tooling, ci, guard-rails, architecture-enforcement]
last_updated: "2026-06-27T16:30:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0006: Establish Rust Toolchain Guard Rails in mise + CI

**Kind**: Story
**Status**: In Progress
**Priority**: High
**Author**: Toby Clemson

## Summary

Stand up the Rust toolchain — format, lint, test, coverage, supply-chain, and
architecture enforcement — wired into `mise run` tasks and enforced in CI, so
Rust code is held to the same automated quality bar as the existing Python and
shell components.

## Context

The epic (0001) interprets "guard rails" as primarily the Rust toolchain. The
repo already runs Python and shell checks through `mise run`; this story adds the
Rust equivalents so the first Rust code (from the scaffold story) lands behind
enforced checks. The toolchain and scaffold stories are paired: there is nothing
to lint or test until Rust code exists, and the scaffold should not merge ahead
of the guard rails meant to enforce its quality.

Beyond the epic's format/lint/test/coverage/supply-chain stack, the hexagonal
architecture (ADR-0009) is enforced mechanically: cargo-pup on a pinned-nightly
lane for intra-crate module-import rules, and architectural cargo-deny ban-lists
at crate boundaries; this story owns those too. (The spike, 0002, also proposed a
CI grep tripwire as a cruder floor, but ADR-0009 deliberately omits it — treating
cargo-pup as sufficient — so it is intentionally not part of this story.)

## Requirements

Wire the following into `mise run` tasks and the existing `.github` CI workflows:

- **Formatting**: rustfmt via `cargo fmt --check`.
- **Linting**: clippy with pedantic + nursery + cherry-picked restriction lints,
  `-D warnings`.
- **Testing**: cargo-nextest (with proptest / insta adopted where they earn their
  place, not by default).
- **Coverage**: cargo-llvm-cov.
- **Supply-chain**: cargo-deny checking advisories, licenses, bans, and sources.
  The bans section also encodes two architectural rules: (a) the ban-lists that
  keep infrastructure crates out of the light/domain crates' dependency closures
  (per the spike, 0002, and ADR-0009); and (b) a workspace-wide ban on
  native-tls / OpenSSL so no transitive dependency re-enables `default-tls` and
  breaks the musl-static build — rustls is mandatory workspace-wide (ADR-0010).
- **Architecture enforcement** (ADR-0009): cargo-pup enforcing intra-crate
  module-import rules (the inward dependency direction), run as a blocking check on
  a pinned-nightly lane while the product build and every other check stay on
  stable. In the single-crate starting state cargo-pup is the sole enforcer of the
  inward rule — ADR-0009 deliberately omits the spike's grep-tripwire floor.

Integrate the Rust checks into the existing component-based mise task tree,
prefixed by component/crate — joining the existing `build-system` and `scripts`
components rather than introducing a generic `rust:` prefix:

- Per-crate check tasks scoped to each workspace member via `-p` — a
  `<crate>:check` component per crate folding rustfmt + clippy (the read-only
  `format:<crate>` / `lint:<crate>` leaves) for that crate only, consistent with
  the existing test-free `build-system:check` / `scripts:check` roll-ups. The
  per-crate tests (`test:unit:<crate>`) are **not** part of `<crate>:check`; they
  are wired into the `test` roll-up (via `test:unit`), exactly as the existing
  Python suite is, with **coverage folded into the test run** (`cargo llvm-cov
  nextest` by default, disable-able per-environment) rather than a separate
  coverage task. The concrete crate set tracks the workspace the scaffold (0007)
  creates under the subdomain-first layout from the spike (0002) and ADR-0010
  (`kernel`, `config`, `config-adapters`, `cli`, one crate per subdomain) — not a
  fixed `core` / `adapters` / `cli` triple, which the spike superseded.
- Workspace-scope tasks for checks that span the whole graph — cargo-deny (the
  dependency graph) and the cargo-pup nightly lane — each as its own task rather
  than per-crate.

The per-crate check tasks and the workspace-scope tasks (cargo-deny and cargo-pup)
are included in `mise run check` and the bare `mise run` default. `mise run check`
stays read-only and **test-free** — format, lint, and the cargo-deny/cargo-pup
static checks; the tests run via the `test` roll-up in the bare `mise run` default,
with coverage folded into that test run (so coverage runs on every test OS,
always), mirroring the repo's existing check/default split.

## Acceptance Criteria

- [ ] Given the Rust toolchain tasks, when `mise run check` is run, then it
      includes the per-crate format-check and clippy `-D warnings` for every
      workspace crate the scaffold creates, plus the workspace-scope
      `cargo deny check` and the cargo-pup architecture check, and exits 0.
      `mise run check` is read-only and **test-free**: the per-crate tests run via
      the `test` roll-up — with coverage folded into the test run (instrumented by
      default, on every test OS) rather than a separate coverage task — in the bare
      `mise run` (the heavy local-CI mirror), not in `mise run check`. This mirrors
      the repo's established check/default split, where `check` is read-only and
      fast and the bare `mise run` is the full gate (the full
      format/clippy/tests+coverage/deny/pup set runs in `mise run`).
- [ ] Given a Rust change that fails format-check, clippy, cargo-deny, or
      cargo-pup, when CI runs on a pull request, then the workflow fails and the
      PR is non-mergeable.
- [ ] `mise run` (the bare default task) exits 0 end-to-end with the Rust
      component included.
- [ ] The clippy configuration enables pedantic + nursery and the cherry-picked
      restriction lints, with `-D warnings` so any lint fails the build.
- [ ] cargo-deny is configured with advisories, licenses, bans, and sources
      sections — the bans section encoding both the architectural ban-lists that
      keep infrastructure crates out of the light/domain crates and a
      workspace-wide ban on native-tls / OpenSSL (rustls only) — and runs in both
      `mise run` and CI.
- [ ] cargo-pup runs as a blocking check on a pinned-nightly lane (the nightly
      pinned in `mise.toml`) in both `mise run check` and CI, while the product
      build and all other checks run on stable; a module-import violation fails
      the build.

## Open Questions

- Which specific restriction lints are cherry-picked? To be decided during
  implementation (the epic says "cherry-picked", not a fixed list).
- Which nightly toolchain version to pin for the cargo-pup lane. The spike fixes
  the approach (pin the exact nightly in `mise.toml`; fall back to advisory-only
  if a bump breaks cargo-pup); the specific version is chosen at implementation.

## Dependencies

- Paired with: the scaffold story (0007) — needs Rust code to lint/test; both
  land before the two `mise run` green-build criteria can pass.
- Blocked by: none hard, but only meaningful once the scaffold provides Rust
  code.
- Parent: epic 0001.

## Assumptions

- The specific Rust tool choices come from the epic (0001), within the
  three-toolchain split framed by ADR-0004; no dedicated ADR ratifies the
  rustfmt / clippy / nextest / llvm-cov / cargo-deny stack, so this story
  implements the epic's choices directly. The architecture-enforcement tools
  (cargo-pup and the cargo-deny ban-lists) derive from ADR-0009; the grep tripwire
  the spike (0002) proposed is deliberately excluded by ADR-0009.
- Tool versions are pinned in `mise.toml` consistent with the existing toolchain
  pinning convention — including the pinned nightly for the cargo-pup lane and the
  cargo-nextest / cargo-llvm-cov / cargo-deny / cargo-pup tools, which are not yet
  present in `mise.toml`.

## Technical Notes

- Line width is 80 everywhere; rustfmt's width is duplicated by hand into
  `rustfmt.toml` (it does not read `.editorconfig`) — keep in sync with the
  other components. `rustfmt.toml`, `clippy.toml`, and `deny.toml` do not yet
  exist and must be created.
- cargo-llvm-cov and cargo-nextest compose (`cargo llvm-cov nextest`).
- Per-crate scoping uses `cargo <tool> -p <crate>`. cargo-deny and cargo-pup have
  no per-crate notion: cargo-deny runs once over the workspace dependency graph,
  and cargo-pup runs once over the workspace on its nightly lane.
- The workspace is subdomain-first (`kernel`, `config`, `config-adapters`, `cli`,
  one crate per subdomain) per the spike (0002) and ADR-0010 — not the
  `core` / `adapters` / `cli` triple this story originally assumed. The per-crate
  `-p` task names track the actual crates the scaffold (0007) creates.
- cargo-pup runs on a pinned-nightly toolchain (pinned in `mise.toml`) while
  everything else stays on stable; a nightly bump that breaks cargo-pup blocks
  merges, so the nightly is pinned and the fallback is downgrading cargo-pup to
  advisory (per the spike's risk note). ADR-0009 deliberately omits the spike's
  grep-tripwire floor, accepting that in the single-crate phase cargo-pup is the
  sole enforcer of the inward rule — do not re-add the tripwire without revisiting
  ADR-0009.
- cargo-deny's bans section is load-bearing for architecture, not only
  supply-chain: it keeps infrastructure crates out of the light/domain crates'
  dependency closures (ADR-0009) and bans native-tls / OpenSSL workspace-wide so
  the musl-static build cannot regress to `default-tls` (ADR-0010). The
  cross-crate ban-lists are largely inert until the workspace splits into multiple
  crates — they first bite at the `config` / `config-adapters` split (story 0009),
  with the later per-subdomain and `cli`-never-depends-on-a-subdomain rules tracked
  separately (work item 0012).
- Component task naming follows the existing `<component>:check` convention
  (see `tasks/README.md` for the task-tree shape); the crates are the new
  components. The repo already provisions rust (rustfmt + clippy) and Rust-aware
  release scaffolding (`tasks/deps.py`, `tasks/shared/targets.py`,
  `tasks/shared/paths.py`); note `tasks/shared/paths.py` currently hard-codes a
  single `cli/Cargo.toml` at repo root and will need revisiting for the
  multi-crate workspace.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (the toolchain wiring).
- Pairing with the scaffold story carried from the epic's Intra-epic ordering
  (recorded as `relates_to`, not a strict block, since the order is mutual).
- The exact restriction-lint set is left open deliberately, matching the epic's
  "cherry-picked" language.
- Updated 2026-06-27 from codebase research
  (`meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`):
  reconciled the stale `core` / `adapters` / `cli` crate triple with the
  subdomain-first layout ratified by the spike (0002) and ADR-0010; folded in the
  ADR-0009 architecture-enforcement guard rails (cargo-pup on a nightly lane,
  architectural cargo-deny ban-lists); and corrected the Assumptions to reflect
  that no dedicated ADR ratifies the quality-tool choices.
- Corrected 2026-06-27: removed the CI grep tripwire (initially folded in from the
  spike) after ADR-0009 was found to deliberately omit it; added the
  workspace-wide rustls / no-native-tls cargo-deny ban (ADR-0010). Cross-crate
  ban-list enforcement that only bites once the workspace splits is homed in story
  0009 (config) and new work item 0012 (subsequent crates).
- Corrected 2026-06-27: moved tests out of `mise run check` to honour the repo's
  established check/default split. `check` is now read-only and test-free (format
  + lint + the cargo-deny/cargo-pup static checks); the per-crate tests run via the
  `test` roll-up (per-suite `test:unit` aggregate) in the bare `mise run` default —
  matching how the existing Python and shell suites are wired. AC1 reworded
  accordingly.
- Corrected 2026-06-27: folded coverage **into** the test run rather than a
  separate coverage task/family — `test:unit:<crate>` runs `cargo llvm-cov nextest`
  by default, so coverage runs on every test OS (linux + macOS), always, with a
  `LUMINOSITY_COVERAGE=off` env toggle for a faster non-instrumented inner loop.
  This removes the prior plain-then-instrumented double execution.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Spike: `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- `meta/decisions/ADR-0004-three-toolchain-split.md`
- `meta/decisions/ADR-0006-mise-invoke-task-runner.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- Research: `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
