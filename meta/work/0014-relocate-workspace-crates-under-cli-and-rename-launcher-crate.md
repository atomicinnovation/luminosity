---
type: work-item
id: "0014"
title: "Relocate Workspace Crates Under cli/ and Rename the Launcher Crate"
date: "2026-07-02T01:14:59+00:00"
author: Toby Clemson
producer: create-work-item
status: ready
kind: task
priority: medium
parent: "work-item:0001"
relates_to: ["work-item:0002", "work-item:0007", "work-item:0008", "work-item:0012"]
tags: [task, rust, workspace, cargo, refactor, build-system]
last_updated: "2026-07-02T01:30:22+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0014: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate

**Kind**: Task
**Status**: Ready
**Priority**: Medium
**Author**: Toby Clemson

## Summary

Move both workspace crates off the repo root into a single top-level `cli/`
container — `cli/` → `cli/launcher/` and `kernel/` → `cli/kernel/` — renaming the
launcher crate's *directory* to `launcher` while preserving the package/binary
name `luminosity`. This is organisational tidiness ahead of more crates arriving
(0008, 0012), so future subdomain crates are born under `cli/` rather than
relocated later.

## Context

The Cargo workspace currently holds two crates at the repo root: `cli/` (package
`luminosity`, the launcher binary) and `kernel/` (a dependency-light domain
crate), both scaffolded by 0007. As the hexagonal architecture grows, more
subdomain crates are coming (per ADR-0010, 0008's distribution work, and 0012's
cross-crate enforcement). Leaving crates scattered at the root will not scale
tidily, so we consolidate them under a `cli/` subdirectory now.

The chosen container name `cli/` clashes with the existing `cli/` crate
directory, so that crate's directory is renamed to `launcher`. `launcher` is not
a new coinage: 0007 already calls this crate "the `cli` launcher," and 0008
places the launcher resolution (fetch → verify → cache → exec) inside the Rust
`cli` binary — i.e. the same crate/binary this item renames to the `cli/launcher/`
directory. The package name stays `luminosity` because it is the shipped binary
name and is held coherent with `plugin.json` / `checksums.json` by
`tasks/version.py`.

Within this repo, **"the launcher crate" hereafter denotes the `cli/launcher/`
directory whose package and binary are `luminosity`** — distinct from the thin
bash bootstrap and from the on-demand fetch→verify→cache→exec resolution pipeline
that 0008 also calls "the launcher". The overloaded term is retained deliberately
(see Drafting Notes); this note fixes its referent for the remainder of 0014.
Likewise, **unqualified `cli/` hereafter denotes the new top-level container
directory**; the crate historically living at the root `cli/` is referred to as
the launcher crate (its old `cli/` directory) to keep the two senses distinct.

This repo has **no automated cross-reference check** for crate paths and names
(the 80-col limit and `msrv` are hand-synced in the same spirit), so the work is
in exhaustively following every hand-maintained reference to the old layout.

## Requirements

**Filesystem & Cargo**

- Move `cli/` → `cli/launcher/` and `kernel/` → `cli/kernel/`; no
  `Cargo.toml`-bearing crate remains at the repo root.
- Update root `Cargo.toml` members from `["cli", "kernel"]` to
  `["cli/launcher", "cli/kernel"]`.
- Verify `cli/launcher/Cargo.toml`'s `kernel = { path = "../kernel" }` still
  resolves (both crates become siblings under `cli/`, so `../kernel` is expected
  to remain correct) — confirm rather than assume.
- Preserve package names `luminosity` and `kernel`, and the `[[bin]]` name
  `luminosity`.

**Build tasks (Python invoke + mise)**

- `tasks/shared/paths.py`: repoint `CLI_DIR` at `cli/launcher` and rename it
  `CLI_DIR` → `LAUNCHER_DIR` for coherence. `paths.py` holds **no** kernel path
  constant (only `CLI_DIR`, `BIN_DIR = CLI_DIR / "bin"`, `CHECKSUMS`,
  `CARGO_TOML`), so no kernel-path edit is needed here — the kernel is referenced
  only via the launcher `Cargo.toml`'s `../kernel`. Because `BIN_DIR` derives from
  `CLI_DIR`, the build output moves automatically to `cli/launcher/bin/`.
