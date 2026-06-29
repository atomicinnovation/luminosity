---
type: plan
id: "2026-06-29-0007-scaffold-hexagonal-rust-workspace"
title: "Scaffold the Hexagonal Rust Workspace with a version Subcommand Implementation Plan"
date: "2026-06-28T23:21:10+00:00"
author: "Toby Clemson"
producer: create-plan
status: ready
work_item_id: "work-item:0007"
parent: "work-item:0007"
derived_from: ["codebase-research:2026-06-28-0007-scaffold-hexagonal-rust-workspace"]
relates_to: ["work-item:0008", "work-item:0009"]
tags: [rust, cli, hexagonal, scaffold, cargo-pup, vergen, mise]
revision: "68ced4569b6bd885d5abeb858a1a1ba05d58059e"
repository: "luminosity"
last_updated: "2026-06-29T00:07:40+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Scaffold the Hexagonal Rust Workspace with a version Subcommand Implementation Plan

## Overview

Replace the throwaway `describe_release` bootstrap with a genuine, minimal
**hexagon** (ADR-0009) for a `luminosity version` subcommand, and add a
second, dependency-light **`kernel`** crate. The proof is structural, not the
feature: `version` is driven through an inbound port, sources its build
metadata through an outbound/driven port wired at a composition root, and is
exercised against an in-memory fake — so the ports-and-adapters architecture is
real and later stories (0008, 0009) have a skeleton to build on. Built strictly
test-first, with cargo-pup proven *live* as the sole inward-direction enforcer.

## Current State Analysis

The Rust footprint today is a deliberate single-crate bootstrap, and every
architectural-enforcement mechanism is present but **inert**:

- **Workspace** (`Cargo.toml:1-20`): versionless, resolver 2,
  `members = ["cli"]`. Centralises **lint levels only** —
  `[workspace.lints.rust] warnings = "deny"`, clippy `pedantic`+`nursery` at
  `warn`, and `unwrap_used`/`expect_used`/`panic`/`dbg_macro`/`todo`/
  `unimplemented` all `warn`. **No `[workspace.dependencies]` table** and no
  `[profile.*]`.
- **`cli` crate**: package `luminosity` `0.1.0-pre.0` (`cli/Cargo.toml`),
  edition 2021, `[lints] workspace = true`, explicit `[[bin]]`, **zero
  dependencies**. `cli/src/lib.rs` holds the throwaway
  `describe_release(bool) -> &'static str` (its own doc comment names story 0007
  as its replacer) with two inline `#[cfg(test)]` tests; `cli/src/main.rs` (5
  lines) prints `luminosity prerelease`.
- **cargo-pup**: `pup.ron` is `( lints: [] )`. The pinned nightly lane
  (`PUP_NIGHTLY = "nightly-2026-01-22"`, `PUP_VERSION = "0.1.8"` in
  `tasks/shared/rust.py:6-7`) is wired (`tasks/pup.py`, `pup:check` in both
  `check` and `default`) and proven to have teeth by a probe test
  (`tests/integration/pup/test_pup_rules.py`).
- **cargo-deny**: `deny.toml` graph covers the four release triples **plus**
  `x86_64-unknown-linux-gnu` (the dev/CI host triple); the native-tls ban is
  active; the architectural `skip`/`skip-tree` ban-lists are explicitly inert
  in the single-crate bootstrap; the licence allow-list is pre-seeded for the
  ADR-0010 stack (clap/reqwest/rustls/tokio closures) but **not** vergen /
  gitoxide.
- **Task tree**: Rust checks are **workspace-scoped**. `format:cli:check`
  (`cargo fmt --all`), `lint:cli:check` (`cargo clippy --workspace`),
  `deny:check`, and `pup:check` already cover *any* new workspace member with no
  task change. The **only** crate-name enumeration is `CLI_CRATE = "luminosity"`
  (`tasks/shared/rust.py:3`), consumed by `test:unit:cli` (`-p luminosity`) and
  `build:cli` (`--bin luminosity`).
- **Version SSOT**: `tasks/version.py` mirrors one version across
  `plugin.json`, `cli/Cargo.toml`, and `checksums.json`; its `read()` reads
  `plugin.json`. `plugin.json` and `cli/Cargo.toml` are coherent at
  `0.1.0-pre.0` today.

### Key Discoveries

- **Workspace-scoped checks are the load-bearing convenience.** Adding a
  *library* crate costs almost nothing for the aggregate lanes; per-crate
  ceremony only matters for a crate that ships a binary or needs an isolated
  test run (`tasks/lint/cli.py:10-14`, `tasks/format/cli.py:9-10`).
- **cargo-pup v0.1.8 module-rule syntax (DataDog/cargo-pup).** The variant is
  `Module(ModuleLint)` carrying `RestrictImports { allowed_only, denied,
  severity }`. **The matcher differs from the existing `Struct` probe**: a
  `Module` lint uses `matches: Module("regex")` (a `ModuleMatch`), *not*
  `Name(...)`. Authored against the real fully-qualified module paths that
  `cargo +nightly-2026-01-22 pup print-modules` reports. (Confirmed against the
  v0.1.8 source `cargo_pup_lint_config/src/module_lint/types.rs`.)
- **The CI test host is gnu, not musl.** `test-unit` runs on `ubuntu-latest`
  (`x86_64-unknown-linux-gnu`) and `macos-latest` (`aarch64-apple-darwin`). So a
  black-box test cannot assert the embedded target triple is one of ADR-0002's
  four *shipped* triples — on the ubuntu runner it will be the gnu dev triple.
  This is exactly why `deny.toml:8-14` lists gnu alongside the four.
- **The lint wall shapes every new file from line one**: `warnings = "deny"` +
  clippy pedantic/nursery + banned `unwrap`/`expect`/`panic`/`todo`/
  `unimplemented`. New production code, the build script, and **the tests** must
  avoid `.unwrap()`/`.expect()`/`panic!` (use `assert_eq!`/`?`/explicit match,
  as the existing inline tests do).
