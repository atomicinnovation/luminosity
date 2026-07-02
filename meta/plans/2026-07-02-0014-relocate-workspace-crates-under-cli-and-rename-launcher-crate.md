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
last_updated: "2026-07-02T16:21:15+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Relocate Workspace Crates Under cli/ and Rename the Launcher Crate Implementation Plan

## Overview

Move both workspace crates off the repo root into a single `cli/` container —
`cli/` → `cli/launcher/` and `kernel/` → `cli/kernel/` — renaming the launcher
crate's *directory* to `launcher` while preserving the package/binary name
`luminosity`. In lockstep, rename everything keyed to the launcher crate's
*directory or task identity* from `cli` to `launcher` (path constant, invoke task
modules, mise tasks, CI jobs) and re-register the renamed CI jobs as
branch-protection required checks. Everything keyed to the crate's *package/binary
name* (`luminosity`) is invariant and stays put.

Delivered as **one atomic, independently-mergeable change**: `mise run` exits 0
end-to-end and the repo-wide reference sweep for old `cli` task/path strings comes
back empty in a single step, with no mixed-naming intermediate state on `main`.

## Current State Analysis

The Cargo workspace holds two crates at the repo root, scaffolded by 0007:

- `cli/` — package and binary `luminosity` (`cli/Cargo.toml:4,16`), the launcher
  crate. Depends on `kernel` via `kernel = { path = "../kernel" }`
  (`cli/Cargo.toml:20`).
- `kernel/` — package `kernel` (`kernel/Cargo.toml:2`), a dependency-light domain
  crate.

The build tooling reaches the launcher crate through a small set of
hand-maintained references. The load-bearing fact — confirmed against the live
tree — is that **the package/binary name `luminosity` and the package name
`kernel` are decoupled from their directories**:

- **Directory-driven** references must change: workspace `members`
  (`Cargo.toml:3`), `CLI_DIR` (`tasks/shared/paths.py:5`) and everything derived
  from it (`BIN_DIR`, `CHECKSUMS`, `CARGO_TOML`), the CI attestation
  `subject-path` (three copies in `.github/workflows/main.yml:272,327,342`), the
  invoke task module filenames, and the mise/CI task/job names.
- **Package-name-driven** references must NOT change: `pup.ron`'s
  `luminosity::version::core` rule, every `cargo -p luminosity` / `-p kernel`
  invocation, the `[[bin]]` name, all `use luminosity::…` / `kernel::…` source
  imports, `env!("CARGO_BIN_EXE_luminosity")`, and the **value** `"luminosity"` of
  `CLI_CRATE` (only the constant *name* changes). This is exactly why `pup.ron`
  and the version-coherence machinery need no edits.

The repo has **no automated cross-reference check** for crate paths/names (the
80-col limit and the clippy `msrv` are hand-synced in the same spirit), so
correctness rests on exhaustively following every hand-maintained reference. A
repo-wide grep (excluding `meta/`, and ignoring regenerated `.jj` / `.pytest_cache`
/ `__pycache__` artifacts) confirms the reference set below is complete.

### Key Discoveries:

- **`../kernel` survives the move unchanged** (`cli/Cargo.toml:20`): launcher
  (`cli/launcher`) and kernel (`cli/kernel`) remain siblings, so `../kernel` still
  resolves. Proven by a green `build:launcher`, not assumed.
- **`build:cli` is a *function-named* task, not a module**
  (`tasks/build.py:69` `def cli(...)`) — unlike lint/format/test, which are
  `tasks/<verb>/cli.py` modules. The rename here is the function name plus the
  `CLI_CRATE` import.
- **Namespace assembly is split across two loci**: `tasks/__init__.py:48,56`
  registers `format`/`lint` via explicit `Collection.from_module(format_.cli)` /
  `from_module(lint.cli)` calls, while `tasks/test/__init__.py:3,8` registers
  `test` via its own `__init__`. Renaming the module files alone leaves these
  import references dangling.
- **`CLI_DIR` is the single source of truth for the build-output path**
  (`BIN_DIR = CLI_DIR / "bin"`), but the CI `subject-path` is a **hand-maintained
  triplicate** of `cli/bin/luminosity-*` — editing `paths.py` does not update it.
