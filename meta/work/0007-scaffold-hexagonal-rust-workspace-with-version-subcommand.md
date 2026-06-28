---
type: work-item
id: "0007"
title: "Scaffold the Hexagonal Rust Workspace with a version Subcommand"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
blocks: ["work-item:0008", "work-item:0009", "work-item:0010"]
relates_to: ["work-item:0002", "work-item:0006"]
tags: [story, rust, cli, hexagonal, scaffold]
last_updated: "2026-06-27T11:51:56+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0007: Scaffold the Hexagonal Rust Workspace with a version Subcommand

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Scaffold the hexagonal Rust workspace — subdomain-first per the spike (0002) and
ADR-0010, with a thin `kernel` crate and the `cli` launcher, hexagonal layers as
modules — and prove it end-to-end with a `luminosity version` subcommand —
printing version plus build metadata — built test-first, so the architecture is
real and subsequent stories have a skeleton to build on.

## Context

This is the first real Rust code in the repo and the proof of the hexagonal
architecture. It follows the modular-CLI / hexagonal architecture spike (0002,
complete), which decided the crate split and dispatch model: a subdomain-first
Cargo workspace (`kernel`, `config`, `config-adapters`, `cli`, one crate per
subdomain) with hexagonal layers as modules, split into separate crates only
under pressure (ADR-0009, ADR-0010). The `version` subcommand is deliberately
trivial — its value is exercising the full path from CLI driving adapter through
the domain, test-first, not the feature itself.

## Requirements

- Create the workspace per the spike's recommendation (0002) and ADR-0010:
  subdomain-first, with a thin `kernel` crate (cross-cutting contracts) and the
  `cli` launcher binary, each hexagon starting as a single crate with
  domain / application (ports as traits) and inbound / outbound adapters as
  modules (hexarch-style), split into separate crates only under pressure. Enforce
  the inward dependency direction — the Cargo graph, the cargo-deny ban-list
  keeping infra crates out of the domain, and cargo-pup intra-crate import rules
  (all from the toolchain story, 0006).
- Implement a `luminosity version` subcommand, built test-first, that prints the
  CLI version plus build metadata: commit SHA, build date, and target triple.
  The version is sourced from the crate version (single source of truth); the
  build metadata is injected at build time (e.g. a build script / vergen-style
  approach — the mechanism is the implementer's choice). Per ADR-0010, `version`
  is a built-in subcommand compiled into the `luminosity` launcher.
- Keep dispatch in-process: a plain clap subcommand over the hexagonal skeleton.
  The git-style external-subcommand launcher/dispatch is entirely the
  distribution story's concern and is out of scope here.
- Wire the crates into the component-based `mise` task tree (a `<crate>:check`
  component per workspace member) established by the toolchain story (0006).

## Acceptance Criteria

- [ ] Given a built CLI, when `luminosity version` is run, then it prints the CLI
      version, commit SHA, build date, and target triple; the behaviour is
      covered by a test written test-first (red → green).
- [ ] The workspace follows the spike's subdomain-first layout (0002, ADR-0010),
      with the domain layer depending on no adapter or I/O crate — a violation
      fails to compile and/or trips cargo-deny (and cargo-pup for intra-crate
      module imports).
- [ ] The version value has a single source of truth (the crate version), and the
      build metadata is injected at build time rather than hard-coded.
- [ ] The CLI exposes only the in-process `version` subcommand; no
      external-subcommand dispatch is wired in this story.
- [ ] The crates' checks run under `mise run check` and the bare `mise run`
      default, both exiting 0.

## Open Questions

- The spike (0002) decided the workspace is subdomain-first with hexagonal layers
  as modules (split into separate crates only under pressure); the concrete
  starting set for a version-only scaffold (likely just the `cli` launcher plus a
  thin `kernel`) is settled during implementation.
- The build-metadata injection mechanism (build script vs a crate like vergen) is
  an implementation choice, not fixed here.

## Dependencies

- Informed by: the modular-CLI / hexagonal architecture spike (0002, complete —
  decided the crate split and dispatch). The toolchain story (0006, provides the
  per-crate checks and architecture enforcement) is paired with this story.
- Blocks: the distribution story (0008), the configuration story (0009), and the
  eval-application story (0010) — all build on this skeleton.
- Parent: epic 0001.

## Assumptions

- The `version` subcommand is a vertical-slice proof, not a feature; no real
  domain logic beyond what proves the architecture.

## Technical Notes

- Git-style dispatch (clap `allow_external_subcommands`) and the on-demand
  launcher are the distribution story's concern; this story needs only the
  in-process `version` subcommand over the hexagonal skeleton.
- Test-first is non-negotiable per the project's TDD convention.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (workspace + one
  subcommand).
- Crate shape deferred to the architecture spike's recommendation rather than
  fixed here.
- version output scope set to version + build metadata (commit, build date,
  target triple) per the author; dispatch kept in-process only (external dispatch
  deferred to the distribution story).
- Updated 2026-06-27 from codebase research
  (`meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`):
  replaced the stale `core` / `adapters` / `cli` crate triple — superseded by the
  now-complete spike (0002) — with the subdomain-first layout from ADR-0010, and
  changed the spike dependency from "blocked by" to "informed by" now that it is
  done.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Spike: `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- Research: `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
