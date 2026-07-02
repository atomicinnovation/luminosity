---
type: codebase-research
id: "2026-06-28-0007-scaffold-hexagonal-rust-workspace"
title: "Research: Scaffolding the Hexagonal Rust Workspace with a version Subcommand (work item 0007)"
date: "2026-06-28T22:46:40+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0007"
parent: "work-item:0007"
relates_to: ["codebase-research:2026-06-27-0006-rust-toolchain-guard-rails"]
topic: "Scaffolding the hexagonal Rust workspace (cli + kernel) and a version subcommand on the 0006 toolchain"
tags: [research, codebase, rust, cli, hexagonal, cargo-pup, mise, version-coherence, scaffold]
revision: "7f90e3a81e1df517b2be9e5391c4d85252f985d4"
repository: "luminosity"
last_updated: "2026-06-28T22:46:40+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Scaffolding the Hexagonal Rust Workspace with a version Subcommand (work item 0007)

**Date**: 2026-06-28T22:46:40+00:00
**Author**: Toby Clemson
**Git Commit**: 7f90e3a81e1df517b2be9e5391c4d85252f985d4 (working copy; not yet pushed to any remote)
**Branch**: detached working copy (jj-colocated)
**Repository**: luminosity (atomicinnovation/luminosity)

## Research Question

What does the codebase look like today, and what exactly must change, to implement
work item 0007 — *Scaffold the Hexagonal Rust Workspace with a version Subcommand*?
The story requires: a two-crate workspace (`cli` + `kernel`); a genuine hexagon for
`version` (inbound port → core → outbound port → build-metadata adapter →
composition root, all as modules inside `cli`); a `luminosity version` subcommand
built test-first that prints version + commit SHA + build date + target triple;
cargo-pup proven live as the sole inward-direction enforcer; build metadata reaching
the core through an outbound port exercised against an in-memory fake; the crate
version as single source of truth; and the new crates wired into the `mise` task tree
so `mise run check` and bare `mise run` both exit 0.

## Summary

The Rust footprint today is a **deliberate bootstrap**: one crate (`cli`, package
name `luminosity`, version `0.1.0-pre.0`) with exactly two source files
(`cli/src/main.rs` + `cli/src/lib.rs`), zero dependencies, and a throwaway
`describe_release(bool)` function whose own doc comment says story 0007 replaces it.
All architectural-enforcement scaffolding exists but is **inert**: `pup.ron` is
`( lints: [] )`, and `deny.toml`'s cross-crate `skip`/`skip-tree` ban-lists are empty
placeholders. Everything the story needs is greenfield — no `clap`, no `build.rs`, no
`vergen`, no `env!`/`CARGO_PKG_VERSION`, no traits, no fakes, no
`[workspace.dependencies]` table exist yet.

The most important structural discovery for wiring: **the Rust checks are
workspace-scoped, not per-crate.** `cargo fmt --all`, `cargo clippy --workspace`,
`cargo deny`, and `cargo pup` already cover any new workspace member with no task
change. The *only* place a crate name is enumerated for tasks is the scalar
`CLI_CRATE = "luminosity"` in `tasks/shared/rust.py:3`, consumed solely by
`test:unit:cli` (`-p luminosity`) and `build:cli` (`--bin luminosity`). So adding
`kernel` as a *library* member needs only two lines (add it to `members`, give it a
`Cargo.toml` opting into workspace lints) for the workspace-wide lanes to cover it.
Whether the story's "add a `<crate>:check` per workspace member" requirement means a
distinct `kernel:check` roll-up (with its own mise tasks + invoke modules + pinned
`test_mise_wiring.py` array updates) or is already satisfied by the workspace-wide
`cli:check` is the **one genuine open interpretation** — see Open Questions.