- **No new CI jobs / branch-protection registrations are required.**
  `test-unit` runs `mise run test:unit` (picks up `test:unit:kernel`),
  `check-cli` runs `mise run cli:check` (workspace-wide, covers `kernel`),
  `check-architecture` runs `pup:check` + `test:integration:pup` (picks up new
  rules + the extended suite), `check-supply-chain` runs `deny:check` (covers
  new deps). Reusing existing job names needs no manual registration.

## Desired End State

- `luminosity version` prints the crate version, commit SHA, build date, and
  target triple, all sourced correctly (version from `CARGO_PKG_VERSION`;
  metadata injected at build time via vergen).
- The workspace is exactly `cli` + `kernel`; `cli` depends on `kernel`; the
  `version` hexagon's inbound port, core, outbound port, build-metadata adapter,
  and composition root are distinct modules **inside `cli`**; `kernel` holds
  only the cross-cutting error taxonomy.
- cargo-pup enforces the inward rule and is **proven live** by an automated
  test: a domain→adapter import is rejected; its removal goes green.
- `mise run check` and the bare `mise run` default both exit 0.

Verified by the success criteria at the end of each phase below.

## What We're NOT Doing

- **No external-subcommand dispatch.** clap's
  `#[command(external_subcommand)] External(Vec<OsString>)` and its derive
  confirmation are relocated to story 0008 (per this story's Drafting Notes and
  ADR-0010). `version` is a plain in-process built-in subcommand only.
- **No `config`, `config-adapters`, or any per-subdomain crate.** The starting
  set is exactly `cli` + `kernel`; the rest arrive with the stories that need
  them (0009+).
