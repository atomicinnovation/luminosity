---
type: plan
id: "2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"
title: "Relocate Workspace Crates Under cli/ and Rename the Launcher Crate Implementation Plan"
date: "2026-07-02T09:36:52+00:00"
author: "Toby Clemson"
producer: create-plan
status: ready
work_item_id: "work-item:0014"
parent: "work-item:0014"
derived_from: ["codebase-research:2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"]
tags: [task, rust, workspace, cargo, refactor, build-system, mise, ci]
revision: "6954609959f960c4213f83fa3ebc7469da756a59"
repository: "luminosity"
last_updated: "2026-07-02T18:10:00+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Relocate Workspace Crates Under cli/ and Rename the Launcher Crate Implementation Plan

## Overview

Make **`cli/` the Cargo workspace root** and adopt a **symmetric, well-named
task model** for the Rust workspace.

- **Workspace root moves into `cli/`.** `Cargo.toml`, `Cargo.lock`, and the four
  Rust-workspace tool configs (`clippy.toml`, `rustfmt.toml`, `deny.toml`,
  `pup.ron`) move from the repo root into `cli/`, so `cli/` is a self-contained
  Cargo workspace. The two member crates are `cli/launcher/` (package/binary
  `luminosity`) and `cli/kernel/` (package `kernel`); the build output tree moves
  to `cli/target/`.
- **Task naming becomes symmetric.** `cli` denotes **the whole workspace**;
  crate directory names denote **a single crate**:
  - `cli:check` / `format:cli:*` / `lint:cli:*` / `test:unit:cli` are
    **workspace-wide aggregates** (one `--workspace` / `--all` cargo invocation).
    `cli:check` is the roll-up that feeds the top-level `check`.
  - `launcher:check` / `format:launcher:*` / `lint:launcher:*` /
    `test:unit:launcher` (`-p luminosity`) and `kernel:check` /
    `format:kernel:*` / `lint:kernel:*` / `test:unit:kernel` (`-p kernel`) are
    **single-crate** tasks for ad-hoc runs, deliberately kept out of the
    aggregates (which cover every crate in one pass).
  - `build:launcher` stays crate-specific — a build produces a binary, and only
    `launcher` produces one; there is no workspace `build:cli`.

This corrects the pre-existing asymmetry where the workspace-wide format/lint
pass was misnamed after one crate (`launcher`) while `kernel` had genuinely
per-crate tasks. The package/binary name `luminosity` and the package name
`kernel` remain decoupled from their directories and are unchanged.

Delivered as **one atomic, independently-mergeable change**: `mise run` exits 0
end-to-end and the repo has no `Cargo.toml`/tool-config at the root, in a single
step with no mixed-layout intermediate state on `main`.

## Current State Analysis

The Cargo workspace root is at the **repo root** (`/Cargo.toml`, `/Cargo.lock`),
with the four tool configs (`/clippy.toml`, `/rustfmt.toml`, `/deny.toml`,
`/pup.ron`) alongside it, and the two crates already relocated under `cli/`
(`cli/launcher/`, `cli/kernel/`). Every invoke task `cd`s to `REPO_ROOT` before
invoking cargo, so cargo/cargo-deny/cargo-pup discover their manifest and config
at the repo root; `target/` lands at the repo root.

Two facts shape the work:

- **`luminosity` / `kernel` are decoupled from their directories.** Only
  directory- and task-identity-driven references change; package-name-driven
  references (`pup.ron`'s `luminosity::version::core` rule, `-p luminosity` /
  `-p kernel`, the `[[bin]]` name, `use` imports, `CARGO_BIN_EXE_luminosity`, the
  **value** of `LAUNCHER_CRATE`/`KERNEL_CRATE`, `plugin.json` / `checksums.json`
  version coherence) do not.
- **Tool-config discovery is cwd-relative for cargo-deny / cargo-pup.**
  `cargo deny check` reads `deny.toml` from its working directory, and
  `cargo pup` reads `pup.ron` from its working directory. So moving those configs
  into `cli/` requires the invoke tasks to `cd` into `cli/` (the new workspace
  root), not `REPO_ROOT`. rustfmt/clippy discover `rustfmt.toml`/`clippy.toml` by
  walking up from the source files / workspace root, so `cli/` placement is found
  once cwd is `cli/`.

### Key Discoveries

