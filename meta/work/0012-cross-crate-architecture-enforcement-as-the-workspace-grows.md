---
type: work-item
id: "0012"
title: "Cross-Crate Architecture Enforcement as the Workspace Grows"
date: "2026-06-27T11:51:56+00:00"
author: Toby Clemson
producer: create-work-item
status: draft
kind: story
priority: medium
parent: "work-item:0001"
relates_to: ["work-item:0006", "work-item:0009", "work-item:0014", "adr:ADR-0009", "adr:ADR-0010"]
tags: [story, rust, architecture-enforcement, cargo-deny, guard-rails]
last_updated: "2026-07-02T23:46:13+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0012: Cross-Crate Architecture Enforcement as the Workspace Grows

**Kind**: Story
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

Extend the cargo-deny ban-lists and verify the inward dependency direction at each
new crate boundary as the workspace grows beyond the scaffold and config —
specifically the `launcher`-never-depends-on-a-subdomain rule, the
`kernel`-stays-dependency-light rule, and each new `luminosity-<sub>` crate's clean
dependency closure — so the hexagonal direction stays mechanically enforced as
subdomains are added.

## Context

ADR-0009 makes crate boundaries the **primary** enforcement of the inward
dependency rule (the Cargo graph plus cargo-deny ban-lists), but those boundaries
are "initially inert" — in the single-crate starting state `cargo-pup` is the
sole enforcer. The toolchain story (0006) provides the cargo-deny mechanism and
the baseline ban-lists; the config story (0009) applies cross-crate enforcement
for the first time at the `config` / `config-adapters` split. This story covers
the enforcement that only becomes meaningful **later** — when the launcher's
relationship to subdomains and the first independently-shipped `luminosity-<sub>`
crates exist.

It exists because that enforcement currently has no home: 0006 owns the mechanism,
0009 owns the first application, but the rules that guard the growing workspace
(`launcher` ↛ subdomain, `kernel` stays light, each subdomain's closure) are
designed in ADR-0009 / ADR-0010 and otherwise unowned. Note there is **no subdomain
(e.g. ads, video) work item yet**, so this story is forward-looking: its concrete
work is triggered by the first such crate.

## Requirements

- **`launcher` never depends on a subdomain crate** (ADR-0010): a cargo-deny
  ban-list entry forbidding any `luminosity-<sub>` crate from entering the
  `launcher` crate's (the `luminosity` launcher's) dependency closure. The
  launcher reaches subdomains only via on-demand `exec`
  dispatch, never as a compile-time dependency.
- **`kernel` stays dependency-light** (ADR-0010): a cargo-deny ban-list keeping
  dependency tails out of `kernel`'s closure (it is linked by everything), so a
  heavy dependency cannot silently enter it.
- **Each new `luminosity-<sub>` crate**: as a subdomain crate is introduced, add
  its inward-direction enforcement — its domain/application core depends on no
  infrastructure crate, with infra confined to the subdomain's outbound adapters —
  enforced by the Cargo graph and an extension of the cargo-deny ban-list.
- Each rule is wired as a blocking check reusing the workspace-scope cargo-deny
  task from 0006, so it runs in `mise run check` and CI.

## Acceptance Criteria

- [ ] The `launcher` crate's (the `luminosity` launcher's) dependency closure
      contains no `luminosity-<sub>` subdomain crate; introducing such a
      dependency trips cargo-deny and fails the build.
- [ ] `kernel`'s dependency closure stays within its declared light-dependency
      allow-set; adding a disallowed (heavy) dependency trips cargo-deny.
- [ ] For each subdomain crate that exists, its domain/application core has no
      infrastructure crate in its closure; a violation fails to compile and/or
      trips cargo-deny.
- [ ] All three checks run under `mise run check` and CI as part of the
      workspace-scope cargo-deny task.

## Open Questions

- There is no subdomain (ads/video) work item yet, so the trigger for the
  per-subdomain rules is unscheduled. The `launcher` ↛ subdomain and
  `kernel`-light bans could be authored **preventively** (they cost nothing while
  matching no
  crates); whether to do that early or defer until the first subdomain lands is a
  sequencing call.
- The exact light-dependency allow-set for `kernel` (what counts as a permitted
  cross-cutting dependency vs a tail) is decided when `kernel` gains real
  dependencies.

## Dependencies

- Relies on: the toolchain story (0006) for the cargo-deny mechanism and baseline
  ban-list configuration this story extends.
- Related to: the config story (0009), which applies cross-crate enforcement first
  (at the `config` / `config-adapters` split); this story is the continuation for
  subsequent crates.
- Triggered by: the first independently-shipped subdomain crate
  (`luminosity-<sub>`) — no such work item exists yet.
- Parent: epic 0001.

## Assumptions

- The cargo-deny ban-list is the chosen cross-crate enforcement mechanism per
  ADR-0009; this story extends it rather than introducing a new tool.
- The `launcher` ↛ subdomain and `kernel`-light rules are static cargo-deny bans
  that can be authored independently of whether the guarded crates exist yet.

## Technical Notes

- ADR-0009 (enforcement model) and ADR-0010 (crate layout: `kernel`, `config`,
  `config-adapters`, the `launcher` crate, `luminosity-<sub>`) are the source of
  these rules. Per 0014 these crates live under a top-level `cli/` container (the
  launcher crate's directory was renamed `cli` → `launcher`; package/binary
  `luminosity` unchanged), so `cli` now names the workspace, not the launcher
  crate.
- cargo-deny has no per-crate notion — it runs once over the workspace dependency
  graph — so these are additional entries in the single workspace `deny.toml`, not
  new per-crate tasks.
- The intra-crate inward rule (module granularity) is `cargo-pup`'s job and is
  owned by 0006; this story is strictly the cross-crate (crate-boundary) half.

## Drafting Notes

- Created 2026-06-27 from codebase research
  (`meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`) to home
  the cross-crate architecture enforcement that ADR-0009 / ADR-0010 mandate but
  that no existing work item owned. The critical-path slice (the `config` split)
  was added to story 0009; this story captures the remainder that only bites as
  the workspace grows.
- Priority set to `medium`: forward-looking, with no immediate trigger until a
  subdomain crate exists, though the preventive bans are cheap to land earlier.
- **0014 alignment (this pass)**: reconciled the launcher-crate terminology to
  the post-relocation layout — the launcher crate is `launcher` (at
  `cli/launcher/`), and `cli` now names the whole workspace. Added a bridging note
  that per 0014 the workspace crates live under a top-level `cli/` container, and
  added 0014 to `relates_to`.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Toolchain: `meta/work/0006-establish-rust-toolchain-guard-rails-in-mise-and-ci.md`
- Config (first application): `meta/work/0009-multi-level-configuration-system.md`
- Relocation: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- Research: `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
