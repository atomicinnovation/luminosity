---
type: pr-description
id: "7"
title: "Relocate the Cargo workspace under cli/ and symmetrise Rust tasks"
date: "2026-07-02T22:18:12+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "work-item:0014"
parent: "work-item:0014"
pr_url: "https://github.com/atomicinnovation/luminosity/pull/7"
pr_number: 7
tags: [rust, workspace, cargo, refactor, build-system, mise, ci]
revision: "2b8bf8f0a60f1b79b2d147917b58d24dafc7e825"
repository: "luminosity"
last_updated: "2026-07-02T22:26:32+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Relocate the Cargo workspace under cli/ and symmetrise Rust tasks

## Summary

Makes **`cli/` the Cargo workspace root** and adopts a **symmetric, well-named Rust task model**. Both workspace crates move under a single `cli/` container — the `luminosity` launcher crate (`cli/` → `cli/launcher/`) and the `kernel` crate (root `kernel/` → `cli/kernel/`) — and the workspace manifest and tool configs follow them in, so `cli/` is a self-contained workspace. Delivered as one atomic change (`mise run` green end-to-end).

## Changes

**Relocate the workspace root and both crates under `cli/`**

- Move the `luminosity` launcher crate `cli/` → `cli/launcher/` and the `kernel` crate `kernel/` → `cli/kernel/` — content-preserving renames (the version hexagon and error taxonomy are unchanged).
- Move the workspace root and the four tool configs into `cli/`: the root `Cargo.toml` becomes `cli/Cargo.toml` with `members = ["launcher", "kernel"]`, and `Cargo.lock`, `clippy.toml`, `rustfmt.toml`, `deny.toml`, `pup.ron` all relocate to `cli/`. Build output is now `cli/target/`.
- The invoke tasks `cd` into `cli/` (a new `WORKSPACE_ROOT`) before invoking cargo, so cargo-deny/cargo-pup discover their config there; the pup integration tests run with `cwd=cli`.

**Symmetric task model**

- `cli:*` name the whole workspace — `cli:check`, `format:cli:*`, `lint:cli:*`, `test:unit:cli` are `--workspace`/`--all` aggregates, and `cli:check` feeds the top-level `check`.
- Crate directory names name a single crate — `launcher:*` (`-p luminosity`) and `kernel:*` (`-p kernel`) are ad-hoc convenience, deliberately kept out of the aggregates. This corrects the prior asymmetry where the workspace-wide format/lint pass was misnamed after one crate.
- `test:unit:cli` is a single `--workspace` coverage pass, removing the per-crate isolated `CARGO_TARGET_DIR` hack.

**CI**

- The check job stays `check-cli` (runs `cli:check`, unchanged from `main`); the build job is `build-launcher` (runs `build:launcher`).
- Every `Swatinem/rust-cache` step sets `workspaces: cli`; attestation subject-paths are `cli/launcher/bin/luminosity-*`.

Package/binary name `luminosity`, `pup.ron`'s `luminosity::version::core` rule, and `plugin.json` version coherence are all unchanged.

## Context

- Work item: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Plan: `meta/plans/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Research: `meta/research/codebase/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Validation: `meta/validations/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-validation.md`

## Testing

- [x] Full local CI mirror green: `mise run` exits 0 end-to-end from `cli/` (format, lint, types, unit + integration tests, `build:launcher`, `deny:check`, `pup:check`).
- [x] Workspace coverage: `test:unit:cli` runs one `cargo llvm-cov nextest --workspace` pass — 3 tests across 4 binaries, 100% line coverage.
- [x] Launcher build produces host-native binaries named `luminosity` under `cli/target/{aarch64,x86_64}-apple-darwin/release/`.
- [x] Task unit suite: `uv run pytest tests/unit/tasks -q` → 183 passed.
- [x] Reference sweep clean: no `REPO_ROOT / "Cargo.toml"`, `CARGO_TARGET_DIR`, or `build-cli` tokens remain under `tasks/`/`.github/`.

## Notes for Reviewers

- **Base branch:** this PR targets `plan-guidance-and-cli-note` (the last reviewed commit before the 0014 work), so the diff is exactly the three 0014 commits. All Rust source appears as content-preserving renames — the crate restructure moves files, it does not rewrite them.
- **Manual follow-up before merge (plan Group H):** the branch-protection required checks must swap `Build cli (ubuntu-latest)` / `Build cli (macos-latest)` for `Build launcher (ubuntu-latest)` / `Build launcher (macos-latest)`; `Check cli` is unchanged. Push once so the new checks become selectable, then add the two `Build launcher (…)` names and remove the two `Build cli (…)` names. `main` currently has no branch protection registered.