- **No realignment of `tasks/version.py read()`** to read the crate version.
  The binary learns its version idiomatically via `env!("CARGO_PKG_VERSION")`,
  which makes the crate the de-facto SSOT without touching `version.py`'s
  plugin.json-first read path. Realigning `read()` / `paths.py` is out of scope
  (it is the 0006-flagged tension and is independent of this story's output).
- **No CI grep tripwire** beneath cargo-pup — ADR-0009 deliberately omits it.
- **No coverage threshold** — coverage stays report-only, per the established
  convention.
- **No new top-level CI job or branch-protection required-check.**

## Implementation Approach

Three phases, each ending with `mise run` green so each is **independently
mergeable**. The dependency order is Phase 1 → 2 → 3 (Phase 3's pup rule
references module paths created in Phase 2), but no phase leaves `main` red.

Decisions taken (confirmed with the story owner):

1. **`kernel:check` is a distinct, targeted roll-up** (`-p kernel`) for ad-hoc
   single-crate runs, but is **kept out of the top-level `check`** — the
   aggregate keeps using the single workspace-wide rustfmt/clippy pass
   (`cli:check`) so the overall check pays one tool startup per tool, not one
   per crate. `kernel`'s code is still fully checked under `check` via that
   workspace-wide pass plus `deny:check`/`pup:check`.
2. **Build metadata via `vergen`**, consumed at the outbound adapter through
   `option_env!` (never bare `env!`) so a build context that cannot resolve a
   value yields a degraded-but-compiling binary rather than a hard compile error.
   **The adapter's `option_env!(...).unwrap_or("unknown")` is the authoritative
   fallback**: when vergen cannot resolve a git fact the env var is simply
   *absent* (vergen does not itself emit an `"unknown"` sentinel), `option_env!`
   evaluates to `None`, and `.unwrap_or("unknown")` supplies the sentinel. The
   build script additionally sets `fail_on_error(false)` on the git emitter —
   **this only stops the build script from erroring on an unresolvable git fact;
   it does not emit a placeholder var.** So git-absence (no `.git` / no `git`
   binary / a shallow-detached state) is handled end-to-end: the build still
   compiles and the binary self-reports `"unknown"` for the missing fact. The
   backend (`gix` vs `gitcl`) is an
   **explicit resilience decision**, not merely a `deny:check` dep-weight
   tiebreak: `gitcl` shells out to the `git` CLI (a hidden host-tool
   prerequisite — `git` on PATH plus a real `.git`), whereas `gix`/`vergen-gix`
   is self-contained. Default to `gitcl` to honour the dependency-resisting
   ethos **only because** the established build pipeline always builds inside a
   git working tree; record that prerequisite, and prefer `gix` if any
   non-git-checkout build context (tarball/vendored/`cargo install`) becomes
   plausible. Either way the licence allow-list is re-checked and extended via
   `[[licenses.exceptions]]` if needed. The `build:cli` success criterion here
   exercises the backend only in the **host-native** build; the chosen backend
   must *also* be confirmed working under the ADR-0002 **zigbuild cross-compile
   release path** (owned by story 0008) — flagged there so the metadata mechanism
   is portable across both build environments, not only the host-native one.
3. **`[workspace.dependencies]`** is introduced now; `cli` consumes
   `clap = { workspace = true }` and `vergen = { workspace = true }`
   (build-dep), setting the central-pinning precedent ADR-0010's workspace-wide
   consistency will need.
4. **Dependency versions are pinned MSRV-first and verified against both
   toolchains.** Every new dep (`clap`, `vergen` + backend, `time`) is pinned to
   a version whose `rust-version` is ≤ the `msrv` mirror (`1.90.0`; see
   `clippy.toml` / `mise.toml`), the resolution is frozen in a committed
   `Cargo.lock`, and the build-dep tree is verified to compile **not only** on
   the stable pin but **also** under cargo-pup's pinned `nightly-2026-01-22`
   (since `pup:check` compiles `cli` including `build.rs` and its build-deps). If
   a required vergen version will not build on that nightly, `PUP_NIGHTLY` /
   `PUP_VERSION` are bumped in lockstep (`tasks/shared/rust.py`).

TDD is applied within each phase: a failing test is written first, then the
minimum code to pass it, then refactor.

---

## Phase 1: The `kernel` crate and its task-tree wiring

### Overview

Add the second workspace member — a deliberately dependency-light `kernel`
holding the cross-cutting error taxonomy `version` will report through — and
wire it into the component-based task tree with a distinct, targeted
`kernel:check` roll-up and a `test:unit:kernel`. This phase stands alone: it
adds no dependency on `cli` and leaves the build green.

### Changes Required

#### 1. Workspace membership

**File**: `Cargo.toml`
**Changes**: add `"kernel"` to `members`.

```toml
members = ["cli", "kernel"]
```

#### 2. The `kernel` crate

**File**: `kernel/Cargo.toml` (new)
**Changes**: a library crate opting into the workspace lints; no dependencies.

```toml
[package]
name = "kernel"
version = "0.1.0-pre.0"
edition = "2021"
license = "MIT"

[lints]
workspace = true
```

**File**: `kernel/src/lib.rs` (new)
**Changes**: a starter cross-cutting error taxonomy — a domain-language error
type the CLI dispatch / `version` report through, with a `Display` impl and
`std::error::Error`. It ships as an **uninhabited (never-constructed) enum** in
Phase 1: a type-level dispatch seam only. Because no variant can be constructed,
its `Display` impl is statically unreachable (`match *self {}`) and **no Phase 1
unit test can exercise rendered behaviour** — so Phase 1 deliberately ships *no*
`Display`/`Error` test for `kernel`. The first real, constructable variant and
its red-green rendered-message test arrive under genuine TDD pressure (Phase 2's
dispatch boundary, or stories 0008/0009), not speculatively here.

```rust
//! Cross-cutting contracts shared across luminosity subdomains. Deliberately
//! dependency-light (ADR-0010): everything links it, so a dependency tail is
//! resisted. For the version scaffold it holds only the error taxonomy.

use std::fmt::{self, Display, Formatter};

/// The cross-cutting error taxonomy luminosity subcommands report through.
#[derive(Debug)]
pub enum Error {
    // Starter variant(s); the exact taxonomy grows with the stories that need
    // it. version never produces one today, but the dispatch boundary speaks
    // this type so the taxonomy is established.
}

impl Display for Error {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        match *self {}
    }
}

impl std::error::Error for Error {}
```

> Implementation note: a never-constructed empty enum keeps `kernel` honestly
> minimal while still giving `cli` a concrete error type to name at its
> dispatch boundary. If TDD pressure during Phase 2 wants a real variant (e.g.
> the inbound port returns `Result<_, kernel::Error>` and a fake exercises a
> failure), add it then, test-first, rather than speculatively here. The
> constraint for Phase 1 is: real `Display` impl, real `Error` impl, no
> `version` core logic — and **no test** (an uninhabited enum has nothing to
> construct, so a rendered-message assertion is unwritable; do not fabricate a
> vacuous one). To keep the seam from being inert at the boundary, the
> composition root's error→exit-code mapping (Phase 2) should be written as a
> `match` over `kernel::Error`, so adding the first variant later is a localised,
> compiler-guided change rather than a structural one.

#### 3. Targeted per-crate task leaves + roll-up

**Files**: `tasks/format/kernel.py`, `tasks/lint/kernel.py`, `tasks/test/kernel.py`
(new) — each a **full structural mirror** of its `cli` sibling (same imports,
docstring, `REPO_ROOT` cd, `warn=True`/`Exit`-on-failure handling, and for the
test module the `coverage_enabled()` branch), changing only the crate scope to
`-p kernel`, so the roll-up is a genuine subset rather than a second
workspace-wide pass. A literal copy of only the differing line would fail ruff
`ALL` / pyrefly strict — the modules must be complete, not snippets.

```python
# tasks/format/kernel.py
result = context.run("cargo fmt -p kernel --check", warn=True, pty=False)
# fix: "cargo fmt -p kernel"

# tasks/lint/kernel.py
result = context.run(
    "cargo clippy -p kernel --all-targets --all-features -- -D warnings",
    warn=True, pty=False,
)
# fix: "cargo clippy -p kernel --all-targets --all-features "
#      "--fix --allow-dirty --allow-staged"

# tasks/test/kernel.py — mirror tasks/test/cli.py, coverage-gated
command = (
    f"cargo llvm-cov nextest -p {KERNEL_CRATE} --summary-only"
    if coverage_enabled()
    else f"cargo nextest run -p {KERNEL_CRATE}"
)
```

**File**: `tasks/shared/rust.py`
**Changes**: add the crate-name constant alongside `CLI_CRATE`.

```python
KERNEL_CRATE = "kernel"  # must equal kernel/Cargo.toml [package] name
```

**File**: `tasks/__init__.py` / `tasks/format/__init__.py` /
`tasks/lint/__init__.py` / `tasks/test/__init__.py`
**Changes**: register the new modules in **two places each**, but the second
location differs by family — the established patterns are not uniform:

- **format / lint**: (a) add `kernel` to `tasks/format/__init__.py` /
  `tasks/lint/__init__.py` (import + `__all__`), **and** (b) add the matching
  `ns_format.add_collection(Collection.from_module(format_.kernel))` /
  `ns_lint.add_collection(Collection.from_module(lint.kernel))` line in the
  hand-built Collections block of the top-level `tasks/__init__.py`, mirroring the
  existing per-module `cli` lines.
- **test**: (a) add `kernel` to `tasks/test/__init__.py` (the `from . import …`
  line + a `Collection.from_module(kernel)` registration there). **No top-level
  edit is needed** — `tasks/__init__.py` pulls the test family *wholesale* via
  `Collection.from_module(test)`, so unlike format/lint there is no per-test-module
  line in the top-level Collections block. Adding one there would be wrong.

Missing the correct second location leaves the new tasks unresolvable
(`format.kernel.*` / `lint.kernel.*` for format/lint; `test:unit:kernel` for
test).

**File**: `mise.toml`
**Changes**: add the leaves + roll-up + the test task, and thread the test into
`test:unit`. Provision rustfmt/clippy on each leaf (the `cli` convention).
`kernel:check` is **not** added to `check`. Because this makes `kernel:check`
the **first** `<component>:check` roll-up that is *not* part of the aggregate
`check` (every existing one — `build-system:check`, `scripts:check`,
`cli:check` — is), the rationale must be discoverable, not silent: put it in the
`kernel:check` task's `description` string (e.g. "Targeted kernel rustfmt+clippy
for ad-hoc runs; deliberately excluded from aggregate `check`, which covers
kernel via the single workspace-wide `cli:check` pass"), not only in test
comments.

```toml
[tasks."format:kernel:check"]   # depends = ["deps:install:rust-components"]
[tasks."format:kernel:fix"]     # depends = ["deps:install:rust-components"]
[tasks."lint:kernel:check"]     # depends = ["deps:install:rust-components"]
[tasks."lint:kernel:fix"]       # depends = ["deps:install:rust-components"]
[tasks."kernel:check"]          # depends = ["format:kernel:check", "lint:kernel:check"]
[tasks."test:unit:kernel"]      # run = "invoke test.kernel.run"

# thread kernel tests into the parallel unit roll-up:
[tasks."test:unit"]             # depends = [..., "test:unit:cli", "test:unit:kernel"]
```

> Deliberate exclusions (asserted in tests): `kernel:check` is **absent** from
> `check`, `fix`, `format:fix`, `lint:fix`, and `format:check`/`lint:check`
> aggregates — the aggregate pays one workspace-wide rustfmt + one
> workspace-wide clippy via `cli:check`, not a second per-crate startup. The
> `check`/`default` top-level arrays are therefore **unchanged**.

#### 4. Document the new task-tree shape

**File**: `tasks/README.md`
**Changes**: `tasks/README.md` is the designated SSOT for the task-tree *shape*
("learn it once" — CLAUDE.md), so the new component must be recorded there or
the documentation drifts from the tree. Add a `kernel` row to the per-component
table, and a sentence under per-component checks noting that `kernel:check` is a
targeted single-crate roll-up **deliberately kept out of the aggregate `check`**
(which covers `kernel` via the workspace-wide `cli:check` pass) — making the one
intentional departure from the "`<component>:check` folds into `check`" pattern a
documented, discoverable choice. Confirm the existing "only binary-producing
crates get a `build:*`" note already covers `kernel` getting no `build:kernel`
(it does).

#### 5. Pin the new wiring with tests

**File**: `tests/unit/tasks/test_mise_wiring.py`
**Changes**: add a `TestKernelCheckWiring` class and update the enumerated
array, in the established style:

```python
class TestKernelCheckWiring:
    def test_kernel_check_folds_format_and_lint_only(self, mise):
        assert _depends(mise, "kernel:check") == [
            "format:kernel:check", "lint:kernel:check",
        ]

    def test_kernel_check_is_deliberately_excluded_from_check(self, mise):
        # Per the story owner: the aggregate uses the single workspace-wide
        # cli:check pass (which covers kernel too) rather than paying a second
        # per-crate tool startup. The targeted kernel:check is for ad-hoc runs.
        assert "kernel:check" not in _depends(mise, "check")

    @pytest.mark.parametrize("leaf", [
        "format:kernel:check", "format:kernel:fix",
        "lint:kernel:check", "lint:kernel:fix",
    ])
    def test_kernel_leaves_provision_rustfmt_and_clippy(self, mise, leaf):
        assert "deps:install:rust-components" in _depends(mise, leaf)

# update the pinned array:
def test_test_unit_array(self, mise):
    assert _depends(mise, "test:unit") == [
        "test:unit:tasks", "test:unit:cli", "test:unit:kernel",
    ]
```

**Files**: new unit tests mirroring `tests/unit/tasks/test_test.py` and the
format/lint task tests — assert the exact command strings built by
`tasks/format/kernel.py`, `tasks/lint/kernel.py`, `tasks/test/kernel.py`
(including the `coverage_enabled()` branch for the test task). This is the
established "every Rust task module ships with parallel unit tests asserting the
exact command string" convention.

### Success Criteria

#### Automated Verification

- [x] Targeted kernel check passes: `mise run kernel:check`
- [x] The kernel test task is wired and green: `mise run test:unit:kernel`
      (it runs zero Rust tests in Phase 1 — the empty enum has nothing to test.
      NOTE: this nextest (0.9.138) treats an empty test set as a hard error
      (exit 4), NOT exit 0 as the plan assumed — so the kernel test task carries
      `--no-tests=pass` to stay green with no tests. The flag is inert once the
      first real kernel test lands.)
- [x] Wiring + command-string unit tests pass:
      `uv run pytest tests/unit/tasks/test_mise_wiring.py -v` and the new
      `test_kernel.py` suite
- [x] Workspace-wide checks still green and now cover `kernel`:
      `mise run cli:check` and `mise run check`
- [x] Full local CI mirror green: `mise run`

#### Manual Verification

- [x] `cargo metadata` (or `cargo tree`) shows exactly two members, `cli` and
      `kernel`, with `kernel` carrying no dependencies.

---

## Phase 2: The `version` hexagon inside `cli`

### Overview

Build the genuine minimal hexagon for `version` as modules **within `cli`**:
inbound/driving port (trait) ← clap inbound adapter; a domain/application core
depending on no infrastructure; an outbound/driven port (trait) for build
metadata; a vergen outbound adapter; and a composition root at the binary entry
point. Replace `describe_release`. Built test-first: the core-against-fake unit
test (AC4) is written and red before the core exists; the black-box integration
test (AC1, AC5) is written and red before the wiring exists.

### Changes Required

#### 1. Central dependency pinning

**File**: `Cargo.toml`
**Changes**: introduce `[workspace.dependencies]`.

```toml
[workspace.dependencies]
# Each version below MUST be chosen MSRV-first: pick the version whose
# rust-version is <= 1.90.0 (the clippy.toml / mise.toml msrv mirror) AND that
# also compiles under cargo-pup's pinned nightly-2026-01-22 (pup compiles cli's
# build-deps). Freeze the resolution in a committed Cargo.lock.
clap = { version = "<pinned 4.x, msrv<=1.90>", features = ["derive"] }
# Backend feature settled by deny:check (default the lighter gitcl):
vergen = { version = "<pinned, msrv<=1.90>", features = ["build", "cargo"], default-features = false }
# (+ a git backend: vergen-gitcl OR vergen-gix as the deny result dictates)
time = { version = "<pinned, msrv<=1.90>", features = ["parsing", "formatting"] }  # dev-only consumer
```

> **Pin the vergen major line: 9.x (the companion-crate model)** — the manifest
> and `build.rs` shapes shown here assume vergen 9.x, where the git emitter lives
> in a separate companion crate (`vergen-gitcl` / `vergen-gix`) with the 9.x
> builder API. vergen 8.x is materially different (git feature on the main
> `vergen` crate, a different builder), so the snippets would not apply — choose
> the 9.x line (subject to the MSRV-≤1.90 / pup-nightly constraints in Decision
> 4). The git-SHA capability comes from the chosen backend crate (`vergen-gitcl`
> default, or `vergen-gix`); `build` gives the RFC-3339 build timestamp, `cargo`
> gives the target triple. Exact crate/feature names are confirmed against the
> pinned vergen version during implementation. `time` is consumed only by the dev
> (test) target.

#### 2. `cli` manifest

**File**: `cli/Cargo.toml`
**Changes**: add the first `[dependencies]`, `[build-dependencies]`, and
`[dev-dependencies]` tables; depend on `kernel` (satisfying AC2's
"`cli` depends on `kernel`").

```toml
[dependencies]
kernel = { path = "../kernel" }
clap = { workspace = true }

[build-dependencies]
vergen = { workspace = true }
# + the chosen vergen git backend

[dev-dependencies]
time = { workspace = true }
```

#### 3. Build-time metadata injection

**File**: `cli/build.rs` (new)
**Changes**: emit the build metadata as `cargo:rustc-env` vars via vergen.
Returns `Result` and uses `?` (no `unwrap`/`expect`/`panic` — the lint wall
applies to the build script too). **Set `fail_on_error(false)` on the git
emitter** so a build context that cannot resolve git facts (no `.git`, no `git`
binary for the gitcl backend, a shallow-detached state) does not *error the build
script*. Note this does **not** make vergen emit a placeholder var — the var is
simply left unset; the binary's degraded-but-buildable behaviour comes from the
adapter's `option_env!(...).unwrap_or("unknown")` fallback (the authoritative
mechanism), which is what keeps it buildable everywhere. **Confirm vergen's
`cargo:rerun-if-changed` directives track the git ref files** (e.g.
`.git/HEAD` and the resolved ref) so the embedded SHA/timestamp actually
invalidate on a new commit rather than being served stale from the build-script
cache.