- **The workspace-wide format/lint pass currently lives in `launcher` tasks**
  (`tasks/format/launcher.py` runs `cargo fmt --all`; `tasks/lint/launcher.py`
  runs `cargo clippy --workspace`). Those become the **`cli`** tasks; new
  `launcher` tasks run `-p luminosity`. `kernel` tasks already run `-p kernel`
  (`tasks/{format,lint}/kernel.py`) and need only the cwd change.
- **`test:unit:kernel` uses an isolated `CARGO_TARGET_DIR`**
  (`tasks/test/kernel.py`, `env={"CARGO_TARGET_DIR": "target/llvm-cov-kernel"}`)
  solely so the per-crate launcher + kernel coverage passes can run concurrently
  under `test:unit` without colliding on cargo-llvm-cov's shared profraw dir. The
  new `test:unit:cli` runs a **single** `cargo llvm-cov nextest --workspace`
  pass, so that isolation hack is **removed** — the per-crate test tasks become
  ad-hoc convenience, no longer run concurrently by the aggregate.
- **`Swatinem/rust-cache` in CI has no `workspaces:` input**, so it defaults to a
  workspace at `.` with `./target`. After the move it must be told
  `workspaces: cli` on every rust-cache step (Cargo.lock + target are under
  `cli/`).
- **The CI *check* job reverts to `check-cli` / `cli:check`.** On `main` today
  the gating jobs are `check-cli` (`Check cli`, runs `cli:check`) and `build-cli`
  (`Build cli (*)`). This plan keeps the check job as `check-cli` running the
  workspace `cli:check` (unchanged from `main`) and renames only the build job
  `build-cli` → `build-launcher` (`Build launcher (*)`, runs `build:launcher`).
  So the branch-protection delta is **only the two `Build …` required-check
  names** — `Check cli` is unchanged and keeps reporting.
- **The two repo-scoped cargo-pup integration tests run against `REPO_ROOT`**
  (`tests/integration/pup/test_pup_rules.py`,
  `test_repo_pup_ron_actually_loads` / `test_real_inward_rule_binds_to_a_real_module`
  call `cargo pup print-modules` with `cwd=REPO_ROOT`). With `pup.ron` in `cli/`,
  those must run with `cwd=REPO_ROOT / "cli"`. The cargo-deny regression uses a
  throwaway `tmp_path` manifest and is unaffected.
- **`.gitignore` already ignores `target/`, `.pup/`, and `**/__pycache__/`
  path-anywhere** (no leading slash), so `cli/target/` and `cli/.pup/` are
  covered with no `.gitignore` edit.
- **`WORKSPACE_MANIFEST` (`tasks/shared/paths.py`) is defined but unconsumed**;
  it is repointed to `cli/Cargo.toml` for coherence.

## Desired End State

- No `Cargo.toml`, `Cargo.lock`, `clippy.toml`, `rustfmt.toml`, `deny.toml`, or
  `pup.ron` at the repo root; all six live in `cli/`. `cli/Cargo.toml` declares
  `members = ["launcher", "kernel"]`. Build output is `cli/target/`.
- The launcher crate's package name, binary name, and built-binary name remain
  `luminosity`; `plugin.json`'s version field is unchanged; `pup.ron` still
  references `luminosity::version::core`.
- Task model is symmetric: `cli:*` = workspace aggregate, `launcher:*` /
  `kernel:*` = single crate. `cli:check` is in `check`; `launcher:check` /
  `kernel:check` are not. `test:unit:cli` is in `test:unit`; per-crate test tasks
  are not. `build:launcher` is in the bare `mise run` default.
- `mise run` (bare default) and `mise run check` both exit 0.
- CI defines `check-cli` (runs `cli:check`) and `build-launcher` (runs
  `build:launcher`), each rust-cache step sets `workspaces: cli`, and the three
  attestation `subject-path`s are `cli/launcher/bin/luminosity-*`.
- Branch-protection required checks: `Build cli (ubuntu-latest)` /
  `Build cli (macos-latest)` replaced by `Build launcher (ubuntu-latest)` /
  `Build launcher (macos-latest)`; `Check cli` unchanged; a PR is mergeable.

Verification: `mise run` green end-to-end; the reference sweep empty; manual
inspection of the required-check list per the `CONTRIBUTING.md` runbook.

## What We're NOT Doing

