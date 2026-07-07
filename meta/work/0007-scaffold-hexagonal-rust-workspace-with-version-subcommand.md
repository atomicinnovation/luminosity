---
type: work-item
id: "0007"
title: "Scaffold the Hexagonal Rust Workspace with a version Subcommand"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: high
parent: "work-item:0001"
blocks: ["work-item:0008", "work-item:0009"]
relates_to: ["work-item:0002", "work-item:0006", "work-item:0014"]
tags: [story, rust, cli, hexagonal, scaffold]
last_updated: "2026-07-02T23:46:13+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0007: Scaffold the Hexagonal Rust Workspace with a version Subcommand

**Kind**: Story
**Status**: Ready
**Priority**: High
**Author**: Toby Clemson

## Summary

Scaffold the hexagonal Rust workspace — subdomain-first per the spike (0002) and
ADR-0010, with a dependency-light `kernel` crate and the `cli` launcher, hexagonal
layers as modules — and prove it end-to-end with a `luminosity version`
subcommand. The proof is structural, not the feature: `version` drives the core
through an inbound port, sources its build metadata through an outbound/driven
port wired at a composition root, and is exercised in tests against an in-memory
fake — so the ports-and-adapters architecture (ADR-0009) is real and subsequent
stories have a skeleton to build on. Built test-first.

## Context

This is the first real Rust code in the repo and the proof of the hexagonal
architecture. It follows the modular-CLI / hexagonal architecture spike (0002,
complete), which decided the crate split and dispatch model: a subdomain-first
Cargo workspace whose *eventual* shape is one crate per subdomain alongside
`kernel`, `config`, `config-adapters`, and `cli` — with hexagonal layers as
modules, split into separate crates only under pressure (ADR-0009, ADR-0010).
This version-only scaffold deliberately does not reach that shape: it creates
just `cli` and `kernel`. (Work item 0014 subsequently relocates both crates
under a top-level `cli/` container — `cli/` → `cli/launcher/`, `kernel/` →
`cli/kernel/` — and renames the launcher crate's directory `cli` → `launcher`;
the package/binary name `luminosity` is unchanged.) ADR-0009 governs the
hexagonal pattern and
the inward-dependency rule; ADR-0010 governs the binary axis (what is split into
independently-shippable units) and reserves git-style external-subcommand
dispatch for the distribution story. The `version` subcommand is deliberately
small — its value is exercising the full path from the CLI inbound adapter,
through the domain, out through an outbound port and back, test-first — not the
feature itself.

## Requirements

- **Workspace layout** — create the workspace per the spike (0002) and ADR-0010:
  subdomain-first, with a deliberately dependency-light `kernel` crate
  (cross-cutting contracts — error taxonomy and the like) and the `cli` launcher
  binary that depends on `kernel`. The version-only starting set is exactly two
  crates, `cli` plus `kernel`; the shared `config` / `config-adapters` crates,
  and any per-subdomain crate, are not pulled in until a story needs them.
  Because `version` is a **built-in** subcommand of the launcher (ADR-0010) and
  not an independently-shippable sub-binary, it does **not** get its own crate:
  the `version` hexagon's concerns live as modules **within the `cli` crate**,
  with the composition root at the `cli` binary's entry point. `kernel` holds
  only cross-cutting contracts, never the `version` core. At this scaffold stage
  `kernel` is present-but-minimal: it ships just enough to be the home of the
  cross-cutting error taxonomy `version` reports through (a starter error type),
  not an empty placeholder — anything the `version` slice does not yet exercise
  is deferred to the story that needs it.