- **`tests/conftest.py`'s `fake_repo_tree` fixture is currently unused** (defined
  at `conftest.py:11`, consumed by no test). Updating its hardcoded `cli` /
  `cli/bin` paths is coherence-only, not correctness-critical — but it is caught
  by the reference sweep, so it is in scope.
- **Beyond the sites the work item enumerates**, the research surfaced these edit
  sites, all confirmed live: `tasks/build.py`, `tasks/shared/targets.py:23,30`,
  `tasks/deps.py:33`, `tasks/__init__.py:48,56`, the in-module error/help strings
  in the three `cli.py` modules, `tests/conftest.py`, `test_build.py`,
  `test_format.py`, `test_lint.py`, `tasks/README.md`, `CONTRIBUTING.md`, and the
  stale prose at `mise.toml:157,232` and `deny.toml:18`.

## Desired End State

- Both crates live at `cli/launcher/` and `cli/kernel/`; no `Cargo.toml`-bearing
  crate sits at the repo root.
- The launcher crate's package name, binary name, and built-binary name all remain
  `luminosity`; `plugin.json`'s version field is unchanged; `pup.ron` still
  references `luminosity::version::core`.
- The crate's tasks are `launcher:*` / `build:launcher`; no `*:cli:*` task and no
  `check-cli` / `build-cli` CI job remains.
- `mise run` (bare default) and `mise run check` both exit 0.
- A repo-wide grep (excluding `meta/`) for `build:cli`, `test:unit:cli`,
  `format:cli`, `lint:cli`, `cli:check`, `check-cli`, `build-cli`, `CLI_CRATE`,
  `CLI_DIR`, and the old root `cli/` crate path returns nothing in tracked source.
- The branch-protection required checks list contains `Check launcher` and
  `Build launcher (ubuntu-latest)` / `Build launcher (macos-latest)`, no longer
  contains the old `Check cli` / `Build cli (…)` names, and a PR is mergeable.

Verification: `mise run` green end-to-end; the reference-sweep grep empty; manual
inspection of the required-check list per the `CONTRIBUTING.md` runbook.

## What We're NOT Doing

- **Not** renaming the package or binary `luminosity` (would break version
  coherence and the shipped binary name).
- **Not** editing `pup.ron` — its rules match the package-name module path
  `luminosity::version::core`, unaffected by a directory move.
- **Not** changing `plugin.json` / `checksums.json` version fields, any Rust
  source, or any runtime behaviour. (`checksums.json` legitimately changes when
  binaries are rebuilt from the relocated path — only the recorded binary *name*
  `luminosity` is preserved.)
- **Not** creating new subdomain crates (owned by 0008 / 0012), and **not**
  renaming the `cli/` container to `crates/` (deferred until scope broadens).
- **Not** splitting into multiple merges — delivered as one atomic change.

## Implementation Approach

One phase, applied in a test-first order wherever the change is assertable. The
affected tests are wiring/assertion tests that pin exact task names, job names,
and paths; the TDD loop is to **flip those expectations to the new names first
(red), then apply the source/config/filesystem changes to make them green**. The
filesystem move, `Cargo.toml`, and the constant renames are not unit-test-first in
a pure sense, but they are gated by the same test suite plus the whole-repo
`mise run` at the end.

The rename touches package-name-invariant call sites too (e.g. `-p luminosity`,
`--bin {LAUNCHER_CRATE}`): those keep their **value** `luminosity` — only the
constant *identifier* `CLI_CRATE` → `LAUNCHER_CRATE` and the *task/module/job*
names change.

Ordering within the phase:

1. Flip test expectations (Group F) — red.
2. Move directories + `Cargo.toml` members (Group A).
3. Repoint + rename path/crate constants (Group B).
4. Rename invoke task modules, registrations, in-module strings, build/targets/deps
   (Group C).
5. Rename mise tasks + `depends` edges + stale prose (Group D).
6. Rename CI jobs + targets + `needs` + `subject-path` (Group E).
7. Update docs (Group G).
8. `mise run fix && mise run` — green.
9. Re-register CI required checks; confirm PR mergeability (Group H, manual).

## Phase 1: Relocate and Rename (atomic)

### Overview

The complete relocation and `cli`→`launcher` rename, ending in a green `mise run`
and an empty reference sweep.

### Changes Required:

#### Group A — Filesystem move + Cargo workspace