- `tasks/shared/rust.py`: keep `CLI_CRATE`'s value `"luminosity"` (package
  unchanged), rename the constant to `LAUNCHER_CRATE`, and fix its
  "must equal cli/Cargo.toml [package] name" comment to the new path.
- Rename the invoke task modules `tasks/lint/cli.py`, `tasks/format/cli.py`,
  `tasks/test/cli.py` → `launcher.py`, and update the `__all__` lists in
  `tasks/lint/__init__.py` and `tasks/format/__init__.py`.
- Rename the mise tasks and every `depends` edge that references them:
  `cli:check` → `launcher:check`, `format:cli:check|fix`,
  `lint:cli:check|fix`, `test:unit:cli`, and `build:cli` → `build:launcher`.

**CI**

- `.github/workflows/main.yml`: rename jobs `check-cli` → `check-launcher` and
  `build-cli` → `build-launcher`; update their `mise run` targets; update the
  attestation `subject-path: "cli/bin/luminosity-*"` to
  `cli/launcher/bin/luminosity-*` (since `BIN_DIR = LAUNCHER_DIR / "bin"` after
  the move).
- Re-register the renamed CI jobs as GitHub branch-protection **required
  checks** (manual step per the `CONTRIBUTING.md` runbook) so PRs remain
  mergeable.

**Tests & docs**

- Update the task-wiring tests to the new names/paths:
  `tests/unit/tasks/test_mise_wiring.py`, `test_workflows.py`, `test_test.py`,
  and any `paths.py` / `rust.py` assertions.
- Update `CLAUDE.md` (the several `cli/` workspace references and the
  single-test command) and the `deny.toml` "cli -> kernel" comment.

**Explicitly out of scope**

- Renaming the package or binary `luminosity` (would break version coherence and
  the shipped binary name).
- Editing `pup.ron` — its rules match the module path
  `luminosity::version::core`, which is package-name-based and unaffected by the
  directory move.
- Changing `plugin.json` / `checksums.json` version fields, any Rust source, or
  any runtime behaviour.
- Creating new subdomain crates (owned by 0008 / 0012); renaming the `cli/`
  container to `crates/` (deferred until scope broadens).

## Acceptance Criteria

- [ ] Given the reorg is complete, when I list the tree, then both crates live at
      `cli/launcher/` and `cli/kernel/` and no `Cargo.toml`-bearing crate sits at
      the repo root.
- [ ] Given the change, when I run `mise run` (the bare default), then it exits 0
      end-to-end — including `build:launcher` and `pup:check`; a green
      `build:launcher` is what confirms the `../kernel` path dependency still
      resolves from `cli/launcher/`.
