---
type: codebase-research
id: "2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"
title: "Research: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate (0014)"
date: "2026-07-02T01:38:34+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0014"
parent: "work-item:0014"
relates_to: ["codebase-research:2026-06-28-0007-scaffold-hexagonal-rust-workspace"]
topic: "Relocating the Cargo workspace crates under cli/ and renaming the launcher crate directory"
tags: [research, codebase, rust, workspace, cargo, build-system, mise, ci, refactor]
revision: "426f657edc8cf9cff3ec6195d438fdd22b72a787"
repository: "luminosity"
last_updated: "2026-07-02T01:38:34+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate (0014)

**Date**: 2026-07-02T01:38:34+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: 426f657edc8cf9cff3ec6195d438fdd22b72a787
**Branch**: (no bookmark — jj working copy `xqvwkumu`)
**Repository**: luminosity

## Research Question

For work item 0014: map every place in the codebase that must change to move the
two workspace crates off the repo root into a `cli/` container (`cli/` →
`cli/launcher/`, `kernel/` → `cli/kernel/`), rename the launcher crate's
*directory* to `launcher` while preserving the package/binary name `luminosity`,
and rename the associated build-tasks/CI-jobs from `cli` to `launcher`. Identify
what the work item's requirements list covers and, critically, **what it
misses**.

## Summary

The refactor spans four layers — Cargo manifests, the Python invoke task tree,
mise task wiring, and CI — plus the tests that assert on all of them. The single
most important architectural fact, which the work item states and the research
confirms, is that **the package/binary name `luminosity` and the package name
`kernel` are decoupled from their directories**. Therefore:

- **Directory-driven references** (workspace members, `CLI_DIR`, `cli/bin/…`
  output paths, CI `subject-path`, task/module names) **must change**.
- **Package-name-driven references** (`pup.ron`'s `luminosity::version::core`
  rule, all `cargo -p luminosity` / `-p kernel` invocations, `CLI_CRATE`'s
  *value* `"luminosity"`, the `[[bin]]` name, source `use luminosity::…` imports,
  `CARGO_BIN_EXE_luminosity` in the integration test) **do not change** — only the
  *constant name* `CLI_CRATE` → `LAUNCHER_CRATE` changes, not its value.

The `../kernel` path dependency in the launcher's `Cargo.toml` **survives the
move unchanged** because both crates remain siblings under `cli/` — this is
verified by a green `build:launcher`, per the acceptance criteria.

**The work item's Requirements list is broadly accurate but incomplete.** Live
research surfaced several reference sites the requirements do not name explicitly:

1. **`tasks/__init__.py:48,56`** — `format`/`lint` collections are assembled here
   with explicit `Collection.from_module(format_.cli)` / `from_module(lint.cli)`
   calls. Renaming the module files alone is **not** enough; these lines break.
2. **`tasks/build.py`** — the `build:cli` task is a function `def cli(...)` here
   (not a `tasks/build/cli.py` module); it imports and uses `CLI_CRATE`, and its
   docstring references `build-cli`. The work item's requirements say "rename
   `build:cli` → `build:launcher`" but do not point at this file.
3. **`tasks/shared/targets.py:23,30`** — the string `build:cli` appears in a
   comment and an error message.
4. **Hardcoded error/help strings** in `tasks/lint/cli.py:18,35`,
   `tasks/format/cli.py:13`, `tasks/test/cli.py:24` reference the old task names.
5. **Extra test files** beyond the three the work item names: `test_build.py`,
   `test_format.py`, `test_lint.py`, and **`tests/conftest.py`** (hardcodes
   `tmp_path / "cli"` and `tmp_path / "cli/bin"`).
6. **`tasks/README.md`** (many hits), **`CONTRIBUTING.md:31,32,41`** (required-check
   table + prose), **`tasks/deps.py:33`** (docstring), **`mise.toml:157`**
   (`kernel:check` description prose that says "workspace-wide `cli:check` pass")
   and **`mise.toml:232`** (default-task description prose) — doc/comment strings
   the reference-sweep acceptance criterion is meant to catch, but which are not
   individually enumerated in Requirements.