**Move the crate directories.** Under jj the move is tracked by content, so plain
`mv` suffices; the two-step dance avoids moving `cli/` into its own subdirectory:

```sh
mv cli .launcher.tmp
mkdir cli
mv .launcher.tmp cli/launcher
mv kernel cli/kernel
```

(`cli/launcher/bin/checksums.json` and any built `luminosity-*` binaries move with
the crate — expected.)

**File**: `Cargo.toml`
**Changes**: repoint the workspace members.

```toml
[workspace]
resolver = "2"
members = ["cli/launcher", "cli/kernel"]
```

**File**: `cli/launcher/Cargo.toml`
**Changes**: none. Confirm `kernel = { path = "../kernel" }` still resolves (both
crates are siblings under `cli/`) — verified by a green `build:launcher`, not by
editing.

#### Group B — Path + crate constants (`tasks/shared/`)

**File**: `tasks/shared/paths.py`
**Changes**: repoint the value AND rename the constant `CLI_DIR` → `LAUNCHER_DIR`;
the derived constants follow automatically.

```python
LAUNCHER_DIR = REPO_ROOT / "cli" / "launcher"
BIN_DIR = LAUNCHER_DIR / "bin"
CHECKSUMS = BIN_DIR / "checksums.json"
CARGO_TOML = LAUNCHER_DIR / "Cargo.toml"
```

**File**: `tasks/shared/rust.py`
**Changes**: rename the constant, keep the value, and repoint the invariant
comment's path — reworded to fit the 80-col limit (the full `must equal
cli/launcher/Cargo.toml [package] name` form is 82 cols and would trip ruff
E501). Also fix the bare-`cli` prose in the `coverage_enabled` docstring
(line 15): "Whether cli tests run instrumented" → "Whether launcher tests run
instrumented".

```python
LAUNCHER_CRATE = "luminosity"  # matches cli/launcher/Cargo.toml [package] name
```

(79 cols. `KERNEL_CRATE`'s `# must equal …` comment is shorter and stays as-is.
The verb differs from the sibling — "matches" vs "must equal" — **deliberately**:
the prescriptive `# must equal cli/launcher/Cargo.toml [package] name` form is 82
cols and trips E501, so "matches" is the width-driven wording. Don't "fix" it back
to "must equal". The invariant is in any case now machine-checked by the new
`TestToolchainCoherence` assertion below, so the comment is a pointer, not the
guarantee.)

#### Group C — Invoke task modules, registrations, and consumers

**Rename the module files** (jj-tracked move):

```sh
mv tasks/lint/cli.py   tasks/lint/launcher.py
mv tasks/format/cli.py tasks/format/launcher.py
mv tasks/test/cli.py   tasks/test/launcher.py
```

**File**: `tasks/lint/launcher.py`
**Changes**: task-name strings in the error message and the trailing comment.

```python
        raise Exit(
            "clippy reported findings — run `mise run lint:launcher:fix`", code=1
        )
```

and the comment `lint:cli:check` → `lint:launcher:check`.

**File**: `tasks/format/launcher.py`
**Changes**: the error message.

```python
        raise Exit(
            "rustfmt: drift — run `mise run format:launcher:fix`",
            code=1,
        )
```

**File**: `tasks/test/launcher.py`
**Changes**: the `CLI_CRATE` import → `LAUNCHER_CRATE`, its two `-p {…}` uses, the
failure message, and the docstring's bare-`cli` prose ("Run cli-crate unit
tests …" → "Run launcher-crate unit tests …").

```python
from tasks.shared.rust import LAUNCHER_CRATE, coverage_enabled
...
    command = (
        f"cargo llvm-cov nextest -p {LAUNCHER_CRATE} --summary-only"
        if coverage_enabled()
        else f"cargo nextest run -p {LAUNCHER_CRATE}"
    )
    with context.cd(str(REPO_ROOT)):
        result = context.run(command, warn=True, pty=False)
    if result.exited != 0:
        raise Exit("nextest: launcher tests failed", code=1)
```

**File**: `tasks/__init__.py`
**Changes**: repoint the two explicit registrations (lines 48, 56).

```python
ns_format.add_collection(Collection.from_module(format_.launcher))
...
ns_lint.add_collection(Collection.from_module(lint.launcher))
```

**File**: `tasks/lint/__init__.py`
**Changes**: import + `__all__`.