- **Realise the hexagon for `version`** (ADR-0009) — establish all three concerns
  as the architectural proof, not a trivial constant read. All of the modules
  below live within the `cli` crate (see Workspace layout above):
  - an **inbound/driving port** (a trait in the core) that the CLI inbound
    adapter drives, delegating immediately into the core with no logic in the
    command layer;
  - a domain/application core holding what little logic `version` needs,
    depending on no infrastructure;
  - an **outbound/driven port** (a trait in the core) for build metadata — commit
    SHA, build date, target triple — which is treated as genuinely external and
    injected at build time (the deliberate acceptance of ADR-0009's indirection
    overhead for this otherwise-trivial read is recorded in Assumptions and
    Drafting Notes);
  - an **outbound adapter** implementing that port (a build script / vergen-style
    mechanism — the implementer's choice);
  - a **composition root** binding the concrete adapter to the port, so the core
    is constructed against traits and never against concrete infrastructure.
- **`version` subcommand, built test-first** — prints the CLI version plus build
  metadata (commit SHA, build date, target triple). The version is sourced from
  the crate version as the single source of truth (which feeds ADR-0002's
  version-coherence obligation across `plugin.json`, the CLI's `Cargo.toml`, and
  the release manifest); the build metadata is injected at build time, not
  hard-coded. Per ADR-0010, `version` is a **built-in** subcommand compiled into
  the `luminosity` launcher, exposed as a plain in-process clap subcommand over
  the hexagonal skeleton.
- **Enforce the inward dependency direction** (ADR-0009, mechanisms from the
  toolchain story 0006) — the domain layer must depend on no adapter or I/O
  module. In the single-crate starting state the cross-crate cargo-deny ban-list
  and the Cargo dependency graph are **inert**, so **cargo-pup is the sole
  enforcer** of the inward rule at module granularity; the Cargo graph and
  cargo-deny take over for a given boundary only once it becomes a crate split.
- **Wire the crates into the task tree** — add a `<crate>:check` component per
  workspace member to the component-based `mise` task tree established by the
  toolchain story (0006).

## Acceptance Criteria

- [ ] Given a built CLI, when `luminosity version` is run, then it prints the CLI
      version, commit SHA, build date, and target triple (the triple being one of
      ADR-0002's four supported triples); the behaviour is covered by a test
      written test-first (red → green).
- [ ] The workspace contains exactly the crates `cli` and `kernel`, `cli`
      depends on `kernel`, and the `version` hexagon's inbound port, core,
      outbound port, build-metadata adapter, and composition root all exist as
      distinct modules within `cli` (no `version` core in `kernel`).
- [ ] The domain layer depends on no adapter or I/O module, and the enforcer is
      proven live, not merely configured: a deliberately introduced
      inward-direction violation (e.g. a throwaway import of the outbound adapter
      module into the core) is rejected by cargo-pup, and removing the violation
      restores a green cargo-pup run — the sole inward-direction enforcer in the
      single-crate starting state (the Cargo graph and cargo-deny ban-list enforce
      a boundary only once it becomes a crate split).
- [ ] Build metadata reaches the core through an outbound/driven port: the core is
      exercised in a test against an in-memory fake of that port (proving the port
      boundary), while the composition root wires the real build-time adapter.
- [ ] The version value has a single source of truth (the crate version), and the
      build metadata is injected at build time rather than hard-coded — verified
      by an observable consequence rather than asserted: the commit SHA in
      `version` output equals the SHA of the commit the binary was built from, and
      the build date parses as an RFC 3339 timestamp falling within the wall-clock
      window of the build invocation (not a hard-coded constant). The build-time
      injected value — produced by the build script / vergen-style mechanism and
      consumed at the composition root — is what proves injection.
- [ ] The crates' checks run under `mise run check` and the bare `mise run`
      default, both exiting 0.

## Open Questions

- The build-metadata injection mechanism (build script vs a crate like vergen) is
  an implementation choice, not fixed here.
- The internal module naming/granularity within `cli` (how finely the hexagon's
  concerns are split into files) is settled during implementation; the crate set
  (`cli` + `kernel`) and the hexagon's home (`cli`) are fixed by this story.

## Dependencies

- Informed by: the modular-CLI / hexagonal architecture spike (0002, complete —
  decided the crate split and dispatch).
- Consumes (prerequisite, now satisfied): the toolchain story (0006, complete) —
  this story's inward-direction enforcement requires 0006's cargo-pup lane, and
  its task-tree wiring requires 0006's component-based `mise` task tree. Both
  exist, so the coupling is discharged; recorded here as a true prerequisite
  rather than merely "paired".
- Blocks (directly): the distribution story (0008) and the configuration story
  (0009) — both build on this skeleton. 0008 additionally owns git-style
  external-subcommand dispatch and the confirmation of clap's
  `external_subcommand` derive (relocated out of this story — see Drafting Notes).
- Blocks (transitively): the eval-application story (0010) depends on this
  skeleton via the configuration story (0009), not directly — 0010's own
  Dependencies list 0003 and 0009, not 0007 — so closing this story does not by
  itself unblock 0010.
- Relates to: the workspace relocation (0014) — relocates the `cli` and `kernel`
  crates under a top-level `cli/` container and renames the `cli` launcher
  crate's directory to `launcher` (package/binary `luminosity` unchanged); 0014
  follows this scaffold.
- Parent: epic 0001.

## Assumptions

- The `version` subcommand is a vertical-slice proof, not a feature; no real
  domain logic beyond what proves the architecture.
- Modelling build metadata as a genuine outbound/driven port (rather than a
  direct constant read) is worth ADR-0009's noted indirection overhead for a
  trivial command, because the scaffold's purpose is to prove the port boundary
  and composition root that every later subdomain reuses.

## Technical Notes

- Build metadata is the natural outbound/driven port for this slice: it is an
  external capability (build-time facts) the core requires, satisfied by a build
  script / vergen-style adapter bound at the composition root and faked in tests.
- `kernel` stays deliberately dependency-light (ADR-0010) — everything links it,
  so a dependency tail is resisted; for this slice it holds only cross-cutting
  contracts such as the error taxonomy.
- In the single-crate starting state cargo-pup is the only thing enforcing the
  inward rule (ADR-0009); treat a cargo-pup lane break as a fix-now signal, since
  there is no cruder backstop until crates split.
- Test-first is non-negotiable per the project's TDD convention.

## Drafting Notes

- **Hexagon depth (decision)**: chose a genuine minimal hexagon over a trivial
  constant read — build metadata is modelled as an outbound/driven port with a
  build-time adapter, a composition root, and an in-memory fake in tests.
  ADR-0009 flags the indirection as overhead for trivial commands; we accept it
  deliberately so the scaffold proves all three hexagonal concerns end-to-end.
- **External dispatch relocated (decision)**: removed this story's negative
  "no external dispatch wired" acceptance criterion and the requirement that
  policed external dispatch as the distribution story's concern. Git-style
  external-subcommand dispatch and the confirmation of clap's
  `#[command(external_subcommand)] External(Vec<OsString>)` derive — which
  ADR-0009/ADR-0010 attribute to "the scaffold" — now belong wholly to 0008.
  0008 has since been updated to receive this scope: its Requirements and
  Acceptance Criteria now own the clap `external_subcommand` dispatch and the
  derive confirmation, and it has been realigned to ADR-0002's hand-rolled
  invoke+gh + minisign/sha256 pipeline (the earlier dist/cargo-dist + GitHub
  Attestations staleness is resolved). The relocated scope therefore has a
  confirmed owner.
- **cargo-deny inertness (clarification)**: per ADR-0009, refined the enforcement
  requirement/AC so cargo-pup is named as the sole inward-direction enforcer in
  the single-crate phase, rather than implying the cross-crate cargo-deny
  ban-list is active now.
- **ADR-0002 touch (where appropriate)**: added ADR-0002 to references; the
  `version` target triple is one of its four supported triples, and the
  single-source-of-truth crate version feeds its version-coherence obligation.
- Kind set to `story`: a concrete, bounded deliverable (workspace + one
  subcommand).
- **0014 cross-link (this pass)**: added a forward-reference to work item 0014,
  which relocates the `cli`/`kernel` crates under a top-level `cli/` container
  and renames the `cli` launcher crate's directory to `launcher` (package/binary
  `luminosity` unchanged). 0007's own description of scaffolding root-level `cli`
  + `kernel` is kept as-is — it is accurate to what this story builds before 0014
  relocates it.
- Updated 2026-06-27 from codebase research
  (`meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`):
  replaced the stale `core` / `adapters` / `cli` crate triple — superseded by the
  now-complete spike (0002) — with the subdomain-first layout from ADR-0010, and
  changed the spike dependency from "blocked by" to "informed by" now that it is
  done.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Spike: `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- Relocation: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md`
- Research: `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