7. **`deny.toml:18`** — a second comment (`exercised by build:cli`), in addition
   to the `deny.toml:49` "cli -> kernel" comment the work item names.

None of these change the *design* of the task — they are additional edit sites
that must be on the implementation checklist so the reference sweep passes.

## Detailed Findings

### 1. Cargo workspace (manifests + config)

- **Root `Cargo.toml:3`** — `members = ["cli", "kernel"]` → `["cli/launcher",
  "cli/kernel"]`. The `[workspace.dependencies]` / `[workspace.lints]` blocks have
  no path refs and are unaffected.
- **`cli/Cargo.toml`** — `[package] name = "luminosity"` (line 4) and `[[bin]]
  name = "luminosity"` (line 16) **stay**. `path = "src/main.rs"` (line 17) is
  package-relative, unaffected. **Line 20: `kernel = { path = "../kernel" }`** —
  survives because launcher (`cli/launcher`) and kernel (`cli/kernel`) remain
  siblings, so `../kernel` still resolves. Line 9 has a comment about exempting
  the kernel path dependency.
- **`kernel/Cargo.toml:2`** — `name = "kernel"` stays (package name, not
  directory-derived).
- **`pup.ron`** — line 8 `Module("^luminosity::version::core($|::)")` is keyed to
  the **crate name** `luminosity`, **not** the directory → **no edit** (this is
  explicitly out of scope in the work item, and research confirms the rule is
  package-name-based). Line 13 `"^kernel(::|$)"` is keyed to the `kernel` package
  name → also unaffected by a pure directory move. `pup.ron` contains no `cli`
  token at all.
- **`deny.toml`** — comments only: line 18 (`exercised by build:cli`) and line 49
  (`# Exempt local path deps (cli -> kernel)…`). The ban-lists (lines 56–65) are
  registry crate names, not workspace paths — unaffected.
- **`clippy.toml:4`** (`msrv = "1.90.0"`) and **`rustfmt.toml`** (`max_width = 80`,
  `edition = "2021"`) — no path/crate references, unaffected.
- **Rust source** — `cli/src/main.rs:8-10` (`use luminosity::version::…`),
  `cli/src/version/inbound/cli.rs:44` (`kernel::Error`), `cli/tests/version.rs:23`
  (`env!("CARGO_BIN_EXE_luminosity")`) and `:53` (`"luminosity "`) are all
  **package/bin-name-keyed → no edit**. Note the literally-named source file
  `cli/src/version/inbound/cli.rs` (the inbound CLI adapter) is unrelated to the
  crate *directory* and stays put inside the moved crate.

### 2. Python invoke task tree (`tasks/`)

**Path constants — `tasks/shared/paths.py`:**
- Line 5: `CLI_DIR = REPO_ROOT / "cli"` → `REPO_ROOT / "cli" / "launcher"`;
  rename `CLI_DIR` → `LAUNCHER_DIR`.
- Lines 6–8 derive from `CLI_DIR` and follow automatically: `BIN_DIR = CLI_DIR /
  "bin"`, `CHECKSUMS = BIN_DIR / "checksums.json"`, `CARGO_TOML = CLI_DIR /
  "Cargo.toml"`. So `cli/launcher/bin/` and `cli/launcher/Cargo.toml` fall out
  once line 5 changes.
- **Confirmed: there is NO kernel path constant** in `paths.py` — only the
  four cli-derived ones. The kernel is referenced solely via the launcher
  `Cargo.toml`'s `../kernel`. This matches the work item's statement.
- Lines 17–22: `binary_path` / `debug_archive_path` produce `luminosity-{platform}`
  filenames (bin-name-keyed, default `bin_dir=BIN_DIR`).

**Crate-name constant — `tasks/shared/rust.py:3`:**
`CLI_CRATE = "luminosity"  # must equal cli/Cargo.toml [package] name`. Rename the
**constant** → `LAUNCHER_CRATE`; keep the **value** `"luminosity"`; fix the
comment path to `cli/launcher/Cargo.toml`. Sibling `KERNEL_CRATE = "kernel"` (line
4) is the naming template and is unaffected.