```python
from . import build_system, kernel, launcher, scripts, workflows

__all__ = ["build_system", "kernel", "launcher", "scripts", "workflows"]
```

**File**: `tasks/format/__init__.py`
**Changes**: import + `__all__`.

```python
from . import build_system, kernel, launcher, scripts

__all__ = ["build_system", "kernel", "launcher", "scripts"]
```

**File**: `tasks/test/__init__.py`
**Changes**: import + registration.

```python
from . import integration, kernel, launcher, unit
...
ns.add_collection(Collection.from_module(launcher))
```

**File**: `tasks/build.py`
**Changes**: rename the task function `cli` → `launcher`, swap the `CLI_CRATE`
import for `LAUNCHER_CRATE` (and its two uses), and update the docstring's
`build-cli` reference.

```python
from tasks.shared.rust import LAUNCHER_CRATE
...
def _binary(triple: str) -> str:
    return f"target/{triple}/release/{LAUNCHER_CRATE}"
...
@task
def launcher(context: Context) -> None:
    """Release-build the host-native triples, checking link/arch invariants.

    Host-native only (the two musl triples on Linux, the two darwin triples on
    macOS); CI's `build-launcher` matrix covers all four across both OSes. Builds
    the binary (`--bin`, not just `-p`) so the link step — the whole point of a
    per-triple build — is always exercised.
    """
    with context.cd(str(REPO_ROOT)):
        for triple in host_targets(platform.system()):
            result = context.run(
                f"cargo build --release --bin {LAUNCHER_CRATE} "
                f"--target {triple}",
                ...
```

**80-col note**: the constant rename lengthens this line. With `CLI_CRATE` (9
chars) the `cargo build …` string is 77 cols; substituting `LAUNCHER_CRATE`
(14 chars) makes it 82 — an E501 breach that would fail `mise run`. So this is
the one call site the rename overflows: split the f-string across two
implicitly-concatenated lines as shown (64 / 37 cols; ruff-format leaves implicit
concatenation unjoined, so the split is stable). The `_binary` helper
(`f"target/{triple}/release/{LAUNCHER_CRATE}"`, 54 cols) and the
`-p {LAUNCHER_CRATE}` uses stay under 80 and need no wrap.

**File**: `tasks/shared/targets.py`
**Changes**: the `build:cli` strings in the comment (line 23) and error message
(line 30) → `build:launcher`.

```python
    result would make `build:launcher` run zero builds and exit 0, a false-green
    ...
        raise Exit(
            f"build:launcher: unsupported host OS {system!r}; "
```

**File**: `tasks/deps.py`
**Changes**: the docstring `cli:check` (line 33) → `launcher:check`.

#### Group D — mise tasks (`mise.toml`)

**Changes**: rename the task keys, their `run` bodies, and every `depends` edge
into them. Concretely:

| Old key / edge          | New                          |
|-------------------------|------------------------------|
| `test:unit:cli`         | `test:unit:launcher`         |
| `format:cli:check`      | `format:launcher:check`      |
| `format:cli:fix`        | `format:launcher:fix`        |
| `lint:cli:check`        | `lint:launcher:check`        |
| `lint:cli:fix`          | `lint:launcher:fix`          |
| `cli:check`             | `launcher:check`             |
| `build:cli`             | `build:launcher`             |
| run `invoke test.cli.run`      | `invoke test.launcher.run`      |
| run `invoke format.cli.check`  | `invoke format.launcher.check`  |
| run `invoke format.cli.fix`    | `invoke format.launcher.fix`    |
| run `invoke lint.cli.check`    | `invoke lint.launcher.check`    |
| run `invoke lint.cli.fix`      | `invoke lint.launcher.fix`      |
| run `invoke build.cli`         | `invoke build.launcher`         |

`depends` edges to repoint (lines 70, 110, 114, 154, 213, 217, 229, 233):
`test:unit`→`test:unit:launcher`; `format:check`/`format:fix`→`format:launcher:*`;
`launcher:check` itself→`format:launcher:check`+`lint:launcher:check`;
`lint:check`/`lint:fix`→`lint:launcher:*`; `check`→`launcher:check`;
`default`→`build:launcher`.

Stale prose — the task *descriptions* still call the crate "cli" using bare words
that the reference-sweep grep does **not** match (it targets delimited tokens like
`build:cli`, not the word `cli`), so these must be edited explicitly:
- Line 31 (`deps:install:rust-components` description): "the cli checks need" →
  "the launcher checks need".
