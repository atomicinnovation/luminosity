---
type: plan
id: "2026-06-27-0006-establish-rust-toolchain-guard-rails"
title: "Establish Rust Toolchain Guard Rails in mise + CI Implementation Plan"
date: "2026-06-27T14:01:19+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0006"
parent: "work-item:0006"
derived_from: ["codebase-research:2026-06-27-0006-rust-toolchain-guard-rails"]
relates_to: ["work-item:0007"]
tags: [rust, tooling, ci, guard-rails, mise, architecture-enforcement]
revision: "9be825bb5841954434a0740d2e55e705dc60c75a"
repository: "luminosity"
last_updated: "2026-06-28T10:45:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Establish Rust Toolchain Guard Rails in mise + CI Implementation Plan

## Overview

Stand up the Rust quality toolchain — rustfmt, clippy, cargo-nextest,
cargo-llvm-cov, cargo-deny, and cargo-pup — wired into the existing
component-based `mise run` task tree and enforced in CI, so the first Rust code
is held to the same automated bar as the Python (`build-system`) and shell
(`scripts`) components.

Because there is no Rust code in the repo yet, this story also lands a **minimal
bootstrap workspace** (a root `Cargo.toml` plus a single trivial `cli` crate)
that gives every tool something real to run against. The bootstrap is
deliberately throwaway scaffolding: the scaffold story (0007) replaces the
placeholder `cli` body with the real hexagonal `version` subcommand and adds the
`kernel` crate. Owning the bootstrap here makes 0006 independently mergeable and
fully self-verifying.

## Current State Analysis

- **No Rust code exists.** No `Cargo.toml`, `Cargo.lock`, `.rs` file, or crate
  directory anywhere (`meta/research/codebase/2026-06-27-0006-...md` summary
  point 1). 0006 is genuinely pre-scaffold.
- **The toolchain is partly provisioned.** `mise.toml:8` already pins
  `rust = { version = "1.90.0", components = "rustfmt,clippy" }`, so rustfmt and
  clippy are installed in every CI job. **cargo-nextest, cargo-llvm-cov,
  cargo-deny, and a cargo-pup nightly are not pinned** and must be added.
- **The task pattern is precise and two-layer (ADR-0006).** Each task is a thin
  declaration in `mise.toml` (`run = "invoke <module>.<task>"` or a `depends`-only
  roll-up) plus a Python invoke body under `tasks/` that runs the command with
  `warn=True` and `raise Exit(<message naming the fix task>, code=1)` on failure
  (`tasks/format/build_system.py:6-15`, `tasks/lint/scripts.py:17-44`,
  `tasks/types/build_system.py:6-14`). Inline shell in `mise.toml` is an
  explicitly rejected option.
- **Naming convention** (`tasks/README.md:23-28`): a component **leads** in its
  roll-up (`build-system:check`) and **trails** in families
  (`format:build-system:check`). `<component>:check` roll-ups exist; there is
  **no `<component>:fix`**. A multi-linter component nests a level deeper
  (`lint:scripts:shellcheck:check`).
- **Aggregation** (`mise.toml:118-140`): `check` = `["build-system:check",
  "scripts:check"]` (the read-only set CI mirrors); `fix` = `["format:fix",
  "lint:fix"]`; `default` = `["format:fix", "lint:check", "types:check",
  "test"]` (the heavy local CI mirror). Family aggregates (`format:check`,
  `format:fix`, `lint:check`, `lint:fix`, `types:check`, `test`) fan across
  components. `lint:fix` is Python-only (shell has no autofixer).
- **CI** (`.github/workflows/main.yml`) does not call aggregate `check`; it fans
  into discrete jobs, each provisioning tools via `jdx/mise-action@v4.1.0`
  (`install: true`, `cache: true`, `experimental: true`) then running one
  `mise run` target (`check-scripts` :59-75, `check-build-system` :77-93).
  Release jobs are `if: github.event_name == 'push'` and are the only place Rust
  is used today (cross-compile). No Rust check job, no cargo caching exist.
  PR mergeability is gated by GitHub branch-protection *required checks* set in
  repo settings, not in YAML — new job names must be added there manually.
- **`tasks/__init__.py:17-52`** assembles the invoke `Collection` namespace; new
  Rust task modules register here.
- **Release scaffolding already assumes `cli/`.** `tasks/shared/paths.py:4-7`
  hard-codes `CLI_DIR = REPO_ROOT / "cli"` and `CARGO_TOML = CLI_DIR /
  "Cargo.toml"`; `tasks/version.py` renders `Cargo.toml` and enforces version
  coherence across `plugin.json` / `Cargo.toml` / `checksums.json`. The bootstrap
  must keep `cli/Cargo.toml` as the crate that carries the product version so this
  machinery keeps working.

### Key Discoveries

- **clippy lint levels belong in `[workspace.lints.clippy]` in the root
  `Cargo.toml`** (members opt in via `[lints] workspace = true`), with
  `[workspace.lints.rust] warnings = "deny"` as the in-manifest `-D warnings`.
  Group lints take `priority = -1` so per-lint overrides win. `clippy.toml` sets
  lint *configuration* (thresholds, `disallowed-types`) — **not** levels. The
  work item's framing of `clippy.toml` as where lints are enabled is corrected
  here.
- **cargo-nextest `0.9.138`, cargo-llvm-cov `0.8.7`, cargo-deny `0.19.8`** all
  install via mise's default registry (aqua-backed prebuilt binaries) — clean
  `[tools]` short-name pins.
- **cargo-llvm-cov needs the `llvm-tools-preview` rustup component** and composes
  with nextest as `cargo llvm-cov nextest`. It runs on stable.
- **cargo-deny's current schema has no top-level `version` field**; target/feature
  config lives under `[graph]`; sections are `[advisories]` / `[licenses]` /
  `[bans]` / `[sources]`.
- **cargo-pup mechanism is confirmed (web research, 2026-06-27).**
  `DataDog/cargo-pup` latest is **`0.1.8`** (2026-06-09; pre-1.0 but actively
  maintained), a nightly rustc-driver linking `rustc_private`. Its
  `rust-toolchain.toml` at the `v0.1.8` tag pins **`nightly-2026-01-22`**
  (confirmed against the live repo, not a guess) with components `rustc-dev`,
  `rust-src`, `llvm-tools-preview`; the **same** nightly both builds and runs it.
  Crate name `cargo_pup` (underscore); it installs two binaries (`cargo-pup`,
  `pup-driver`) and is **source-only** (no prebuilt binaries). Configured by
  `pup.ron` (RON), scaffolded by `cargo pup generate-config`; invoked `cargo pup`
  (other subcommands: `generate-config`, `print-modules`, `print-traits`); build
  output is isolated in a `.pup/` directory (gitignore it).
- **mise drives rustup under the hood — this resolves the nightly mechanism.**
  mise's rust backend installs rustup (if absent) and sets `RUSTUP_TOOLCHAIN`;
  toolchains live under rustup, not under mise. mise **cannot** cleanly pin two
  rust toolchains at once — **there is no `rust-nightly` short-name**, so the
  draft's `"rust-nightly" = ...` `[tools]` line is invalid and is removed.
  However, rustup's `+toolchain` shorthand **outranks** `RUSTUP_TOOLCHAIN`, so
  `cargo +nightly-2026-01-22 pup` reliably overrides mise's stable pin for that
  single invocation. The supported pattern (and what Phase 4 adopts): keep stable
  pinned in mise; install the nightly via `rustup toolchain install` in a
  provisioning task; invoke the tool with `+nightly-2026-01-22`. Requires
  `~/.cargo/bin` (rustup's proxies) on PATH; there is no mise-vs-rustup shim
  conflict for rust because mise delegates to rustup.

## Desired End State

`mise run check` (the fast, read-only CI mirror) runs the per-crate `cli:check`
(rustfmt + clippy `-D warnings` only — **no tests**), the workspace-scope
`deny:check`, and the blocking nightly `pup:check`, and exits 0. Tests do not run
in `check`: the cli unit tests are wired into the `test` roll-up (via the
per-suite `test:unit` aggregate, exactly as the existing Python/shell suites are),
which the bare `mise run` default runs. **Coverage is part of the test run, not a
separate task**: `test:unit:cli` runs `cargo llvm-cov nextest` by default, so it
both executes the cli unit tests and reports their coverage in one pass, on **both
linux and macOS**. A `LUMINOSITY_COVERAGE=off` env toggle (mirroring the
`LUMINOSITY_PUP_MODE` precedent) drops it back to a plain `cargo nextest run` for a
faster inner loop; CI leaves coverage on. So the heavier `mise run` (bare default)
is the full gate — it runs format, lint, type checks, the whole `test` roll-up
(including the cli unit tests *with* coverage), the `build:cli` host-native release
build, and the deny/pup static checks — and exits 0 end-to-end. (`check` stays
read-only, fast, test-free, and build-free, mirroring the established
`build-system:check` / `scripts:check` roll-ups; tests-with-coverage live in the
`test` roll-up and the release build in `default`.) A Rust change that fails format,
clippy, cargo-deny, or cargo-pup fails CI and is non-mergeable; a change that breaks
the cli unit tests fails the `test-unit` CI job (on both OSes), and one that breaks
the release build fails the `build-cli` matrix job — both likewise non-mergeable. The stable toolchain and the registry-backed tools
(cargo-nextest, cargo-llvm-cov, cargo-deny) are pinned in `mise.toml`; the
cargo-pup nightly is pinned via `rustup toolchain install` in `deps:install:pup`
and cargo-pup itself is pinned to `0.1.8 --locked`. `rustfmt.toml`, `clippy.toml`,
`deny.toml`, and `pup.ron` exist. Each invoke task module ships with unit tests
asserting the exact command string it builds, and the security/architecture
config (the native-tls ban) plus the CI job wiring are guarded by automated
regression tests, not manual checks alone.

Verification: `mise run check` → 0; `mise run` → 0; a deliberately-broken Rust
change makes the relevant CI job red.

## What We're NOT Doing

- **Not building the real hexagonal architecture or the `version` subcommand** —
  that is 0007. The bootstrap `cli` crate is a placeholder with a trivial test.
- **Not adding the `kernel` / `config` / `config-adapters` / per-subdomain
  crates** — they arrive with 0007 (kernel) and 0009 (config). The task wiring is
  built so adding a `kernel:check` later is a small, mechanical addition.
- **Not authoring real cargo-pup `restrict_imports` layering rules** — there are
  no hexagonal modules to constrain yet; `pup.ron` starts minimal and the real
  rules land in 0007.
- **Not adding the CI grep tripwire** — ADR-0009 deliberately omits it, treating
  cargo-pup as sufficient. Do not re-add without revisiting ADR-0009.
- **Not enforcing a coverage threshold** — the acceptance criterion only requires
  coverage to *run*; `cargo llvm-cov` is report-only (no `--fail-under`).
- **Not enforcing the cross-crate architectural ban-lists in anger** — they are
  scaffolded in `deny.toml` but largely inert until the workspace splits
  (first bites at the `config` / `config-adapters` split, story 0009; later
  crates tracked in work item 0012). The workspace-wide native-tls/OpenSSL ban
  *is* live from day one.
- **Not configuring GitHub branch-protection required checks** in code — that is
  a manual repo-settings step (now captured as a durable runbook, not just a
  checkbox — see Phase 5).
- **Not packaging or publishing release artifacts on every PR** — version bump,
  checksums, attestation, and upload stay in the push-only release jobs. The
  PR-time `build:cli` task *compiles and links* all four shipped triples (to
  exercise the static-link invariant pre-merge — the native-tls ban alone does not
  guarantee static linking) but produces no shippable output. It does so across a
  CI matrix, each runner building its **host-native** pair (the two musl triples on
  Linux, the two darwin triples on macOS), so cross-linking pain is avoided and all
  four triples are nonetheless covered before merge.
- (SHA-pinning is now **in scope** — see Phase 1 §7. This supply-chain story
  SHA-pins both the action it introduces (`Swatinem/rust-cache`) and the
  pre-existing tag-pinned actions in the high-privilege release jobs
  (`actions/checkout`, `jdx/mise-action`, `actions/attest-build-provenance`),
  and adds a workspace-wide least-privilege token default.)

## Implementation Approach

Five independently-mergeable phases. Each phase that adds an invoke task ships
its TDD command-string unit test and its CI job in the same change, and leaves
`mise run check` and `mise run` green. Phase 1 lands the bootstrap workspace
alongside the first two (already-provisioned) tools so the very first merge
delivers format+lint-enforced Rust code rather than an unchecked workspace.

**Wiring model** (settled, applied incrementally across phases):

- Per-crate component roll-up **`cli:check`** folds `format:cli:check` +
  `lint:cli:check` **only** — it carries **no tests**, mirroring the established
  `build-system:check` / `scripts:check` roll-ups (neither of which runs tests).
  This keeps `check` read-only, fast, and test-free.
- The cli unit tests are a separate leaf **`test:unit:cli`** that feeds the
  existing per-suite **`test:unit`** aggregate (alongside `test:unit:tasks`), which
  feeds the top-level **`test`** roll-up — exactly the path the Python suite
  already takes (`test:unit:tasks` → `test:unit` → `test`, `mise.toml:27-47`). The
  cli unit tests run via `mise run test`/`mise run test:unit`, never via `check`.
- **Coverage is folded into `test:unit:cli`, not a separate task.** By default
  `test:unit:cli` runs `cargo llvm-cov nextest` (a single instrumented pass that
  both runs the tests and reports coverage), so coverage runs **wherever and
  whenever the tests run** — on both linux and macOS, always. A
  `LUMINOSITY_COVERAGE=off` env toggle (read in `tasks/shared/rust.py`, mirroring
  the `LUMINOSITY_PUP_MODE` precedent) switches the leaf to a plain
  `cargo nextest run -p <crate>` for a faster non-instrumented inner loop; CI
  leaves it on. There is **no** standalone `coverage:cli:check` leaf and **no**
  `coverage:check` family aggregate — coverage has no edges of its own.
- Workspace-scope tasks **`deny:check`** and **`pup:check`** are their own
  top-level roll-ups (no `-p`, no per-crate notion) — analogous to the standalone
  `lint:workflows:check`. These are static analysis (supply-chain and architecture
  *linting*), **not** tests, so they belong in `check`. `pup:check` **`depends` on
  `deps:install:pup`** — mirroring how every Python check `depends` on
  `deps:install:python`: a check provisions what it needs. The nightly + cargo-pup
  are not mise `[tools]`, so `deps:install:pup` is their install task, and a check
  that needs them must declare that dependency. `deps:install:pup` is idempotent
  (`rustup toolchain install` and `cargo install … --locked` both no-op when the
  pinned versions are already present), so the steady-state cost is small — the same
  shape as `uv sync --frozen` running ahead of every Python check. (`deny:check`
  needs no such edge: cargo-deny is a mise `[tool]` and `Cargo.lock` is committed.)
- The release-build guard **`build:cli`** is folded into the bare `mise run`
  default (the heavy full-CI-mirror) but **not** into the read-only `check` — a
  release build is heavier than the read-only checks and would slow the fast
  `check` loop. Because the task is OS-aware, a local `mise run` release-builds the
  host's native triple pair (mirroring that OS's CI leg); the full four-triple
  coverage still only exists across the CI matrix (Phase 1 §7). It is **not** in any
  family aggregate and **not** in `cli:check`.
