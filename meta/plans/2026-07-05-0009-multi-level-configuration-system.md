---
type: plan
id: "2026-07-05-0009-multi-level-configuration-system"
title: "Multi-Level Configuration System — CLI Command + Thin configure Skill Implementation Plan"
date: "2026-07-05T14:10:42+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0009"
parent: "work-item:0009"
derived_from: ["codebase-research:2026-07-05-0009-multi-level-configuration-system"]
tags: [configuration, cli, skills, architecture-enforcement, hexagonal]
revision: "b9b93160449cbe428e4e759f7d0ce98f01fc10f7"
repository: "luminosity"
last_updated: "2026-07-06T00:37:42+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Multi-Level Configuration System — CLI Command + Thin configure Skill Implementation Plan

## Overview

Implement a two-level configuration system (team + personal precedence) as the
workspace's first cross-crate hexagon: a dependency-free `config` core crate
holding resolution, a `config-adapters` crate holding the serde/YAML/filesystem
concerns, a built-in `luminosity config get`/`set` command wired into the
launcher, the cargo-deny ban-list that keeps infrastructure out of the core, and
a thin `configure` skill that drives the CLI. This proves the skills-vs-CLI
division end-to-end and makes cross-crate dependency-direction enforcement live
for the first time.

## Current State Analysis

- The launcher (`cli/launcher/`) organises each built-in as a hexagon. `version`
  is the minimal template: `core.rs` holds a domain value object, an outbound
  port trait, an inbound port trait, and a generic application service
  (`cli/launcher/src/version/core.rs:6-47`); `inbound/cli.rs` holds a pure
  `render` plus a side-effecting `report` that `println!`s exactly one trailing
  newline (`cli/launcher/src/version/inbound/cli.rs:6-19`); `outbound/` holds the
  concrete adapter. `launch` is the richer variant: a rich error enum with
  `impl From<…> for kernel::Error` at the boundary
  (`cli/launcher/src/launch/core.rs:32-152`) and `&impl Trait` ports in
  `dispatch` (`cli/launcher/src/launch/mod.rs:21-37`).
- The clap command tree is centralised in one inbound adapter
  (`cli/launcher/src/launch/inbound/cli.rs:8-23`): `Cli` + `Command { Version,
  External(Vec<OsString>) }`, with `external_subcommand` catching unknown
  subcommands. The composition root injects concrete adapters into `dispatch`
  and maps errors to stderr + `ExitCode::FAILURE`
  (`cli/launcher/src/main.rs:80-112`).
- `kernel::Error::Failed(String)` is the shared boundary type; each subdomain
  maps its own error into it (`cli/kernel/src/lib.rs:9-21`).
- `cli/deny.toml` already carries the live `native-tls`/`openssl` architectural
  ban (`deny = [...]`, lines 60-64) as the working exemplar, and its comment
  (lines 65-71) has already been corrected to state that `skip`/`skip-tree` are
  duplicate-version suppression, **not** direction enforcement, and that the
  config/config-adapters split adds the first `[[bans.deny]]` + `wrappers` entry.
- The workspace has three members (`cli/Cargo.toml:5`: `launcher`, `kernel`,
  `verify`); `verify`'s manifest (`cli/verify/Cargo.toml`) is the minimal
  member template. The launcher already depends on `serde`/`serde_json` directly
  for release-manifest parsing (`cli/launcher/Cargo.toml:38-39`).
- The repo has no skills yet: no `skills/` directory and `plugin.json` has
  `"skills": []` (`.claude-plugin/plugin.json:10`). `.gitignore:12` ignores
  `.accelerator/config.local.md` and has no `.luminosity/` rule.
- The accelerator (https://github.com/atomicinnovation/accelerator, typically
  checked out locally at `../accelerator`) is the port source for the model
  (team `.md` committed + personal `.local.md` gitignored, personal wins, YAML
  frontmatter, dotted keys, empty-vs-unset), but its reader is a bash-3.2 awk
  parser, it has no `--level` on reads, and it only writes *top-level*
  frontmatter fields — so level-scoped reads and nested writes are net-new here.

### Key Discoveries

- The empty-vs-unset distinction must be modelled as a domain type, not carried
  in an exit code as accelerator does: the core returns a `Found(Scalar)`/`Absent`
  result — presence decided in the core, the `Scalar` rendered at the inbound
  boundary — where a present value (empty for null/empty string) → print + exit 0
  and `Absent` → error + exit non-zero
  (`cli/launcher/src/version/inbound/cli.rs:17-19` shows the print path).
- A bad `--level` value is best rejected by clap: a `Level` `ValueEnum` makes
  `--level bogus` fail at parse time via `error.exit()`
  (`cli/launcher/src/main.rs:103`), before any handler runs and before any file
  is touched — satisfying that acceptance criterion for free.
- The `config` core depends inward on `kernel` only (as `version`/`launch` cores
  do), so `impl From<ConfigError> for kernel::Error` lives in the `config` crate.
- cargo-pup is **not** involved: `config` is cross-crate, so its inward direction
  is enforced by the Cargo graph + cargo-deny, not by a `pup.ron` rule.

## Desired End State

`luminosity config get`/`set` resolves values across `.luminosity/config.md`
(team, committed) and `.luminosity/config.local.md` (personal, gitignored) with
personal precedence, full-stack by default and single-level under `--level`;
`set` defaults to personal (the gitignored file) and auto-creates `.luminosity/`
and its files on first write; the store is rooted at the discovered project root
(the nearest ancestor holding `.luminosity/`, else the repo root), so `get`/`set`
work from any subdirectory; the `config` core crate carries the resolution logic
with unit tests and
no serde/YAML/filesystem crate in its closure; `cargo deny check` fails if serde
is added to `config`; `.gitignore` ignores the personal file and tracks the team
file; and a thin `configure` skill drives the CLI with no config logic of its
own. Verified by the acceptance criteria in the work item, each mapped to an
automated check below.

## What We're NOT Doing

- No configuration schema or key namespace beyond the single proof value
  `core.example` (Assumption A2 in work item 0001). The typed `Node` retains value
  types and key order so the schema layers on cleanly later, but the schema
  itself, cross-crate schema composition, and value validation are deferred to
  0011.
- No comment preservation across a `set`: a whole-document reserialize cannot
  retain YAML comments, and no Rust YAML library offers comment-preserving
  round-trip for a dynamic-key tree. A comment strategy (generate-from-schema)
  is deferred to 0011.
- No plugin-global body-context channel, per-skill `context.md`/`instructions.md`,
  template/agent extension points, or template-management subcommands (deferred
  to epic 0011).