- Line 59 (`test:unit:cli` description): "Run cli-crate unit tests" →
  "Run launcher-crate unit tests".
- Line 153 (`cli:check` description): "Run all cli-crate format and lint checks" →
  "Run all launcher-crate format and lint checks".
- Line 157 (`kernel:check` description): "workspace-wide `cli:check` pass" →
  "workspace-wide `launcher:check` pass".
- Line 232 (`default` description): both "the build:cli host-native release build"
  → "the build:launcher host-native release build" **and** the "(cli tests carry
  coverage)" clause → "(launcher tests carry coverage)".

#### Group E — CI (`.github/workflows/main.yml`)

**Changes**:
- Job `check-cli` (key line 106) → `check-launcher`; `name: Check cli` →
  `name: Check launcher`; `run: mise run cli:check` → `mise run launcher:check`.
- Job `build-cli` (key line 129) → `build-launcher`; `name: Build cli` →
  `name: Build launcher`; `run: mise run build:cli` → `mise run build:launcher`
  (matrix and linker env unchanged).
- `needs:` edges in the `prerelease` job (lines 234, 235): `check-cli` →
  `check-launcher`, `build-cli` → `build-launcher`.
- Attestation `subject-path: "cli/bin/luminosity-*"` at lines 272, 327, 342 →
  `"cli/launcher/bin/luminosity-*"` (all three occurrences).

#### Group F — Tests (flip expectations first — red)

**File**: `tests/unit/tasks/test_mise_wiring.py`
**Changes**: rename `TestCliCheckWiring` → `TestLauncherCheckWiring`;
`TestBuildCliWiring` → `TestBuildLauncherWiring`; `TestTestUnitCliWiring` →
`TestTestUnitLauncherWiring`; update every asserted task-name string
(`cli:check`→`launcher:check`, `format:cli:*`→`format:launcher:*`,
`lint:cli:*`→`lint:launcher:*`, `build:cli`→`build:launcher`,
`test:unit:cli`→`test:unit:launcher`); the negative assertion
`"coverage:cli:check" not in names` (line 139) → `"coverage:launcher:check"`; the
`TestFinalEnumeratedArrays` arrays (lines 223, 234, 242); and
`test_rustfmt_edition_matches_cli_crate_edition` (line 261)
`REPO_ROOT / "cli/Cargo.toml"` → `REPO_ROOT / "cli/launcher/Cargo.toml"`.

Additionally, add a sibling coherence test in `TestToolchainCoherence` asserting
`LAUNCHER_CRATE` equals the `[package].name` parsed from
`cli/launcher/Cargo.toml` (reusing the same manifest read the edition test does).
This converts the hand-maintained "matches … [package] name" comment into a tested
invariant — the same treatment the edition/msrv mirrors already get — and is the
one assertion that binds the plan's highest-risk mutation (a lockstep
`luminosity`→`launcher` value-rewrite) in the fast unit suite rather than only at
`build:launcher`. It is a genuine red→green flip: it fails to import
`LAUNCHER_CRATE` before Group B lands and passes once the constant exists. Put the
`from tasks.shared.rust import LAUNCHER_CRATE` at module top (ruff `ALL` forbids
function-level imports); during the red phase this reddens the whole
`test_mise_wiring.py` module via `ImportError` until Group B introduces the
constant — acceptable, since that module's wiring assertions are being flipped in
the same phase anyway.

**File**: `tests/unit/tasks/test_workflows.py`
**Changes**: `test_check_cli_job_…` → asserts `jobs["check-launcher"]` runs
`"mise run launcher:check"` and `"check-launcher" in needs`; `test_build_cli_job_…`
→ asserts `jobs["build-launcher"]` runs `"mise run build:launcher"` and
`"build-launcher" in needs`.

**File**: `tests/unit/tasks/test_test.py`
**Changes**: `from tasks.test import cli, …` → `import launcher, …`;
`INSTRUMENTED`/`PLAIN` keep `-p luminosity` (value unchanged); `cli.run(ctx)` →
`launcher.run(ctx)`; class name `TestTestUnitCli` → `TestTestUnitLauncher`.