- **Not** renaming the package or binary `luminosity`, or the package `kernel`.
- **Not** editing `pup.ron`'s rules — the `luminosity::version::core` module path
  is package-name-based and unaffected by the directory move (only the file's
  location changes).
- **Not** changing `plugin.json` / `checksums.json` version fields, any Rust
  source, or any runtime behaviour. (`checksums.json` legitimately changes when
  binaries are rebuilt from the relocated path — only the recorded binary *name*
  `luminosity` is preserved.)
- **Not** creating new subdomain crates (owned by 0008 / 0012), and **not**
  renaming the `cli/` container to `crates/` (deferred until scope broadens).
- **Not** adding a workspace `build:cli` — a build is inherently per-binary-crate.
- **Not** splitting into multiple merges — delivered as one atomic change.

## Implementation Approach

Test-first where assertable: the wiring/command tests pin exact task names,
job names, commands, and config paths, so the loop is to **flip those
expectations to the new model first (red), then apply the source / config /
filesystem changes to make them green**, gated finally by a whole-repo
`mise run`.

Ordering within the single phase:

1. Flip test expectations (Group F) — red.
2. Move the workspace root + tool configs into `cli/` and repoint members
   (Group A).
3. Repoint path constants and add `WORKSPACE_ROOT` (Group B).
4. Split invoke tasks into `cli` (workspace) + per-crate, cwd → workspace root,
   drop the kernel coverage-isolation, fix registrations (Group C).
5. Rebuild the mise task tree (Group D).
6. Rewire CI jobs, rust-cache `workspaces`, `needs` (Group E).
7. Update docs (Group G).
8. `mise run fix && mise run` — green.
9. Re-register the two `Build …` CI required checks; confirm mergeability
   (Group H, manual).

## Phase 1: Relocate Workspace Root and Symmetrise Tasks (atomic)

### Overview

The complete workspace-root move + symmetric task re-model, ending in a green
`mise run` and an empty root-config / old-task reference sweep.

### Changes Required

#### Group A — Filesystem: workspace root + tool configs into `cli/`

Move the six workspace-root files into `cli/` (jj tracks by content, so plain
`mv` suffices):

```sh
mv Cargo.toml cli/Cargo.toml
mv Cargo.lock cli/Cargo.lock
mv clippy.toml cli/clippy.toml
mv rustfmt.toml cli/rustfmt.toml
mv deny.toml cli/deny.toml
mv pup.ron cli/pup.ron
```

**File**: `cli/Cargo.toml`
**Changes**: repoint members to be relative to the new root.

```toml
[workspace]
resolver = "2"
members = ["launcher", "kernel"]
```

(`[workspace.dependencies]` / `[workspace.lints]` are unchanged; the member
crates' `workspace = true` / `{ workspace = true }` now resolve to
`cli/Cargo.toml`. `cli/launcher/Cargo.toml`'s `kernel = { path = "../kernel" }`
still resolves — both crates are siblings under `cli/`.)

#### Group B — Path constants (`tasks/shared/paths.py`)

Add a `WORKSPACE_ROOT` (the cargo/tool cwd) and repoint the rest.

```python
WORKSPACE_ROOT = REPO_ROOT / "cli"
WORKSPACE_MANIFEST = WORKSPACE_ROOT / "Cargo.toml"
LAUNCHER_DIR = WORKSPACE_ROOT / "launcher"
BIN_DIR = LAUNCHER_DIR / "bin"
CHECKSUMS = BIN_DIR / "checksums.json"
CARGO_TOML = LAUNCHER_DIR / "Cargo.toml"
```

`tasks/shared/rust.py`: fix the now-stale `KERNEL_CRATE` comment
`# must equal kernel/Cargo.toml …` → `# must equal cli/kernel/Cargo.toml …`.
`LAUNCHER_CRATE`'s comment (`matches cli/launcher/Cargo.toml …`) is already
correct.

#### Group C — Invoke tasks: cli (workspace) + per-crate, cwd → workspace root

**Every cargo-invoking task `cd`s to `WORKSPACE_ROOT` instead of `REPO_ROOT`**:
`tasks/build.py`, `tasks/deny.py`, `tasks/pup.py`, and all of
`tasks/{format,lint,test}/*` Rust tasks.

**Format** (`tasks/format/`):
- `cli.py` (NEW; take the current `launcher.py` workspace body): `cargo fmt --all
  [--check]`; error/help strings say `format:cli:fix`.