- No eval harness to capture `configure` skill output (deferred to 0010); the
  in-scope skill proof is the grep-verifiable thin-skill criterion.
- No `$HOME`/machine-global config tier (ADR-0003).
- No unset sentinel (ADR-0003 — last-writer-wins offers none).
- No standalone `config init` command; `.luminosity/` scaffolding happens as a
  side effect of the first `config set`, and the `.gitignore` edit is a one-time
  repo change made by this story.
- No cargo-pup rule for `config` (cross-crate enforcement is cargo-deny's job).
- No Model 2 config composition (launcher-resolves-once); Model 1 only (ADR-0010).
- No concurrency control on `set`: it is a read-modify-write with an atomic
  temp+rename, so two interleaved `set`s on the same level file are last-writer-wins
  on the **whole document** — a racing writer's update to a key the other never
  touched is dropped entirely. This is distinct from ADR-0003's *per-key* resolution
  precedence (which is about which level wins, not concurrent writes); single-writer
  is assumed, and an advisory lock is deferred if concurrent invocation becomes a
  supported use.
- No `config list` / `--show-origin` (enumerate keys, report which level won a
  resolution) — deferred DX, not needed for the one-value proof slice.
- No `config unset` and no `--force`/overwrite for `PathConflict`: a shape clash is
  a hard error with no CLI remedy in this slice (deferred to 0011). The
  `PathConflict` message names the conflict so the user is not left guessing.

## Implementation Approach

Copy the `version` hexagon's shape and scale to `launch` where the error taxonomy
demands it. Split the hexagon across two crates per ADR-0010: `config` (domain +
ports + application service, kernel-only dependencies) and `config-adapters`
(serde + `serde-saphyr` + `std::fs`). The launcher owns the inbound (clap)
adapter and, as the composition root (Model 1), instantiates the `config-adapters`
store and injects it into the core service. The outbound port hands the core a
parsed, serde-free **typed** document tree per level, so **both** the precedence
resolution and the nested-dotted-path walk/insert live in the core; the adapter
owns only YAML (de)serialization, frontmatter/body splitting, atomic writes, and
directory creation.

The core's `Node` tree is **typed and order-preserving**: it distinguishes string,
boolean, integer, float, null, and sequence values, and retains mapping key
insertion order. This keeps `set` — a read-mutate-one-path-write-whole-document
cycle — from coercing an untouched sibling value's type (e.g. rewriting
`enabled: true` as a string) or alphabetising keys, so a `set` preserves each
untouched sibling's type and the mapping's key order. (A whole-document reserialize
can still normalise a scalar's *textual* form — e.g. float formatting `1.50` →
`1.5`, or quoting style — and an integer outside `i64` range is preserved as a
string (a value-type change), so the fidelity guarantee is by value **type and key
order** for `i64`-range and non-numeric scalars, not byte-exact representation;
these join comment loss as deferred-to-0011 caveats and are unreachable in this
slice's tool-authored, string-valued files.) Retaining types also readies the core for the typed
configuration schema that story 0011 layers on at the composition root. What a whole-document reserialize **cannot** preserve is YAML comments (no
Rust YAML library offers comment-preserving round-trip for a dynamic-key tree);
comment handling is therefore out of scope here and deferred to 0011, where the
schema makes a generate-comments-from-schema strategy viable. In this story's
scope the config files are tool-authored (only `core.example`), so comment loss is
not reachable in practice.

Build strictly test-first, and phase so every phase leaves `mise run` green and
is independently mergeable: the two crates land first (tested, unwired), then the
ban-list, then the launcher wiring that delivers the CLI end-to-end **together
with the `.gitignore` protection for the files that wiring can create** (so the
write capability and its ignore rules ship in one mergeable unit, never in an
order that could leak an untracked personal file or temp scratch into a commit),
then the thin skill.

Decisions settled during planning: the deny ban widens `wrappers` to include the
launcher crate (`luminosity`) because it legitimately uses serde/serde_json, so
adding serde to `config` still fails while the launcher stays green; YAML parsing
uses `serde-saphyr` (pure-Rust, MIT/Apache, saphyr lineage), chosen because it
round-trips typed values (bool/int/float/null/sequence) and preserves mapping key
order — the fidelity the typed `Node` needs; `config set` creates `.luminosity/`
and its files on first write.

---

## Phase 1: `config` core crate — domain, ports, resolution service

### Overview

Stand up the dependency-free core: the domain types, the two outbound ports and
the inbound service methods, the precedence resolution, and the nested-path
walk/insert — all unit-tested against in-memory fakes. Not yet wired into the
launcher.

### Changes Required

#### 1. Workspace registration

**File**: `cli/Cargo.toml`
**Changes**: Add `config` to `members`; add `serde-saphyr` to
`[workspace.dependencies]` with an explicit version pin (e.g.
`serde-saphyr = "0.0.29"`, the current release at planning time) matching every
other entry's MSRV-first convention, plus a one-line rationale comment as the block
does for less-familiar deps (consumed in Phase 2, declared here for coherence).
Confirm the pinned version builds under the 1.90 MSRV during Phase 2.

```toml
members = ["launcher", "kernel", "verify", "config"]
```

#### 2. The `config` crate manifest

**File**: `cli/config/Cargo.toml`
**Changes**: New library crate, package name `config` (so `cargo tree -p config`
resolves per the acceptance criterion), depending only on `kernel`. Naming follows
the workspace convention that library members are unprefixed (like `kernel`) while
shipped binaries are prefixed (`luminosity`, `luminosity-verify`); confirm no graph
crate shares the bare `config` name (it is a common crates.io name) so
`cargo tree -p config` and the deny `wrappers` matching stay unambiguous. If a
collision ever surfaces, fall back to the disambiguating `luminosity-config`
(mirroring the `luminosity-verify` prefix convention).

```toml
[package]
name = "config"
version = "0.1.0-pre.0"
edition = "2021"
rust-version = "1.90.0"
license = "MIT"
publish = false

[lints]
workspace = true

[dependencies]
kernel = { path = "../kernel" }
```

#### 3. Domain, ports, and service

**File**: `cli/config/src/lib.rs` (plus `core.rs` / module split mirroring
`version`)
**Changes**: Model the domain and resolution. Illustrative shape:

```rust
pub enum Level { Team, Personal }

pub struct Key(Vec<String>);

pub enum Node {
    Scalar(Scalar),
    Sequence(Vec<Node>),
    Mapping(Mapping),
}

pub enum Scalar { String(String), Bool(bool), Int(i64), Float(f64), Null }

pub struct Mapping(Vec<(String, Node)>);

pub enum Resolved { Found(Scalar), Absent }

pub trait ReadConfigLevel {
    fn read(&self, level: Level) -> Result<Option<Node>, ConfigError>;
}

pub trait WriteConfigLevel {
    fn write(&self, level: Level, document: &Node) -> Result<(), ConfigError>;
}

pub trait ConfigAccess {                         // inbound/driving port
    fn get(&self, key: &Key, level: Option<Level>) -> Result<Resolved, ConfigError>;
    fn set(&self, key: &Key, value: &str, level: Level) -> Result<(), ConfigError>;
}

pub struct ConfigService<R, W> { reader: R, writer: W }

impl<R: ReadConfigLevel, W: WriteConfigLevel> ConfigAccess for ConfigService<R, W> {
    // get/set bodies per the semantics below
}
```

- `ConfigAccess` is the **inbound/driving port** (the analogue of `version`'s
  `ReportVersion`): `ConfigService<R, W>` implements it, and `dispatch` depends on
  `&impl ConfigAccess` — not on the concrete service or on the two outbound ports.
  The composition root (`main.rs`) assembles `ConfigService::new(reader, writer)`
  and injects that single value. This keeps the config hexagon's boundary
  consistent with `version`/`launch`.
- `Key::parse(&str) -> Result<Key, ConfigError>` is the only constructor: it splits
  on `.` and **rejects degenerate input** — an empty key, a leading/trailing dot,
  or consecutive dots (any empty segment) — with `ConfigError::InvalidKey`. The
  inbound adapter parses the raw clap string through it, so empty segments never
  reach the walk.
- `Node` is **typed** (`Scalar` distinguishes string/bool/int/float/null) and
  **order-preserving** (`Mapping` is an insertion-ordered `Vec<(String, Node)>`,
  not a `BTreeMap`, so a `set` neither alphabetises keys nor coerces sibling
  types). `Mapping` stays a zero-dependency structure to keep the core kernel-only
  — no `indexmap` or other crate enters the `config` closure.
- **Walk resolution (shared by `get` and `set`).** A dotted path descends through
  `Mapping` segments only, to arbitrary depth (no two-level cap, per ADR-0003). A
  path that must descend through a non-mapping (a `Scalar` or `Sequence`), or that
  ends on a `Mapping`/`Sequence` rather than a scalar, does **not** resolve to a
  value. Factor the traversal into small named operations rather than one dense
  `set` body — e.g. a read-only `descend(node, segment)` shared with `get`, and an
  order-preserving `upsert(segment, node)` on `Mapping` (which also encapsulates the
  linear find-or-insert over the `Vec<(String, Node)>`) — so conflict detection,
  intermediate-mapping creation, and leaf replacement are each independently named
  and testable.
- `get(key, None)` reads **both** level documents up front, then resolves: if the
  path resolves to a scalar in the personal document it wins (`Found(scalar)`),
  otherwise the team document is walked (fall-through), otherwise `Absent`. A level
  that does not resolve to a scalar — absent file, absent key, or a path blocked by
  / ending on a non-scalar — contributes nothing, so a scalar at the other level
  still resolves. `Found` carries the typed `Scalar` verbatim (including
  `Scalar::Null` and an empty `Scalar::String`); the **core decides presence**, and
  the inbound adapter renders the `Scalar` to the stdout string (see Phase 4). A
  present key whose value is null or an empty string is `Found(_)` and renders to an
  empty line (exit 0); only genuine non-resolution is `Absent` (exit non-zero) —
  the empty-vs-unset distinction, decided by presence in the core and rendered at
  the boundary.
- `get(key, Some(level))` walks only that level — no cross-level resolution —
  returning `Found(scalar)`/`Absent` the same way.
- **Fail-loud reads (symmetric).** A read that returns `MalformedFrontmatter`/`Io`
  aborts the `get`. Because a full-stack `get` reads *both* levels before
  resolving, **either** level being malformed fails the command — a malformed team
  file is caught even when the personal level would have supplied the value, not
  only the reverse. A `--level` read fails on the named level. Only a genuinely
  absent file (`Ok(None)`) or an unresolved path contributes nothing; a malformed
  file is never silently skipped.
- `set(key, value, level)` reads the level's current document — a genuinely absent
  file (`Ok(None)`), or a present file whose frontmatter is empty or parses to a
  null/non-mapping root, starts from an empty `Mapping`; a `MalformedFrontmatter`
  or `Io` read aborts the `set` and leaves the file untouched (fail-closed, never
  clobber a file it could not parse) — then inserts/replaces a
  `Scalar::String(value)` at the path, creating intermediate mappings as needed.
  Replacing an existing **scalar**
  leaf is a normal update. But if an intermediate segment already exists as a
  non-mapping, or the leaf currently holds a `Mapping`/`Sequence`, `set` returns
  `ConfigError::PathConflict` naming the conflicting segment and its shape rather
  than descending into or clobbering it — and no write happens. Untouched siblings
  retain their parsed types and order.

**File**: `cli/config/src/error.rs`
**Changes**: `ConfigError` enum implementing `Display`, `std::error::Error`, and
`From<ConfigError> for kernel::Error` (mapping to `kernel::Error::Failed(String)`,
so each variant's `Display` text is exactly the message the user sees after
`main`'s `luminosity: ` prefix). Each variant carries the context its message
needs — messages name concrete keys and **file paths**, never an internal `Level`
enum:

- `NotFound { key, level: Option<Level> }` — the resolved value was absent. Display:
  `config key 'core.example' is not set` (full-stack), or
  `config key 'core.example' is not set at level 'team'` (`--level`-scoped).
- `PathConflict { key, at, existing }` — `set` hit a shape clash; `key` is the
  requested dotted key, `at` the conflicting segment, `existing` whether it is a
  value or a section. Display, per shape:
  `cannot set 'core.example': 'core' is a value, not a section` (descent blocked),
  or `cannot set 'net': 'net' is a section, not a value` (would replace a
  container).
- `MalformedFrontmatter { path, detail }` — carries the concrete **file path** and
  the parser's `detail` (ideally serde-saphyr's line/column). Display:
  `config file '.luminosity/config.local.md' has malformed frontmatter: line 3,
  column 1: did not find expected key`.
- `Io { path, detail }` — carries the file path and the underlying I/O error.
  Display: `I/O error on config file '.luminosity/config.md': permission denied`.
- `InvalidKey { key }` — `Key::parse` rejected a degenerate dotted key. Display:
  `invalid config key '': expected dot-separated non-empty segments`.

The adapter (which knows paths) constructs `MalformedFrontmatter`/`Io` with the
concrete path. The core `get` returns `Ok(Resolved::Absent)` for a missing value
and **never constructs `ConfigError::NotFound`** — the not-found→error (exit-code)
policy lives solely at the inbound boundary, where the adapter maps
`Resolved::Absent` to `ConfigError::NotFound` with the key and any `--level`. (The
distinct names — `Resolved::Absent` the domain outcome, `ConfigError::NotFound` the
boundary error — keep the domain-vs-error seam legible.)
A bad `--level` is not a `ConfigError` — clap rejects it at parse time with its
own message naming the invalid value and the valid `team`/`personal` set.

### Success Criteria

#### Automated Verification

- [x] The crate builds and lints: `mise run cli:check`
- [x] Core unit tests pass: `cargo nextest run -p config`
- [x] Personal-over-team override, team-only fall-through, and level-scoped reads
      are each covered by a named test (asserted by inspecting
      `cargo nextest run -p config` output for the test names)
- [x] Presence is covered: a present **null** (`Scalar::Null`) and a present empty
      string both resolve to `Found(_)`, while a key absent from all levels resolves
      to `Resolved::Absent`
- [x] `get` returns the matching typed `Scalar` for a resolved value — a `Bool` key
      resolves to `Found(Scalar::Bool)`, an `Int` to `Found(Scalar::Int)` — leaving
      display formatting to the inbound `render` (tested in Phase 4)
- [x] `get` that must descend through a non-mapping, or that ends on a
      `Mapping`/`Sequence`, yields `Resolved::Absent`; a test covers full-stack
      fall-through where the personal level holds a mapping at the path and the
      team level holds the scalar (team value resolves)
- [x] Nested-path walk and nested `set` (creating an absent `core:` block) are
      each covered by a test, including a **≥3-level** path (`a.b.c.d`) that both
      walks and, on `set`, creates every intermediate mapping — so no two-level
      ceiling is hard-coded
- [x] `set` `PathConflict` is covered by two tests: descending through an existing
      scalar segment, and replacing a `Mapping`/`Sequence` leaf — each returns
      `ConfigError::PathConflict` and produces no document for the writer
- [x] `Key::parse` accepts `core.example` and a ≥3-level key, and rejects the empty
      key, a leading/trailing dot, and consecutive dots with `ConfigError::InvalidKey`
- [x] Fail-loud `get` is covered at the core against fakes: a `ReadConfigLevel` that
      returns `Err` for the personal level while the team level holds the value
      makes `get` return `Err` (not the team scalar), and symmetrically an erroring
      team read fails a full-stack `get` even when the personal level resolves
- [x] Fail-closed `set` is covered at the core against fakes: a `ReadConfigLevel`
      that returns `Err` makes `set` return `Err` and the fake `WriteConfigLevel` is
      never invoked (no clobber)
- [x] A `set` that mutates one path leaves untouched sibling nodes' types and the
      mapping's key order unchanged — a test builds a `Node` with a typed sibling
      (e.g. a bool) ahead of the target key, sets the target, and asserts the
      sibling's variant and the key order both survive
- [x] `cargo tree -p config` lists no serde, YAML, filesystem, or `indexmap` crate
      — the typed `Node` stays kernel-only
- [x] Full local CI mirror is green: `mise run`

#### Manual Verification

- [x] The core reads as domain-first: no presentation, I/O, or serde types leak
      into `cli/config/src/`

---

## Phase 2: `config-adapters` crate — YAML/filesystem outbound adapter

### Overview

Implement the outbound port over the real filesystem: discover the two config
files, split frontmatter from the markdown body, parse YAML into the core's
`Node` tree, serialize a mutated document back while preserving the body, write
atomically, and create `.luminosity/` and its files on first write. Not yet wired
into the launcher.

### Changes Required

#### 1. Workspace registration

**File**: `cli/Cargo.toml`
**Changes**: Add `config-adapters` to `members`.

```toml
members = ["launcher", "kernel", "verify", "config", "config-adapters"]
```

#### 2. The `config-adapters` crate manifest

**File**: `cli/config-adapters/Cargo.toml`

```toml
[package]
name = "config-adapters"
version = "0.1.0-pre.0"
edition = "2021"
rust-version = "1.90.0"
license = "MIT"
publish = false

[lints]
workspace = true

[dependencies]
config = { path = "../config" }
serde = { workspace = true }
serde-saphyr = { workspace = true }
```

Before committing to `serde-saphyr`, confirm three gates: it passes `cargo deny
check` (licenses/advisories/unmaintained), its MSRV is ≤ 1.90, and — critically for
distribution — its dependency closure is **pure-Rust with no C / `*-sys`
build-script linkage** (inspect `cargo tree -p config-adapters`), so the
musl-static release build (`build:launcher`, exercised by the full `mise run`)
stays green; the native-tls/openssl ban does **not** catch a generic C linker, so
this is a separate check. If `serde-saphyr` fails any of the three, fall back to
`serde_yaml_ng` deserialising into its typed `Value` with the `preserve_order`
(indexmap) feature — also pure-Rust — which keeps the typed, order-preserving
fidelity the `Node` needs. The plan's structure is unaffected either way because
YAML types never cross into `config`: the adapter maps whatever value type the
library produces into the serde-free `config::Node`.

#### 3. The filesystem store

**File**: `cli/config-adapters/src/lib.rs`
**Changes**: `FileConfigStore` rooted at a project directory, implementing both
`ReadConfigLevel` and `WriteConfigLevel`.

- **Project-root discovery** (a filesystem concern, so it lives in the adapter,
  not the pure core): a `FileConfigStore::discover(start_dir)` constructor makes a
  **single** upward walk from `start_dir` and, at each ancestor, checks for a
  `.luminosity/` directory (preferred) or a `.git` entry; it roots at the **first**
  ancestor that has either (`.luminosity/` winning on a tie at the same directory).
  A single pass — rather than an all-ancestors `.luminosity/` scan then a separate
  `.git` scan — means the enclosing `.git` **bounds** the walk, so discovery never
  crosses a repo boundary to root at an outer `.luminosity/` above a nested repo. If
  the walk reaches the filesystem root with no marker, it roots at `start_dir`. This
  makes
  `get`/`set` work from any subdirectory of a project (like `git config` finding
  the repo root) and stops `set` scattering a stray `.luminosity/` in the current
  subdirectory. `.git` detection is an **existence check** (a `.git` that is either
  a directory **or** a file — git worktrees and submodules use a `.git` *file* that
  points at the real git dir), not an `is_dir` check, so those layouts resolve the
  right root; the adapter still takes no git dependency.

- Paths: `<root>/.luminosity/config.md` (Team),
  `<root>/.luminosity/config.local.md` (Personal).
- A single **frontmatter-split** helper is shared by `read` and `write`: it treats
  only the **first two** `---` fence lines (the first on line 1) as the delimiters
  and returns `(frontmatter, body)` verbatim, **never re-scanning the body** for
  further `---`. Fence detection compares each candidate line with a trailing `\r`
  trimmed, so a CRLF-terminated file (`---\r\n` — a committed team file checked out
  under `core.autocrlf=true` or edited on Windows) is recognised as a fence rather
  than misread as an empty-frontmatter, all-body file. A file whose line 1 is not
  `---` has empty frontmatter and all-body content; an unclosed block (opening
  `---` with no closing `---`) is `MalformedFrontmatter`. Sharing one routine keeps
  read and write on an identical boundary so a body containing a `---` thematic
  break, or a file with no trailing newline, round-trips exactly.
- `read`: absent file → `Ok(None)`; present → split, parse the frontmatter via
  `serde-saphyr` into a serde-derived intermediate value, then map to the
  serde-free `config::Node` **preserving types and key order** (mappings →
  order-preserving `Mapping`, sequences → `Sequence`, booleans/integers/floats/
  null → the matching `Scalar` variant, strings → `Scalar::String`; an integer
  outside `i64` range is preserved as `Scalar::String` rather than overflowing).
  Malformed/unclosed frontmatter → `MalformedFrontmatter` — distinct from
  `Ok(None)`, so callers can tell malformed from absent (this is what makes the
  fail-loud/fail-closed behaviour in Phase 1 possible).
- `write`: split the current file (when present) to recover its body verbatim,
  serialize the `Node` back through `serde-saphyr` — retaining sibling value types
  and key order — reassemble `---\n{yaml}---\n{body}`, and write **atomically**:
  write to a uniquely-named temp file under `<root>/.luminosity/tmp/` (created if
  absent), then `rename` it onto the target. Because the temp file and the target
  share the `.luminosity/` filesystem the rename is atomic and cannot fail
  `EXDEV`, mirroring the launcher's write-then-rename at `cache.rs:80-92`. The temp
  file is removed if serialization, the write, **or the rename** fails, so a failed
  write leaves the target byte-unchanged and no stray temp behind. Reassembly uses
  **LF** fences (`---\n…`), so editing a CRLF-checked-out team file emits LF
  frontmatter beside its preserved body — a conscious LF-normalisation of the
  frontmatter block, not an accident. Create `.luminosity/` and the target file
  (empty body) when absent. Comments in an existing frontmatter block are not
  preserved across a write (deferred to 0011); in this story's scope the files are
  tool-authored, so this is not reachable.

### Success Criteria

#### Automated Verification

- [x] The crate builds and lints: `mise run cli:check`
- [x] Adapter tests pass: `cargo nextest run -p config-adapters`
- [x] A test parses a fixture `.md` (nested `core:`/`example:`) into the expected
      `Node`
- [x] A test parses a fixture carrying a boolean, an integer, a float, a null, and
      a sequence and asserts each maps to the matching typed `Scalar`/`Sequence`
      variant (types retained from the parse); a further case asserts an integer
      beyond `i64::MAX` maps to `Scalar::String` rather than overflowing
- [x] `cargo tree -p config-adapters` shows no `*-sys` / C-linking crate — a
      standing check of the pure-Rust, musl-static invariant, not just a one-time
      inspection at adoption
- [x] A test writes a nested key into an absent file, creating `.luminosity/` and
      the `core:` block, then reads it back (round-trip against a tempdir)
- [x] A test asserts the markdown body is preserved across a `write`
- [x] Body round-trips exactly for the edge cases: a body that itself contains a
      `---` line, a file with no trailing newline, a file with no frontmatter
      block, and a CRLF-terminated frontmatter (`---\r\n`) that is recognised
      rather than misread as bodyless
- [x] A test writes one key into a fixture that already holds a typed sibling
      (e.g. `enabled: true`) and further keys, then asserts the sibling keeps its
      type and the key order is unchanged after the round-trip (no coercion, no
      alphabetising)
- [x] A test asserts malformed/unclosed frontmatter yields `MalformedFrontmatter`
- [x] A `write` against a present-but-malformed file returns `MalformedFrontmatter`
      and leaves the file byte-for-byte unchanged (fail-closed)
- [x] A successful `write` leaves no stray temp file under `.luminosity/tmp/`, and
      the atomic write targets a temp file in `.luminosity/tmp/` (not the system
      temp dir), so the `rename` stays same-filesystem
- [x] `FileConfigStore::discover` tests bound the upward walk so it cannot escape
      into the real repo (see the isolation note in Testing Strategy). Cases:
      `.luminosity/` at the tempdir root with a start dir two levels down roots at
      the tempdir; only a `.git` **directory** present roots there; a `.git` that is
      a **file** (worktree/submodule layout) still roots there; and a neither-marker
      case (isolated tempdir with no ancestor marker) roots at the start dir
- [x] Full local CI mirror is green: `mise run`

#### Manual Verification

- [ ] A hand-run `config set`/`get` (once Phase 4 lands) produces well-formed,
      re-readable `.luminosity/config*.md` files

---

## Phase 3: cargo-deny cross-crate dependency-direction ban

### Overview

Add the `[[bans.deny]]` + `wrappers` entries that keep serde, serde_json, and the
YAML crate reachable only through their legitimate wrappers, so a direct
`config → serde` edge fails `cargo deny check`. This makes cross-crate
enforcement live for the first time.

### Changes Required

#### 1. The ban entries

**File**: `cli/deny.toml`
**Changes**: Add the cross-crate bans (extending the existing `native-tls`/
`openssl` ban). Each banned crate's `wrappers` must list **every** crate that
depends on it **directly** in the resolved graph, not just the first-party users —
cargo-deny permits the banned crate only through a listed direct parent, so a
missing legitimate parent makes `deny:check` fail on a legal edge. `serde` in
particular is depended on directly not only by `config-adapters` and `luminosity`
(release-manifest parsing) but by `serde_json` and `serde-saphyr` themselves, so
all of them appear in its `wrappers`; `serde_json`, by contrast, is used directly
only by the launcher here (`config-adapters` depends on `serde` and `serde-saphyr`,
not `serde_json`). Determine the exact sets empirically with `cargo tree -i serde`,
`cargo tree -i serde_json`, and `cargo tree -i serde-saphyr`, and include exactly
the direct dependents each reports — no more, no less (the negative check below
forces completeness; drop any wrapper the graph does not show).

Because the `wrappers` lists push the inline-table form past the 80-column house
rule and TOML inline tables cannot wrap, write the entries as `[[bans.deny]]`
array-of-tables sections (one field per line) rather than the inline `deny = [ … ]`
form, so every line stays within 80 columns:

```toml
# wrappers are illustrative — reconcile against `cargo tree -i` output
[[bans.deny]]
crate = "native-tls"

[[bans.deny]]
crate = "serde"
wrappers = ["config-adapters", "luminosity", "serde_json", "serde-saphyr"]

[[bans.deny]]
crate = "serde_json"
wrappers = ["luminosity"]

[[bans.deny]]
crate = "serde-saphyr"
wrappers = ["config-adapters"]
```

(the `openssl`/`openssl-sys` entries convert to the same section form). None of
these listed wrappers lets `config` reach a banned crate: `config` appears in no
`wrappers` list, so a direct `config → serde` (or `→ serde-saphyr`) edge is still a
violation — which is exactly the guardrail.

**Known maintenance cost (accepted tradeoff).** Banning ubiquitous crates
(`serde`, `serde_json`) globally and re-permitting them by an exhaustive `wrappers`
allow-list couples `deny.toml` to the full transitive graph: any future dependency
bump (reqwest, clap, tokio, …) that introduces a **new direct `serde` parent** will
fail `deny:check` on a perfectly legal edge until that parent is added. This is
inherent to the `[[bans.deny]]` + `wrappers` mechanism ADR-0009/0010 chose, and is
the price of enforcing the `config` boundary this way. The recovery is mechanical
and should be noted for the next maintainer (in the commit / PR, not in a stale
`deny.toml` comment): re-run `cargo tree -i <crate>`, add the omitted direct parent
to its `wrappers` — a failure here is an allow-list gap, not a real architectural
violation.

Reword the existing `skip`/`skip-tree` comment (lines 65-71) to be
state-descriptive and reference-free: it should state that `[[bans.deny]]` +
`wrappers` expresses the cross-crate dependency-direction ban while `skip`/
`skip-tree` only suppress duplicate-version warnings for the `multiple-versions`
check. Drop the `(work item 0009)` parenthetical and the "adds the first such
entry" narration — both go stale once the entry exists. Per house style, no
work-item or ADR references belong in `deny.toml` comments.

#### 2. Committed regression guard for the ban

**File**: a new integration test (Python/pytest, per ADR-0004 — the test language
for non-Rust surfaces), e.g. `tests/integration/cli/test_config_dependency_ban.py`.

**Changes**: A test that proves the ban actually bans, so a future loosening fails
CI rather than passing silently. It copies the `cli/` workspace source into a
tempdir, injects `serde = { workspace = true }` into the copied
`config/Cargo.toml`, runs `cargo deny check bans` in the copy, and asserts it exits
non-zero and names `serde` (and `config`). The mutation is confined to the throwaway
copy, so the real working tree is never made dirty. Wire the test into the suite so
it runs under `mise run test` / `mise run` (and therefore CI). This replaces the
one-time manual "add serde, revert" step with a standing guard on the story's
headline deliverable.

#### Automated Verification

- [ ] Negative check: `mise run deny:check` passes on the clean tree with the new
      entries — proving every legitimate direct dependent (including `serde_json`
      and `serde-saphyr` depending on `serde`) is present in the `wrappers` lists;
      an incomplete list fails here and names the omitted parent
- [ ] `cargo tree -p config` shows no serde, serde_json, or `serde-saphyr`
- [ ] Positive check (automated, committed): the regression test injects `serde`
      into a throwaway copy of `config` and asserts `cargo deny check bans` fails
      naming `serde`/`config` — this is the authoritative guard and runs in CI; a
      build failure is a secondary signal
- [ ] Full local CI mirror is green: `mise run`

#### Manual Verification

- [ ] Eyeball the failure output the regression test captures: it names the banned
      `serde` crate and the `config` dependent, so the guardrail reads legibly to a
      developer who trips it (not just a bare non-zero exit)

---

## Phase 4: Launcher wiring — `config` command and the CLI output contract

### Overview

Add the `Config` clap variant with a `Level` value-enum, the config inbound
adapter, the dispatch arm, the error mapping, and the Model-1 composition-root
wiring. Black-box integration tests assert the exact stdout/exit-code contract
for every functional acceptance criterion. This phase is the first to make the
writer user-invocable — it can create `.luminosity/config.local.md` and the
`.luminosity/tmp/` scratch dir — so it also lands the `.gitignore` protection for
those paths in the same mergeable unit, rather than deferring it to a later phase.

### Changes Required

#### 1. Launcher dependencies

**File**: `cli/launcher/Cargo.toml`
**Changes**: Add `config` and `config-adapters` path dependencies.

```toml
config = { path = "../config" }
config-adapters = { path = "../config-adapters" }
```

#### 2. Command tree

**File**: `cli/launcher/src/launch/inbound/cli.rs`
**Changes**: Add a named `Config` variant (named variants take precedence over
`external_subcommand`) with a nested subcommand and a `Level` value-enum.

```rust
pub enum Command {
    Version,
    Config { #[command(subcommand)] action: ConfigAction },
    #[command(external_subcommand)]
    External(Vec<OsString>),
}

#[derive(Subcommand)]
pub enum ConfigAction {
    Get { key: String, #[arg(long)] level: Option<Level> },
    Set { key: String, value: String, #[arg(long)] level: Option<Level> },
}

#[derive(Clone, Copy, ValueEnum)]
pub enum Level { Team, Personal }
```

An unrecognised `--level` is rejected by clap at parse time (`error.exit()` in
`main`), so no handler runs and no file is touched.

Every command, subcommand, argument, and `Level` variant carries a `///` doc
comment (as `Version` does), since clap derives `--help` text from them: explain
the dotted `section.key` convention, that `get` without `--level` resolves
personal-over-team while `--level` reads one level, and that `set` writes one level
defaulting to personal — naming the backing files and their commit/visibility
consequence (`team` → the committed, shared `.luminosity/config.md`; `personal` →
the git-ignored, local `.luminosity/config.local.md`), since the level choice is
the most consequential decision in the command. The inbound adapter owns the total
`clap::Level →
config::Level` mapping (a `From`/`match`), so the presentation `Level` (a clap
`ValueEnum`) and the domain `Level` stay explicitly bridged and cannot silently
drift.

#### 3. Config inbound adapter

**File**: `cli/launcher/src/config_command/inbound/cli.rs` (module mirroring
`version`)
**Changes**: Map `ConfigAction` to the injected core service. For `get`: `None`
level → full-stack, `Some` → that level; `Found(scalar)` → render the `Scalar` to a
display string via a **pure** `render(&Scalar) -> String` (`String` verbatim,
`Bool` → `true`/`false`, `Int` → decimal, `Float` → canonical form, **`Null` →
`""`**) and `println!("{rendered}")` (single trailing newline, including the empty
string); `Absent` → map to `ConfigError::NotFound` and return it. Keeping `render`
pure (mirroring `version/inbound/cli.rs`'s `render`) makes the presentation
rules unit-testable in the launcher without spawning the binary. For `set`: `None`
level → `Level::Personal` (the gitignored file, so an
accidental `set` never lands in shared committed state — `--level team` is
required to write the team file), `Some` → that level; run and return `Ok`.

#### 4. Dispatch and composition root

**File**: `cli/launcher/src/launch/mod.rs`
**Changes**: Add a single `config: &impl ConfigAccess` parameter to `dispatch`
(mirroring the existing `reporter: &impl ReportVersion` — the assembled service,
not a raw port pair) and a `Command::Config { action }` arm routing into the config
inbound adapter, mapping `ConfigError` into `kernel::Error` at the boundary.

**File**: `cli/launcher/src/main.rs`
**Changes**: In `run`, inject a **lazy** `ConfigAccess` implementation, mirroring
`LazyProductionResolver` (main.rs:44-56) which defers heavy wiring so a built-in
like `version` never touches infrastructure. The injected value defers
`FileConfigStore::discover(current_dir)` and the `ConfigService` build until the
first `get`/`set` call, so `version` and external dispatch pay no project-root
filesystem walk — only an actual `config` command discovers. `dispatch` still
receives it as `&impl ConfigAccess`; the laziness lives in the injected impl, not
the signature. Because `FileConfigStore` holds only its resolved root path it is a
cheap `Clone`, so the single discovered store can back both the `ReadConfigLevel`
and `WriteConfigLevel` ports the service needs without re-discovering.

#### 5. gitignore protection for the writable paths

**File**: `.gitignore`
**Changes**: Add `**/.luminosity/config.local.md` (leaving `.luminosity/config.md`
tracked) and `**/.luminosity/tmp/` (transient atomic-write scratch, never
committed). The `**/` prefix is required for depth-independence: a bare
`.luminosity/config.local.md` contains a mid-string slash, which Git anchors to the
`.gitignore` directory (the repo root), so it would **not** ignore a
`.luminosity/` that project-root discovery roots below the repo root — the `**/`
form matches at any depth and keeps every discovered personal file and temp
scratch ignored. This lands in this phase — the first that makes the writer
invocable — so the protection ships with the capability. The existing
`.accelerator/config.local.md` rule is unrelated and stays.

### Success Criteria

#### Automated Verification

- [ ] Builds, lints, and the release build pass: `mise run cli:check` and
      `mise run build:launcher`
- [ ] `git check-ignore .luminosity/config.local.md` and
      `git check-ignore .luminosity/tmp/scratch` both succeed (personal file and
      temp scratch ignored), and the same holds at a nested depth
      (`git check-ignore sub/dir/.luminosity/config.local.md` succeeds — proving the
      `**/` form), while `git check-ignore .luminosity/config.md` returns nothing
      (team file tracked)
- [ ] New black-box integration tests pass:
      `cargo nextest run -p luminosity -E 'test(config)'`
- [ ] Full-stack resolution returns the personal value (both levels set)
- [ ] Team-only fall-through returns the team value (personal absent)
- [ ] `--level team` returns team and `--level personal` returns personal when
      both are set
- [ ] `set` with no `--level` writes the personal file
      `.luminosity/config.local.md`; `--level team` writes the team file
      `.luminosity/config.md`
- [ ] `get`/`set` invoked from a subdirectory of a project resolve the ancestor
      `.luminosity/` (discovery), rather than finding nothing or scaffolding a
      stray nested `.luminosity/`
- [ ] `set --level personal` then `get` (full-stack) returns the personal value
      (round-trip)
- [ ] Key absent from both levels: `get` exits non-zero, prints nothing to stdout,
      and prints a stderr message naming the key (`config key '…' is not set`)
- [ ] Key present but empty: `get` exits 0 and prints an empty string — covered
      for both an empty-string value and a bare null value (`example:`)
- [ ] The inbound `render(&Scalar)` is unit-tested (no binary spawn): `String`
      verbatim, `Bool` → `true`/`false`, `Int` → decimal, `Float` → canonical form,
      and `Null` → `""` — mirroring `version`'s pure `render`
- [ ] `set` into a conflicting path (a key whose parent segment is a scalar, or
      whose target is an existing section) exits non-zero naming the conflicting
      key and leaves every config file byte-unchanged
- [ ] A full-stack `get` of a team-only key with a present-but-malformed personal
      file exits non-zero (fail-loud), prints nothing to stdout, and prints a
      stderr message naming the concrete malformed file path
      (`.luminosity/config.local.md`), not a `Level` word
- [ ] The `set` `PathConflict` case above asserts the stderr message names the
      conflicting segment and its shape (value-vs-section)
- [ ] `--level bogus` on `get` and `set` exits non-zero, names the invalid level,
      and creates/modifies no config file
- [ ] A degenerate key (e.g. `""` or `core..example`) on both `get` and `set`
      exits non-zero, prints nothing to stdout, names the invalid key on stderr, and
      creates/modifies no config file — the `set` case in particular creates no
      `.luminosity/` directory (validation precedes discovery/scaffolding)
      (`Key::parse` → `InvalidKey`)
- [ ] `get` on a resolved value prints the value + exactly one trailing newline
      and exits 0
- [ ] `luminosity config --help`, `config get --help`, and `config set --help`
      show non-empty descriptions for the commands, the `key`/`value` args, and
      `--level` (doc comments are wired), and `--level`'s help lists `team`,
      `personal`
- [ ] Full local CI mirror is green: `mise run`

#### Manual Verification

- [ ] Running `luminosity config set core.example v` then
      `luminosity config get core.example` from a scratch directory behaves as
      specified and leaves readable files under `.luminosity/`

---

## Phase 5: the thin `configure` skill

### Overview

Add the repo's first skill — a thin `configure` that reads/writes config solely
through `luminosity config get`/`set`. (The `.gitignore` protection for the
personal file and temp scratch lands with the writer in Phase 4, not here.)

### Changes Required

#### 1. The thin skill

**File**: `skills/config/configure/SKILL.md`
**Changes**: New skill under a `config` category directory (matching the plugin
convention that skills are grouped by category — as in the accelerator's
`skills/config/`), so this first skill sets the pattern rather than sitting flat.
YAML frontmatter carries `name`, `description`, `argument-hint`, and
`allowed-tools` scoped to the luminosity bin in the plugin's
`Bash(${CLAUDE_PLUGIN_ROOT}/…)` form (e.g. `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity
config *)`, matching the accelerator's Bash-glob scoping); the
`description`/`argument-hint` name the get/set operations, the dotted `section.key`
convention, and the team/personal `--level` semantics so the skill is discoverable. The body invokes
the CLI via the `!` preprocessor — every config read/write is a
`` !`${CLAUDE_PLUGIN_ROOT}/bin/luminosity config get …` `` or `set` call, with no
YAML parsing, precedence logic, path construction, or direct
`.luminosity/config*.md` access.

#### 2. Skill registration

**File**: `.claude-plugin/plugin.json`
**Changes**: Add the category directory to the `skills` array as `"./skills/config/"`
(a category-directory path, matching the accelerator's registration form), turning
the current `"skills": []` into `"skills": ["./skills/config/"]`.

### Success Criteria

#### Automated Verification

- [ ] Grep over the skill body finds only `luminosity config get`/`set` for config
      access and no direct read of `.luminosity/config*.md`, no YAML parsing, and
      no precedence/path-construction command
- [ ] `plugin.json` is valid JSON and lists the skill: `mise run check`
- [ ] Full local CI mirror is green: `mise run`

#### Manual Verification

- [ ] Invoking the `configure` skill and reading a key returns the same value as
      `luminosity config get` for that key (full behavioural equivalence is
      validated by the eval-application story 0010)

---

## Testing Strategy

### Unit Tests

- `config` core (Phase 1): precedence (personal-over-team), fall-through
  (team-only, including where the personal level blocks the path with a
  non-scalar), level-scoped reads, empty-vs-unset (`Found(_)` for empty-string and
  null, `Resolved::Absent` for missing), returning the matching typed `Scalar`
  variant, nested-path walk and nested `set` at arbitrary depth (≥3 levels), `set`
  `PathConflict` (descend through a scalar; replace a container leaf), and sibling
  type/key-order preservation across a `set` — all against in-memory fake
  `ReadConfigLevel`/`WriteConfigLevel`, mirroring `version/core.rs:49-78`. The
  inbound adapter's pure `render(&Scalar)` is unit-tested in the launcher
  (bool/int/float/null), mirroring `version`'s `render`.
- `config-adapters` (Phase 2): typed YAML→`Node` parse (string/bool/int/float/
  null/sequence), nested write + dir/file creation round-trip, body preservation
  (including bodies with an embedded `---` and files with no trailing newline),
  sibling type + key-order preservation across a write, fail-closed write against
  a malformed file (target byte-unchanged), atomic temp handling under
  `.luminosity/tmp/`, and malformed-frontmatter handling — all against tempdirs.

### Integration Tests

- `cli/launcher/tests/config.rs` (Phase 4): spawn `CARGO_BIN_EXE_luminosity` with
  a per-test working directory (`.current_dir(tempdir)`), write fixture config
  files, and assert stdout/newline/exit-code for every functional acceptance
  criterion — mirroring `cli/launcher/tests/version.rs`. Include a from-subdirectory
  case exercising project-root discovery. Error cases additionally assert the
  **stderr** message content (key named on not-found, concrete file path on
  malformed, conflicting segment on `PathConflict`), not just the exit code.
- Dependency-ban regression (Phase 3, Python/pytest): copy the `cli/` workspace to
  a tempdir, inject `serde` into the copied `config/Cargo.toml`, and assert
  `cargo deny check bans` fails naming `serde`/`config` — a standing guard that the
  architectural ban still bans, run in CI.

### Test isolation (discovery walk)

Because **every** `config get`/`set` runs `FileConfigStore::discover`, which walks
*upward* for a `.luminosity/`/`.git` marker, this isolation requirement applies to
**every** config integration test — not only the from-subdirectory case, but
especially the absent-file negatives (the not-found `get` with both files absent)
and the `set`-creation / round-trip tests, whose tempdirs carry no boundary marker.
Without bounding, the walk escapes the fixture and finds the **real** repo: cargo's
`CARGO_TARGET_TMPDIR` lives under `cli/target/`, inside this git repo (the existing
`cli/launcher/tests/resolution.rs` roots tempdirs there), so a `set` would scaffold
a git-ignored `.luminosity/config.local.md` into the real working tree while the
tempdir assertion still passed. Each config test therefore either uses a
system-temp tempdir outside any git repo (e.g. the `tempfile` crate's default
location) **and/or** plants the intended boundary marker (`.git` or `.luminosity/`)
at the tempdir root, so the walk terminates inside the fixture. This is a hard
requirement, not a convenience — without it the tests are non-deterministic and can
read or mutate the real working tree.

### Manual Testing Steps

1. From a scratch directory, `luminosity config set core.example team-value
   --level team` and confirm `.luminosity/config.md` is created with a nested
   `core:`/`example:`.
2. `luminosity config set core.example personal-value` (no `--level`, so the
   personal default) and confirm `.luminosity/config.local.md` is created.
3. `luminosity config get core.example` returns `personal-value`; `--level team`
   returns `team-value`.
4. From a subdirectory of the scratch directory, `luminosity config get
   core.example` still returns `personal-value` (project-root discovery).
5. `luminosity config get missing.key` exits non-zero with empty stdout.
6. Invoke the `configure` skill and confirm it emits the CLI's value verbatim.

## Performance Considerations

Negligible. Config resolution reads at most two small files per invocation; the
built-in `config` command, like `version`, never touches the launcher's
fetch/verify/cache infrastructure (`cli/launcher/src/main.rs:42-56`).

## Migration Notes

No data migration. The `.gitignore` edit is additive. `.luminosity/` is created
lazily on first `config set`; repos that never configure remain untouched.

## References

- Original work item: `meta/work/0009-multi-level-configuration-system.md`
- Research: `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md`
- Work-item review: `meta/reviews/work/0009-multi-level-configuration-system-review-1.md`
- Hexagon template: `cli/launcher/src/version/` (core/inbound/outbound + `main.rs` wiring)
- Error boundary: `cli/kernel/src/lib.rs:9-21`; rich-error variant: `cli/launcher/src/launch/core.rs:148-152`
- Live architectural ban exemplar: `cli/deny.toml:60-71`
- ADR-0003 (config model), ADR-0009 (hexagon + enforcement split), ADR-0010 (cross-crate split, Model 1)
- YAML library: `serde-saphyr` (https://github.com/bourumir-wyngs/serde-saphyr) — pure-Rust, MIT/Apache, typed + order-preserving round-trip
- Deferred schema/comment work: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
- Port source: the accelerator (https://github.com/atomicinnovation/accelerator),
  `scripts/config-read-value.sh` and `scripts/config-common.sh`