Three facts will bite if not handled: (1) cargo-pup's module-import rule RON syntax
does **not** appear anywhere in the repo — only a `Struct/MustBePrivate` probe — so
the actual `restrict_imports`/layering variant must come from cargo-pup v0.1.8 itself
(`cargo +nightly-2026-01-22 pup generate-config` / `print-modules`); (2) the
version SSOT is contested — `tasks/version.py read()` currently reads from
`plugin.json`, while the story wants the *crate* version (`CARGO_PKG_VERSION`) as
SSOT, and `tasks/shared/paths.py` hard-codes `cli/Cargo.toml` as the version-bearing
file; (3) the active lint wall (`warnings = "deny"`, clippy pedantic+nursery,
`unwrap_used`/`expect_used`/`panic`/`todo`/`unimplemented` all warn) means the new
code and its tests must avoid `.unwrap()`/`.expect()`/`panic!` from the first commit.

## Detailed Findings

### Area 1 — Current Rust workspace bootstrap (what exists today)

**Root `Cargo.toml`** (`Cargo.toml:1-20`) — versionless workspace, resolver 2,
`members = ["cli"]` (line 3). It centralizes **lint levels only**, not dependency
versions:
- `[workspace.lints.rust] warnings = "deny"` (line 7) — warnings are hard errors.
- `[workspace.lints.clippy]` (lines 9-20): `pedantic` + `nursery` at `warn`
  (priority -1); `unwrap_used`, `expect_used`, `panic`, `dbg_macro`, `todo`,
  `unimplemented` all `warn`; `module_name_repetitions` and `must_use_candidate`
  `allow`.
- **No `[workspace.dependencies]` table** and **no `[profile.*]`**. If `clap` (and
  any build-metadata crate) should be version-pinned centrally via
  `dep = { workspace = true }`, that table must be created — it is not an
  established pattern yet.

**The `cli` crate**:
- `cli/Cargo.toml` — package `name = "luminosity"` (line 4), `version = "0.1.0-pre.0"`
  (line 5, comment: seeded from `plugin.json`, bumps owned by `tasks/version.py`),
  `edition = "2021"`, `license = "MIT"`. Opts into workspace lints via
  `[lints] workspace = true` (lines 9-10). Binary declared explicitly:
  `[[bin]] name = "luminosity" path = "src/main.rs"` (lines 12-14). **No
  `[dependencies]` table at all** — zero deps today.
- `cli/src/main.rs` (5 lines) — `use luminosity::describe_release;` then
  `println!("luminosity {}", describe_release(true));`. Always prints
  `luminosity prerelease`.
- `cli/src/lib.rs` (28 lines) — crate doc comment (lines 1-3) says the hexagonal
  `version` subcommand replaces this in story 0007. Single fn (lines 5-13):
  `#[must_use] pub const fn describe_release(prerelease: bool) -> &'static str`
  returning `"prerelease"`/`"stable"` (branch exists so coverage has something to
  exercise). Inline `#[cfg(test)] mod tests` (lines 15-28) with two tests.

**Inert enforcement config**:
- `pup.ron` (`pup.ron:1-7`) — `( lints: [] )`, comment says story 0007 adds the
  inward-direction `restrict_imports` module rules once the kernel/cli split lands.