- `launcher.py` (rewrite to single-crate): `cargo fmt -p luminosity [--check]`
  (via `-p {LAUNCHER_CRATE}`); strings say `format:launcher:fix`.
- `kernel.py`: unchanged commands (`cargo fmt -p kernel …`); cwd → workspace
  root.

**Lint** (`tasks/lint/`):
- `cli.py` (NEW; take the current `launcher.py` workspace body): `cargo clippy
  --workspace --all-targets --all-features [-- -D warnings | --fix …]`; strings
  say `lint:cli:fix` / `lint:cli:check`.
- `launcher.py` (rewrite to single-crate): `cargo clippy -p luminosity
  --all-targets --all-features …`; strings say `lint:launcher:fix`.
- `kernel.py`: unchanged commands; cwd → workspace root.

**Test** (`tasks/test/`):
- `cli.py` (NEW): workspace coverage —
  `cargo llvm-cov nextest --workspace --summary-only` when `coverage_enabled()`,
  else `cargo nextest run --workspace`; failure message `nextest: cli tests
  failed`. No `CARGO_TARGET_DIR` override needed (single pass).
- `launcher.py`: keep `-p {LAUNCHER_CRATE}`; cwd → workspace root.
- `kernel.py`: keep `-p {KERNEL_CRATE}`; **drop** the `CARGO_TARGET_DIR`
  isolation (no longer run concurrently with launcher); cwd → workspace root;
  drop the isolation rationale from the docstring.

**Build** (`tasks/build.py`): `build.launcher` unchanged except cwd → workspace
root (`_binary` stays `target/{triple}/release/{LAUNCHER_CRATE}`, now resolved
under `cli/target/`).

**deny / pup** (`tasks/deny.py`, `tasks/pup.py`): cwd → workspace root so
`cli/deny.toml` / `cli/pup.ron` are discovered.

**Registrations**:
- `tasks/format/__init__.py`: `from . import build_system, cli, kernel, launcher,
  scripts` + matching `__all__`.
- `tasks/lint/__init__.py`: add `cli` alongside `build_system, kernel, launcher,
  scripts, workflows` + `__all__`.
- `tasks/test/__init__.py`: add `cli` collection alongside `integration, kernel,
  launcher, unit`.
- `tasks/__init__.py`: register `format_.cli` and `lint.cli` collections (in
  addition to the existing `launcher` / `kernel` registrations).

#### Group D — mise tasks (`mise.toml`)

Target Rust task tree (each rust leaf keeps `depends = ["deps:install:rust-components"]`;
`build:launcher` keeps `deps:install:rust-targets`):

| Task | run | scope |
|------|-----|-------|
| `format:cli:check` / `:fix`      | `invoke format.cli.*`      | workspace |
| `format:launcher:check` / `:fix` | `invoke format.launcher.*` | `-p luminosity` |
| `format:kernel:check` / `:fix`   | `invoke format.kernel.*`   | `-p kernel` |
| `lint:cli:check` / `:fix`        | `invoke lint.cli.*`        | workspace |
| `lint:launcher:check` / `:fix`   | `invoke lint.launcher.*`   | `-p luminosity` |
| `lint:kernel:check` / `:fix`     | `invoke lint.kernel.*`     | `-p kernel` |
| `test:unit:cli`                  | `invoke test.cli.run`      | `--workspace` |
| `test:unit:launcher`             | `invoke test.launcher.run` | `-p luminosity` |
| `test:unit:kernel`               | `invoke test.kernel.run`   | `-p kernel` |
| `build:launcher`                 | `invoke build.launcher`    | `--bin luminosity` |

Roll-ups / aggregates:
- `cli:check` depends `["format:cli:check", "lint:cli:check"]` — **in `check`**.
- `launcher:check` depends `["format:launcher:check", "lint:launcher:check"]` —
  ad-hoc, **not** in `check`.
- `kernel:check` depends `["format:kernel:check", "lint:kernel:check"]` — ad-hoc,
  **not** in `check`.
- `format:check` → `[…, format:cli:check]`; `format:fix` → `[…, format:cli:fix]`.
- `lint:check` → `[…, lint:cli:check]`; `lint:fix` → `[…, lint:cli:fix]`.
- `test:unit` depends `["test:unit:tasks", "test:unit:cli"]` (per-crate test
  tasks dropped from the aggregate).