```rust
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    // vergen emitter: build timestamp (RFC 3339), cargo target triple, git SHA.
    // git emitter built with fail_on_error(false) so a git-less / shallow build
    // does not error the build script (the var is then simply unset; the
    // adapter's option_env!(...).unwrap_or("unknown") supplies the sentinel).
    // Emits VERGEN_BUILD_TIMESTAMP, VERGEN_CARGO_TARGET_TRIPLE, VERGEN_GIT_SHA
    // plus the cargo:rerun-if directives vergen manages (verify these track
    // .git/HEAD + the ref so the SHA changes on a new commit).
    Ok(())
}
```

#### 4. The hexagon modules (all inside `cli`)

Proposed layout (internal naming settled during implementation per the story;
the constraint is that the five concerns are distinct modules and the inward
rule holds). This scaffold sets the module-file style every later subdomain
copies, so the choice is **deliberate, not incidental**: the layout below uses
the `version/mod.rs` directory-module form (the `version.rs` + `version/` sibling
form is the equally-valid alternative — pick one and keep subsequent stories
consistent with it):

```
cli/src/
  lib.rs                       # crate root: module declarations only
  main.rs                      # composition root + clap entry (thin)
  version/
    mod.rs                     # re-exports the slice's public surface
    core.rs                    # domain + application core; defines BOTH ports
    inbound/cli.rs             # clap subcommand adapter (presentation only)
    outbound/build_metadata.rs # vergen-backed adapter (reads env! values)
```