- Family aggregates gain Rust: `format:check`/`format:fix` ← `format:cli:*`;
  `lint:check`/`lint:fix` ← `lint:cli:*`; `test:unit` ← `test:unit:cli` (and so
  `test` transitively, carrying coverage with it). No `coverage` family is added.

The final top-level aggregate `depends` arrays (enumerated so an implementer can
diff against them; new edges in **bold**):

- **`check`**: `["build-system:check", "scripts:check", `**`"cli:check",
  "deny:check", "pup:check"`**`]`
- **`default`**: `["format:fix", "lint:check", "types:check", "test", `**`"build:cli",
  "deny:check", "pup:check"`**`]` (no `coverage:check` edge — coverage rides inside
  `test`)
- `cli:check`: `["format:cli:check", "lint:cli:check"]` (no tests)
- `test:unit`: `["test:unit:tasks", `**`"test:unit:cli"`**`]` (so `test` →
  `test:unit` → `test:unit:cli`, which carries coverage by default)

**AC reconciliation note.** Work item 0006's first acceptance criterion lists
"format-check, clippy, tests, coverage" as belonging to `mise run check`. The
repo's established model, however, separates `check` (read-only, fast — runs *no*
tests; it is `[build-system:check, scripts:check]` today) from the bare `mise run`
default (heavy, runs the whole `test` roll-up). This plan **honours that
convention**: `check` stays test-free (format + lint + types, plus the deny/pup
static checks), and the cli unit tests — **with coverage folded in** — live in the
`test` roll-up (`test` → `test:unit` → `test:unit:cli`), which the bare `mise run`
default runs. The full gate the AC intends — format, clippy, tests, coverage,
deny, pup — is therefore satisfied by the bare `mise run` (the third AC), not by
`mise run check`. Update 0006's first AC to read "tests (with coverage) run in
`mise run`" rather than "in `mise run check`", aligning the AC with the repo's
check/test separation.

**Shared constants.** To avoid duplicating magic literals across `mise.toml`,
task bodies, and CI, a small **`tasks/shared/rust.py`** defines the cli crate
name (`CLI_CRATE = "luminosity"`), the pinned nightly
(`PUP_NIGHTLY = "nightly-2026-01-22"`), and the cargo-pup version
(`PUP_VERSION = "0.1.8"`). The two environment toggles are **call-time
functions, not module constants** — `coverage_enabled()` (reads
`LUMINOSITY_COVERAGE`, default on) and `pup_mode()` (reads `LUMINOSITY_PUP_MODE`,
default `"deny"`). They must be evaluated *inside* the task body at run time, not
captured at import: a module-level `os.environ.get(...)` constant is frozen at
first import (long before any task runs) and copied into each consumer by
`from … import`, so an env var set at invocation has no effect and tests cannot
drive both branches with `monkeypatch.setenv`. The call-time-function form matches
the existing env idiom in `tasks/release.py` (`_refuse_under_ci` reads the env when
called). Task bodies compose command strings from the constants, and the
command-string unit tests assert against the same constants — one source of
truth. The `-p <crate>` argument must equal the crate's `[package] name` (not the
`[[bin]]` name); the tests pin this so a later rename (0007) fails loudly.

On-disk layout: a **flat workspace root** — `cli/Cargo.toml` sits beside the root
workspace `Cargo.toml`, consistent with `tasks/shared/paths.py`. Future crates
(`kernel/`, etc.) are sibling top-level directories. The root `Cargo.toml` is
intentionally a `[package]`-free, *versionless* workspace manifest; the product
version stays in `cli/Cargo.toml` (Migration Notes).

---

## Phase 1: Bootstrap workspace + rustfmt + clippy

### Overview

Land the minimal buildable workspace and wire the two already-provisioned tools
(rustfmt, clippy) into the task tree with a `cli:check` roll-up and a CI job.
After this phase the repo has format- and lint-enforced Rust code.

### Changes Required

#### 1. Root workspace manifest

**File**: `Cargo.toml` (new, repo root)
**Changes**: Workspace declaration, the resolver, shared lint levels, and the
80-column-aware Rust edition. Restriction-lint starter set chosen per the
planning decision.

```toml
[workspace]
resolver = "2"
members = ["cli"]

[workspace.lints.rust]
warnings = "deny"

[workspace.lints.clippy]
pedantic = { level = "warn", priority = -1 }
nursery  = { level = "warn", priority = -1 }
# restriction is allow-by-default; these are the cherry-picked opt-ins
unwrap_used    = "warn"
expect_used    = "warn"
panic          = "warn"
dbg_macro      = "warn"
todo           = "warn"
unimplemented  = "warn"
module_name_repetitions = "allow"
must_use_candidate      = "allow"
```

(Comments are trimmed to the genuinely non-obvious "why" per the
comments-as-last-resort rule: the standard clippy `priority = -1` /
group-vs-override mechanics are not commented, only the restriction opt-in is.
`nursery` is accepted as a deliberately churny set — a future rust bump can
surface new nursery findings; if that proves disruptive, demote `nursery` to a
non-`-D` warning to decouple toolchain bumps from merge-blocking.)

#### 2. Bootstrap `cli` crate

**File**: `cli/Cargo.toml` (new) — carries the product version (keeps
`tasks/shared/paths.py` and `tasks/version.py` coherence working).

```toml
[package]
name = "luminosity"
version = "0.1.0-pre.0"  # seed = current plugin.json version; subsequent bumps
                         # owned by tasks/version.py (keep the 3 sources coherent)
edition = "2021"

[lints]
workspace = true

[[bin]]
name = "luminosity"
path = "src/main.rs"
```

**File**: `cli/src/lib.rs` (new) — a trivial pure function with a test, so
nextest and llvm-cov have something to exercise (no `unwrap`/`panic`, to satisfy
the restriction lints). Give it **at least one branch** (e.g. a small `match`/`if`
with both arms covered by tests) rather than a straight-line function, so the
instrumented `cargo llvm-cov nextest` run demonstrably reports more than a single
line — cheap insurance that coverage is actually measuring branches before 0007's
real code relies on it.

**File**: `cli/src/main.rs` (new) — trivial binary entry calling into the lib;
placeholder that 0007 replaces.

> Test-first: write the failing `cli/src/lib.rs` unit test before its
> implementation (red → green), per the TDD mandate.

#### 3. rustfmt + clippy config

**File**: `rustfmt.toml` (new) — `max_width = 80` (hand-duplicated from
`.editorconfig`, which rustfmt does not read) plus `edition = "2021"`.

**File**: `clippy.toml` (new) — configuration only (e.g. `msrv = "1.90"`); lint
*levels* live in the workspace manifest, not here. Carry a one-line comment
`# lint levels live in [workspace.lints] in Cargo.toml; this file is config only`
— the work item itself made the levels-belong-here mistake (see Key Discoveries),
so the next contributor is the likely repeat-offender. Note that `msrv` is a
**fourth** hand-synced mirror of the `mise.toml` rust pin (alongside the three
80-col copies); keep it in lockstep on any rust bump.

#### 4. Invoke task bodies

**File**: `tasks/shared/paths.py` — add `WORKSPACE_MANIFEST = REPO_ROOT /
"Cargo.toml"` (the existing `CLI_DIR` / `CARGO_TOML` stay).

**File**: `tasks/format/cli.py` (new) — mirror `tasks/format/build_system.py`:

```python
from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT


@task
def check(context: Context) -> None:
    """Check Rust formatting with rustfmt (read-only; fails on drift)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo fmt --all --check", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit(
            "rustfmt: drift — run `mise run format:cli:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format Rust in place with rustfmt."""
    with context.cd(str(REPO_ROOT)):
        context.run("cargo fmt --all", warn=True, pty=False)
```

**File**: `tasks/lint/cli.py` (new) — clippy check + fix:

```python
@task
def check(context: Context) -> None:
    """Lint Rust with clippy (pedantic + nursery + restriction, -D warnings)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo clippy --workspace --all-targets --all-features "
            "-- -D warnings",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("clippy reported findings — run `mise run lint:cli:fix`", code=1)


@task
def fix(context: Context) -> None:
    """Apply clippy's machine-applicable suggestions."""
    with context.cd(str(REPO_ROOT)):
        context.run(
            "cargo clippy --workspace --all-targets --all-features "
            "--fix --allow-dirty --allow-staged",
            warn=True,
            pty=False,
        )
```

**File**: `tasks/__init__.py` — register `format_.cli` under `ns_format` and
`lint.cli` under `ns_lint`.

> Note on the `fix` bodies: like the existing `build_system`/`scripts` fix tasks,
> they discard the exit code. For clippy `--fix` specifically a non-zero exit
> means the autofix step *itself* failed (e.g. an uncompilable tree blocked it) —
> a more likely outcome than for a pure formatter. The `fix` body should therefore
> **capture the result and `print("WARNING: …")`** when clippy `--fix` exits
> non-zero (rather than silently reporting success), so `mise run fix` does not
> appear clean while having applied nothing; the subsequent `lint:cli:check` still
> provides the hard gate. Concretely: `result = context.run(…)` then
> `if result.exited != 0: print("WARNING: clippy --fix could not apply …")` —
> using `print` (not logging), consistent with the codebase, asserted via `capsys`.

#### 5. mise task declarations

**File**: `mise.toml` — add:

```toml
[tasks."format:cli:check"]
description = "Check Rust formatting with rustfmt (read-only; fails on drift)"
run = "invoke format.cli.check"

[tasks."format:cli:fix"]
description = "Format Rust in place with rustfmt"
run = "invoke format.cli.fix"

[tasks."lint:cli:check"]
description = "Lint Rust with clippy (pedantic + nursery + restriction, -D warnings)"
run = "invoke lint.cli.check"

[tasks."lint:cli:fix"]
description = "Apply clippy's machine-applicable fixes"
run = "invoke lint.cli.fix"