- `check` depends `["build-system:check", "scripts:check", "cli:check",
  "deny:check", "pup:check"]`.
- `default` depends `["format:fix", "lint:check", "types:check", "test",
  "build:launcher", "deny:check", "pup:check"]`.

Descriptions: `cli:*` describe the whole workspace; `launcher:*` / `kernel:*`
describe the single crate; `launcher:check` / `kernel:check` note they are
excluded from `check` (covered by `cli:check`); `deps:install:rust-components`
description says "the cli checks need"; `default` says "(cli tests carry
coverage)"; `test:unit:cli` says "Run the whole Rust workspace's unit tests …".

#### Group E — CI (`.github/workflows/main.yml`)

- Keep job `check-cli` (`name: Check cli`, `run: mise run cli:check`) — unchanged
  from `main`.
- Rename job `build-cli` → `build-launcher` (`name: Build launcher`,
  `run: mise run build:launcher`; matrix + linker env unchanged).
- `needs:` in `prerelease`: `build-cli` → `build-launcher` (leave `check-cli`).
- Every `Swatinem/rust-cache` step gains `with: { workspaces: cli }` (jobs
  `test-unit`, `test-integration`, `check-cli`, `build-launcher`,
  `check-architecture`).
- Attestation `subject-path` stays `cli/launcher/bin/luminosity-*` (already set;
  three occurrences).

#### Group F — Tests (flip expectations first — red)

**`tests/unit/tasks/test_mise_wiring.py`**:
- `TestCliCheckWiring`: `cli:check` folds `["format:cli:check",
  "lint:cli:check"]`; `test:unit:cli` not in `cli:check`; `cli:check` in `check`;
  the four `cli` leaves provision rust-components.
- Add `TestLauncherCheckWiring`: `launcher:check` folds `["format:launcher:check",
  "lint:launcher:check"]`; not in `check`; leaves provision rust-components.
- `TestKernelCheckWiring`: unchanged (kernel folds kernel; not in `check`).
- `TestBuildLauncherWiring`: unchanged (build:launcher in default, absent from
  check / cli:check, provisions cross-targets).
- `TestTestUnitCliWiring`: `test:unit:cli` folded into `test:unit`; not in
  `cli:check`; provisions llvm-tools. Per-crate `test:unit:launcher` /
  `test:unit:kernel` are **not** in `test:unit`.
- `TestFinalEnumeratedArrays`: `check` = `[…, cli:check, …]`; `default` =
  `[…, build:launcher, …]`; `test:unit` = `["test:unit:tasks",
  "test:unit:cli"]`.
- `TestToolchainCoherence`: `clippy.toml` / `rustfmt.toml` now read from
  `cli/clippy.toml` / `cli/rustfmt.toml`; edition test reads
  `cli/launcher/Cargo.toml`; keep the `LAUNCHER_CRATE` ↔ `[package].name`
  assertion.

**`tests/unit/tasks/test_workflows.py`**: `check-cli` runs `mise run cli:check`
and gates release; `build-launcher` runs `mise run build:launcher` and gates
release.

**`tests/unit/tasks/test_test.py`**: import `cli, launcher` (+ `integration`,
`unit`); `TestTestUnitCli` asserts `cli.run` → `cargo llvm-cov nextest
--workspace --summary-only` / `cargo nextest run --workspace`;
`TestTestUnitLauncher` asserts `launcher.run` → `-p luminosity` forms.

**`tests/unit/tasks/test_build.py`**: unchanged (still `--bin {LAUNCHER_CRATE}`,
`build.launcher`).

**`tests/unit/tasks/test_format.py`**: `TestFormatCli*` assert `cargo fmt --all
[--check]`; add `TestFormatLauncher*` asserting `cargo fmt -p luminosity
[--check]`.

**`tests/unit/tasks/test_lint.py`**: `TestLintCli*` assert `cargo clippy
--workspace …`; add `TestLintLauncher*` asserting `cargo clippy -p luminosity …`.

**`tests/unit/tasks/test_kernel.py`**: drop `test_runs_in_isolated_target_dir`
(the isolation is removed); keep the command/coverage assertions.

**`tests/integration/pup/test_pup_rules.py`**: `test_repo_pup_ron_actually_loads`
and `test_real_inward_rule_binds_to_a_real_module` run with
`cwd=REPO_ROOT / "cli"` (where `pup.ron` now lives).