**`version/core.rs`** — the core and **both ports as traits** (ADR-0009: ports
live with the core, not the adapters):

```rust
/// Build-time facts the core requires — an outbound/driven port. ALL four facts
/// (including the crate version) flow through this one boundary so the core is
/// uniformly env!-free and fully substitutable by the in-memory fake.
pub trait BuildMetadata {
    fn crate_version(&self) -> &str;  // real adapter: env!("CARGO_PKG_VERSION")
    fn commit_sha(&self) -> &str;
    fn build_date(&self) -> &str;     // RFC 3339
    fn target_triple(&self) -> &str;
}

/// What `version` produces — a value object, no presentation.
pub struct VersionReport {
    pub version: String,
    pub commit_sha: String,
    pub build_date: String,
    pub target_triple: String,
}

/// The operation the core offers callers — an inbound/driving port.
pub trait ReportVersion {
    fn report(&self) -> VersionReport;
}

/// The application service: depends only on the outbound trait, never on a
/// concrete adapter (this is what the in-memory fake substitutes).
pub struct VersionReporter<M: BuildMetadata> { metadata: M }

// Assembly is infallible: each port method returns &str, copied into the owned
// String fields via .to_owned() (no fallible conversion -> no unwrap/expect,
// satisfying the lint wall).
impl<M: BuildMetadata> ReportVersion for VersionReporter<M> { /* assemble via to_owned() */ }
```

> Decision (review-1): the crate version is routed through `BuildMetadata` like
> the other three build facts (rather than read via `env!("CARGO_PKG_VERSION")`
> directly in the core), so the core has a single, uniform, fully-fakeable
> dependency on its build environment and the AC4 fake can vary the version
> independently. The real adapter remains the SSOT (`env!("CARGO_PKG_VERSION")`).

**`version/outbound/build_metadata.rs`** — the adapter implementing
`BuildMetadata` by reading the build-time env vars with **`option_env!`** (never
bare `env!`): `option_env!` resolves at compile time but yields `None` instead of
a *compile error* when a var is unset, so a build context where vergen could not
resolve git facts produces a degraded `"unknown"` SHA rather than failing to
compile. `crate_version` is the SSOT read (`env!("CARGO_PKG_VERSION")` is always
provided by Cargo, so a bare `env!` is correct there):