**Task modules to rename `cli.py` → `launcher.py`:**
- `tasks/lint/cli.py` — imports only `REPO_ROOT`; `check` runs `cargo clippy
  --workspace …` (no crate name); error string line 18 (`mise run lint:cli:fix`),
  comment line 35 (`lint:cli:check`).
- `tasks/format/cli.py` — imports only `REPO_ROOT`; `cargo fmt --all …`; error
  string line 13 (`mise run format:cli:fix`).
- `tasks/test/cli.py` — **imports `CLI_CRATE`** (line 4); uses `-p {CLI_CRATE}`
  (lines 17, 19); error string line 24 (`nextest: cli tests failed`). Only cli
  task module that consumes the crate constant.

**Namespace registration (GAP — beyond Requirements):**
- `tasks/__init__.py:48` — `ns_format.add_collection(Collection.from_module(format_.cli))`
- `tasks/__init__.py:56` — `ns_lint.add_collection(Collection.from_module(lint.cli))`
  These explicit calls must be repointed at the renamed modules — renaming files
  alone won't update them.
- `tasks/lint/__init__.py:1,3` and `tasks/format/__init__.py:1,3` — the `from .
  import … cli …` line and the `__all__` list (the work item names these two).
- `tasks/test/__init__.py:3,8` — `from . import cli, …` and
  `ns.add_collection(Collection.from_module(cli))`.

**Build task (GAP — beyond Requirements):**
- `tasks/build.py:6` imports `CLI_CRATE`; `:47` `f"target/{triple}/release/{CLI_CRATE}"`;
  `:69` `def cli(...)` (the `build:cli` task — renames the **function** to make
  `build:launcher`); `:80` `cargo build --release --bin {CLI_CRATE} …`; `:71-75`
  docstring mentions `build:cli` / `build-cli`. Build output lands in cargo's
  `target/…/release/`, **not** `BIN_DIR` — so the binary build itself is
  unaffected by the directory move; only the constant/task name matter here.

**Indirect consumers (follow `paths.py` automatically):**
- `tasks/github.py:13,139,144,146` — uses `CHECKSUMS` / `binary_path` /
  `debug_archive_path`.
- `tasks/version.py:10,33,39,79,80` — the version-coherence writer; reads/writes
  `CARGO_TOML` and `CHECKSUMS`. Keeps working as long as `CARGO_TOML` points at the
  version-bearing launcher manifest (it will, via the `CLI_DIR` edit).
- `tasks/shared/targets.py:23,30` (GAP) — `build:cli` in a comment + error string.
- `tasks/deps.py:33` (GAP) — docstring `the one cli:check runs against`.

### 3. mise task wiring (`mise.toml`)

**Crate tasks to rename** (definitions): `test:unit:cli` (line 58),
`format:cli:check` (88), `format:cli:fix` (93), `lint:cli:check` (132),
`lint:cli:fix` (137), `cli:check` (152, roll-up), `build:cli` (160). Their `run`
bodies invoke `invoke test.cli.run` / `format.cli.*` / `lint.cli.*` / `build.cli`
(lines 61, 91, 96, 135, 140, 163) — these must repoint at the renamed invoke
namespaces.

**Every `depends` edge into a renamed task** (must be edited in lockstep):
- `test:unit` (line 70) → `test:unit:cli`
- `format:check` (110) → `format:cli:check`
- `format:fix` (114) → `format:cli:fix`
- `lint:check` (213) → `lint:cli:check`
- `lint:fix` (217) → `lint:cli:fix`
- `check` (229) → `cli:check`
- `default` (233) → `build:cli`
- `cli:check` itself (154) → `format:cli:check` + `lint:cli:check`

**Prose that goes stale (GAP):** `mise.toml:157` — the `kernel:check` description
says kernel is covered "via the single workspace-wide `cli:check` pass"; and
`mise.toml:232` — the `default` task description mentions `build:cli`.

### 4. CI (`.github/workflows/main.yml`)

`.github/workflows/main.yml` is the **only** workflow file.

- Job `check-cli` — key line 106, `name: Check cli` (107), step `Run cli checks`
  (126), `run: mise run cli:check` (127). → `check-launcher`, target
  `launcher:check`.
