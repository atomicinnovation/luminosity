---
type: plan-validation
id: "2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-validation"
title: "Validation Report: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate"
date: "2026-07-02T22:02:25+00:00"
author: "Toby Clemson"
producer: validate-plan
status: complete
result: "pass"
parent: "plan:2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"
target: "plan:2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"
tags: [task, rust, workspace, cargo, refactor, build-system, mise, ci]
last_updated: "2026-07-02T22:02:25+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Validation Report: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate

Implementation delivered as a single atomic change (`slzzprtmvssk` —
"Relocate the Cargo workspace under cli/ and symmetrise Rust tasks").

### Implementation Status

✓ Group A — Workspace root + tool configs relocated into `cli/` — Fully implemented
✓ Group B — Path constants (`WORKSPACE_ROOT` added, rest repointed) — Fully implemented
✓ Group C — Invoke tasks split into `cli`/per-crate, cwd → workspace root, coverage-isolation dropped — Fully implemented
✓ Group D — mise task tree rebuilt (symmetric model) — Fully implemented
✓ Group E — CI jobs rewired (`check-cli` kept, `build-cli` → `build-launcher`, `workspaces: cli`) — Fully implemented
✓ Group F — Test expectations flipped to the new model — Fully implemented (183 task unit tests pass)
✓ Group G — Docs updated (CLAUDE.md, tasks/README.md, CONTRIBUTING.md, deny.toml) — Fully implemented
⚠️ Group H — CI required-check re-registration — Deferred (manual, post-push; see Manual Testing)

### Automated Verification Results

✓ Full local CI mirror green: `mise run` exits 0 end-to-end (format:fix, lint:check,
  types:check, test [unit + integration], build:launcher, deny:check, pup:check),
  all run from `cli/`.
✓ Workspace coverage pass: `test:unit:cli` ran a single `cargo llvm-cov nextest
  --workspace` pass — 3 tests across 4 binaries (kernel + luminosity), 100% line
  coverage, no cross-crate profraw collision.
✓ Launcher build: `build:launcher` produced host-native darwin binaries named
  `luminosity` under `cli/target/{aarch64,x86_64}-apple-darwin/release/`.
✓ Task unit suite: `uv run pytest tests/unit/tasks -q` → 183 passed.
✓ Integration suite: `test:integration:pup` / `test:integration:deny` ran clean
  within `mise run`; no failures in the full log.
✓ Workspace root relocated: `cli/Cargo.toml`, `cli/Cargo.lock`, `cli/clippy.toml`,
  `cli/rustfmt.toml`, `cli/deny.toml`, `cli/pup.ron` all present; none remain at
  the repo root.
✓ `cli/Cargo.toml` declares `members = ["launcher", "kernel"]`; both crate
  manifests exist.
✓ Build output tree is `cli/target/`; no root `target/`.
✓ Reference sweep clean: no `REPO_ROOT / "Cargo.toml"`, `CARGO_TARGET_DIR`, or
  `build-cli` tokens under `tasks/`/`.github/` (remaining `str(REPO_ROOT)` uses
  are the non-Rust build-system/workflows/types tasks that correctly stay at the
  repo root).
✓ Package invariants: `cli/launcher/Cargo.toml` `[package] name` and `[[bin]] name`
  are `luminosity`; `cli/pup.ron` still references `luminosity::version::core`
  (1 occurrence); `plugin.json` version field unchanged.
✓ CI topology: `main.yml` defines `check-cli` (runs `cli:check`) and
  `build-launcher` (runs `build:launcher`); every rust-cache step sets
  `workspaces: cli` (5 jobs); all three attestation `subject-path`s are
  `cli/launcher/bin/luminosity-*`; `needs:` in `prerelease` references
  `check-cli` + `build-launcher`; no `build-cli` remains.

### Code Review Findings

#### Matches Plan:

- Symmetric task tree exactly as specified: `cli:check` folds
  `["format:cli:check", "lint:cli:check"]` and is in `check`; `launcher:check` /
  `kernel:check` fold their single-crate tasks and are excluded from `check`;
  `test:unit` folds `["test:unit:tasks", "test:unit:cli"]` (per-crate test tasks
  dropped); `default` includes `build:launcher`.
- All cargo-invoking tasks (`build`, `deny`, `pup`, `format/{cli,launcher,kernel}`,
  `lint/{cli,launcher,kernel}`, `test/{cli,launcher,kernel}`) `cd` to
  `WORKSPACE_ROOT`; the non-Rust tasks correctly retain `REPO_ROOT`.
- `test/cli.py` runs the single `--workspace` coverage pass; `test/kernel.py` no
  longer sets `CARGO_TARGET_DIR` (isolation hack removed as planned) and its
  docstring drops the isolation rationale.
- `tasks/format` and `tasks/lint` each gained a `cli.py` (workspace body) with
  `launcher.py` rewritten to single-crate `-p luminosity`; `tasks/test` gained
  `cli.py`.
- pup integration tests (`test_repo_pup_ron_actually_loads`,
  `test_real_inward_rule_binds_to_a_real_module`) run with
  `cwd=WORKSPACE_ROOT` (`REPO_ROOT / "cli"`); the deny regression uses a
  throwaway `tmp_path` manifest and is unaffected.
- Docs reflect the `cli/` workspace root, the four tool configs under `cli/`, the
  symmetric task model, and the `check-cli` / `build-launcher` required-check
  names.

#### Deviations from Plan:

- None material. `WORKSPACE_MANIFEST` was repointed to `cli/Cargo.toml` as planned
  (still defined-but-unconsumed, per the plan's note).

#### Potential Issues:

- None identified. The one-time incremental-cache invalidation from the root move
  is expected (called out under Performance Considerations) and does not affect
  correctness.

### Manual Testing Required:

1. Branch-protection required checks (Group H — post-push, cannot be verified pre-merge):
  - [ ] After pushing the branch and letting CI run once, in Settings → Branches →
    `main`: add `Build launcher (ubuntu-latest)` / `Build launcher (macos-latest)`
    and remove `Build cli (ubuntu-latest)` / `Build cli (macos-latest)`; confirm
    `Check cli` still present.
  - [ ] Confirm a PR is mergeable.

  Note: `gh api .../branches/main/protection` currently returns 404 ("Branch not
  protected"), so no required checks are registered on the remote yet — this step
  is genuinely outstanding operational work, not an implementation gap.

### Recommendations:

- Proceed with Group H exactly as the plan's runbook describes when the branch is
  pushed; the rollback note in the plan (revert the single atomic commit to
  restore `build-cli`) remains valid.
- No code changes recommended — the implementation is faithful to the plan.