```rust
pub struct VergenBuildMetadata;
impl BuildMetadata for VergenBuildMetadata {
    fn crate_version(&self) -> &str { env!("CARGO_PKG_VERSION") }  // always set by Cargo
    fn commit_sha(&self) -> &str { option_env!("VERGEN_GIT_SHA").unwrap_or("unknown") }
    fn build_date(&self) -> &str { option_env!("VERGEN_BUILD_TIMESTAMP").unwrap_or("unknown") }
    fn target_triple(&self) -> &str { option_env!("VERGEN_CARGO_TARGET_TRIPLE").unwrap_or("unknown") }
}
```

> `.unwrap_or(...)` on an `Option` is a total, infallible method — it is **not**
> the banned `Option::unwrap()`, so it satisfies the lint wall.

**`version/inbound/cli.rs`** — the clap subcommand adapter: parses (no args),
drives the inbound port, and **formats** the `VersionReport` to stdout
(presentation is the adapter's job, keeping the core presentation-free). No
business logic. Keep the layout in a single pure rendering function
(`fn render(report: &VersionReport) -> String`) that the adapter prints, so the
rendering is independently unit-testable and the composition root only wires and
dispatches — presentation never leaks into `main.rs`.

**`main.rs`** — the **composition root**: builds `VergenBuildMetadata`, injects
it into `VersionReporter` (core constructed against the trait, never the
concrete adapter), parses the clap `Cli`, and on the `Version` subcommand hands
the constructed core to the inbound adapter. Returns `Result<(), kernel::Error>`
(or maps to an exit code) so the dispatch boundary speaks the kernel taxonomy.

#### 5. Tests (written first)

**AC4 — core against an in-memory fake** (inline `#[cfg(test)] mod tests` in
`version/core.rs`, matching the existing convention — `use super::…`, no glob,
snake_case sentence names, no `unwrap`):

```rust
struct FakeBuildMetadata;          // canned version/commit/date/triple
impl BuildMetadata for FakeBuildMetadata { /* fixed values, incl. crate_version */ }

#[test]
fn reports_the_injected_build_metadata() {
    let report = VersionReporter { metadata: FakeBuildMetadata }.report();
    // ALL four fields come from the fake — proving the port boundary uniformly.
    assert_eq!(report.version, "<fake version>");
    assert_eq!(report.commit_sha, "<fake sha>");
    // ... date, triple from the fake.
}
```

> Because the version is now an injected port value (not a direct `env!` read in
> the core), the fake supplies a canned version distinct from the real
> `CARGO_PKG_VERSION`, so this test proves the field genuinely flows through the
> port rather than tautologically matching the compile environment. The
> real-adapter SSOT (`env!("CARGO_PKG_VERSION")`) is exercised by the black-box
> binary test below.

**AC1 + AC5 — black-box test of the compiled binary**
(`cli/tests/version.rs`, new — integration tests can run the binary via
`env!("CARGO_BIN_EXE_luminosity")` and can read the crate's build-script env
vars via `env!`):

```rust
// Run `luminosity version`, capture stdout. The test reads the SAME build-baked
// values the binary was compiled with (cargo:rustc-env vars apply to the
// package's integration tests too), so every assertion is deterministic and
// about the built artefact — NOT about live git state or the wall clock.
//
// AC1 (version): stdout contains env!("CARGO_PKG_VERSION").
// AC5 (SHA injected): the printed SHA equals
//   option_env!("VERGEN_GIT_SHA").unwrap_or("unknown") — the *exact* expression
//   the adapter uses, so they agree by construction in every build context
//   (full/short/dirty/git-less). This proves the SHA plumbs through to stdout.
//   Do NOT compare against a fresh `git rev-parse HEAD`: vergen may emit a short
//   or `-dirty` SHA (the jj working copy is often dirty), HEAD can move between
//   build and test, and a git binary may be absent on the test host.
// AC5 (date injected): assert the printed date equals
//   option_env!("VERGEN_BUILD_TIMESTAMP").unwrap_or("unknown") (plumbing), and
//   when it is not the "unknown" sentinel, parse it with `time` as RFC 3339 and
//   assert it is not in the future. Deliberately NO "recent window" lower bound:
//   a cache-honouring incremental build legitimately carries an earlier (but
//   real) timestamp, so a window assertion would be flaky.
// Target triple: assert the printed triple equals
//   option_env!("VERGEN_CARGO_TARGET_TRIPLE").unwrap_or("unknown") (plumbing).
//   This is host-correct on every runner and does NOT assert "one of the four",
//   which fails on the gnu CI runner (see Key Discoveries). Membership in the
//   four shipped triples is a release-build shape property; see the build:cli
//   success criterion below for where that property is actually guarded.
//
// Symmetry-breaking guards (so the equality checks above are not tautologies).
// The baked-value equalities prove a value reaches stdout, but if a field were
// dropped or two fields swapped in the real adapter, both sides would still move
// together — and in a degraded git-less build the SHA/date/triple collapse to
// the literal "unknown" on both sides. To catch those, additionally assert:
//   - every printed field is NON-EMPTY, and the four are MUTUALLY DISTINCT
//     (version != sha != date != triple) — catches a swapped/dropped field;
//   - because the local + CI build always runs inside a git working tree (the
//     gitcl rationale), the SHA, date, and triple are NOT the "unknown"
//     sentinel here — so the equality checks are genuinely discriminating in the
//     environments this test runs in, not silently reduced to "unknown=="unknown".
// The authoritative proof that each field flows from the correct source is the
// AC4 core-against-fake test (canned, distinct values); this black-box test is a
// consistency + non-degradation guard on the real, non-fakeable adapter.
```

**File**: `cli/src/lib.rs`
**Changes**: remove `describe_release` and its tests; declare the `version`
module tree. `cli/src/main.rs`: replace the `describe_release` print with the
composition root + clap dispatch.

### Success Criteria

#### Automated Verification

- [x] Core-against-fake unit test passes (AC4):
      `cargo nextest run -p luminosity -E 'test(reports_the_injected_build_metadata)'`
- [x] Black-box binary test passes (AC1, AC5):
      `cargo nextest run -p luminosity -E 'test(version)'` (or the
      `cli/tests/version.rs` test name)
- [x] All cli unit tests + coverage pass: `mise run test:unit:cli`
      (100% region/line coverage on the version modules)
- [x] Lint wall satisfied (incl. build.rs and tests):
      `mise run cli:check`. NOTE deviations forced by the lint wall: the
      `BuildMetadata` port returns `&'static str` (build facts are baked-in
      literals — satisfies `clippy::unnecessary_literal_bound` naturally rather
      than per-method `#[expect]`s); module/item doc first-paragraphs were split
      (`clippy::too_long_first_doc_paragraph`); `dispatch` carries an `# Errors`
      doc section (`clippy::missing_errors_doc`). The planned
      `#[expect(unnecessary_wraps)]` was NOT needed — clippy does not flag the
      always-Ok dispatch seam — so it was omitted.
- [x] Supply chain clean with the new deps (clap, vergen backend, time):
      `mise run deny:check`. Two deny.toml/manifest changes were required (not
      licence exceptions): `[bans] allow-wildcard-paths = true` plus
      `publish = false` on both crates, so the `cli -> kernel` path dep is not
      flagged as a wildcard (the exemption does not apply to publishable
      crates). No licence exceptions were needed — vergen/gitcl/clap/time all
      fall under the pre-seeded allow-list.
- [x] New deps resolve MSRV-compatibly and `Cargo.lock` is committed: every
      resolved crate declares `rust-version` ≤ `1.90.0`. NOTE: vergen 10.x needs
      Rust 1.95, so the **9.x line** is used (`vergen 9.0.6` + `vergen-gitcl
      1.0.8`), exactly as the plan's Decision-4 / 9.x pin anticipated. `vergen`
      is pinned EXACTLY to `=9.0.6` (9.1.0 bumped its vergen-lib incompatibly
      with vergen-gitcl 1.0.8), and the transitive `cargo-platform` is pinned to
      `0.3.2` in the lock (0.3.3 needs Rust 1.91).
- [x] The build-dep tree compiles under cargo-pup's pinned nightly (not only the
      stable pin): `cargo +nightly-2026-01-22 pup print-modules` succeeds with
      `cli`'s new `build.rs` + `[build-dependencies]` present (no
      PUP_NIGHTLY/PUP_VERSION bump needed). It reports
      `luminosity::version::core` — the path Phase 3's rule binds to.