- Job `build-cli` — key line 129, `name: Build cli` (130), dual-OS matrix
  (131–135: `[ubuntu-latest, macos-latest]`), `run: mise run build:cli` (168). →
  `build-launcher`, target `build:launcher`.
- `needs` edges in the `prerelease` job — `check-cli` (234), `build-cli` (235).
- **Attestation `subject-path: "cli/bin/luminosity-*"`** at lines **272, 327,
  342** (three occurrences: prerelease + two release steps) → must become
  `cli/launcher/bin/luminosity-*` to track the moved `BIN_DIR`. These are
  independent hardcoded copies of the path — editing `paths.py` does **not**
  update them.
- **Required-check re-registration** — renaming the two jobs changes their
  required-check names in GitHub branch protection. This is a **manual repo-settings
  step with no local signal** (per the `CONTRIBUTING.md` runbook) and will silently
  block merges if forgotten. `CONTRIBUTING.md:31,32,41` document the current
  `check-cli` / `build-cli` rows and must be updated too.

### 5. Tests

Work item names `test_mise_wiring.py`, `test_workflows.py`, `test_test.py`.
Research confirms those **plus additional files**:

- **`test_mise_wiring.py`** — heaviest: classes `TestCliCheckWiring` (35–64),
  `TestBuildCliWiring` (110–121), `TestTestUnitCliWiring` (124–142),
  `TestFinalEnumeratedArrays` (223, 234, 242), and `TestToolchainCoherence` line
  261 reads `REPO_ROOT / "cli/Cargo.toml"`. Many exact task-name string
  assertions (`"cli:check"`, `"build:cli"`, `"test:unit:cli"`, `"format:cli:*"`,
  `"lint:cli:*"`) and the negative `"coverage:cli:check" not in names` (139).
- **`test_workflows.py`** — `test_check_cli_job_…` (188–193) asserts
  `jobs["check-cli"]` runs `"mise run cli:check"`; `test_build_cli_job_…`
  (196–203) asserts `jobs["build-cli"]` runs `"mise run build:cli"`. Both read job
  keys by exact string.
- **`test_test.py`** — line 7 `from tasks.test import cli, …`; lines 9–10
  `INSTRUMENTED`/`PLAIN` use `-p luminosity` (value unchanged); `cli.run(ctx)`
  calls.
- **`test_build.py` (GAP)** — line 8 imports `CLI_CRATE`; line 111 asserts
  `--bin {CLI_CRATE}`; `build.cli(ctx)` calls (108, 121, 135).
- **`test_format.py` (GAP)** — line 7 `from tasks.format import cli as fmt_cli`;
  `fmt_cli.check/fix`.
- **`test_lint.py` (GAP)** — line 9 `from tasks.lint import cli as lint_cli`;
  `lint_cli.check/fix`.
- **`tests/conftest.py` (GAP)** — `fake_repo_tree` fixture hardcodes
  `tmp_path / "cli"` (16) and `tmp_path / "cli/bin"` (21).

Clean (no cli-crate refs): `test_kernel.py` (kernel-only), `test_deps.py`,
`test_deny.py`, `test_pup.py`, the `tests/unit/tasks/shared/` suite, and the
integration suites (`test_github.py:53` `CHECKSUMS` patch is unrelated).

### 6. Docs / prose (reference-sweep targets)

- **`CLAUDE.md`** — lines 20, 24, 25, 27, 28, 47 (workspace prose + single-test
  command; the work item names this).
- **`tasks/README.md`** (GAP) — lines 14, 21, 27, 31, 32, 58, 59, 63, 73 reference
  `cli:check`, `build:cli`, `test:unit:cli`, `build-cli`.
- **`CONTRIBUTING.md`** (GAP) — required-check table rows (31, 32) and prose (41).

## Code References

