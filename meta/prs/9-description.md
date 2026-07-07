---
type: pr-description
id: "9"
title: "Multi-level configuration system: CLI command + thin configure skill (0009)"
date: "2026-07-06T15:03:46+00:00"
author: Toby Clemson
producer: describe-pr
status: complete
work_item_id: "0009"
parent: "work-item:0009"
pr_url: "https://github.com/atomicinnovation/luminosity/pull/9"
pr_number: 9
tags: [configuration, cli, skills, hexagonal, architecture-enforcement]
revision: "37dfbd3130934f9603dbb8bc2c3c4948411d1b2b"
repository: "luminosity"
last_updated: "2026-07-06T15:03:46+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Multi-level configuration system: CLI command + thin configure skill (0009)

## Summary

Introduces a two-level configuration system (team + personal precedence) as the
workspace's first cross-crate hexagon: a dependency-free `config` core crate
holding resolution, a `config-adapters` crate holding the serde/YAML/filesystem
concerns, a built-in `luminosity config get`/`set` command, the cargo-deny
ban-list that keeps infrastructure out of the core, and a thin `configure` skill
that drives the CLI. This proves the skills-vs-CLI division end-to-end and makes
cross-crate dependency-direction enforcement live for the first time.

## Changes

Implemented test-first across five independently-mergeable phases:

- **`config` core crate** — a kernel-only domain: `Level`, `Key` (rejects
  degenerate dotted keys), the typed order-preserving `Node`/`Scalar`/`Mapping`
  tree, the `ReadConfigLevel`/`WriteConfigLevel` driven ports, the
  `ConfigAccess` driving port, and `ConfigService` performing personal-over-team
  resolution plus the arbitrary-depth walk/insert. Empty-vs-unset is a domain
  distinction (`Resolved::Found` for a present null/empty string,
  `Resolved::Absent` for a missing key); reads are fail-loud and `set` is
  fail-closed against an unparseable file.
- **`config-adapters` crate** — `FileConfigStore` over `std::fs`: single-pass
  project-root discovery (`.luminosity/`/`.git`, respecting a nested-repo
  boundary), CRLF-aware frontmatter splitting that never re-scans the body,
  typed order-preserving YAML round-trip via `serde-saphyr`, and an atomic
  temp+rename write that preserves the markdown body and creates `.luminosity/`
  on first write. An integer beyond `i64` range is preserved as a string rather
  than overflowing.
- **cargo-deny cross-crate ban** — converts the TLS bans to `[[bans.deny]]`
  form and adds the serde-family ban so `serde`, `serde_json`, and the YAML
  crate are reachable only through their legitimate wrappers; a direct
  `config → serde` edge now fails `cargo deny check`. A committed Python
  regression test injects `serde` into a throwaway copy of `config` and asserts
  the ban fires.
- **launcher wiring** — the `config` clap subcommand (`get`/`set` with a
  `--level` value-enum whose doc comments drive `--help`), the inbound adapter
  with a pure `render(&Scalar)`, the dispatch arm, and a Model-1 composition
  root that lazily discovers the project root and builds the store only on the
  first `get`/`set`. `set` defaults to the git-ignored personal level. Adds the
  depth-independent `.gitignore` protection for the personal file and the
  atomic-write scratch dir alongside the writer that creates them.
- **thin `configure` skill** — the repo's first skill, driving configuration
  solely through `luminosity config get`/`set` (no file access, YAML parsing,
  or path construction); registered in `plugin.json`.

## Context

- Work item: `meta/work/0009-multi-level-configuration-system.md`
- Plan: `meta/plans/2026-07-05-0009-multi-level-configuration-system.md`
- ADR-0003 (config model), ADR-0009 (hexagon + enforcement split), ADR-0010
  (cross-crate split, Model 1)

## Testing

- [x] Full local CI mirror is green end-to-end (`mise run`): formatters, all
      lints and type-checks, the workspace test suite with coverage, the
      host-native release build, and the `deny:check`/`pup:check` static checks
- [x] `config` core: 36 unit tests against in-memory fakes (precedence,
      fall-through, level-scoped reads, empty-vs-unset, typed scalars, nested
      walk/insert at ≥3 levels, `PathConflict`, fail-loud/fail-closed, sibling
      type + key-order preservation)
- [x] `config-adapters`: 23 unit tests against tempdirs (typed YAML parse, big-int
      to string, nested-write round-trip, body preservation incl. embedded `---`,
      no-trailing-newline, no-frontmatter and CRLF edge cases, malformed
      fail-closed, atomic-temp handling, discovery boundary cases)
- [x] launcher: 15 black-box integration tests, each bounded by a `.git` marker so
      project-root discovery cannot escape the fixture (full-stack resolution,
      fall-through, level-scoped reads, personal/team file targeting,
      from-subdirectory discovery, round-trip, not-found, empty/null,
      `PathConflict`, malformed fail-loud, bogus `--level`, degenerate key, help)
- [x] Dependency ban: committed Python regression proves `cargo deny check bans`
      rejects a `config → serde` edge; `cargo tree -p config` is kernel-only
- [x] Thin-skill grep criterion: the skill body references only
      `luminosity config get`/`set`, with no direct file access, YAML parsing, or
      path construction

## Notes for Reviewers

- **Stacked branch.** This branch is stacked on the still-unmerged 0007/0008
  work (`main` is at the 0006 merge), so the raw PR diff spans those too. The
  changes owned by this PR are the five `0009` commits (`config` core →
  `config-adapters` → deny ban → launcher wiring → thin skill); the diff
  narrows to just those once the prior work items merge. Reviewing per-commit
  keeps the scope clear.
- **Deny `wrappers` reconciled empirically.** The plan's illustrative wrapper
  lists were superseded by the resolved graph: under serde 1.0.228,
  `serde_json`/`serde-saphyr` depend on `serde_core` (not `serde`), and the real
  direct `serde` parents include the vergen build-dependency chain
  (`cargo_metadata`, `cargo-platform`). The committed lists match
  `cargo tree -i`, and the regression test guards them.
- **Deferred (per the plan / story 0011).** No config schema beyond the single
  proof value `core.example`; no YAML comment preservation across a `set`; no
  `config list`/`--show-origin`/`unset`; no concurrency control on `set`
  (single-writer, whole-document last-writer-wins). Behavioural equivalence of
  the `configure` skill to the CLI is validated by the eval-application story
  0010.