**File**: `tests/unit/tasks/test_build.py`
**Changes**: `from tasks.shared.rust import CLI_CRATE` → `LAUNCHER_CRATE`; the
`--bin {CLI_CRATE}` assertion → `{LAUNCHER_CRATE}`; `build.cli(ctx)` →
`build.launcher(ctx)`; class name `TestBuildCli` → `TestBuildLauncher`.

**File**: `tests/unit/tasks/test_format.py`
**Changes**: `from tasks.format import cli as fmt_cli` →
`import launcher as fmt_launcher`; `fmt_cli.check/fix` → `fmt_launcher.*`; class
names `TestFormatCli*` → `TestFormatLauncher*`.

**File**: `tests/unit/tasks/test_lint.py`
**Changes**: `from tasks.lint import cli as lint_cli` →
`import launcher as lint_launcher`; `lint_cli.check/fix` → `lint_launcher.*`; class
names `TestLintCli*` → `TestLintLauncher*`.

**File**: `tests/conftest.py`
**Changes** (unused fixture, coherence only): `tmp_path / "cli"` →
`tmp_path / "cli" / "launcher"` (line 16) and `tmp_path / "cli/bin"` →
`tmp_path / "cli/launcher/bin"` (line 21).

#### Group G — Docs / prose

**File**: `CLAUDE.md`
**Changes**: lines 20, 24, 25, 27, 28, 47 — `build:cli`→`build:launcher`,
`cli:check`→`launcher:check`, `test:unit:cli`→`test:unit:launcher`,
`lint:cli:fix`→`lint:launcher:fix`; the component list entry `cli (Rust)` →
`launcher (Rust)`; and the single-test note (line 47) — the `cargo nextest run -p
luminosity …` command keeps `-p luminosity` (value unchanged), but its prose label
`test:unit:cli path` → `test:unit:launcher path`. Note line 28 carries **both**
`build:cli` **and** `build-cli` (the CI-job token) — rename both (to
`build:launcher` / `build-launcher`); `build-cli` is a sweep pattern so a miss
here fails the sweep, but call it out so a line-by-line editor catches it.