- `deny.toml` — `[graph]` targets (lines 8-14) list the four release triples plus
  host/CI dev triples. `[licenses]` allow-list (lines 27-44) pre-seeded for the
  ADR-0010 stack (so 0007 isn't blocked). `[bans]` (lines 46-63): native-tls
  ban-list **active** (`native-tls`/`openssl`/`openssl-sys` denied, lines 54-58);
  architectural `skip = []` / `skip-tree = []` (lines 62-63) explicitly **"Inert in
  the single-crate bootstrap,"** load-bearing only after the workspace splits.
- `clippy.toml` (`clippy.toml:4`) — only `msrv = "1.90.0"` (hand-synced mirror of
  the `mise.toml` rust pin). Lint *levels* live in `Cargo.toml`, not here.
- `rustfmt.toml` — `max_width = 80` (line 3), `edition = "2021"` (line 4).

### Area 2 — What does NOT exist yet (all greenfield for 0007)

Confirmed absent across all `.rs` files and manifests:
- **`clap`** — no dependency, no derive structs. Every `clap` mention is in `meta/`
  docs and one `deny.toml:29` comment. Adding it creates the first `[dependencies]`
  table in `cli/Cargo.toml`.
- **`build.rs`** anywhere; **`vergen`**; **`env!` / `option_env!` /
  `CARGO_PKG_VERSION`** in any source. The build-metadata injection mechanism is
  entirely to-be-built (story `0007:140` leaves build-script-vs-vergen open).
- **traits / `impl ... for` / `dyn` / ports-adapters / mock/fake/stub** — none.
  The first trait (the ports), the first adapter, and the first in-test fake are all
  created by this story.
- **`cli/tests/`** integration-test directory — does not exist; black-box CLI tests
  (if any) are created from scratch.
- **`[workspace.dependencies]`** — does not exist.

**Existing test convention to mirror** (`cli/src/lib.rs:15-28`): inline
`#[cfg(test)] mod tests`, `use super::<item>;` (not glob), full-sentence snake_case
test names with no `test_` prefix (`describes_a_stable_release`), bare `assert_eq!`
(no custom matchers / `pretty_assertions`). The unit test of the core against the
in-memory fake (acceptance criterion 4) naturally fits this inline style; a
black-box test of the compiled `version` output (criterion 5, SHA == build commit,
RFC-3339 date within the build window) more naturally wants a `cli/tests/` integration
test driving the binary.

### Area 3 — cargo-pup: the sole inward-direction enforcer

cargo-pup runs on a **pinned nightly** lane separate from the stable product build.
- Pins (`tasks/shared/rust.py:6-7`): `PUP_NIGHTLY = "nightly-2026-01-22"`,
  `PUP_VERSION = "0.1.8"` (bump as a matched pair).
- `pup_mode()` (`tasks/shared/rust.py:27-48`) reads `LUMINOSITY_PUP_MODE` at call
  time, default `"deny"` (blocking); `"warn"` downgrades a *findings* failure to
  advisory; unrecognised values fail closed to `"deny"`. (This covers a findings
  failure, not a toolchain-unavailable failure.)
- `pup:check` (`tasks/pup.py:7-24`) `cd`s to repo root and runs
  `cargo +{PUP_NIGHTLY} pup` with `warn=True`; on non-zero exit it either warns and
  returns (warn mode) or `raise Exit(..., code=1)` (deny mode). It passes **no
  explicit config path** — cargo-pup reads `pup.ron` from CWD (repo root), so the new
  rules must live in the **root `pup.ron`**.
- Provisioning: `deps:install:pup` (`tasks/deps.py:49-101`) installs the nightly
  (`rustup toolchain install` with `rustc-dev`/`rust-src`/`llvm-tools-preview`), then
  `cargo +{PUP_NIGHTLY} install cargo_pup --version {PUP_VERSION} --locked` if absent,
  then a preflight. `pup:check` `depends` on it (`mise.toml:139-142`).
- Wiring: `pup:check` is in both `check` (`mise.toml:199`) and `default`
  (`mise.toml:203`).

**RON syntax gap (important).** The only concrete rule example in the repo is a test
probe (`tests/integration/pup/test_pup_rules.py:47-59`):
```ron
( lints: [ Struct(( name: "force_failure", matches: Name(".*"),
                    rules: [ MustBePrivate(Error) ] )) ] )
```
This shows the top-level schema (`( lints: [ <Variant>(( ... )) ] )`) but is the
`Struct` lint, **not** the module-import/layering variant the story needs. The
`restrict_imports` / module-direction variant's exact field names appear **nowhere**
in this repo and must be obtained from cargo-pup v0.1.8 directly —
`cargo +nightly-2026-01-22 pup generate-config`, `pup print-modules`,
`pup print-traits` are the discovery subcommands.

**Existing nets that must stay green / be extended** once real rules land:
- `tests/integration/pup/test_pup_rules.py` —
  `test_module_rule_violation_fails_the_check` (probe-based, proves the lane has
  teeth) and `test_repo_pup_ron_actually_loads` (runs `pup print-modules` against the
  real `pup.ron`, asserts exit 0 — will fail loudly if the new RON doesn't parse).
  This integration suite (`test:integration:pup`) is deliberately **not** in the
  `test:integration` roll-up (`mise.toml:66-69`); it runs in CI's `check-architecture`
  job.
- Unit nets: `tests/unit/tasks/test_pup.py` (exact command, deny-raises,
  warn-returns, mode normalisation) and `test_deps.py:45-93` (install behaviour).

The story's acceptance criterion — *introduce a deliberate inward violation (e.g.
core `use`s the outbound adapter module), cargo-pup rejects it, removing it goes
green* — is exactly the kind of behavioural proof the existing probe test models. A
parallel integration test asserting that a real domain→adapter import is rejected
would extend `test_pup_rules.py` in keeping with the established pattern.

### Area 4 — mise task tree and how to add a crate

**Key discovery: Rust checks are workspace-scoped.** The `cli` in task names is
historical; the commands already cover every member:
- `format:cli:check`/`:fix` → `cargo fmt --all [--check]` (`tasks/format/cli.py`).
- `lint:cli:check`/`:fix` → `cargo clippy --workspace --all-targets --all-features
  -- -D warnings` [+ `--fix --allow-dirty --allow-staged`] (`tasks/lint/cli.py`).
- `deny:check` → `cargo deny check ...` (workspace graph). `pup:check` →
  `cargo +nightly pup` (workspace). Neither is crate-scoped.

**The only crate-name enumeration** is `CLI_CRATE = "luminosity"`
(`tasks/shared/rust.py:3`), consumed by:
- `test:unit:cli` (`tasks/test/cli.py`) →
  `cargo llvm-cov nextest -p {CLI_CRATE} --summary-only` (or
  `cargo nextest run -p {CLI_CRATE}` when `coverage_enabled()` is false via
  `LUMINOSITY_COVERAGE` ∈ off/false/0/no).
- `build:cli` (`tasks/build.py:68-86`) → iterates `host_targets(...)` and runs
  `cargo build --release --bin {CLI_CRATE} --target {triple}`.

The four triples + host partitioning live in `tasks/shared/targets.py`
(`TARGETS` lines 3-8; `host_targets` lines 17-34).

**Roll-up composition** (`mise.toml`):
- `[tasks."cli:check"]` = `["format:cli:check", "lint:cli:check"]` (lines 126-128) —
  format+lint only, no tests/build (pinned by
  `test_mise_wiring.py:test_cli_check_folds_format_and_lint_only`).
- `check` (line 199) = `["build-system:check", "scripts:check", "cli:check",
  "deny:check", "pup:check"]`.
- `default` (lines 201-203) = `["format:fix", "lint:check", "types:check", "test",
  "build:cli", "deny:check", "pup:check"]`.
- `test:unit` (line 64) = `["test:unit:tasks", "test:unit:cli"]`.

**Namespace wiring**: mise `run = "invoke <module>.<task>"` strings resolve through
invoke `Collection`s assembled in `tasks/__init__.py` (e.g. it explicitly adds
`format_.cli` and `lint.cli`); a new per-crate `format/<crate>.py` / `lint/<crate>.py`
module requires a matching `add_collection` line.

**To add `kernel`** — two paths:
- *Minimal (library-only `kernel`, covered by workspace-wide lanes):* add `"kernel"`
  to `members` (`Cargo.toml:3`) and create `kernel/Cargo.toml` with
  `[lints] workspace = true`. `cargo fmt --all`, `cargo clippy --workspace`,
  `cargo deny`, `cargo pup` then cover it with **zero** mise/invoke changes. A
  `kernel` with tests also wants a `test:unit:kernel` (a `KERNEL_CRATE` constant +
  `tasks/test/kernel.py` + thread into `test:unit`).
- *Distinct `kernel:check` roll-up (if the story's wording is read literally):* add
  `format:kernel:*` / `lint:kernel:*` leaves + a `[tasks."kernel:check"]` roll-up,
  register invoke modules, thread into `check`/`format:*`/`lint:*`, and update the
  **exact-array assertions** in `test_mise_wiring.py`
  (`TestFinalEnumeratedArrays`, lines 171-195) plus add a kernel analogue of
  `TestCliCheckWiring`. Given the workspace-scoped design this is largely ceremonial
  for a pure library; see Open Questions.

**Tests that pin the wiring and will need updating if the arrays change**:
`tests/unit/tasks/test_mise_wiring.py` — `test_cli_check_folds_format_and_lint_only`
(35-39), `test_check_array` (171-178), `test_default_array` (180-189),
`test_test_unit_array` (191-195), `test_rustfmt_edition_matches_cli_crate_edition`
(210-213). New Rust task modules "should ship with parallel unit tests asserting the
exact command string built" (the established convention).

**CI** (`.github/workflows/main.yml`): `check-cli` (line 127, `mise run cli:check`,
workspace-wide), `build-cli` matrix (lines 129-170, all four triples),
`check-architecture` (line 195: `pup:check` + `test:integration:pup`). Branch-
protection **required checks are registered manually** (CONTRIBUTING.md runbook) — a
*new* CI job name needs manual registration; reusing existing jobs does not.

### Area 5 — Version coherence and the SSOT contention

`tasks/version.py` propagates one version into three files:
- **Write path** (`write()`, lines 71-80) stamps all three in lockstep:
  `_render_plugin_json` → `plugin.json`, `_render_cargo_toml` → `cli/Cargo.toml`
  (`data["package"]["version"]`), `_render_checksums_version` → `checksums.json`.
  `bump()` (83-111) reads → bumps semver → `write()`.
- **Read path** (`read()`, lines 61-68) reads the canonical value from
  **`plugin.json`** (`read_plugin_metadata()`), *not* from `cli/Cargo.toml`.
- Paths (`tasks/shared/paths.py`): `CARGO_TOML = cli/Cargo.toml`,
  `CHECKSUMS = cli/bin/checksums.json`, `PLUGIN_JSON = .claude-plugin/plugin.json`.
- mise tasks: `version:read`/`:write`/`:bump` (lines 205-215). **No `version:check`**
  task and **no `test_version.py`** exist — coherence is enforced only by always
  mutating through `write`/`bump`, not by an assertion.

**Current values are coherent today** — `plugin.json:3` and `cli/Cargo.toml:5` both
`0.1.0-pre.0`. **`checksums.json` does not exist yet** (resolves to
`cli/bin/checksums.json`, which is empty); only a test fixture
`tests/unit/tasks/fixtures/checksums.example.json` (version `1.20.0`) exists. So
`_render_checksums_version` would fail (`CHECKSUMS.read_text()`) if invoked before the
manifest exists — not a concern for `version` *output*, but relevant context.

**The SSOT contention (the one real friction for this story):** the story says the
*crate* version is the single source of truth (`0007:127`), and a built binary learns
its own version idiomatically via `env!("CARGO_PKG_VERSION")` — which resolves from
`cli/Cargo.toml`. But `version.py read()` currently treats `plugin.json` as the value
it reads. These don't contradict at runtime (the `version` binary reads the crate
version; `version.py` keeps `plugin.json`/`Cargo.toml` mirrored), but the *intent*
("crate version is SSOT") and the *tooling* ("read() reads plugin.json") point at
different files. The 0006 research already flagged this: `paths.py` hard-coding
`cli/Cargo.toml` "predates the multi-crate workspace decision and may need
revisiting." The story can either consume `CARGO_PKG_VERSION` (idiomatic, makes the
crate the de-facto SSOT regardless of `version.py`'s read direction) and leave
`version.py` untouched, or additionally realign `version.py read()` — the latter is
arguably out of 0007's scope.

### Area 6 — Architecture rules from the ADRs (the hexagon to build)

**ADR-0009** (hexagonal ports-and-adapters):
- The inward dependency direction is *the* load-bearing rule, enforced mechanically
  (lines 95-97). Core "depends on no infrastructure" and "depends on neither inbound
  nor outbound adapters" (lines 77-89).
- Terminology to use in the code: **inbound/driving ports** (operations the core
  offers callers) and **outbound/driven ports** (capabilities the core requires) —
  both are **traits living with the core**, not the adapters (lines 78-81, 155-156).
  The **CLI is the primary inbound adapter** — "argument parsing and presentation
  only, delegating immediately into the core … no business logic in the command
  layer" (lines 82-85). **Outbound adapters** implement outbound ports against
  concrete tech (lines 87-89). **Composition root** binds concrete adapters to ports
  "so the core is constructed against traits and never against concrete
  infrastructure — which is also what lets it be tested with in-memory fakes"
  (lines 91-93) — this is the exact justification for acceptance criterion 4.
- Enforcement granularity (lines 99-108): crate boundaries (Cargo graph +
  cargo-deny ban-lists) enforce *between* crates; **cargo-pup** enforces *inside* a
  crate at module granularity. "Because each subdomain begins as a single crate with
  its layers as modules, crate boundaries are initially inert and **cargo-pup is the
  sole enforcer** of the inward rule" — directly mandating the story's "pup is sole
  enforcer" framing. The spike's proposed CI grep tripwire was **deliberately
  omitted** (lines 159-161) — do not add it.
- The indirection overhead for trivial commands is acknowledged and accepted
  (lines 141-142) — the story accepts it deliberately.

**ADR-0010** (binary axis):
- Subdomain-first workspace; supporting crates (lines 94-104): **`kernel`** =
  "deliberately dependency-light crate for genuinely cross-cutting concerns (error
  taxonomy, the config-access and dispatch/launcher contracts, logging); everything
  links it, so a dependency tail is resisted" — there is no explicit forbidden list
  beyond "resist anything with a dependency tail." **`cli`** = the `luminosity`
  launcher; depends on `kernel` (and `config` for the built-in `config` command),
  **never on a subdomain**.