- [x] Release build still links/arches correctly with the build script:
      `mise run build:cli`. Note: the embedded target triple is one of ADR-0002's
      four shipped triples **by construction** here — `build:cli` only builds the
      host-native shipped triples (the two musl triples on Linux, the two darwin
      triples on macOS), so vergen's `VERGEN_CARGO_TARGET_TRIPLE` is necessarily a
      shipped triple in this lane. This is where AC1's "one of the four" property
      is guarded (structurally), as distinct from the black-box test above, which
      only asserts the *runtime* self-report is host-correct (it runs on the gnu
      dev/CI host, not a shipped triple). Executing each cross-built binary to
      assert its embedded triple is not feasible (cross-compiled musl/darwin
      artefacts are not all host-runnable), so the structural guarantee is the
      coverage — recorded here rather than left implicit.
- [x] Full local CI mirror green: `mise run`

#### Manual Verification

- [x] `cargo run -p luminosity -- version` prints version, commit SHA, build
      date, and target triple, all populated and plausible.
- [x] Re-running after a new commit changes the printed commit SHA (metadata is
      genuinely build-time, not cached/hard-coded) — verified after the Phase 2
      commit.
- [x] The core module has no `use` of the `outbound`/`inbound` adapter modules
      (read the source) — `core.rs` imports nothing infrastructural; confirmed
      mechanically in Phase 3.

---

## Phase 3: cargo-pup inward-direction enforcement, proven live

### Overview

Make cargo-pup the live, sole enforcer of the inward dependency rule for the
`version` hexagon, and **prove it has teeth** with an automated test — a
deliberate domain→adapter import is rejected, and its removal goes green
(AC3) — matching the existing probe-test philosophy.

### Changes Required

#### 1. Author the real inward-direction rule

First discover the real module paths:
`cargo +nightly-2026-01-22 pup print-modules` (run from repo root) reports the
fully-qualified paths to match on. Then author the rule against them.

**File**: `pup.ron`
**Changes**: replace `( lints: [] )` with a `Module`/`RestrictImports` rule
constraining what the `version` core may import. (Field/variant names per
cargo-pup v0.1.8; the matcher is `Module(...)`, not `Name(...)`.)

**Prefer a fail-closed `allowed_only` allow-list over a deny-list.** A deny-list
of two adapter paths (`version::inbound`/`version::outbound`) only catches those
two specific imports — it would silently permit the core importing *any*
infrastructure (`clap`, `vergen`, `std::fs`, a future adapter module under a new
namespace), and in the single-crate phase the cross-crate `deny.toml` ban-list
that would otherwise catch infrastructure crates is explicitly inert, so this pup
rule is the **whole** guard. An `allowed_only` list (the core may import only the
permitted namespaces — `std`/`core`/`alloc`, `kernel`, and the slice's own pure
value types) fails closed: any new infrastructure import the core acquires later
is rejected by default.

```ron
(
    lints: [
        Module((
            name: "version_core_imports_only_permitted",
            // Mirror the real path from `pup print-modules` (confirm before
            // committing — a path that matches nothing yields a green-but-inert
            // rule; see the load-bearing assertion in the tests below).
            matches: Module("^luminosity::version::core($|::)"),
            rules: [
                RestrictImports(
                    // Allow-list: everything the core legitimately needs, and
                    // nothing else. Exact patterns confirmed against
                    // `pup print-modules` output for the pinned cargo-pup.
                    allowed_only: Some([
                        "^(std|core|alloc)(::|$)",
                        "^kernel(::|$)",
                        "^luminosity::version::core(::|$)",   // intra-module
                    ]),
                    denied: None,
                    severity: Error,
                ),
            ],
        )),
    ],
)
```

> The real production code already complies (the core imports only its own value
> types + `kernel`), so adding this rule keeps `pup:check` green — the phase is
> mergeable. If `allowed_only` proves too coarse for the pinned cargo-pup v0.1.8
> (e.g. it cannot express a needed legitimate import), fall back to the
> deny-list form — but document that the deny-list must be *extended* as adapter
> modules are added, since it no longer fails closed.