**`tests/conftest.py`**: the `fake_repo_tree` fixture already builds
`cli/launcher` + `cli/launcher/bin`; no change (the workspace-root move doesn't
touch that fixture's crate layout).

#### Group G — Docs / prose

**`CLAUDE.md`**:
- Build/test section: the Rust component is `cli` (the workspace); `cli:check` is
  the workspace rustfmt+clippy roll-up; `test:unit:cli` carries coverage;
  `lint:fix` runs `lint:cli:fix`; `build:launcher` / CI `build-launcher`
  unchanged. Single-test note: `cargo nextest run -p luminosity …` keeps
  `-p luminosity`; prose label "unlike the default `test:unit:cli` path".
- Architecture → Rust workspace: heading path is `cli/`; the workspace root
  (`Cargo.toml`, `Cargo.lock`) and the four tool configs now live **in `cli/`**;
  the version-bearing manifest is `cli/launcher/Cargo.toml`; rewrite the "four
  root config files" bullet list to say they live in `cli/`.

**`tasks/README.md`**: rewrite the per-component table and prose for the
symmetric model — `cli:check` = workspace roll-up (in `check`); `launcher:check`
/ `kernel:check` = single-crate ad-hoc (excluded from `check`, covered by
`cli:check`); `test:unit:cli` = workspace coverage pass (in `test:unit`);
per-crate test tasks are ad-hoc; `build:launcher` per-crate; note the tool
configs + workspace root live in `cli/`.

**`cli/deny.toml`**: keep the `build:launcher` / `launcher -> kernel` comment
wording (already updated).

**`CONTRIBUTING.md`**: required-check table — `check-cli` / `Check cli` unchanged;
`build-cli` → `build-launcher`, `Build cli (…)` → `Build launcher (…)`; update
the matrix-gotcha prose to `build-launcher` / `Build launcher (…)`.

#### Group H — CI required-check re-registration (manual)

Only the two **`Build …`** required checks change (the `Check cli` job/name is
unchanged from `main`, so its required check keeps reporting). After pushing the
branch so `Build launcher (ubuntu-latest)` / `Build launcher (macos-latest)` run
once and become selectable, in one Settings → Branches → `main` →
required-status-checks visit: **add** the two `Build launcher (…)` names and
**remove** the two `Build cli (…)` names. The stale `Build cli (…)` checks would
otherwise sit forever as "Expected — waiting" and block the merge, so removal is
what unblocks the PR; adding keeps `main`'s release build gated. Merge.

**Rollback**: pre-merge, restore the protection rule (re-add `Build cli (…)`,
drop any half-added `Build launcher (…)`) and leave the branch unmerged;
post-merge, revert the single atomic commit (which restores `build-cli`) so the
still-registered `Build cli (…)` checks report again.

### Success Criteria

#### Automated Verification

- [x] Flipped tests fail before the code lands: `uv run pytest tests/unit/tasks
      -v` shows the re-modelled wiring/command tests red.
- [x] Full local CI mirror green: `mise run` exits 0 — includes the workspace
      `build:launcher` and `test:unit:cli`, `deny:check`, `pup:check`, all run
      from `cli/`.
- [x] Read-only check set green: `mise run check` exits 0.
- [x] Symmetric task tree present and old shape gone: `mise tasks` lists
      `cli:check`, `format:cli:*`, `lint:cli:*`, `test:unit:cli`,
      `launcher:check`, `kernel:check`, `build:launcher`; there is no
      workspace-wide task hiding under a `launcher` name (i.e. `format:launcher:*`
      / `lint:launcher:*` run `-p luminosity`, asserted by the command tests).
- [x] Workspace root relocated: `test -f cli/Cargo.toml && test -f cli/Cargo.lock
      && test -f cli/clippy.toml && test -f cli/rustfmt.toml && test -f
      cli/deny.toml && test -f cli/pup.ron` succeeds; `ls Cargo.toml Cargo.lock
      clippy.toml rustfmt.toml deny.toml pup.ron` at the repo root all fail
      (moved).
- [x] Only crate manifests + the workspace manifest are Cargo.tomls under `cli/`:
      `cli/Cargo.toml` has `members = ["launcher", "kernel"]`;
      `cli/launcher/Cargo.toml` + `cli/kernel/Cargo.toml` exist; no `Cargo.toml`
      at the repo root.
- [x] Task modules present: `tasks/format` and `tasks/lint` each have `cli.py`,
      `launcher.py`, `kernel.py`; `tasks/test` has `cli.py`, `launcher.py`,
      `kernel.py`.
- [x] Reference sweep empty for stale root-config / old-task tokens:
      `grep -rn --exclude-dir=meta --exclude-dir=.git --exclude-dir=.jj
      --exclude-dir=target --exclude-dir=.venv --exclude-dir=.pytest_cache
      --exclude-dir=__pycache__ -e 'REPO_ROOT / "Cargo.toml"'
      -e 'CARGO_TARGET_DIR' -e 'build-cli' -e '(str(REPO_ROOT))' tasks/ .github/`
      returns nothing that refers to the old root layout (the `cd` calls now use
      `WORKSPACE_ROOT`; `CARGO_TARGET_DIR` is gone).
- [x] Package/bin invariants hold: `cli/launcher/Cargo.toml` `[package] name` and
      `[[bin]] name` are `luminosity`; `grep -c luminosity::version::core
      cli/pup.ron` is non-zero; `plugin.json`'s version field is unchanged.
- [x] CI topology asserted: `uv run pytest tests/unit/tasks/test_workflows.py
      tests/unit/tasks/test_mise_wiring.py -v` passes; `main.yml` defines
      `check-cli` (runs `cli:check`) and `build-launcher` (runs `build:launcher`),
      each rust-cache step sets `workspaces: cli`, and the three `subject-path`s
      are `cli/launcher/bin/luminosity-*`.

#### Manual Verification

- [x] The built binary is named `luminosity` (inspect `cli/target/*/release/`
      after `mise run`).
- [ ] Branch-protection required checks: `Build launcher (ubuntu-latest)` /
      `Build launcher (macos-latest)` present, `Build cli (…)` absent, `Check cli`
      still present (`gh api repos/{owner}/{repo}/branches/main/protection --jq
      '.required_status_checks.contexts'`), and a PR is mergeable.

---

## Testing Strategy

### Unit Tests

- The re-model is guarded by the task-wiring suite (`test_mise_wiring.py`,
  `test_workflows.py`) and the per-module command-string suites (`test_test.py`,
  `test_build.py`, `test_format.py`, `test_lint.py`, `test_kernel.py`). These are
  flipped to the new model first (red), then green as the source lands.
- Key edge to preserve: assertions carrying the **value** `luminosity`
  (`-p luminosity`, `--bin {LAUNCHER_CRATE}`) keep that value; only task
  names, scopes (`--workspace`/`--all` vs `-p`), and config paths change.

### Integration Tests

- `mise run` exercises the relocated workspace end-to-end from `cli/`:
  `build:launcher`, `test:unit:cli` (`--workspace` coverage), `deny:check`,
  `pup:check`.
- `tests/integration/pup/test_pup_rules.py` proves `cli/pup.ron` loads against
  the real workspace (`cwd=cli`); the cargo-deny regression (throwaway manifest)
  is unaffected.

### Manual Testing Steps

1. `mise run` → exit 0 and a `luminosity`-named binary under `cli/target/`.
2. Confirm the repo root has no `Cargo.toml`/tool-config; all six are in `cli/`.
3. Push, let CI run once, re-register the two `Build launcher (…)` required
   checks (removing `Build cli (…)`), confirm a PR is mergeable.

## Performance Considerations

`mise run` recompiles Rust once (the workspace root move invalidates the
incremental cache), a one-time cost. `test:unit:cli` replaces two per-crate
coverage passes with one `--workspace` pass — marginally faster and simpler (no
isolated target dir).

## Migration Notes

- Delivered atomically; no intermediate state on `main` where the workspace root
  and task names disagree.
- `Cargo.lock` moves from the repo root to `cli/Cargo.lock` (locked versions
  preserved by moving, not regenerating).
- Only the two `Build …` branch-protection required checks change (Group H);
  `Check cli` is unchanged.

## References

- Original work item: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Related research: `meta/research/codebase/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Work-item review: `meta/reviews/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-review-1.md`
- Antecedent (scaffolded the crates being moved):
  `meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md`
- Required-check runbook: `CONTRIBUTING.md` (Branch-protection required checks)
- Task-tree shape: `tasks/README.md`