- `Cargo.toml:3` — workspace `members` list
- `cli/Cargo.toml:4,16,20` — package name, bin name, `../kernel` path dep
- `pup.ron:8,13` — module/use rules (package-name-keyed, NO edit)
- `deny.toml:18,49` — comments only
- `tasks/shared/paths.py:5-8` — `CLI_DIR` and derived `BIN_DIR`/`CHECKSUMS`/`CARGO_TOML`
- `tasks/shared/rust.py:3` — `CLI_CRATE = "luminosity"` (rename constant, keep value)
- `tasks/build.py:6,47,69,80` — build task + `CLI_CRATE` usage (GAP)
- `tasks/__init__.py:48,56` — explicit collection registration (GAP)
- `tasks/shared/targets.py:23,30` — `build:cli` strings (GAP)
- `tasks/deps.py:33` — docstring (GAP)
- `tasks/lint/cli.py`, `tasks/format/cli.py`, `tasks/test/cli.py` — modules to rename
- `mise.toml:58,88,93,132,137,152,160` — task definitions; `:70,110,114,154,213,217,229,233` — depends edges; `:157,232` — stale prose (GAP)
- `.github/workflows/main.yml:106,127,129,168,234,235` — jobs/targets/needs; `:272,327,342` — attestation subject-path
- `tests/unit/tasks/test_mise_wiring.py`, `test_workflows.py`, `test_test.py`, `test_build.py`, `test_format.py`, `test_lint.py` — assertions
- `tests/conftest.py:16,21` — `cli`/`cli/bin` fixture paths (GAP)
- `CLAUDE.md`, `tasks/README.md`, `CONTRIBUTING.md` — prose

## Architecture Insights

- **Directory vs. package-name decoupling is the load-bearing principle.** The
  crate directory is incidental; the package/binary name `luminosity` is the
  contract held coherent with `plugin.json` / `checksums.json` by
  `tasks/version.py`. Everything keyed to the *name* (pup rules, `-p` flags, bin
  name, source imports, `CLI_CRATE`'s value) is invariant under this move; only
  *directory* and *task/module/constant-name* references change. This is exactly
  why `pup.ron` and version-coherence need no edits.
- **`CLI_DIR` is a single source of truth; `main.yml`'s `subject-path` is a
  hand-maintained duplicate.** The Python side propagates from one constant, but CI
  hardcodes `cli/bin/luminosity-*` three times — a classic hand-synced mirror (the
  same species as the 80-col and `msrv` mirrors CLAUDE.md warns about). The repo
  has no automated cross-reference check, so the reference sweep is the safety net.
- **`build:cli` is a function-named task, not a module.** Unlike lint/format/test
  (which are `tasks/<verb>/cli.py` modules), the build task is `def cli()` in
  `tasks/build.py`. This asymmetry is easy to miss when treating the rename as
  "rename the `cli.py` files".
- **Namespace assembly is split** between `tasks/__init__.py` (format/lint,
  explicit `from_module` calls) and the per-package `__init__.py` (test). A rename
  must touch both loci.

## Historical Context

- `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md` —
  scaffolded the very `cli/` + `kernel` crates this item relocates (the blocking
  dependency).
- `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
  — the workspace/hexagon split decision.
- `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md` — origin of
  the overloaded "launcher" term; places launcher resolution inside the Rust `cli`
  binary.
- `meta/work/0012-cross-crate-architecture-enforcement-as-the-workspace-grows.md` —
  future cargo-pup cross-crate enforcement; the soft-ordering reason to land 0014
  first.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md` and
  `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md` —
  the hexagonal-growth and distribution decisions cited in the work item's Context.
- `meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md` and
  `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md` —
  describe the current (pre-move) layout.
- `meta/reviews/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-review-1.md`
  — the existing review of this work item (staged, uncommitted).

## Related Research

- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md` —
  the antecedent describing how the crates being relocated were built.

## Open Questions

- **None blocking.** The work item's Open Questions section is empty and the
  research confirms the design is settled. The only actionable output is to fold
  the **gap sites** above (`tasks/__init__.py`, `tasks/build.py`,
  `tasks/shared/targets.py`, `tasks/deps.py`, `tests/conftest.py`, the extra test
  files, `tasks/README.md`, `CONTRIBUTING.md`, and the stale mise/deny prose) into
  the implementation checklist so the reference-sweep acceptance criterion
  (`grep … for old references → none remain`) actually passes.
- **Confirm during implementation** (per the work item's own caveats): that
  `../kernel` resolves post-move via a green `build:launcher`, and that the CI
  `subject-path` matches the actual `build:launcher` output path.