[tasks."cli:check"]
description = "Run all cli-crate format and lint checks (read-only; no tests)"
depends = ["format:cli:check", "lint:cli:check"]
```

`cli:check` is format + lint only — no tests — mirroring `build-system:check`
and `scripts:check`. The cli unit tests are wired into the `test` roll-up in
Phase 2, not here.

Extend the family aggregates (`mise.toml:57-63, 118-124`): add `format:cli:check`
to `format:check`, `format:cli:fix` to `format:fix`, `lint:cli:check` to
`lint:check`, `lint:cli:fix` to `lint:fix`. Add `cli:check` to the top-level
`check` (`mise.toml:134-136`).

#### 6. Release build (PR-time static-link / cross-target guard)

**File**: `tasks/build.py` (new) — a `cli` task (so the mise name `build:cli`
maps to the invoke path `build.cli`, mirroring the `version.py` →
`version:read`/`version:write` precedent — `build` is a module, `cli` a task, no
sub-package needed). The task is **OS-aware**: it builds the release triples that
match the *host* OS — the two `*-apple-darwin` triples on macOS, the two
`*-unknown-linux-musl` triples on Linux. The host→triples mapping lives in a
**pure `host_targets(system: str) -> tuple[str, ...]` helper in
`tasks/shared/targets.py`** that **partitions the single existing `TARGETS` tuple**
(filter by the triple's OS substring) rather than re-listing triples — so the
build set provably shares one definition with the install set (`deps.py` consumes
the same `TARGETS`) and the shipped set; a future triple added to `TARGETS` is
automatically built/link-checked rather than silently shipped-but-unbuilt. It is a
pure helper (not inline in the effectful body), so the selection logic is
unit-tested directly without monkeypatching `platform` on the task module, and the
body stays a thin loop. **The helper must `Exit` with an actionable message
on any unsupported `platform.system()`** (e.g. `"build:cli: unsupported host OS
'<name>'; supported: Darwin, Linux"`) — an empty/silent result would make
`build:cli` run *zero* `cargo build`s and exit 0, a false-green on the authoritative
static-link guard (and `build:cli` is in `default`, so it runs on every developer
host). Each triple is built with **`cargo build --release --bin {CLI_CRATE}
--target {triple}`** (`--bin`, not just `-p`, so the *binary* is always linked —
the link step is the whole point of the per-triple build; a lib-only `-p` build
would pass without exercising linking), `warn=True`, and
`Exit(f"release build failed: {triple}", code=1)` on non-zero. The name is
deliberately verb-less: it **is** a build (it compiles and links binaries into
`target/`), not a read-only check, so it does not borrow the `:check` suffix.

> **⚠ Diverges from ADR-0002 (`cargo-zigbuild` from one host) — conscious
> decision, ADR amendment required.** ADR-0002 §"How it works" commits the release
> to `cargo-zigbuild`, cross-compiling all four triples *from one host*. This plan
> instead validates via **per-OS-native** `cargo build` across a matrix (the macOS
> leg builds the darwin triples on a real macОС runner), because building/validating
> the macOS variants on Apple hardware is preferred over zigbuild's
> SDK-on-Linux cross-compile. Consequences: (1) `build:cli` is a *host-native*
> guard, so for it to actually protect what ships, **0008's release build must adopt
> the same per-OS-native matrix model rather than zigbuild-from-one-host** — recorded
> in Migration Notes; (2) **ADR-0002's cross-compilation mechanism must be amended/
> superseded** to ratify the host-native model (a follow-up ADR, raised before 0008
> implements the release build). Until that ADR lands, this is a recorded divergence,
> not silent drift.