- `version` and `config` are **built-in subcommands compiled into `luminosity`**;
  external dispatch is purely the growth mechanism (lines 114-115, 182-184). So
  `version` is an in-process clap subcommand inside `cli` — confirming the story's
  "version hexagon lives as modules within `cli`, not its own crate, not in `kernel`."
- External-subcommand dispatch (clap `#[command(external_subcommand)]
  External(Vec<OsString>)`, Unix `exec`-only) is described (lines 109-124) but its
  *implementation* is relocated to story 0008 (per the work items / git history, not
  the ADR body). ADR-0010 still notes (lines 189-190) "clap's derive enabling
  external dispatch … is to be confirmed on the pinned clap version when the scaffold
  (0007) is built" — but story 0007's Drafting Notes explicitly move that
  confirmation to 0008.

### Area 7 — Distribution / triples / spike constraints

**ADR-0002**: the four supported targets are `darwin-arm64`, `darwin-x64`,
`linux-arm64`, `linux-x64` (Linux via musl) — the exact Rust triples (from spike
`0002:265-267`, matching `deny.toml:8-14`) are:
- `aarch64-apple-darwin`, `x86_64-apple-darwin`,
  `aarch64-unknown-linux-musl`, `x86_64-unknown-linux-musl`.
The `version` output's target triple must be one of these four. ADR-0002 records the
version-coherence obligation across `plugin.json` / `cli/Cargo.toml` / the release
manifest (lines 96-100, 155-156). It does **not** specify the `version` build-metadata
fields (SHA/date) or the injection mechanism — that is 0007's to decide.