- [ ] Given the change, when I run `mise run check`, then it exits 0.
- [ ] Given the package name is preserved, when I inspect the relevant files,
      then each stated invariant holds: `cli/launcher/Cargo.toml`'s `[package]
      name` and `[[bin]] name` remain `luminosity`; `plugin.json`'s version field
      is unchanged; `pup.ron`'s rules still reference the module path
      `luminosity::version::core`; and the built binary is named `luminosity`.
      (`checksums.json` legitimately changes when binaries are rebuilt from the
      relocated path — only the recorded binary *name* `luminosity` must be
      preserved, not the file byte-for-byte.)
- [ ] Given the invoke/mise tasks are renamed, when I run `mise tasks`, then the
      crate's tasks are `launcher:*` / `build:launcher` and no `*:cli:*` task for
      the crate remains.
- [ ] Given the task modules are renamed, when I list `tasks/lint/`,
      `tasks/format/`, and `tasks/test/`, then each holds `launcher.py` and no
      `cli.py` for the crate remains, and the wiring tests
      (`test_mise_wiring.py`, `test_workflows.py`, `test_test.py`) pass under
      `mise run test` / `mise run check`.
- [ ] Given the reference sweep is complete, when I grep the whole repo
      (excluding `meta/`, which legitimately records the old layout) for the
      crate's old references (`build:cli`, `test:unit:cli`, `format:cli`,
      `lint:cli`, `check-cli`, `build-cli`, and the old root `cli/` crate path),
      then none remain. (The `mise tasks` / `mise run` criteria transitively cover
      the code-side task and path references; this sweep is what catches stray
      doc/comment strings such as those in `CLAUDE.md` and `deny.toml`.)
- [ ] Given the CI jobs are renamed, when I inspect `.github/workflows/main.yml`,
      then it defines jobs named `check-launcher` and `build-launcher`, no
      `check-cli` / `build-cli` job remains, and the attestation `subject-path`
      matches the path `build:launcher` writes (`cli/launcher/bin/luminosity-*`).
      (Locally verifiable.)
- [ ] Given the required checks are re-registered, when I inspect the repo's
      required-status-checks (Settings → Branches, or `gh api
      repos/{owner}/{repo}/branches/main/protection`, per the `CONTRIBUTING.md`
      runbook), then the list contains `check-launcher` and `build-launcher`, no
      longer contains `check-cli` / `build-cli`, and a PR is mergeable. (Manual
      step — no local signal; see Technical Notes.)

## Open Questions

- None outstanding — sequencing, linkage, and the naming decision are settled.

## Dependencies

- Blocked by: **0007** — 0007 scaffolds the very crates this item relocates (the
  root `cli/` package `luminosity` and the `kernel` crate), so the work is
  impossible until 0007 lands. (0007 is currently status `ready`, not done.)
- Blocks: none as a hard edge, but 0014 **should precede 0008 / 0012**: landing it
  first means their new subdomain crates are born under `cli/` rather than
  relocated later. This is a soft ordering benefit, not a hard block — 0008 / 0012
  can proceed and relocate afterwards if 0014 has not landed.
- Recommended sequencing: land after 0007 settles and before 0008 / 0012 add
  further crates, so new crates are created under `cli/` rather than relocated.
- External coupling: the CI required-check re-registration is a manual action in
  GitHub repo settings (branch protection), not the workflow YAML — the one
  coupling with no local signal (see Technical Notes) that will silently block
  merges if missed.

## Assumptions

- All crates move under `cli/`, including `kernel` → `cli/kernel/` — not just the
  launcher crate.
- The build-output binary path (currently `cli/bin/luminosity-*`, driven by
  `BIN_DIR = CLI_DIR / "bin"`) moves with the crate. Because `BIN_DIR` derives
  from `CLI_DIR` (→ `LAUNCHER_DIR`), after the move it becomes
  `cli/launcher/bin/luminosity-*`, and the CI attestation `subject-path` must be
  set to that. (Confirm against the actual `build:launcher` output during
  implementation.)

## Technical Notes

- The `../kernel` relative path in the launcher's `Cargo.toml` is expected to
  survive the move unchanged because both crates stay siblings under `cli/`.
- Package name `luminosity` is deliberately decoupled from its directory: the
  directory becomes `launcher`, the package/binary stays `luminosity`. This is
  why `pup.ron` (module-path based) and the version-coherence machinery need no
  edits.
- The CI required-check re-registration is the one step with no local signal —
  it lives in repo settings, not the workflow YAML — so it is easy to forget and
  will silently block merges if missed.

## Drafting Notes

- `launcher` chosen as the crate directory name because it matches existing repo
  usage (0007 calls the crate "the launcher"; 0008 puts launcher resolution in
  the Rust `cli` binary). Overload noted: "launcher" is also used loosely for the
  bash bootstrap and the distribution concept in 0008. Alternatives if sharper
  disambiguation is wanted: `dispatch` or `cli-launcher`.
- "Rename the crate" interpreted as renaming the directory/location only;
  package name preserved (per author's direction).
- Container kept as `cli/` for now; a future rename to `crates/` is possible if
  scope broadens (per author's direction).
- Task-module rename included at author's request, recorded here with its full
  CI/required-check consequence so a reviewer weighs that cost deliberately.

## References

- Related: 0002 (workspace/hexagon split decision), 0007 (scaffolded the current
  `cli/` + `kernel` crates), 0008 (distribution & launcher; "launcher"
  terminology), 0012 (cross-crate enforcement as the workspace grows)
- ADRs: ADR-0009 (thin CLI over a hexagonal ports-and-adapters core), ADR-0010
  (git-style modular CLI of on-demand static binaries) — the hexagonal-growth and
  distribution decisions referenced in Context above
- Parent: 0001 (baseline architecture and engineering guard rails)