> **Linker prerequisite (the bootstrap is green only because the crate is empty).**
> `rustup target add <triple>` installs only std, not a cross-linker. The pure-Rust
> bootstrap links via Rust's self-contained linking (rust-lld + bundled startup) on
> both legs, so no external linker is needed *yet* — but **0007 immediately lands a
> C-FFI stack (ADR-0010's reqwest/rustls/tokio)** that needs musl cross-linkers on
> the Linux leg (and the macOS SDK's x86_64 slice for the cross-arch darwin build).
> The Linux leg is x86_64 `ubuntu-latest` but builds **both** musl triples, so it
> needs **two** linkers: `musl-tools` provides the x86_64 musl-gcc, and the
> *cross-architecture* `aarch64-unknown-linux-musl` build additionally needs an
> aarch64 cross-linker (`gcc-aarch64-linux-gnu`) wired via
> `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER` — `musl-tools` alone does **not**
> cover the arm64 target. To avoid the matrix going red the moment 0007 merges with
> no provisioning staged: add **both** the `musl-tools` and `gcc-aarch64-linux-gnu`
> installs (plus the `CARGO_TARGET_*_LINKER` env) to the `build-cli` Linux leg
> **now, as a commented, ready-to-enable step**, and call out in the plan that 0007
> must enable it. Consider pinning the TLS backend (rustls-with-ring vs aws-lc-rs)
> now, since it
> is a static-linking decision.

> **Per-triple output assertions (verify the invariants directly, don't infer
> them).** Build a small pure verdict helper (parse `file`/`lipo`/`ldd` output →
> bool) so the logic is unit-testable on both pass and fail strings, and have the
> task `Exit` on a bad verdict:
> - **musl legs**: assert the binary is actually *static* — `file
>   target/<musl-triple>/release/luminosity` reports "statically linked" (or `ldd`
>   reports "not a dynamic executable"). The native-tls ban is
>   necessary-but-not-sufficient (other system-C `*-sys` crates link dynamically
>   too), so this turns the static-link guarantee into a checked fact.
> - **darwin legs**: assert the produced Mach-O is the *expected arch* — e.g.
>   `lipo -archs …` / `file …` reports `x86_64` for the `x86_64-apple-darwin`
>   binary and `arm64` for `aarch64-apple-darwin`. This makes the cross-arch slice
>   (x86_64 built on the arm64 `macos-latest` runner) a CI-failing assertion rather
>   than a manual checkbox, so a runner-SDK regression that silently drops the
>   x86_64 slice reddens CI instead of shipping an uncovered triple.

**In `default`, not in `check`**: `build:cli` is folded into the bare `mise run`
default (the heavy full-CI-mirror — "done" means it exits 0), so a local `mise run`
release-builds the host's native triples and a build break is caught locally, not
only in CI. It is **not** folded into `cli:check` or `check` — a release build is
heavier than the read-only checks and would slow the fast `check` loop. Because the
task now builds only host-native targets, this is a *cheap* native release build on
either OS (no cross-linking), so putting it in `default` is no longer the
macOS-hostile cost it once would have been. (The full four-triple coverage still
lives only in CI's `build-cli` matrix, §7 — one local machine is one OS.)

**File**: `mise.toml` — add a **`build:cli`** leaf (2 segments → invoke path
`build.cli`), `run = "invoke build.cli"`, `depends = ["deps:install:rust-targets"]`
(which already installs all four targets — reused rather than a narrower per-OS
install; installing a target you do not build on a given runner is harmless).
Register `build` in `tasks/__init__.py`. **Add `build:cli` to the top-level
`default` `depends`** (`mise.toml:138-140`) — *not* to `check`. Note this makes
`default` provision the cross-targets (via `build:cli`'s `deps:install:rust-targets`
dependency); `rustup target add` is idempotent, so the cost is one-time.

#### 7. CI jobs

**File**: `.github/workflows/main.yml` — add **two** jobs, keeping the read-only
checks separate from the heavier matrixed build:

- **`check-cli`** (ubuntu-latest), mirroring `check-build-system` (:77-93):
  - Declare least-privilege `permissions: { contents: read }` (the existing check
    jobs inherit the default token; the new PR-triggered Rust jobs that build/run
    fetched code should be read-only).
  - Run `mise run cli:check` (format + lint only — no tests, no build).
  - Add cargo build caching pinned by **commit SHA**, not tag:
    `uses: Swatinem/rust-cache@<full-40-char-sha> # v2.x.y` (resolve the SHA at
    implementation). Tag pins (`@v2`) are re-pointable and a live CI
    code-execution vector.
- **`build-cli`** — the release-build guard, run as a **matrix** over
  `[ubuntu-latest, macos-latest]` so each runner builds its host-native pair and
  all four shipped triples are covered:
  - `permissions: { contents: read }`; `Swatinem/rust-cache@<full-40-char-sha>`
    keyed per-OS.
  - Run `mise run build:cli` (the OS-aware task builds the host's two triples).
  - Stage the linker prerequisite from §6 **now as a commented, ready-to-enable
    step** on the Linux leg (`apt-get install musl-tools gcc-aarch64-linux-gnu` +
    `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER=aarch64-linux-gnu-gcc`) — **both**
    the x86_64 musl-gcc *and* the aarch64 cross-linker, since the x86_64 runner
    builds the arm64 musl triple too — with a comment that 0007 must enable it when
    the C-FFI stack lands, so the matrix does not silently go red on the 0007 merge.
    The macOS leg links the darwin triples natively (the arm64-runner x86_64 slice
    is checked by the automated arch assertion in §6).
- Add **both** `check-cli` and `build-cli` to the `prerelease`/`release` `needs:`
  lists. (A matrix job is a single `needs:` entry but surfaces as one required
  check **per matrix leg** — `build-cli (ubuntu-latest)` and
  `build-cli (macos-latest)` — which matters for branch protection, see Phase 5.)

**Workflow-wide hardening (folded into this phase, supply-chain story scope):**

- Add a top-level workflow default `permissions: { contents: read }` so every job
  is read-only by default; the `prerelease`/`release` jobs keep their existing
  explicit elevated block (`id-token`/`contents`/`attestations: write`). This
  also closes the existing PR-triggered jobs (`test-unit`, `test-integration`,
  `check-scripts`, `check-build-system`) inheriting the repo default token while
  building/running fetched code.
- **SHA-pin every third-party action**, not just the new one: convert the
  pre-existing `actions/checkout@v5`, `jdx/mise-action@v4.1.0`, and
  `actions/attest-build-provenance@v2` to full-40-char-SHA pins (with the version
  in a trailing comment). These run in the release jobs that sign/attest the
  shipped binaries, where a re-pointed tag is the worst-case vector; for a
  supply-chain guard-rail story, pinning them here rather than deferring is the
  point. (`actionlint` / `lint:workflows:check` must stay green after the edit.)
  Note the tradeoff: SHA pins never auto-receive upstream security/compat patches,
  so a stale pin can drift behind a breaking runner-image change — pair the pins
  with a documented refresh cadence (or a Dependabot/Renovate config that bumps the
  SHA while preserving the pin + version-comment idiom) so they stay current.

#### 8. Documentation (landed with this phase, not deferred)

**Files**: `tasks/README.md` + `CLAUDE.md` — because each phase is independently
mergeable, the docs for each surface land in the phase that introduces it (not
all in Phase 5, which would leave the docs wrong for the whole interim).

**Concrete `tasks/README.md` edits (not just "describe it"):** this is the
canonical "task-tree shape" file CLAUDE.md points contributors to, so it must carry
the structural change, not only CLAUDE.md. Add a **`cli` row to the
"Per-component checks" table** (Folds: rustfmt + clippy; no tests); add the
**workspace-scope `deny:check` / `pup:check`** entries (no `-p`, modelled on
`lint:workflows:check`); document the **`test:unit:cli` → `test:unit` → `test`**
path with coverage folded in; and document the **`build:*` family convention** —
verb-less per-crate release builds, only for binary-producing crates, in `default`
but **not** `check` — and **reconcile the existing `tasks/README.md` note** (~line
15) that calls `build-system` "unrelated to the `build:*` artifact namespace": that
note was written when `build:*` was empty, so update it now that `build:cli`
populates the namespace, making the `build-system`-component vs `build:*`-family
distinction explicit rather than pointing at an empty namespace. Crucially, **qualify the "this is what CI runs" claim** on the
`check` line (`tasks/README.md` ~line 20): `check` is the read-only/static subset CI
runs; the **tests run via `test` in the `test-unit`/`test-integration` jobs and the
release build via `build:cli` in the `build-cli` matrix job** — none of which are in
`mise run check`. So "green `check` ⇒ green CI" is *not* a valid inference; say so.

In this phase, also (CLAUDE.md): add `cli` to the component table (noting
`cli:check` = rustfmt + clippy only — like the other `<component>:check` roll-ups it
runs no tests; the cli unit tests run via the `test` roll-up / `test:unit:cli`,
which carries coverage by default — `cargo llvm-cov nextest`, disable with
`LUMINOSITY_COVERAGE=off`); note the `build:cli` task that release-builds the
host-native triples — it is in the bare `mise run` default (so it runs as part of
the full local check) but **not** in the fast read-only `mise run check`, and is
matrix-covered across both OSes in CI; record that `lint:fix` now includes
`lint:cli:fix` (clippy `--fix`, machine-applicable only, rewrites a dirty tree
via `--allow-dirty --allow-staged`) while shell still has no autofixer; note the
root `Cargo.toml` is an intentionally versionless workspace manifest with the
version in `cli/Cargo.toml`; add the Rust single-test invocation to CLAUDE.md's
"Running a single test" — **the plain (uninstrumented) form with nextest's real
filter syntax**, e.g. `cargo nextest run -p luminosity -E 'test(<name>)'`, and note
it deliberately skips coverage (unlike the default `test:unit:cli` path). Add a
brief **Rust subsection to CLAUDE.md Architecture** (mirroring the Build-system /
Shell subsections) mapping each new root config file to its role —
`Cargo.toml`/`clippy.toml`/`deny.toml`/`pup.ron` — including the non-obvious
"levels live in `Cargo.toml`, not `clippy.toml`", the deliberately-inert
architectural ban-lists, and the intentionally-empty `pup.ron`.

Enumerate the specific CLAUDE.md spots so the two docs do not disagree: update the
inner-loop **component list prose** (CLAUDE.md ~lines 26–27, currently
"Components: `build-system`, `scripts`") to include `cli`; and add to "Conventions
and gotchas" that `clippy.toml`'s `msrv` is a **fourth** hand-synced mirror of the
`mise.toml` rust pin (alongside the three 80-col copies) — the same manual-sync
hazard the 80-col note already warns about. Also note where `build:cli` sits
relative to the aggregates: it is in the bare `mise run` default (so the full local
check release-builds the host's triples) but **not** in `mise run check` — so the
"exact read-only set CI runs" framing for `check` excludes the build (CI runs it in
its own `build-cli` matrix job). The only residual local/CI gap is inherent and
non-fixable: one developer machine is one OS, so a local `mise run` builds that
OS's triple pair while CI's matrix builds both pairs. (Coverage, by contrast, runs
on every test OS — the `LUMINOSITY_COVERAGE=off` toggle is a developer convenience,
not a CI/local divergence.)

#### 9. TDD task-module unit tests

**Files**: extend the existing `tests/unit/tasks/test_format.py` and
`test_lint.py` with new `TestFormatCli` / `TestLintCli` classes — matching the
established one-file-per-family-module layout (e.g. `test_format.py` already
covers `tasks/format/scripts.py` via `TestFormatCheck` / `TestFormatFix`
classes), **not** new per-leaf `test_format_cli.py` files. Assert the exact
command string for **both** the `check` and the `fix` variant (the existing
`TestFormatFix` precedent tests fix too), and that a non-zero exit raises `Exit`
(`mocker: MockerFixture` fully annotated). Add a `test_build.py` (or a
`TestBuildCli` class) covering both the pure helper and the task body:
- **`host_targets()` directly** (no `platform` monkeypatch needed — pass the system
  string): `"Darwin"` → exactly the two `*-apple-darwin` triples, `"Linux"` →
  exactly the two `*-unknown-linux-musl` triples (pinned, drawn from
  `tasks/shared/targets.py`), and an unsupported value (e.g. `"Windows"`) **raises
  `Exit`** — so the silent-empty-build case is a tested failure, not a false-green.
- **Union assertion**: `set(host_targets("Darwin")) | set(host_targets("Linux"))`
  equals the set of release triples in `TARGETS` — so a triple dropped from either
  `TARGETS` or the partition cannot leave a shipped triple unbuilt pre-merge while
  the per-OS tests still pass.
- **The task body**: each built command is `cargo build --release --bin {CLI_CRATE}
  --target <triple>` (assert `--bin` and the crate from `CLI_CRATE`), and a non-zero
  exit raises `Exit`.
- **The output-verdict helper** (static-linkage + Mach-O arch from §6): unit-test
  the pure parser on both pass and fail `file`/`lipo`/`ldd` strings, and assert the
  build task composes the check per leg — so the guard's own logic is covered, not
  just the `cargo build` invocations.
This keeps the test deterministic regardless of the host it runs on.

**File**: `tests/unit/tasks/test_mise_wiring.py` (new) — the existing task tests
mock invoke's `Context` and assert command strings only; **none reads
`mise.toml`**, so the `depends`/aggregate edges this plan relies on are otherwise
untested. This module parses `mise.toml` with `tomllib` and asserts the wiring
directly. In this phase it asserts: `cli:check` folds `format:cli:check` +
`lint:cli:check` and **nothing else** (in particular **no** `test:unit:cli` edge —
guarding the test-free-`check` decision against a future re-add); the top-level
`check` contains `cli:check`; and `default` contains `build:cli` while `check` and
`cli:check` do **not** (the release-build-in-`default`-only decision). It is
**extended in each subsequent phase** as that phase adds edges (so every
independently-mergeable phase ships its own wiring assertions), converging on the
full enumerated `check`/`default`/`cli:check` arrays. This is the automated guard
that turns the plan's wiring prose into executable assertions.

Because this module already parses TOML, also add a **toolchain-coherence
assertion** here: the `clippy.toml` `msrv` and the `rustfmt.toml` `edition` must
match the `mise.toml` `rust` pin / workspace edition. This converts the
fourth-hand-synced-mirror hazard (the `msrv` copy, §3/§8) from a prose warning into
a tested invariant, so a rust bump that updates `mise.toml` but forgets
`clippy.toml` fails loudly rather than silently applying MSRV-gated lints against a
different stable than CI provisions.

### Success Criteria

#### Automated Verification

- [x] Workspace builds: `cargo build --workspace`
- [x] Release build of host-native triples: `mise run build:cli` (the two musl
      triples on Linux, the two darwin triples on macOS)
- [x] rustfmt clean: `mise run format:cli:check`
- [x] clippy clean with `-D warnings`: `mise run lint:cli:check`
- [x] Roll-up green: `mise run cli:check`
- [x] Task unit tests pass: `uv run pytest tests/unit/tasks/test_format.py tests/unit/tasks/test_lint.py tests/unit/tasks/test_build.py tests/unit/tasks/test_mise_wiring.py -v`
- [x] Aggregate still green: `mise run check`
- [x] Python/shell checks unaffected: `mise run build-system:check && mise run scripts:check`
- [x] Docs lint clean after CLAUDE.md/README edits: `mise run build-system:check`
- [x] Workflow lint passes: `mise run lint:workflows:check`

#### Manual Verification

- [ ] Breaking `cli` formatting makes `check-cli` red in CI on a PR.
- [ ] A break in the release build makes `build-cli` red — on the ubuntu leg for a
      musl-target break, on the macOS leg for a darwin-target break.
- [ ] The per-triple output assertions actually fire (these are now automated, not
      manual): the musl legs `Exit` on a non-static binary, and the darwin legs
      `Exit` if the Mach-O arch is wrong (in particular the arm64 `macos-latest`
      runner producing an `x86_64-apple-darwin` slice) — confirm by inspecting a CI
      run's output, since the verdict helper's logic is unit-tested separately.
- [ ] The `check-cli` and `build-cli` (both matrix legs) display names are added to
      branch-protection required checks (deferred to Phase 5 tie-off, but note it
      now).

---

## Phase 2: cargo-nextest + cargo-llvm-cov

### Overview

Add the test runner with coverage folded directly into it, scoped to the `cli`
crate, and wire `test:unit:cli` into the existing `test:unit` → `test` roll-up.
Coverage is not a separate task: by default `test:unit:cli` runs
`cargo llvm-cov nextest` (one instrumented pass that tests *and* reports
coverage), so coverage runs on every platform the tests run on, always — with a
`LUMINOSITY_COVERAGE=off` env toggle to drop to a plain `cargo nextest run` for a
faster inner loop.

### Changes Required

#### 1. Tool pins + coverage component

**File**: `mise.toml [tools]` — add:

```toml
"cargo-nextest" = "0.9.138"
"cargo-llvm-cov" = "0.8.7"
```

`llvm-tools-preview` is required by llvm-cov: add it to the `rust` components
list (`mise.toml:8` → `components = "rustfmt,clippy,llvm-tools-preview"`) so it is
present in every job without a separate `rustup component add`.

> **Verify at implementation (compatibility):** (1) the composed
> `cargo llvm-cov nextest` invocation works at this *exact* pair (llvm-cov 0.8.7
> shells out to nextest 0.9.138 — independently versioned tools that must agree on
> the nextest CLI surface); the Phase 2 success criterion "runs the instrumented
> pass and prints a summary" covers this if exercised at the pinned versions —
> record the known-good pairing. (2) each pinned tool resolves to an **aqua
> prebuilt binary on both `ubuntu-latest` and `macos-latest` (arm64)**; a missing
> darwin-arm64 prebuilt makes the macOS legs fall back to a slow source build or
> fail asymmetrically.

**Docs (with this surface, per the per-phase principle):** this is the first phase
to touch CLAUDE.md's inline tool list, so do the **structural reconcile here**: add
`cargo-nextest` and `cargo-llvm-cov`, **drop the stale `node`/`jj`** (never in
`[tools]`), and **add the omitted `gh`/`actionlint`** — so the list agrees with
`mise.toml` from this phase on (Phase 3 adds cargo-deny, Phase 4 adds the cargo-pup
exception).

#### 2. Invoke task bodies

**File**: `tasks/shared/rust.py` (new) — single source of truth for the literals
that would otherwise be duplicated across `mise.toml`, task bodies, and CI:

```python
import os

CLI_CRATE = "luminosity"            # must equal cli/Cargo.toml [package] name
PUP_NIGHTLY = "nightly-2026-01-22"  # cargo-pup v0.1.8 rust-toolchain.toml (Phase 4)
PUP_VERSION = "0.1.8"               # pinned cargo-pup release (Phase 4)


_FALSEY = {"off", "false", "0", "no"}


def coverage_enabled() -> bool:
    """Whether tests run instrumented. Read at CALL time, never at import.

    True → cargo llvm-cov nextest (coverage reported); False → plain cargo
    nextest run (faster inner loop). Env-sourced so a developer can drop coverage
    without a source edit; CI leaves it on. Must be called inside the task body —
    a module-level constant would freeze the value at import and ignore the env.
    Any of off/false/0/no (case-insensitive) disables it, so a plausible falsey
    value does not silently leave the slow path on.
    """
    return os.environ.get("LUMINOSITY_COVERAGE", "on").strip().lower() not in _FALSEY
```

**File**: `tasks/test/cli.py` (new) — `test:unit:cli` (composes `-p` from
`CLI_CRATE`, never a bare literal). Coverage is folded in: the **default** path is
the instrumented `cargo llvm-cov nextest` run (report-only — **no
`--fail-under`/threshold**, by design, see "What We're NOT Doing"); the env toggle
selects the plain `cargo nextest run`. The leaf function is named `run` (not
`check`) so the invoke name reflects that it runs tests rather than a read-only
check — the mise task `test:unit:cli` maps to `invoke test.cli.run`. One leaf, one
place tests execute, with `coverage_enabled()` read at call time:

```python
from tasks.shared.rust import CLI_CRATE, coverage_enabled

@task
def run(context: Context) -> None:
    """Run cli-crate unit tests (instrumented with coverage unless disabled)."""
    command = (
        f"cargo llvm-cov nextest -p {CLI_CRATE} --summary-only"
        if coverage_enabled()
        else f"cargo nextest run -p {CLI_CRATE}"
    )
    with context.cd(str(REPO_ROOT)):
        result = context.run(command, warn=True, pty=False)
    if result.exited != 0:
        raise Exit("nextest: cli tests failed", code=1)
```

**File**: `tasks/test/__init__.py` — register `cli` in the **`test` sub-package's**
collection (`from . import …, cli` + `ns.add_collection(Collection.from_module(cli))`,
alongside the existing `unit`/`integration`), **not** the top-level `tasks/__init__.py`
— `test` is a sub-package whose Collection is assembled in `tasks/test/__init__.py`,
so registering it at the top level would leave `invoke test.cli.run` unresolved and
break `mise run test:unit:cli` (and the whole `test` roll-up). No separate
`coverage` collection — coverage lives inside `test:unit:cli`.

#### 3. mise declarations + aggregation

**File**: `mise.toml` — add a single `test:unit:cli` leaf (`run = "invoke
test.cli.run"`) and fold it into the existing per-suite **`test:unit`** roll-up
(`mise.toml:37-39`) so it becomes `["test:unit:tasks", "test:unit:cli"]` — and
*only* there, so the cli unit tests (with coverage) flow through `test:unit` →
`test` exactly as the Python suite does. **Do not add `test:unit:cli` to
`cli:check`** — `cli:check` stays `["format:cli:check", "lint:cli:check"]`
(read-only, test-free). There is **no** `coverage:cli:check` leaf, **no**
`coverage:check` family aggregate, and **no** new edge on `default`: coverage
rides inside `test:unit:cli`, so the single `test` roll-up (already in `default`
since the repo baseline) is the only place it is wired. This phase therefore
leaves `default` structurally unchanged — `["format:fix", "lint:check",
"types:check", "test"]` — while `test` now transitively carries the instrumented
cli run. (`deny:check` / `pup:check` join `default` in Phases 3 / 4.)

#### 4. CI

**File**: `.github/workflows/main.yml` — two distinct concerns, kept separate to
honour the check/test split:

- **`check-cli`** (the read-only Rust check job, ubuntu-only) runs only
  `mise run cli:check` (format + lint, **no tests**). It runs **no** coverage step
  — coverage is now part of the test run, not a check. (The release build lives in
  its own `build-cli` matrix job from Phase 1 §7; it is not part of `check-cli`.)
- **The cli unit tests — with coverage — run in the existing `test-unit` job**,
  not in `check-cli`: that job already runs `mise run test:unit` (matrix ubuntu +
  macos), which now folds `test:unit:cli` (instrumented `cargo llvm-cov nextest` by
  default), so the Rust unit tests **and their coverage** run there automatically,
  **on both ubuntu and macOS**, with no new job. This is the deliberate change from
  the prior ubuntu-only-coverage contract: coverage is now always run, on every
  test OS. mise-action already provisions the stable toolchain + `cargo-nextest` +
  `cargo-llvm-cov` (with `llvm-tools-preview`) from `[tools]`; **add
  `Swatinem/rust-cache@<full-sha> # v2.x.y` to the `test-unit` job** (and, for
  parity, the `test-integration` job, whose cargo-deny/cargo-pup behavioural
  regressions shell out to cargo) so the cargo build is cached. CI leaves
  `LUMINOSITY_COVERAGE` at its `"on"` default; the toggle exists for local fast
  runs (and, if a future need arises, for a CI job to opt out).

#### 5. Tests

**File**: `tests/unit/tasks/test_test.py` (new, family-named — the first test for
the `test` task family; there is **no** `test_coverage.py`, coverage having no
task of its own). Assert **both** toggle branches of `test:unit:cli` (with `-p`
composed from `CLI_CRATE`, asserted against the shared constant): with the env
unset/default it builds `cargo llvm-cov nextest -p luminosity --summary-only`, and
with `LUMINOSITY_COVERAGE=off` it builds `cargo nextest run -p luminosity`. **Drive
both branches with `monkeypatch.setenv("LUMINOSITY_COVERAGE", …)` and invoke the
task** — this is the assertion that the call-time-function form (not an import-time
constant) actually honours the env, so a regression back to a frozen constant fails
the test. Assert `coverage_enabled()` defaults to on when the env is absent. Add a
**negative assertion** that the instrumented command contains no
`--fail-under`/threshold flag — mirroring the existing negative-flag idiom (e.g.
`_STYLE_FLAGS_OWNED_BY_EDITORCONFIG`) — so a future edit cannot silently add a
coverage gate the plan deliberately excludes. Add one **exit-code assertion**:
mock a non-zero `result.exited` on the default (instrumented) path and assert the
body raises `Exit`, guarding that `cargo llvm-cov nextest` propagates an inner
test failure rather than masking it behind a successful coverage collection.

**Extend `test_mise_wiring.py`**: assert `test:unit:cli` is folded into
`test:unit` (and is therefore reachable from `test`); assert it is **not** in
`cli:check` (which stays `["format:cli:check", "lint:cli:check"]`) — guarding the
test-free-`check` decision; and assert there is **no** `coverage:check` task and
**no** `coverage:check` edge anywhere (in particular not on `default`) — so a
future edit reintroducing a standalone coverage task that bypasses the `test`
roll-up is caught automatically.

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:cli` runs the instrumented `cargo llvm-cov nextest`,
      passes, and prints a coverage summary
- [x] `LUMINOSITY_COVERAGE=off mise run test:unit:cli` runs the plain
      `cargo nextest run` (no coverage), passes
- [x] `mise run cli:check` stays `format:cli:check` + `lint:cli:check` only — it
      runs **no** tests and no coverage (`check` stays read-only/fast)
- [x] `mise run test:unit` and `mise run test` both include the cli unit tests
      (with coverage)
- [x] `mise run check` runs **no** cli tests and **no** coverage
- [x] There is no `coverage:check` / `coverage:cli:check` task at all
- [x] Task unit tests pass: `uv run pytest tests/unit/tasks/test_test.py -v`
- [x] `mise run check` and `mise run` both exit 0

#### Manual Verification

- [ ] Coverage summary appears in the `test-unit` CI job log on **both** the
      ubuntu and macOS legs.
- [ ] Removing the cli test does not fail the build on a threshold (report-only
      confirmed).

---

## Phase 3: cargo-deny (supply-chain + architectural ban-lists)

### Overview

Add workspace-scope supply-chain enforcement with `deny.toml`, encoding the
live workspace-wide native-tls/OpenSSL ban and scaffolding the (initially inert)
architectural infra-crate ban-lists.

### Changes Required

#### 1. Tool pin

**File**: `mise.toml [tools]` — add `"cargo-deny" = "0.19.8"`.

#### 2. `deny.toml`

**File**: `deny.toml` (new, repo root) — current schema (no top-level `version`;
`[graph]` for targets):

```toml
[graph]
# The four shipped release triples (ADR-0002) PLUS the two host/CI dev triples.
# The dev triples are added so advisory/license/ban evaluation also covers the
# graph that is actually built and run during development and in the test/check CI
# jobs (gnu on ubuntu, aarch64-darwin locally) — otherwise a banned crate (e.g.
# native-tls) or an advisory reachable ONLY on the dev triple would be compiled and
# executed yet never deny-evaluated. Extra targets are cheap to evaluate (no build
# cost).
targets = [
    "aarch64-apple-darwin",
    "x86_64-apple-darwin",
    "aarch64-unknown-linux-musl",
    "x86_64-unknown-linux-musl",
    "x86_64-unknown-linux-gnu",   # CI ubuntu host dev triple
    # aarch64-apple-darwin already listed (also the local dev triple)
]
# Evaluate the graph as the release ships it (ADR-0010: default-features = false,
# rustls). NOT all-features = true — that would enable feature-gated paths the
# musl-static binaries never build (e.g. reqwest's native-tls feature) and fire
# false-positive bans that block unrelated work. The actual static-link guarantee
# is exercised by build:cli (Phase 1); this ban is a complementary,
# necessary-but-not-sufficient guard.

[advisories]
ignore = []
# Set the policy explicitly rather than leaning on version-sensitive defaults
# (the unmaintained default has shifted across cargo-deny releases). Verify the
# exact key names against the cargo-deny 0.19.8 schema at implementation.
unmaintained = "all"
yanked = "deny"

[licenses]
# Pre-seeded with the permissive licenses the ADR-0010 stack (reqwest, rustls,
# tokio, clap and their closures) is known to require, so 0007 is not blocked by
# an unrelated allow-list PR. Any future copyleft / MPL / *GPL license must be
# justified per-crate via [[licenses.exceptions]], never added to this blanket
# allow.
allow = [
    "MIT", "Apache-2.0", "Apache-2.0 WITH LLVM-exception",
    "BSD-2-Clause", "BSD-3-Clause", "ISC", "Zlib",
    "Unicode-3.0", "Unicode-DFS-2016",
]
confidence-threshold = 0.8

[bans]
multiple-versions = "warn"
wildcards = "deny"
# ADR-0010: rustls only — no transitive dep may re-enable default-tls and break
# the musl-static build. NOTE: this covers the TLS vector only; other system-C
# linkers (libgit2-sys, curl-sys, libsqlite3-sys w/o bundled, libz-sys) can also
# break the static build and are added here if/when they become relevant. The
# musl build (Phase 1) is the authoritative static-link check.
deny = [
    { crate = "native-tls" },
    { crate = "openssl" },
    { crate = "openssl-sys" },
]
# Architectural infra-crate ban-lists (ADR-0009) are scaffolded here and become
# load-bearing once the workspace splits (config/config-adapters — story 0009;
# later crates — work item 0012). Inert in the single-crate bootstrap.
skip = []
skip-tree = []

[sources]
unknown-registry = "deny"
unknown-git = "deny"
allow-registry = ["https://github.com/rust-lang/crates.io-index"]
```

> The `[licenses] allow` list is pre-seeded for the ADR-0010 stack but may still
> need a small broadening PR as real dependencies land in 0007+. Keep additions
> permissive-only; route any copyleft via per-crate exceptions.

**Cargo.lock**: commit `Cargo.lock` for the workspace (cargo-deny's
advisories/sources resolution reads it). With zero dependencies today this is
trivial, but committing it now means `deny:check` behaves identically locally and
in CI from the first real dependency in 0007. **Generate it with the
mise-pinned 1.90.0 toolchain** (e.g. `mise exec -- cargo generate-lockfile`) so
its lockfile-format version is one the pinned cargo accepts under
`--locked`/`--frozen` — a lock written by a newer local cargo can be rejected by
the pinned CI cargo.

**Known follow-ups (tracked, not actioned in 0006's empty graph):**
`[bans] multiple-versions = "warn"` is non-blocking for now; tighten to `"deny"`
with explicit `skip` entries once real dependencies land (0009/0012) so
duplicate-version drift becomes a visible decision. (The earlier host-dev-triple
coverage gap — a crate pulled in only on `x86_64-unknown-linux-gnu`/the local
darwin triple escaping deny-evaluation — is **closed** by adding those triples to
`[graph] targets` above, so advisory/ban coverage now matches every triple that is
actually built and run, not only the shipped four.)

#### 3. Invoke task + mise declaration

**File**: `tasks/deny.py` (new) — `deny:check`:

```python
@task
def check(context: Context) -> None:
    """Check the workspace dependency graph with cargo-deny."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo deny check advisories licenses bans sources",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("cargo-deny reported findings — see output", code=1)
```

**File**: `tasks/__init__.py` — register `deny`.

**File**: `mise.toml` — add `deny:check` leaf; add it to the top-level `check`
and `default`.

#### 4. CI

**File**: `.github/workflows/main.yml` — add a `check-supply-chain` job
(`ubuntu-latest`) with least-privilege `permissions: { contents: read }`, running
`mise run deny:check`; add to the `prerelease`/`release` `needs:` lists. Ensure
the RustSec advisory DB is fetched **fresh** each run (do not cache it stale) so
newly-disclosed advisories are caught, and confirm cargo-deny fails (not warns)
if the DB is unavailable — the advisories check is only as good as the DB's
freshness.

#### 5. Tests

**File**: `tests/unit/tasks/test_deny.py` (new) — command-string assertion (the
four sections in order).

**File**: a ban-violation regression test (e.g.
`tests/integration/tasks/test_deny_bans.py`) — runs `cargo deny check bans`
against a throwaway manifest that depends on `native-tls` and asserts a non-zero
exit. This converts the "adding native-tls fails the build" manual step into an
executed regression test, so a future edit that loosens `[bans] deny` is caught
automatically (the ADR-0010 invariant is "live from day one" and must not
silently regress). **Isolate the throwaway manifest** in `tmp_path` with its own
`[workspace]` table (so cargo/cargo-deny do not walk upward and absorb the real
workspace or its committed `Cargo.lock`); otherwise the test could pass for the
wrong reason — resolving the real graph rather than the banned dependency — and
hide a genuine loosening of the ban. The cargo-pup rule regression (Phase 4 §5)
takes the same `tmp_path` + `[workspace]` isolation.

**Where it runs (closing the skip-to-green hole).** This is a pytest test, so it
runs via `mise run test:integration` in the existing **`test-integration`** job —
*not* the `check-supply-chain` job (which runs `mise run deny:check`, not pytest).
cargo-deny is a mise `[tool]`, so it **is** provisioned in `test-integration` (it
runs `jdx/mise-action` with `install: true`), and the test runs there rather than
skipping. To guarantee it never silently skips in CI: gate it on
`shutil.which("cargo-deny")` for *local* dev convenience, but make the skip a
**hard failure when `CI` is set** (`pytest.fail` if the env var `CI`/`GITHUB_ACTIONS`
is truthy and the tool is absent) — so a missing/mis-provisioned tool reddens CI
instead of passing green. `test_workflows.py` (Phase 5) additionally asserts the
`test-integration` job is in the release `needs:` list so the job itself cannot be
silently dropped.

**Extend `test_mise_wiring.py`**: assert `deny:check` is in both `check` and
`default`.

#### 6. Documentation (landed with this phase)

**File**: `CLAUDE.md` + `tasks/README.md` — describe the workspace-scope
`deny:check` roll-up and the cargo-deny ban-list's dual role (supply-chain +
the architectural / native-tls invariants). Also **add `cargo-deny` to CLAUDE.md's
inline tool list** (the structural reconcile of that list — drop `node`/`jj`, add
`gh`/`actionlint`, add cargo-nextest/cargo-llvm-cov — landed in Phase 2 §1; this
phase appends its own tool), per the docs-land-with-the-surface principle.

### Success Criteria

#### Automated Verification

- [x] `cargo deny --version` reports `0.19.8`, and `mise run deny:check` exits 0
      against the bootstrap workspace — the clean exit also **validates the
      `[advisories]` schema** (`unmaintained`/`yanked` keys), since a wrong/removed
      key makes cargo-deny error on the config rather than evaluate it
- [x] `cargo deny check` confirms the four sections run (advisories, licenses,
      bans, sources)
- [x] Task unit test passes: `uv run pytest tests/unit/tasks/test_deny.py -v`
- [x] `mise run check` and `mise run` both exit 0

#### Manual Verification

- [ ] Adding a `native-tls` dependency makes `deny:check` (and the CI
      `check-supply-chain` job) fail.
- [ ] The bans `deny` list rejects `openssl` transitively.

---

## Phase 4: cargo-pup nightly lane (blocking)

### Overview

Add the architecture-enforcement lane on a pinned nightly, blocking, with a
minimal `pup.ron`. The real `restrict_imports` layering rules arrive with 0007's
hexagonal modules; in the single-crate bootstrap the lane proves the toolchain
end-to-end and satisfies 0006's blocking-check acceptance criterion.

**Deliberate tradeoff — blocking with empty rules.** Until 0007 adds rules,
`pup:check` enforces nothing yet but carries the full cost of a blocking nightly
lane (a SPOF on the whole repo's mergeability via the most volatile, least-mature
tool). This is accepted because 0006's AC explicitly requires a *blocking*
cargo-pup lane. The risk is mitigated by making advisory↔blocking a **first-class
toggle**, not a scramble: the `pup:check` body calls `pup_mode()` from
`tasks/shared/rust.py` (`"deny"` → `Exit(code=1)` on findings; `"warn"` → log and
exit 0), read at call time from the `LUMINOSITY_PUP_MODE` environment variable
(default `"deny"`). So a single broken host or CI run can downgrade to
advisory *without a source edit* (no need to land a commit through the red CI it
would unblock); and if a nightly/cargo-pup bump breaks the lane durably, the
committed default flips in one unit-tested line — the documented fallback from
spike 0002 / ADR-0009.

### Changes Required

#### 1. Provision the nightly + cargo-pup (rustup-managed, NOT a mise [tools] pin)

**Mechanism is confirmed (web research, 2026-06-27), resolving the prior
unknown.** mise's rust backend drives **rustup** (it sets `RUSTUP_TOOLCHAIN` and
delegates to rustup's proxies). mise **cannot** pin two rust toolchains at once
and there is **no `rust-nightly` short-name** — so the draft's
`"rust-nightly" = ...` `[tools]` line is **removed entirely**. Instead:

- **Stable stays in `mise.toml`** (`rust = 1.90.0`) — the product build and every
  other check.
- **The nightly is rustup-managed** by a `deps:install:pup` provisioning task. It
  is *not* in `[tools]`; the pin lives in the install command + `PUP_NIGHTLY` in
  `tasks/shared/rust.py`.
- **Invocation uses `cargo +nightly-2026-01-22 ...`** — rustup's `+toolchain`
  shorthand outranks the `RUSTUP_TOOLCHAIN` mise exports, so the override is
  reliable even with mise pinning stable (requires `~/.cargo/bin` on PATH; no
  mise/rustup shim conflict for rust). `+toolchain` only *selects*, so the
  explicit `rustup toolchain install` is required first.

**File**: `tasks/shared/rust.py` — extend with the pup mode toggle, sourced from
the environment (default committed) so a single host or CI run can downgrade to
advisory **without a source edit** (the escape hatch must not require landing a
commit through the very CI it is meant to unblock):

```python
def pup_mode() -> str:
    """cargo-pup blocking mode. Read at CALL time, never at import.

    "deny" → fail on findings (blocking, per AC6); "warn" → advisory (log only).
    Default "deny" honours AC6: with an empty pup.ron (0006 bootstrap) "deny"
    passes trivially — no rules means nothing to violate — so the only blocking
    exposure is a nightly/cargo-pup toolchain break, recoverable per-environment
    via LUMINOSITY_PUP_MODE=warn (and, if a bump breaks the lane durably, by
    flipping this default in one line). 0007's real restrict_imports rules give
    "deny" teeth. NOTE: warn covers a cargo-pup *findings* failure, not a
    toolchain-*unavailable* failure — see the nightly-GC recovery note in §1.
    The value is normalised (strip + lower-case) so an incident-time typo like
    "Warn"/" warn " still activates the advisory escape hatch; an unrecognised
    value is treated as "deny" (fail-closed) but printed as a WARNING so the
    typo is visible rather than silently blocking.
    """
    raw = os.environ.get("LUMINOSITY_PUP_MODE", "deny").strip().lower()
    if raw not in {"deny", "warn"}:
        print(f"WARNING: unrecognised LUMINOSITY_PUP_MODE={raw!r}; using 'deny'")
        return "deny"
    return raw
```

> **Why a function, not a `PUP_MODE` constant**: identical reasoning to
> `coverage_enabled()` (Implementation Approach → Shared constants). A module-level
> `PUP_MODE = os.environ.get(...)` is frozen at import and copied into `tasks/pup.py`
> by `from … import`, so the `LUMINOSITY_PUP_MODE=warn` escape hatch — the
> documented recovery for a nightly/cargo-pup break — would silently not work, and
> the toggle tests would assert a path production never takes. Read it at call time.

**File**: `mise.toml` — add a `deps:install:pup` task declaration; **`tasks/deps.py`**
body (mirrors `install_rust_targets` at `tasks/deps.py:14-17`, composing from
`PUP_NIGHTLY` / `PUP_VERSION`) running, as discrete checked steps:

```text
# Step 1 — install the nightly. If this fails (e.g. the dated nightly has been
# GC'd from static.rust-lang.org), Exit NOW with the actionable bump-the-pin
# message, BEFORE any `+nightly` invocation — otherwise a downstream `+nightly`
# call emits an opaque "override does not resolve" error instead (see recovery note).
rustup toolchain install nightly-2026-01-22 --profile minimal \
    --component rustc-dev --component rust-src --component llvm-tools-preview
# Step 2 — presence probe: skip the (multi-minute, network) cargo install when the
# exact pinned cargo-pup is already on PATH, so deps:install:pup is a true no-op in
# steady state — important because pup:check depends on it and pup:check is in the
# read-only `check`. `cargo install --locked` is NOT a pure no-op (it resolves and
# inspects the existing install and can rebuild/hit the network), so guard it.
# Do the version comparison IN PYTHON via token equality (not a shell grep): capture
# `cargo +{PUP_NIGHTLY} pup --version` stdout, and treat as "present" iff PUP_VERSION
# appears as a whitespace-split TOKEN (e.g. "cargo-pup 0.1.8" → tokens
# {"cargo-pup", "0.1.8"}). Token equality avoids both failure modes: the substring
# false-match (0.1.80 / 10.1.8) AND the whole-line brittleness of `grep -Fqx`
# (trailing build metadata, name-form, or "cargo_pup" vs "cargo-pup" would break an
# anchored whole-line match and force a reinstall every run). Pseudocode:
#     out = run("cargo +{PUP_NIGHTLY} pup --version", warn=True).stdout
#     present = PUP_VERSION in out.split()
#     if not present: run("cargo +{PUP_NIGHTLY} install cargo_pup
#                          --version {PUP_VERSION} --locked")
# Step 3 — PATH/override pre-flight (see below).
cargo +nightly-2026-01-22 --version
```

(The invoke body composes this from `PUP_NIGHTLY`/`PUP_VERSION`; each numbered step
is a discrete `context.run` with `warn=True` + an `Exit` on non-zero — step 1's
`Exit` carries the nightly-GC bump message. Step 2's presence check is Python
token-equality, not a brittle anchored `grep`. In CI, the checksum-mismatch path
from §4 forces step 2 to "absent" by **deleting the restored binaries before this
step runs**, so the version probe — which cannot itself detect a same-version
poisoned binary — is bypassed and a clean rebuild happens.)

The final `cargo +nightly-2026-01-22 --version` is a **pre-flight**: it confirms
rustup's `+toolchain` override actually resolves on this machine (i.e. that
`~/.cargo/bin`'s rustup proxy is the `cargo` on PATH, not a shim that ignores
`+toolchain`). If it reports a non-nightly version or errors, the install task
fails with an actionable message rather than letting `pup:check` later run the
wrong toolchain and emit an opaque `rustc_private` load error. This is a Phase 4
automated success criterion, not just prose.

`--version 0.1.8 --locked` pins cargo-pup itself (the README's install is
unpinned; for a supply-chain story the tool must be reproducible — confirmed
latest is 0.1.8, the matching nightly is `nightly-2026-01-22`). The components
are exactly those cargo-pup's `rust-toolchain.toml` requires. (`rust-analyzer`
from upstream's file is convenience-only and omitted.)

> **Nightly-unavailable recovery (distinct from the findings fallback).** Dated
> nightlies are garbage-collected from `static.rust-lang.org` over time. If
> `rustup toolchain install nightly-2026-01-22` can no longer resolve, the
> **install step itself fails** before any check runs — and `LUMINOSITY_PUP_MODE=warn`
> does **not** help (it only downgrades a cargo-pup *findings* failure, not a
> toolchain-*unavailable* one). The recovery is to bump **`PUP_NIGHTLY` and
> `PUP_VERSION` together** to a compatible cargo-pup release + its
> `rust-toolchain.toml` nightly (they are a matched pair — the rustc-driver only
> loads under the nightly it was built against). The CI built-binary cache (§4)
> mitigates transient outages but not permanent GC. Record this as the documented
> recovery so an on-call dev is not left guessing why a green lane suddenly cannot
> provision.

> **Trust boundary (security, accepted with notes).** Two residual surfaces in this
> lane: (a) `rustup toolchain install` fetches the nightly over the network — rely
> on rustup's built-in signature/checksum verification (document that it is in
> effect; prefer the runner's cached toolchains where available); and (b)
> cargo-deny audits the *product* `Cargo.lock`, **not** cargo-pup's own build
> closure (its deps, build scripts, proc-macros), which executes as a rustc-driver
> with full privileges. Record this as an explicit accepted-risk boundary (or
> periodically `cargo audit` cargo-pup's resolved tree) so the tool closure is not a
> silent blind spot in an otherwise thorough supply-chain posture.

#### 2. `pup.ron`

**File**: `pup.ron` (new, repo root) — minimal config generated via
`cargo pup generate-config` then trimmed to an empty/near-empty rule set (no
`restrict_imports` rules yet — there are no hexagonal layers to constrain). A
comment records that 0007 adds the inward-direction module rules.

**File**: `.gitignore` — add `.pup/` (cargo-pup isolates its build output in a
`.pup/` directory, separate from `target/`).

#### 3. Invoke task + mise declaration

**File**: `tasks/pup.py` (new) — `pup:check`. Composes the nightly from
`PUP_NIGHTLY` and honours the `PUP_MODE` toggle. Provisioning is guaranteed by the
mise `depends` edge on `deps:install:pup` (below), so the body simply runs the tool
— no in-body provisioning probe is needed (it mirrors the Python check bodies,
which depend on `deps:install:python` and then just run):

```python
from tasks.shared.rust import PUP_NIGHTLY, pup_mode

@task
def check(context: Context) -> None:
    """Enforce intra-crate module-import rules with cargo-pup (nightly lane)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(f"cargo +{PUP_NIGHTLY} pup", warn=True, pty=False)
    if result.exited != 0:
        if pup_mode() == "warn":        # advisory fallback (nightly-bump escape)
            print(
                "WARNING: cargo-pup reported findings (advisory mode, "
                "LUMINOSITY_PUP_MODE=warn — NOT blocking); see output above"
            )
            return
        raise Exit("cargo-pup: module-import rule violation", code=1)
```

> The advisory branch uses `print()` with a `WARNING:` prefix — matching the
> codebase's existing task-body convention (e.g. `tasks/test/integration.py` prints
> progress directly; `tasks/` uses no `logging`). The prefix makes a
> downgraded-to-advisory gate greppable in captured `mise run` output without
> introducing a logging dependency the rest of the tree does not have. Tests assert
> it via `capsys`. Apply the same `print("WARNING: …")` treatment to the clippy
> `--fix` non-zero-exit note in Phase 1 §4.

**Why `depends` on `deps:install:pup`**: this follows the repo convention — every
Python check `depends` on `deps:install:python`, because a check must provision the
non-mise-`[tools]` it needs. The nightly + cargo-pup are exactly such non-`[tools]`
dependencies (rustup-managed, not in `[tools]`), so `pup:check` declares the edge
the same way. `deps:install:pup` is idempotent — `rustup toolchain install` no-ops
when the nightly is present, and `cargo install … --version … --locked` no-ops when
that exact version is installed — so the per-run cost in steady state is small (the
same shape as `uv sync --frozen` ahead of every Python check), and the install
task's own `cargo +{PUP_NIGHTLY} --version` pre-flight (§1) still gives a clear,
distinct error if provisioning is somehow broken. Wiring it as a `depends` makes
`mise run check` and `mise run pup:check` self-provisioning, so a fresh checkout
needs no separate manual install step.

**File**: `tasks/__init__.py` — register `pup`.

**File**: `mise.toml` — add `pup:check` leaf with
`depends = ["deps:install:pup"]`; add it to the top-level `check` and `default`.

#### 4. CI nightly lane

**File**: `.github/workflows/main.yml` — add a `check-architecture` job
(`ubuntu-latest`) with least-privilege `permissions: { contents: read }` that:

- restores the *built* `cargo-pup` binary cache keyed on
  `(PUP_NIGHTLY, PUP_VERSION, OS)` (so a transient crates.io/nightly hiccup during
  `cargo install` cannot independently redden CI) **before** the run step, plus
  `Swatinem/rust-cache@<full-sha> # v2.x.y` keyed on the nightly for the analysis
  build,
- then runs `mise run pup:check` — which **self-provisions** via its
  `deps:install:pup` dependency (the presence-probe-guarded install no-ops on a
  cache hit, builds on a miss), so no separate explicit provisioning step is needed.
  (Running `mise run deps:install:pup` as its own step is optional — harmless but
  redundant now that the depends edge exists.)

**Cache-poisoning guard (the restored binary is executed, so its integrity must be
verified).** A GitHub Actions cache is writable by workflow runs, so a poisoned
entry under the `(PUP_NIGHTLY, PUP_VERSION, OS)` key would substitute the
`cargo-pup`/`pup-driver` binaries that then execute as a rustc-driver with full
filesystem access — a code-execution vector in the very supply-chain story meant to
shrink that surface. The integrity check must anchor on a value **outside** the
writable cache — verifying a binary against a checksum stored in the same cache is
no protection (an attacker who writes the key writes both). Therefore:
- (a) the **expected** SHA-256s live **out-of-band**: a committed **per-OS map**
  in `tasks/shared/rust.py` keyed `(PUP_NIGHTLY, PUP_VERSION, OS)` — matching the
  cache key, because `cargo-pup`/`pup-driver` are platform-specific so a single hash
  cannot match two OS legs (a version-only constant would fail-closed on every leg
  it does not match, or get loosened to a non-exact compare that defeats the guard).
  Each value is populated once from a trusted from-source build (see the
  checksum-refresh runbook). The verify step **looks up the entry for the running
  OS** and fail-closes unless the restored binaries' hashes match it. A unit test
  asserts every cached OS has a committed entry.
- (b) confirm the cache is **not writable from `pull_request`/fork contexts** (the
  trusted lane must not read a key a fork PR can populate) — assert this as a
  concrete cache-key-scoping check, not a confirm-at-impl note;
- (c) **a mismatch deletes the restored `cargo-pup`/`pup-driver` binaries** before
  `deps:install:pup` runs, so the step-2 presence probe genuinely sees "absent" and
  rebuilds from `--locked` source. This must be a real delete, **not** a reliance on
  the probe noticing tampering — the version-string probe cannot detect a
  *same-version* poisoned binary (the attacker controls the reported version), so
  integrity enforcement lives in the checksum-verify-then-delete step, with the probe
  only deciding present-vs-absent afterward.

If a trustworthy out-of-band checksum cannot be maintained, drop the binary cache
and rebuild from source every run — correctness over speed for a compiler plugin.

**Apply the same lens to `Swatinem/rust-cache`.** That action caches the compiled
`target/` dir on the PR-triggered `check-cli`/`build-cli`/`test-unit`/
`test-integration` jobs, and restored compiled artifacts (build scripts,
proc-macros) are *executed* during `cargo build`/`nextest` — the same
cache-poisoning class as the pup binary. Confirm fork-PR runs cannot populate the
keys the trusted (push) lane reads (GitHub scopes caches per-branch, but
base-branch caches are readable by PR branches), and record the residual (rust-cache
caches executed compiled output) as an explicit accepted-risk boundary alongside the
cargo-pup build-closure note in §1.

Add `check-architecture` to the `prerelease`/`release` `needs:` lists. Every other
job stays on stable. **macOS note**: `pup:check` is part of the aggregate
`mise run check`, so a macOS developer's local run also exercises it — and now
auto-provisions it via the `deps:install:pup` dependency. That from-source
cargo-pup build under nightly is a *one-time* cost (idempotent thereafter), and CI
validates the lane on ubuntu. If macOS-local cargo-pup proves troublesome, the
`PUP_MODE = "warn"` toggle lets a developer run without it blocking; the lane's
authoritative gate is the ubuntu `check-architecture` job.

#### 5. Tests

**File**: `tests/unit/tasks/test_pup.py` (new) — assert, precisely (not loosely):
the `pup:check` command is `cargo +{PUP_NIGHTLY} pup` (composed from the
constant); that with `monkeypatch.setenv("LUMINOSITY_PUP_MODE", "deny")` (or unset
→ default) a non-zero exit raises `Exit`, while `…setenv(…, "warn")` returns
cleanly and **prints a `WARNING:`-prefixed message** (assert via `capsys`) —
driving the toggle via the env through `pup_mode()` so the test proves the
call-time read honours the env (a regression to an import-time constant fails it).
Also assert `pup_mode()` **normalises** its input (e.g. `"Warn"`/`" warn "` →
`"warn"`) so an incident-time typo does not silently leave the lane blocking;
and (in `test_mise_wiring.py`) that `pup:check` **`depends` on `deps:install:pup`**
(mirroring the Python-check ↔ `deps:install:python` convention). Extend the deps
tests (`test_deps.py`) to assert the `deps:install:pup` composition exactly: the
`rustup toolchain install {PUP_NIGHTLY}` step, the full `rustc-dev` + `rust-src` +
`llvm-tools-preview` component set, the **presence-probe guard** around
`cargo +{PUP_NIGHTLY} install cargo_pup --version {PUP_VERSION} --locked` (so the
install is skipped when the pinned version is already present), and the
`cargo +{PUP_NIGHTLY} --version` pre-flight — so a dropped component (cargo-pup
won't build) or a removed guard is caught by the test, not by a slow CI failure.

**File**: a cargo-pup behavioural regression test (e.g.
`tests/integration/tasks/test_pup_rules.py`) — parallel to the cargo-deny
ban-violation test, this makes the blocking-check AC (a module-import violation
fails the build) self-verifying in 0006 rather than deferring it entirely to
0007. Against a throwaway crate carrying a trivial `restrict_imports` rule it
violates, assert `cargo +{PUP_NIGHTLY} pup` exits non-zero (and that `pup:check`
under `pup_mode() == "deny"` therefore raises `Exit`).

**Where it runs (the pup tool is not a `[tool]`, unlike cargo-deny).** The nightly
+ cargo-pup are provisioned only by `deps:install:pup`, which the general
`test-integration` job does *not* run — so this test cannot simply ride
`test:integration` like the deny one (it would skip there, and a CI-hard-fail-skip
would then wrongly redden `test-integration`). Instead mark it
`@pytest.mark.requires_pup` and partition it out, which requires **three concrete
edits, not just the marker**:

1. **Register the marker** in `pyproject.toml` `[tool.pytest.ini_options]`:
   `markers = ["requires_pup: needs the cargo-pup nightly toolchain (run only in
   check-architecture)"]`, and add `--strict-markers` to `addopts` (currently
   `"--import-mode=importlib"`) so a typo'd or unregistered marker fails collection
   loudly instead of silently selecting/deselecting nothing.
2. **Wire the deselection into the mise task**: edit the existing
   `[tasks."test:integration:tasks"]` `run` line (`mise.toml:32-35`) from
   `uv run pytest tests/integration/tasks -v` to
   `uv run pytest tests/integration/tasks -v -m "not requires_pup"`, so the
   `test-integration` job (which lacks the nightly) does not run — and therefore
   does not hard-fail on — the pup regression.
3. **Run it explicitly** as a `uv run pytest -m requires_pup` step in the
   **`check-architecture` job** (which provisions the nightly via the `pup:check` →
   `deps:install:pup` dependency); there the skip degrades to a **hard failure when
   `CI` is set**, so a provisioning regression reddens rather than skips.

`test_mise_wiring.py` asserts the `-m "not requires_pup"` filter is present on
`test:integration:tasks` (so it cannot be dropped), and `test_workflows.py`
(Phase 5) asserts `check-architecture` runs the `-m requires_pup` step — together
making the partition tamper-evident.

**Also assert the committed `pup.ron` loads.** Because the 0006 `pup.ron` is
deliberately empty, `pup:check` passing is indistinguishable from `pup:check`
passing because the config failed to parse. Add an assertion (in
`test_pup_rules.py` or alongside) that `cargo +{PUP_NIGHTLY} pup print-modules`
(or `print-traits`) against the repo's real `pup.ron` exits 0 — covering the
"config is actually loaded" contract independently of whether any rules exist yet.

**Extend `test_mise_wiring.py`**: assert `pup:check` is in both `check` and
`default`, and that it **`depends` on `deps:install:pup`** (so a future edit
dropping the provisioning edge — which would make a fresh checkout's `pup:check`
fail for a missing toolchain — is caught), mirroring the existing Python-check ↔
`deps:install:python` convention. This completes the full enumerated `check` /
`default` / `cli:check` arrays in the wiring test.

#### 6. Documentation (landed with this phase)

**File**: `CLAUDE.md` + `tasks/README.md` — describe the cargo-pup nightly lane:
that it is the sole inward-direction enforcer, runs blocking on the pinned nightly
while everything else is stable, auto-provisions via `pup:check`'s
`deps:install:pup` dependency (so `mise run check` on a fresh checkout installs the
nightly + cargo-pup itself, the same way a Python check triggers `uv sync`), and
has the `PUP_MODE` / `LUMINOSITY_PUP_MODE` advisory fallback. Reconcile with CLAUDE.md's
tool-provisioning inventory (which states tools are "pinned in `mise.toml`; mise
provisions them"): note cargo-pup + its nightly are the **one exception** — *not*
in `[tools]`, rustup-provisioned via `deps:install:pup`, pinned by `PUP_NIGHTLY` /
`PUP_VERSION` in `tasks/shared/rust.py`. Add cargo-pup to CLAUDE.md's inline tool
list **flagged as the one non-`[tools]` exception** (rustup-provisioned via
`deps:install:pup`). The structural reconcile of that list (drop `node`/`jj`, add
the omitted `gh`/`actionlint`) lands with the first phase that touches the line —
Phase 2 §1 — and the registry tools land in the phases that add them (cargo-nextest
/ cargo-llvm-cov in Phase 2 §1, cargo-deny in Phase 3 §6), per the
docs-land-with-the-surface principle; this phase only adds the cargo-pup exception.

### Success Criteria

#### Automated Verification

- [ ] `mise run deps:install:pup` provisions the nightly + pinned cargo-pup, and
      `cargo +nightly-2026-01-22 pup` resolves (rustup `+toolchain` override works
      under mise-pinned stable)
- [ ] `mise run pup:check` exits 0 against the bootstrap (minimal `pup.ron`), and
      from a clean checkout it **self-provisions** via its `deps:install:pup`
      dependency (no separate manual install needed) — `test_mise_wiring.py` asserts
      the `depends` edge
- [ ] Task unit tests pass: `uv run pytest tests/unit/tasks/test_pup.py tests/unit/tasks/test_deps.py -v`
      (including the `PUP_MODE` deny/warn toggle and the exact install-step
      composition)
- [ ] `mise run check` and `mise run` both exit 0, with the product build still
      on stable (`cargo build --workspace` uses 1.90.0)

#### Manual Verification

- [ ] The `check-architecture` CI job runs on the pinned nightly and is blocking
      (a forced rule violation, once 0007 adds rules, makes it red).
- [ ] Stable jobs are unaffected by the nightly lane.
- [ ] Risk note recorded: a nightly bump breaking cargo-pup blocks merges;
      fallback is flipping `PUP_MODE = "warn"` (one line, unit-tested).

---

## Phase 5: Tie-off — aggregation, docs, branch protection

### Overview

Confirm the two green-build acceptance criteria end-to-end, verify the
phase-distributed docs are coherent, harden the CI-wiring guard, and record a
durable branch-protection runbook. (Per-surface docs already landed in Phases
1/3/4 — this phase verifies, it does not author them from scratch.)

### Changes Required

#### 1. Documentation coherence + the descriptions earlier phases missed

The component-table, `lint:cli:fix`, deny, and pup docs landed in their phases.
This phase fixes the *aggregate* descriptions that go stale and that no single
earlier phase owns:

**File**: `CLAUDE.md` — update the descriptions of what `mise run check` and the
bare `mise run` actually run: `check` now also runs `cli:check` + `deny:check` +
`pup:check` (it is no longer "format + lint + types" only — but it remains
**test-free** and **build-free**, the deny/pup additions being static analysis, not
tests or builds), and `default` adds the cli unit tests via the `test` roll-up
(which carry coverage by default — note the `LUMINOSITY_COVERAGE=off` toggle), the
host-native release build `build:cli`, and deny + pup. Also: **verify**
`rustfmt.toml` is now real (CLAUDE.md
already *listed* it as an 80-col location while the file did not exist — reword
from "add it" to "it now exists"); confirm the Rust single-test line and the
versionless-root-manifest note from Phase 1 are present.

**File**: `mise.toml` — update the `check` and `default` task `description`
strings to match: `check` adds the deny/pup static checks (still read-only,
test-free, build-free); `default` adds deny/pup, the `build:cli` host-native
release build, and notes that `test` now carries the cli unit tests with coverage
(they currently say "read-only format, lint, and type checks" / omit
build/deny/pup).

#### 2. CI presence assertion (REQUIRED, not optional)

**File**: `tests/unit/tasks/test_workflows.py` — assert that `check-cli`,
`build-cli`, `check-supply-chain`, and `check-architecture` each exist, run their
expected `mise run` target, and appear in the `prerelease`/`release` `needs:`
lists; that `build-cli` carries the `[ubuntu-latest, macos-latest]` matrix (so a
future edit dropping the macOS leg — and with it darwin build coverage — is
caught); that the pre-existing `test-unit` job still runs `mise run test:unit` (the
path the cli unit tests now flow through) and `test-integration` runs
`mise run test:integration` (the deny ban regression's home), both in the release
`needs:` list; and that **`check-architecture` runs the explicit
`uv run pytest -m requires_pup` step** (so the cargo-pup behavioural regression
cannot be silently dropped from the one job that provisions its nightly).

**Scope this guard honestly.** `test_workflows.py` verifies CI *job topology* — that
the jobs exist, run the right targets, and gate the release — **not** branch-protection
mergeability, which is configured in repo settings and is genuinely untestable from
the repo (the plan already treats it as a manual runbook step, Phase 5 §3). So this
test is a *necessary* backstop, not the *sufficient* enforcement: a job present in
YAML but absent from branch-protection required checks would let a red build merge
with this test still green. Word the test's docstring accordingly, and add a
lightweight follow-up (not blocking 0006): a scripted `gh api
repos/{owner}/{repo}/branches/main/protection` audit (runbook-driven or a periodic
CI job) that asserts the five required-check names are actually registered — the only
thing that closes the gap between "jobs exist" and "jobs gate".

Confirm `tests/unit/tasks/test_mise_wiring.py` (introduced in Phase 1, extended
each phase) now asserts the **complete** enumerated arrays: `check` =
`[..., cli:check, deny:check, pup:check]`; `default` = `[..., test, build:cli,
deny:check, pup:check]` with **no** `coverage:check` edge (coverage rides inside
`test`); `cli:check` = `[format:cli:check, lint:cli:check]` (test-free); `test:unit`
= `[test:unit:tasks, test:unit:cli]` (so the cli unit tests — carrying coverage —
reach `test` but never `check`); that **no** `coverage:check`/`coverage:cli:check`
task exists; that `build:cli` is in `default` but **absent** from `check`/`cli:check`
(release build in the heavy default only, never the fast read-only checks); and
that `pup:check` **`depends` on `deps:install:pup`** (the check provisions its
non-`[tools]` nightly + cargo-pup, mirroring the Python-check ↔
`deps:install:python` convention). Together with `test_workflows.py`, these two
parsers are the automated backstop for the entire mise + CI wiring.

#### 3. Branch protection — durable runbook (manual step, documented)

Capture the procedure as a durable runbook in a **new `CONTRIBUTING.md`** (no
CONTRIBUTING exists today, and `tasks/README.md` is scoped to the task-tree
*shape*, an awkward home for a repo-admin runbook whose audience differs). Cover:
the repo Settings → Branches path; that the required-check **name must match the
YAML job display name exactly** (`Check cli`, `Check supply chain`, `Check
architecture` — confirm against the final YAML); the gotcha that a **matrix** job
surfaces one required check **per leg**, so `build-cli` contributes *two* names —
`Build cli (ubuntu-latest)` and `Build cli (macos-latest)` — and **both** must be
added or the darwin (or musl) build is not actually gating; and the gotcha that a
job only appears as a selectable required check **after it has run at least once**.
Then add all the names (the three single-leg checks plus the two `build-cli` legs)
to the protected-branch required checks. **Cross-link the new `CONTRIBUTING.md`
from CLAUDE.md** (a one-line pointer in the "Build, test, and check" area) so the
runbook is discoverable from the canonical entry point rather than orphaned in a
file a contributor may not know exists.

### Success Criteria

#### Automated Verification

- [ ] `mise run check` exits 0 and includes `cli:check`, `deny:check`,
      `pup:check`
- [ ] `mise run` (bare default) exits 0 end-to-end including all Rust checks, the
      cli tests with coverage, and the `build:cli` host-native release build
- [ ] Full task suite passes: `uv run pytest tests/unit/tasks -v`
- [ ] `test_mise_wiring.py` + `test_workflows.py` assert the complete final
      `check`/`default`/`cli:check` arrays and the Rust CI jobs — `check-cli`,
      `build-cli` (matrix, both legs), `check-supply-chain`, `check-architecture`
      (+ their `needs:` edges) — the automated backstop for the whole wiring
- [ ] `mise run build-system:check` passes (docs/workflow + SHA-pin changes lint
      clean; `actionlint` green)

#### Manual Verification

- [ ] Branch-protection required checks updated with the new job names (including
      **both** `build-cli` matrix legs); a failing Rust check, build, or test makes
      a PR non-mergeable.
- [ ] `CLAUDE.md` and `tasks/README.md` accurately describe the Rust components.

---

## Testing Strategy

### Unit Tests

- Each new invoke task gets command-string + `Exit`-on-failure tests in the
  existing **family-named** file (`TestFormatCli`/`TestLintCli` in
  `test_format.py`/`test_lint.py`; new family files `test_test.py`,
  `test_build.py`, `test_deny.py`, `test_pup.py`), not per-leaf files. There is no
  `test_coverage.py` — coverage has no task of its own; its two command forms are
  the `test:unit:cli` toggle branches asserted in `test_test.py`. Fully-annotated
  fixtures (`mocker: MockerFixture`); no relaxed profile. Assert **both** `check`
  and `fix` variants where they exist.
- Constants-as-source-of-truth: tests assert command strings against
  `tasks/shared/rust.py` (`CLI_CRATE`, `PUP_NIGHTLY`, `PUP_VERSION`), so a
  mise.toml/task-body drift cannot pass green.
- Toggle assertions: `test:unit:cli` builds the instrumented
  `cargo llvm-cov nextest … --summary-only` by default and the plain
  `cargo nextest run` under `LUMINOSITY_COVERAGE=off` (both branches pinned;
  default `"on"`), with a negative assertion that the instrumented form carries no
  `--fail-under`; `pup:check` honours the `PUP_MODE` deny/warn toggle
  (env-overridable; `"warn"` logs); the `deps:install:pup` composition includes the
  exact component set.
- **Wiring test** (`test_mise_wiring.py`, `tomllib`-parsed): the `depends`/
  aggregate edges live only in `mise.toml`, which no other test reads — this
  module asserts the enumerated `check`/`default`/`cli:check`/`test:unit` arrays
  and that `pup:check` `depends` on `deps:install:pup`, no
  `coverage:check`/`coverage:cli:check` task exists, and `test:unit:cli` is in
  `test:unit` but **not** in `cli:check`/`check` (the test-free-`check` invariant).
  Introduced in Phase 1,
  extended each phase.
- The bootstrap `cli` crate gets one trivial Rust unit test, written test-first,
  so nextest and llvm-cov exercise real code. (Meaningful Rust coverage — the
  `version` subcommand's behaviour and error paths — is owned by 0007, which
  replaces this throwaway test.)

### Integration Tests

- **Ban-violation regression** (Phase 3): `cargo deny check bans` against a
  throwaway native-tls manifest must exit non-zero — automating the ADR-0010
  invariant rather than leaving it a manual step.
- **Release build / static-link guard** (Phase 1): `build:cli` exercises the
  static-link and cross-target invariants pre-merge across the `build-cli` matrix —
  the two musl triples on the ubuntu leg, the two darwin triples on the macOS leg —
  so all four shipped triples are built before merge.
- **CI-wiring guard** (Phase 5): `test_workflows.py` asserts the Rust jobs
  (`check-cli`, `build-cli` incl. its matrix, `check-supply-chain`,
  `check-architecture`) exist, run the right target, and are in the release
  `needs:` lists.
- The end-to-end gate is `mise run check` → 0 and `mise run` → 0 with the Rust
  component present (the two acceptance criteria). CI runs on both `ubuntu-latest`
  and `macos-latest`: the cli unit tests **with coverage** run on both, and the
  `build-cli` matrix builds each OS's native triple pair. Nothing is OS-restricted
  any more — there is no ubuntu-only carve-out left (the prior cross-OS contract is
  retired).

### Manual Testing Steps

1. On a branch, break `cli` formatting → confirm `check-cli` red.
2. Introduce a clippy `-D warnings` violation → confirm `check-cli` red.
3. Introduce a darwin-only build break (e.g. a `#[cfg(target_os = "macos")]`
   compile error) → confirm `build-cli (macos-latest)` red while
   `build-cli (ubuntu-latest)` stays green (verifies the macOS leg actually gates).
4. Add a `native-tls`/`openssl` dependency → confirm `check-supply-chain` red
   (also covered by the automated ban-violation test).
5. (After 0007) add a domain→adapter module import → confirm
   `check-architecture` red.
6. Confirm the product build stays on stable while only `pup:check` uses nightly.

## Performance Considerations

- CI Rust jobs are slow without caching; every Rust job uses
  `Swatinem/rust-cache` (SHA-pinned) over the cargo target dir (mise-action's
  cache covers only mise tool binaries). The nightly lane caches separately
  (distinct toolchain key) **and** caches the built `cargo-pup` binary keyed on
  `(PUP_NIGHTLY, PUP_VERSION, OS)`, so the multi-minute `cargo install` runs only
  on a cache miss.
- The `build-cli` matrix adds a per-PR **macOS** runner leg (release-building the
  two darwin triples). GitHub bills macOS runners at ~10× the Linux per-minute
  rate, so this is the most expensive new CI minute — accepted to close the
  "darwin is release-only" gap (a darwin build break would otherwise reach `main`
  before any gate caught it). macOS is already in the PR path (`test-unit` matrix),
  so this is an incremental job, not a new platform; the per-OS `rust-cache` keeps
  warm builds short, and each leg builds only its native pair (no cross-linking).
- The cli tests run **once** per invocation: coverage is folded into
  `test:unit:cli` (one instrumented `cargo llvm-cov nextest` pass), so there is no
  plain-then-instrumented double run. The read-only `check` runs **no** cli tests
  at all, keeping it fast. The instrumented build is heavier than a plain
  `cargo nextest run`; the fast inner loops are `mise run cli:check` (format +
  lint) and `LUMINOSITY_COVERAGE=off mise run test:unit:cli` (plain tests, no
  instrumentation) — run independently.
- `default` runs `format:fix` (which mutates files) alongside read-only Rust
  checks (`lint:cli:check` via `lint:check`), the `test` roll-up, and now the
  `build:cli` host-native release build. This is the same shape the existing
  `default` already relies on for Python (`format:fix` + `lint:check` + `test`), so
  it inherits mise's established `depends` execution behaviour — no new ordering
  guarantee is introduced, and a future mise change to `depends` parallelism would
  affect the existing Python tasks identically.
- Folding `build:cli` into `default` makes a local `mise run` heavier — it adds a
  `--release` build of the host's two triples (plus the one-time
  `deps:install:rust-targets` provisioning). This is consistent with `default`'s
  documented role as the heavy full-CI-mirror ("compiles Rust several times"); the
  `rust-cache`-less local `target/` dir still incrementally caches between runs, so
  only the first `mise run` pays the full release-build cost. The fast inner loop
  remains `mise run check` (no build) and the per-task leaves.

## Migration Notes

- `tasks/shared/paths.py` keeps `cli/Cargo.toml` as the version-bearing crate so
  `tasks/version.py` coherence (`plugin.json` / `Cargo.toml` / `checksums.json`)
  and the release pipeline keep working unchanged. The new root `Cargo.toml` is a
  pure workspace manifest with no `[package]`. If 0007/0008 later centralises the
  version, revisit `paths.py` then — out of scope here.
- The bootstrap `cli` body is throwaway: 0007 replaces `src/main.rs` /
  `src/lib.rs` with the hexagonal `version` subcommand and adds `kernel`. The
  task wiring is structured so a new crate adds one `kernel:check` roll-up + its
  family edges (and a `test:unit:kernel` leaf), nothing more — a **library** crate
  like `kernel` needs no `build:kernel`, since only binary-producing crates get a
  release `build:<crate>` task (the binary is what must link statically per triple).
- **`build:cli` is per-OS-native, diverging from ADR-0002's `cargo-zigbuild`
  -from-one-host release mechanism (deliberate; ADR amendment owed).** Two
  follow-ups must travel with this: (1) **0008's release build must adopt the same
  per-OS-native matrix model** (real ubuntu + macOS runners) rather than zigbuild,
  so the PR-time `build:cli` guard validates the same toolchain that ships — if 0008
  instead uses zigbuild, the guard and the release drift and the guard's premise is
  void; and (2) **raise a superseding/amending ADR for ADR-0002** before 0008
  implements the release build, ratifying host-native cross-target builds (and
  whether the macОС SDK / musl cross-linker provisioning is staged in CI). Until
  that ADR lands this is a recorded divergence, not silent drift. 0008 must also
  share `build:cli`'s target/flag derivation (`host_targets()`, `--bin`,
  `--release`) so the guard and the shipping build cannot diverge in flags.

## References

- Original work item: `meta/work/0006-establish-rust-toolchain-guard-rails-in-mise-and-ci.md`
- Paired scaffold story: `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md`
- Research: `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — commits the
  release to `cargo-zigbuild` (all four triples from one host). **`build:cli` and
  the planned 0008 release build diverge from this (per-OS-native matrix); a
  superseding/amending ADR is owed before 0008** (see Phase 1 §6 + Migration Notes).
- `meta/decisions/ADR-0004-three-toolchain-split.md`
- `meta/decisions/ADR-0006-mise-invoke-task-runner.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- Cross-crate ban-list follow-ups: story 0009 (config), work item 0012 (later crates)
- Task-pattern exemplars: `tasks/format/build_system.py:6`, `tasks/lint/scripts.py:17`,
  `tasks/types/build_system.py:6`, `tasks/lint/workflows.py:14`
- Aggregation + CI: `mise.toml:118-140`, `.github/workflows/main.yml:59-93`
- cargo-pup nightly mechanism (web research, 2026-06-27):
  - [mise Rust docs](https://mise.jdx.dev/lang/rust.html) — mise drives rustup,
    sets `RUSTUP_TOOLCHAIN`; no `rust-nightly` short-name.
  - [rustup overrides](https://rust-lang.github.io/rustup/overrides.html) —
    `+toolchain` outranks `RUSTUP_TOOLCHAIN` (the load-bearing fact).
  - [DataDog/cargo-pup](https://github.com/DataDog/cargo-pup) +
    [`rust-toolchain.toml` @ v0.1.8](https://raw.githubusercontent.com/DataDog/cargo-pup/v0.1.8/rust-toolchain.toml)
    — confirms `0.1.8` / `nightly-2026-01-22` / components / `pup.ron` / `.pup/`.
