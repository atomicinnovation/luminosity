---
type: work-item
id: "0002"
title: "Modular Rust CLI Architecture & Hexagonal Workspace Layout"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: spike
priority: high
parent: "work-item:0001"
blocks: ["work-item:0005", "work-item:0007", "work-item:0008"]
tags: [spike, rust, cli, architecture, hexagonal]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0002: Modular Rust CLI Architecture & Hexagonal Workspace Layout

**Kind**: Spike
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Resolve how to structure the Luminosity Rust CLI as a modular, git-style command
over a hexagonal core, evaluating current options on merit, so the dependent
scaffold, distribution, and spike-dependent ADR stories proceed on settled
foundations. Time-boxed to 3 days.

## Context

The epic (0001) commits to a thin CLI over a ports-and-adapters core, presented
as a single `luminosity` command that dispatches to on-demand sub-binaries. The
author is not deeply familiar with structuring a modularised Rust CLI or
splitting crates across CLI / domain / persistence, so this spike de-risks those
choices before the scaffold story begins. The accelerator's solved approach is
one input among several — the spike evaluates alternatives rather than adopting
it by default.

## Requirements

Research questions to resolve, time-boxed to **3 days**:

- **Crate split & dependency direction.** Confirm the lean `core` (domain +
  ports as traits + application) / `adapters` (port impls) / `cli` (composition
  root) workspace layout, and how the inward dependency direction is enforced.
  (Research finding: the Cargo dependency graph is itself the primary enforcement
  — `core` simply does not depend on `adapters`/I/O crates and a violation won't
  compile — reinforced by a `cargo-deny` ban-list keeping infra crates out of
  `core`. No ArchUnit-equivalent exists for Rust. Reference: howtocodeit/hexarch,
  which models the trait/`Service` core within a single crate — evaluate whether
  the multi-crate split earns its keep now or later.)
- **Git-style dispatch.** Validate clap 4.x `allow_external_subcommands` /
  `#[command(external_subcommand)]` collecting `Vec<OsString>` (not `String`, to
  pass non-UTF-8 args); first positional as subcommand, everything after handed
  off verbatim. Decide how to synthesise `--help`/a plugin listing (clap won't
  generate help for external subcommands) and `exec` on Unix vs spawn+wait on
  Windows. Compare rustup's shim/proxy model and uv's resolve-once-and-cache
  model.
- **On-demand launcher.** Decide the fetch → verify → cache → exec pipeline:
  `reqwest`(rustls) or `self_update`(rustls feature) for download, `sha2` for
  checksum, signature verification (zipsign/minisign), a managed bin dir for
  caching, `self-replace` for the launcher's own self-update. Confirm
  `default-features = false` + rustls throughout (native-tls pulls OpenSSL on
  Linux and breaks musl-static).
- **Cross-compile & distribution (scan, defer detail to the distribution
  story).** Note current best practice — `cargo-zigbuild` for musl-static/macOS
  cross, `cross` as fallback for awkward native deps, `dist` (formerly
  cargo-dist, v0.32+) for signed/checksummed per-platform artifacts — and
  confirm which of these the accelerator already uses before re-selecting.

Output: a written recommendation with a decision, evaluating the alternatives
above, recorded directly in this spike work item (a `Recommendation` section
added when the spike concludes). The spike-dependent ADRs (decisions 9–10) cite
this work item, and the scaffold and distribution stories reference it when they
are implemented. A throwaway proof-of-concept of the dispatch/launcher exec path
is optional, not required.

## Acceptance Criteria

- [ ] Given the 3-day time-box, when the spike concludes, then this work item
      contains a Recommendation section naming a chosen crate split, dispatch
      mechanism, launcher pipeline, and cross-compile/distribution toolchain,
      each with the alternatives considered and the rationale for the choice.
- [ ] The Recommendation explicitly states whether the multi-crate
      core/adapters/cli split is adopted now or deferred, and how the inward
      dependency direction is enforced.
- [ ] The spike-dependent ADR(s) for decisions 9–10 cite this work item, and the
      scaffold and distribution stories reference it when implemented.

## Open Questions

- Whether the hexagonal split starts multi-crate or begins single-crate
  (hexarch-style) and splits later — to be decided by the recommendation.

## Dependencies

- Blocks: scaffold story (0007), distribution story (0008), spike-dependent ADR
  story (0005).
- Blocked by: none.
- Parent: epic 0001.

## Assumptions

- The hexagonal split is crate-level, not module-level (per the epic's Technical
  Notes) — though the spike may recommend a single-crate start, given the leading
  reference (hexarch) does hexagonal well within one crate.

## Technical Notes

- clap 4.x external-subcommand support is stable and ergonomic; ignore older
  clap 2/3 `AppSettings` workarounds in stale articles.
- rustls + webpki-roots keeps the launcher independent of the host cert store and
  statically linkable; audit the dep tree so no transitive dep re-enables
  `default-tls`.
- `self_update` is steady but low-velocity and oriented at self-replacement; for
  a multi-sub-binary launcher, compose download/verify/cache primitives directly
  and use `self-replace` only for the launcher's own update.

## Drafting Notes

- Kind set to `spike` because the epic frames this as resolving an unknown via
  research with a written recommendation, not a deliverable.
- Latitude set to genuine evaluation of alternatives (per the author); the
  accelerator is one input, not the default.
- Output framed so the recommendation is recorded in this spike work item itself
  (per the author); dependent stories and ADRs reference this work item rather
  than the decisions being copied into them.
- Enriched with web research (clap 4.x dispatch, rustls launcher, hexarch,
  cargo-zigbuild/dist) current as of mid-2026.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Research: clap external subcommands (docs.rs/clap 4.6.x); rustup proxy/shim
  model; uv tool caching; howtocodeit/hexarch (hexagonal in Rust); cargo-zigbuild
  v0.23; dist (formerly cargo-dist) v0.32; self_update / self-replace; rustls vs
  native-tls.
