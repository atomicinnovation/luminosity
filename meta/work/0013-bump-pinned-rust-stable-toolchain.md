---
type: work-item
id: "0013"
title: "Bump the Pinned Rust Stable Toolchain and Reduce Dependency-Pin Friction"
date: "2026-06-29T07:52:07+00:00"
author: Toby Clemson
producer: create-work-item
status: draft
kind: task
priority: low
parent: "work-item:0001"
relates_to: ["work-item:0006", "work-item:0007"]
tags: [rust, toolchain, mise, msrv, dependencies, maintenance]
last_updated: "2026-06-29T07:52:07+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0013: Bump the Pinned Rust Stable Toolchain and Reduce Dependency-Pin Friction

**Kind**: Task
**Status**: Draft
**Priority**: Low
**Author**: Toby Clemson

## Summary

Raise the pinned Rust stable toolchain past 1.90 and remove the
dependency-version-pinning workarounds the 1.90 ceiling forced during work item
0007. This is maintenance/friction-reduction: the current pins work, but they
hold the project ~6 releases behind stable and require non-obvious exact pins to
keep MSRV-compatible.

## Context

Story 0006 stood up the Rust toolchain and pinned its versions (rustfmt, clippy,
nextest, llvm-cov, cargo-deny, and the cargo-pup blocking nightly lane), treating
the specific versions as point-in-time implementation choices. The Rust stable
pin landed at 1.90.0 with the MSRV mirrored by hand into `clippy.toml` (coherence
asserted by `tests/unit/tasks/test_mise_wiring.py`).

While implementing 0007, that 1.90 ceiling forced the build-metadata adapter onto
the vergen 9.x line (vergen 10.x requires Rust 1.95), and to stay MSRV-compatible
it needed an exact `vergen = "=9.0.6"` pin (9.1.0 bumped `vergen-lib`
incompatibly with `vergen-gitcl 1.0.8`, producing a duplicate-`vergen-lib` build
break) plus a transitive `cargo-platform 0.3.2` lock pin (0.3.3 needs Rust 1.91).

Luminosity ships **self-contained static binaries** (ADR-0002), not a published
crates.io library, so there is no downstream consumer whose older toolchain the
MSRV protects — the classic "low MSRV = wider compatibility" benefit does not
apply. Meanwhile the cargo-pup architecture lane already runs on a 1.95 nightly
(`nightly-2026-01-22`), leaving stable and nightly 5 versions apart. ADR-0006
documents the *pinning philosophy* (reproducible, version-pinned provisioning so
local mirrors CI) but records no rationale for 1.90 specifically.

## Requirements

- Raise the Rust stable pin in `mise.toml` and re-sync the hand-mirrored
  `clippy.toml` `msrv` in lockstep (coherence is asserted by
  `tests/unit/tasks/test_mise_wiring.py`).
- Choose a target version and record why. Candidate: the latest stable that
  builds cleanly under the existing pinned cargo-pup nightly, narrowing the
  current 5-version stable↔nightly gap.
- Collapse the 0007 vergen workarounds: drop the exact `vergen = "=9.0.6"` pin
  and the explicit `vergen` build-dependency, move to a plain
  `vergen-gitcl = "10"` (with `vergen` on the 10.x line), and drop the
  transitive `cargo-platform 0.3.2` lock pin.
- Re-resolve and re-freeze `Cargo.lock`; confirm no remaining crate declares a
  `rust-version` exceeding the new pin.
- Fix any new clippy `pedantic`/`nursery` findings the newer toolchain activates
  under the `-D warnings` wall.
- Leave the cargo-pup nightly lane and all other pinned tools (uv, python, gh,
  shellcheck, shfmt, actionlint) unchanged.

## Acceptance Criteria

- [ ] Given the bumped pin, when `mise run` is executed, then it exits 0
      end-to-end (format/lint/types, full test suite, `build:cli`, `deny:check`,
      `pup:check`).
- [ ] Given the new pin, `clippy.toml` `msrv` equals the `mise.toml` Rust version
      (the `test_mise_wiring.py` coherence assertion passes).
- [ ] Given the bump, the manifests carry no `=9.0.6` exact pin, no explicit
      `vergen` build-dependency, and no `cargo-platform` pin; `vergen-gitcl` and
      `vergen` resolve on the 10.x line.
- [ ] Given the re-resolved `Cargo.lock` (committed), every crate's declared
      `rust-version` is ≤ the new Rust pin.

## Open Questions

- What is the project's deliberate Rust-pin / bump cadence — track latest
  stable, stable-minus-one, align to the cargo-pup nightly, or bump every N
  releases? (Formalizing this as an ADR/CONTRIBUTING note is out of scope here;
  this item just surfaces the question.)
- Exact target version: the latest stable, or the newest confirmed compatible
  with the pinned cargo-pup nightly?

## Dependencies

- Relates to: 0006 (stood up the toolchain pins), 0007 (introduced vergen and
  surfaced the pinning friction).
- Parent: epic 0001 (Baseline Architecture and Engineering Guard Rails,
  Theme 2 — Rust toolchain guard rails).

## Assumptions

- The cargo-pup nightly lane stays put and stable moves up toward it (not the
  reverse), so a bump narrows rather than widens the stable↔nightly gap.
- No external/downstream consumer depends on luminosity as a crates.io library,
  so the pin is purely a build-toolchain choice with no compatibility contract.

## Technical Notes

- The 80-column width is mirrored by hand into `.editorconfig` / `rustfmt.toml` /
  `pyproject.toml`, and `clippy.toml`'s `msrv` is a fourth hand-synced mirror of
  the `mise.toml` Rust pin — only the `msrv` mirror is relevant to this bump, and
  `test_mise_wiring.py` fails loudly if it drifts.
- The lint wall is strict (`warnings = "deny"` + clippy pedantic/nursery); a
  newer stable may surface new lints, so budget for a small lint-fix pass.

## Drafting Notes

- Framed as a Task (concrete, bounded mechanical change) rather than a Spike —
  the cadence question is captured as an Open Question, not made the deliverable
  (per the requester's chosen scope: bump + cleanup).
- Priority Low: the 0007 vergen 9.x pinning works today, so there is no
  functional gap or deadline; this is overhead removal.
- Scoped to the stable pin + the vergen/cargo-platform cleanup only; deliberately
  excludes bumping other pinned tools and excludes formalizing the cadence policy.

## References

- Related: 0006, 0007; parent epic 0001
- `meta/decisions/ADR-0006-mise-invoke-task-runner.md` — pinning philosophy
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — static-binary distribution (no library MSRV contract)
- `meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md` — where the vergen 9.x / cargo-platform pins were introduced