#### 2. Prove the rule is live (automated)

**File**: `tests/integration/pup/test_pup_rules.py`
**Changes**: extend the existing suite (which CI runs via
`mise run test:integration:pup` in `check-architecture`):

- Keep `test_repo_pup_ron_actually_loads` — now meaningfully asserts the
  **non-empty** real `pup.ron` parses + loads (`pup print-modules` exits 0).
- **Add `test_real_inward_rule_binds_to_a_real_module` (closes the
  green-but-inert gap)** — the most important new assertion against the *real*
  workspace: run `cargo +<nightly> pup print-modules` and assert that the exact
  module path the real rule's `matches` regex targets (`luminosity::version::core`)
  **appears** in the output and **is matched** by that regex. A rule whose
  matcher binds to no real module parses fine, loads fine, and enforces
  *nothing* while showing green — exactly the silent-inert failure that would
  leave the sole inward-direction enforcer toothless. This test fails loudly if a
  rename or a regex typo decouples the rule from the real core. (The mirror test
  below proves the rule *shape* rejects a violation; this proves the real rule is
  actually *attached* to the real core — both are needed.)
- Add `test_inward_violation_is_rejected_and_removal_passes` — following the
  established `test_module_rule_violation_fails_the_check` probe pattern: build
  a throwaway crate in `tmp_path` that mirrors the hexagon layering (`core`
  module + an `outbound` adapter module) and carries a `pup.ron` with the
  **same `Module`/`RestrictImports` rule shape** as the repo's. Assert that a
  version where `core` has `use crate::outbound::…` makes
  `cargo +<nightly> pup` exit **non-zero**, and that the otherwise-identical
  version **without** that import exits **zero**. This proves the rule variant
  rejects exactly the inward violation, live — not merely that the config
  parses.

> Rejected alternative: copying the real `cli` crate to a temp dir and patching
> its core to inject the violation. More faithful but fragile (whole-workspace
> copy, path rewrites) and slow for a compiler-plugin run; the probe-mirror
> above plus `test_repo_pup_ron_actually_loads` (which exercises the *real*
> config against the *real* workspace) together give the same assurance in the
> repo's established style.

### Success Criteria

#### Automated Verification

- [ ] Real `pup.ron` loads and the inward rule is active:
      `mise run pup:check`
- [ ] The enforcer is proven live (violation rejected, removal passes) **and the
      real rule is proven attached to the real core** (the binding test):
      `mise run test:integration:pup`
- [ ] Full local CI mirror green: `mise run`

#### Manual Verification

- [ ] Temporarily add `use crate::version::outbound::build_metadata;` (unused)
      into `version/core.rs`, run `mise run pup:check`, observe it **fails**,
      then revert and observe it **passes** — the AC3 behaviour, confirmed by
      hand against the real tree once before relying on the automated test.

---

## Testing Strategy

### Unit Tests

- **kernel** (Phase 1): **none** — the error taxonomy ships as an uninhabited
  enum (a type-level seam), which has nothing to construct, so no `Display`/`Error`
  behaviour can be exercised yet. The first real variant brings the first
  (red-green) kernel test under later TDD pressure.
- **version core** (Phase 2): `VersionReporter` against an in-memory
  `BuildMetadata` fake — the port-boundary proof (AC4). All four fields
  (including the version) come from the fake, so the test proves each genuinely
  flows through the port rather than echoing the compile environment.
- **build-system** (Phases 1 & 3): exact command strings for the new kernel
  tasks; the mise wiring arrays and `kernel:check` exclusion; (Phase 3 adds no
  Python task, only test extensions).

### Integration Tests

- **Black-box `version`** (Phase 2): run the compiled binary; assert each printed
  field equals the **build-baked value the test reads from the same package**
  (`env!("CARGO_PKG_VERSION")` and `option_env!("VERGEN_*").unwrap_or("unknown")`),
  with the build date additionally parsed as RFC 3339 and asserted not-in-the-
  future. No comparison against live `git`/wall-clock, so the test is
  deterministic and about the built artefact (AC1, AC5).
- **cargo-pup behavioural** (Phase 3): the real `pup.ron` loads **and is proven
  attached to the real `version::core`** (binding test); a probe-mirror crate
  proves a domain→adapter import is rejected and its removal passes.

### Manual Testing Steps

1. `cargo run -p luminosity -- version` — eyeball the four fields.
2. Commit a no-op change, rebuild, re-run — confirm the SHA changes.
3. Inject a domain→adapter `use` into the core, run `mise run pup:check`,
   confirm failure, revert, confirm green.

## Performance Considerations

- Two `cargo llvm-cov nextest` passes (`-p luminosity`, `-p kernel`) under
  `test:unit` run in parallel (mise `test:unit` is a parallel roll-up), so the
  added kernel pass does not serialise behind the cli pass.
- The vergen build script adds negligible build time; with the `gitcl` backend
  it shells out to `git` once. vergen's `cargo:rerun-if` directives keep
  rebuilds correct without spuriously re-running.
- cargo-pup remains a separate pinned-nightly compile; no change to its cost.

## Migration Notes

None — greenfield code. `describe_release` and its tests are removed in Phase 2;
nothing else consumes them (`grep` confirms only `main.rs` and the inline tests
reference it).

## References

- Work item: `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md`
- Research: `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
  — hexagon, inward rule, cargo-pup-as-sole-enforcer.
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
  — binary axis, `kernel`/`cli` roles, `version` as built-in.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md`
  — four triples, version coherence.
- cargo-pup v0.1.8 module-rule syntax: DataDog/cargo-pup
  (`cargo_pup_lint_config/src/module_lint/types.rs`).
- Existing patterns to mirror: `cli/src/lib.rs:15-28` (inline test style),
  `tests/integration/pup/test_pup_rules.py` (probe-test pattern),
  `tasks/test/cli.py` (coverage-gated per-crate test task),
  `tasks/lint/cli.py` / `tasks/format/cli.py`,
  `tests/unit/tasks/test_mise_wiring.py` (pinned-array assertions).