**Spike 0002** (done) decided: subdomain-first hexagonal-within workspace; reference
model is **howtocodeit/hexarch — a single crate with `domain` / `inbound` / `outbound`
modules, ports as traits** (lines 154-155, 182). `version`/`config` are built-in
in-process clap subcommands (lines 197-200). It does **not** decide vergen-vs-build-
script (no mention of either) — left to 0007. Guiding principle: start single-crate,
"splitting later is cheap, over-splitting early is not" (line 155) — i.e. keep the
scaffold minimal (the story's `cli` + `kernel` only).

## Code References

- `Cargo.toml:3` — `members = ["cli"]`; add `"kernel"` here.
- `Cargo.toml:7-20` — workspace lint levels the new code must satisfy.
- `cli/Cargo.toml:4-14` — package name/version + explicit `[[bin]]`; first
  `[dependencies]` table (clap, build-metadata) goes here.
- `cli/src/lib.rs:1-28` — throwaway `describe_release` + the inline test convention to
  mirror; doc comment names story 0007 as its replacer.
- `cli/src/main.rs:1-5` — current binary entry point to be restructured into the CLI
  inbound adapter + composition root.
- `pup.ron:1-7` — empty `( lints: [] )`; add inward-direction module rules here (root,
  CWD-resolved).
- `tests/integration/pup/test_pup_rules.py:47-59,90-102` — the only RON example
  (probe) + the load/teeth regression tests to extend.
- `tasks/shared/rust.py:3` — `CLI_CRATE` (only crate-name enumeration); `:6-7` pup
  pins; `:13-24` coverage gate; `:27-48` `pup_mode()`.
- `tasks/pup.py:7-24` — `pup:check` body (no explicit config path).
- `tasks/deps.py:49-101` — `deps:install:pup`.
- `tasks/format/cli.py`, `tasks/lint/cli.py` — `--all` / `--workspace` (cover new
  members automatically).
- `tasks/test/cli.py:7-24`, `tasks/build.py:68-86`, `tasks/shared/targets.py:3-34` —
  the only `-p`/`--bin`/triple-scoped tasks.
- `mise.toml:126-128` (`cli:check`), `:199` (`check`), `:201-203` (`default`),
  `:64` (`test:unit`), `:205-215` (`version:*`).
- `tasks/version.py:61-80` (read from plugin.json / write all three),
  `tasks/shared/paths.py:7-9` (path constants).
- `.claude-plugin/plugin.json:3` & `cli/Cargo.toml:5` — both `0.1.0-pre.0` (coherent).
- `tests/unit/tasks/test_mise_wiring.py:35-39,171-213` — pinned-array assertions to
  update if roll-ups change.

## Architecture Insights

- **Workspace-scoped checks are the load-bearing convenience.** Because format/lint/
  deny/pup all run `--all`/`--workspace`, the cost of adding a *library* crate is
  almost nothing; the per-crate ceremony only matters for crates that ship a binary
  or need isolated test/coverage runs. This strongly suggests the minimal `kernel`
  path (members + Cargo.toml) unless the story's "`<crate>:check` per member" wording
  is taken literally.
- **The hexagon is modules-in-one-crate, by design.** ADR-0009/0010 and the spike all
  converge on the hexarch single-crate-with-`domain`/`inbound`/`outbound`-modules
  model. The `version` hexagon lives entirely inside `cli`; `kernel` holds only the
  cross-cutting error taxonomy `version` reports through. Resist the urge to split
  the hexagon's layers into crates ("over-splitting early is not [cheap]").
- **cargo-pup is the proof, not just config.** The story's "prove the enforcer live"
  criterion mirrors the existing probe-test philosophy: a rule is only trusted once a
  deliberate violation is shown to fail and its removal shown to pass. The new RON
  rules and a matching behavioural test are a pair.
- **Lint wall shapes the code from line one.** `warnings = "deny"` + clippy
  pedantic/nursery + banned `unwrap`/`expect`/`panic`/`todo`/`unimplemented` mean the
  ports, adapter, composition root, and especially the *tests* must be written
  clean — no `.unwrap()` in tests (use `assert_eq!`/`?`/explicit match as the
  existing tests do).
- **SSOT is "crate version" in spirit; `env!("CARGO_PKG_VERSION")` realises it.**
  Reading the version via the compile-time macro makes the crate the de-facto SSOT
  without touching `version.py`'s plugin.json-first read path, side-stepping the
  contention noted in Area 5.

## Historical Context

- `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md` — the
  pre-implementation research for story 0006. **Caveat:** written before 0006 landed,
  so it describes intended infrastructure ("deny.toml … must be created"); the live
  state (this document + CLAUDE.md) is authoritative where they differ. Its enduring
  value is the conventions and its **open questions explicitly handed to 0007**:
  which crates get per-crate tasks (the `core/adapters/cli` triple is stale —
  reconcile with `kernel`/`cli`); on-disk layout (`crates/<name>/` vs top-level
  `<name>/` — `paths.py` hard-codes `cli/Cargo.toml` at repo root, implying flat
  top-level crate dirs); which restriction lints to cherry-pick for pup; coverage has
  no threshold (only "runs"); and CI has no cargo caching (a new Rust job will be
  slow without `Swatinem/rust-cache`).
- `meta/decisions/ADR-0009-...md` — hexagonal ports-and-adapters + inward rule +
  cargo-pup-as-sole-enforcer (accepted).
- `meta/decisions/ADR-0010-...md` — binary axis, kernel/cli roles, version as built-in
  (accepted).
- `meta/decisions/ADR-0002-...md` — four triples, version coherence, distribution
  pipeline (accepted).
- `meta/work/0002-...md` — the spike (done): subdomain-first hexagonal-within,
  hexarch reference model, in-process clap built-ins.

## Related Research

- `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md` — direct
  predecessor; this document is its scaffold-time successor.

## Open Questions

1. **Does "`<crate>:check` per workspace member" require a distinct `kernel:check`
   roll-up?** Given workspace-scoped checks, a library `kernel` is already fully
   covered by `cli:check`/`deny:check`/`pup:check`. Literal reading → add
   `format:kernel:*`/`lint:kernel:*`/`kernel:check` + update pinned `test_mise_wiring`
   arrays (mostly ceremonial). Pragmatic reading → members+Cargo.toml suffices. The
   story author should confirm which they intend. (Recommendation: minimal path
   unless `kernel` grows tests/a binary.)
2. **Build-metadata injection: build script vs vergen?** Left open by story
   (`0007:140`) and spike. `vergen` (or `vergen-gix`) gives commit SHA / build date /
   target triple with little code but adds a build-dep + must satisfy the license
   allow-list (`deny.toml:27-44`); a hand-rolled `build.rs` emitting `cargo:rustc-env`
   has zero deps but more code. Either must inject the value consumed at the
   composition root (criterion 5). Worth a quick check of vergen's current crate +
   transitive licenses against the allow-list before choosing.
3. **clap as a dependency + central pinning.** First `[dependencies]` entry — decide
   whether to introduce `[workspace.dependencies]` now (clean for the future multi-
   crate world) or pin directly in `cli/Cargo.toml`. clap 4.x derive is the decided
   style; its license (MIT/Apache-2.0) is already allow-listed.
4. **Does 0007 realign `tasks/version.py read()` to the crate version, or just
   consume `CARGO_PKG_VERSION` at runtime?** The latter satisfies the story without
   touching version.py; the former addresses the 0006-flagged `paths.py`/SSOT tension
   but is arguably scope creep.
5. **cargo-pup module-rule RON syntax** is not in-repo — must be derived from
   `cargo +nightly-2026-01-22 pup generate-config` / `print-modules`. Confirm the
   exact variant/field names (the `restrict_imports`/module-direction lint) before
   authoring `pup.ron`, and confirm `test_repo_pup_ron_actually_loads` still passes.
6. **Where does the deliberate-violation proof live** so it doesn't ship green-but-
   broken? Options: a documented manual step in the PR, or (better, matching the
   existing probe pattern) an automated integration test that asserts a real
   domain→adapter import is rejected by pup — extending
   `tests/integration/pup/test_pup_rules.py`.