Also the **Architecture → Rust workspace** section (lines 65, 69, 83), whose
bare-`cli/` directory references the sweep does not match: line 69's
`cli/Cargo.toml` becomes a **dead path** after the move → `cli/launcher/Cargo.toml`
(the version-bearing manifest); the line-65 heading path `cli/` and the line-83
"The `cli/` crate …" reference to the launcher crate → `cli/launcher/`. (Leave the
surrounding pre-0007 "throwaway bootstrap" wording alone — that drift is outside
0014's scope; only repoint the crate-directory paths.)

**File**: `deny.toml`
**Changes**: line 18 comment `build:cli` → `build:launcher`; line 49 comment
`(cli -> kernel)` → `(launcher -> kernel)`.

**File**: `tasks/README.md`
**Changes**: lines 14, 21, 27, 31, 32, 58, 59, 63, 73 — the "Rust cli crate" table
row and roll-up (`cli:check`→`launcher:check`), `build:cli`→`build:launcher`,
`test:unit:cli`→`test:unit:launcher`, `build-cli`→`build-launcher`. Also reword the
bare-noun `cli` references to the crate ("Rust cli crate", "cli unit tests") →
"launcher crate" / "launcher unit tests", so bare `cli` reads unambiguously as the
new container directory (these are not sweep patterns).

**File**: `CONTRIBUTING.md`
**Changes**: the required-check table (lines 31, 32) — job ids `check-cli` →
`check-launcher`, `build-cli` → `build-launcher`; required-check names `Check cli`
→ `Check launcher`, `Build cli (ubuntu-latest)` / `Build cli (macos-latest)` →
`Build launcher (ubuntu-latest)` / `Build launcher (macos-latest)`; the prose at
lines 41, 43 referencing `build-cli` and the `Build cli (…)` names.

#### Group H — CI required-check re-registration (manual)

This is the one step with **no local signal**, and it carries a rename-specific
deadlock: the PR that renames the jobs is itself gated by the *old* required-check
names (`Check cli`, `Build cli (…)`), which will never report once the jobs are
renamed — so the old checks sit forever as "Expected — waiting for status to be
reported" and the PR cannot merge until they are **removed** from the protection
rule. Adding the new names alone is not enough. Perform this as an ordered
sequence, by someone with branch-protection edit rights:

1. Push the branch / open the PR so `Check launcher`,
   `Build launcher (ubuntu-latest)`, and `Build launcher (macos-latest)` run once
   on the PR head and become selectable in the settings UI.
2. In **one** Settings → Branches → `main` → required-status-checks visit:
   **add** the three `launcher` names **and remove** the three old `cli` names
   (`Check cli`, `Build cli (ubuntu-latest)`, `Build cli (macos-latest)`) —
   removal is what unblocks the PR, addition is what keeps `main` gated.
3. Merge.

**Rollback (if the switch cannot be completed).** Because the workflow triggers on
both `push` and `pull_request`, a half-applied protection rule affects every open
and subsequent PR, not just this one. Pick the lever for the state you are in:
- **Pre-merge (step 2 interrupted, PR not yet landed)** — the common case, since
  the deadlock blocks the merge. There is no commit on `main` to revert: just
  restore the protection rule to its prior state (re-add the old `cli` names if you
  removed them, drop any half-added `launcher` names) and leave the branch
  unmerged; the still-existing `check-cli` / `build-cli` jobs keep reporting.
- **Post-merge (the rename commit already landed on `main`)** — revert that single
  atomic commit, which restores the `check-cli` / `build-cli` job names so the
  still-registered old required checks report again and the repo returns to a
  fully-gated known-good state; or temporarily remove the affected checks from the
  required list to unblock, then re-add the `launcher` names once the rename
  settles.

An admin bypass to force-merge before step 2 completes leaves a window where the
Rust guard-rail jobs gate nothing — avoid it; finish step 2 first.

### Success Criteria:

#### Automated Verification:

- [ ] Tests flipped to new names fail before the code changes land (confirms the
      assertions actually bind): `uv run pytest tests/unit/tasks -v` shows the
      renamed wiring/assertion tests red. Note the meaningful red→green signal
      comes from the **positive** exact-array/exact-dependency assertions
      (`TestFinalEnumeratedArrays`, the `== [format:launcher:check,
      lint:launcher:check]` roll-up assertion) and the new `LAUNCHER_CRATE`-import
      coherence test — the negative/absence assertions (`"build:cli" not in …`,
      `"coverage:cli:check" not in names`) pass in both the old and new state, so
      treat those as coherence updates, not red-first proof.
- [ ] Full local CI mirror is green end-to-end: `mise run` exits 0 — includes
      `build:launcher` (which confirms `../kernel` resolves from `cli/launcher/`),
      the whole test roll-up, and `deny:check` / `pup:check`.
- [ ] Read-only check set is green: `mise run check` exits 0.
- [ ] The crate's tasks are renamed and none of the old ones survive:
      `mise tasks | grep -E 'launcher|build:launcher'` lists them and
      `mise tasks | grep -E ':cli:|cli:check|build:cli'` is empty.
- [ ] No `[package]`-bearing crate at the repo root and both crates relocated:
      `test -f cli/launcher/Cargo.toml && test -f cli/kernel/Cargo.toml` succeeds,
      and `find . -maxdepth 2 -name Cargo.toml -not -path './cli/*' -not -path
      './target/*'` returns only the root `./Cargo.toml` (the `[package]`-free
      workspace manifest, which stays).
- [ ] Task modules renamed: `ls tasks/lint tasks/format tasks/test` each show
      `launcher.py` and no `cli.py`.
- [ ] Reference sweep empty — the safety net for stray *task/path tokens*
      (**not** bare-noun `cli` prose, which the Group C/D/G edits cover
      explicitly, since these delimited patterns don't match the word `cli`):
      `grep -rn --exclude-dir=meta --exclude-dir=.git --exclude-dir=target
      --exclude-dir=.venv --exclude-dir=.pytest_cache --exclude-dir=__pycache__
      -e 'build:cli' -e 'test:unit:cli' -e 'format:cli' -e 'lint:cli'
      -e 'cli:check' -e 'check-cli' -e 'build-cli' -e 'CLI_CRATE' -e 'CLI_DIR' .`
      returns nothing.
- [ ] Bare-`cli` prose coherence pass (catches the stale descriptions/docstrings
      the token sweep misses): `grep -rniw --exclude-dir=meta --exclude-dir=.git
      --exclude-dir=target --exclude-dir=.venv --exclude-dir=.pytest_cache
      --exclude-dir=__pycache__ cli tasks/ CLAUDE.md tasks/README.md CONTRIBUTING.md`
      — every remaining hit legitimately refers to the new `cli/` **container
      directory** (or paths under it) or the inbound CLI adapter source file, not
      the relocated crate. (Not an empty-grep criterion — a manual confirm that no
      hit still names the crate `cli`.)
- [ ] Package/bin invariants hold: `cli/launcher/Cargo.toml` `[package] name` and
      `[[bin]] name` are `luminosity`; `grep -c luminosity::version::core pup.ron`
      is non-zero; `plugin.json`'s version field is unchanged
      (`git diff -- .claude-plugin/plugin.json` empty for the version line).
- [ ] CI job topology asserted: `uv run pytest
      tests/unit/tasks/test_workflows.py tests/unit/tasks/test_mise_wiring.py -v`
      passes with the `launcher` names.
- [ ] `main.yml` defines `check-launcher` and `build-launcher`, no `check-cli` /
      `build-cli`, and the three `subject-path` values are
      `cli/launcher/bin/luminosity-*`.

#### Manual Verification:

- [ ] The built binary is named `luminosity` (inspect
      `cli/launcher/bin/` / `target/*/release/` after `mise run`).
- [ ] Branch-protection required checks list contains `Check launcher`,
      `Build launcher (ubuntu-latest)`, `Build launcher (macos-latest)` and no
      longer contains the old `Check cli` / `Build cli (…)` names
      (`gh api repos/{owner}/{repo}/branches/main/protection --jq
      '.required_status_checks.contexts'`), and a PR is mergeable.

---

## Testing Strategy

### Unit Tests:

- The rename is guarded by the existing task-wiring suite
  (`test_mise_wiring.py`, `test_workflows.py`) and the per-module command-string
  suites (`test_test.py`, `test_build.py`, `test_format.py`, `test_lint.py`).
  These are flipped to the `launcher` names first, so they go red, then green as
  the source lands — the TDD loop for a rename.
- Key edge to preserve: assertions that carry the **value** `luminosity`
  (`-p luminosity`, `--bin {LAUNCHER_CRATE}`, `INSTRUMENTED`/`PLAIN` in
  `test_test.py`) must keep that value — only identifiers/task names change. A
  test that accidentally rewrites `luminosity` → `launcher` would be a regression.

### Integration Tests:

- `mise run` exercises the relocated build end-to-end: `build:launcher` compiling
  and link/arch-checking the host-native triples from `cli/launcher/` is the
  authoritative proof that `../kernel` still resolves.
- `test:integration:deny` / `test:integration:pup` (via the `test` roll-up and
  `check`) confirm the supply-chain and architecture lanes are unaffected by the
  directory move.

### Manual Testing Steps:

1. Run `mise run` and confirm exit 0 and a `luminosity`-named binary under
   `cli/launcher/bin/`.
2. Run the reference-sweep grep above and confirm it is empty.
3. Push the branch, let CI run once, then re-register the required checks per the
   `CONTRIBUTING.md` runbook and confirm a PR shows the new checks as required and
   is mergeable.

## Performance Considerations

None. The change is a directory move plus identifier/string renames; build and
runtime behaviour are unchanged. `mise run` recompiles Rust (the relocated crate
paths invalidate incremental caches once), a one-time cost.

## Migration Notes

- The move is delivered atomically in one change; there is no intermediate state
  on `main` where the directory and task names disagree.
- `checksums.json` moves from `cli/bin/` to `cli/launcher/bin/` and its recorded
  binary bytes may change when rebuilt from the relocated path; only the recorded
  binary **name** `luminosity` must be preserved.
- The CI required-check re-registration (Group H) is the sole coupling with no
  local signal. It must **add the new names and remove the old ones in the same
  settings visit** — removing the old `cli` names is what unblocks the rename PR
  (which is still gated by them), adding the `launcher` names is what keeps `main`
  gated. See Group H for the ordered sequence and the rollback path if the switch
  is interrupted.

## References

- Original work item: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Related research: `meta/research/codebase/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- Work-item review: `meta/reviews/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-review-1.md`
- Antecedent (scaffolded the crates being moved):
  `meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md`
- Required-check runbook: `CONTRIBUTING.md` (Branch-protection required checks)
- Task-tree shape: `tasks/README.md`
