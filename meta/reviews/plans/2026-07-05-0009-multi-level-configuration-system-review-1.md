---
type: plan-review
id: "2026-07-05-0009-multi-level-configuration-system-review-1"
title: "Plan Review: Multi-Level Configuration System — CLI Command + Thin configure Skill"
date: "2026-07-05T14:33:38+00:00"
author: Toby Clemson
producer: review-plan
status: complete
parent: "plan:2026-07-05-0009-multi-level-configuration-system"
target: "plan:2026-07-05-0009-multi-level-configuration-system"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, correctness, test-coverage, code-quality, safety, usability, standards, portability]
review_number: 1
review_pass: 3
tags: [configuration, cli, skills, hexagonal, architecture-enforcement]
last_updated: "2026-07-06T00:03:10+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: Multi-Level Configuration System — CLI Command + Thin configure Skill

**Verdict:** REVISE

The plan is architecturally excellent and unusually well-grounded: it faithfully
realises ADR-0010's first cross-crate hexagon (kernel-only `config` core +
`config-adapters`), correctly diagnoses and fixes the enforcement mechanism
(`[[bans.deny]]` + `wrappers`, not the inert `skip`/`skip-tree`), models
empty-vs-unset as a domain type rather than an exit code, and phases the work so
each phase leaves `mise run` green and is independently mergeable. It is not,
however, ready to implement as written: a single unspecified design choice — the
string-only `Node` tree reserialised whole on every `set` — is a latent
data-corruption bug flagged independently by four lenses, and a cluster of
write-path safety gaps (malformed-file clobber, `---`-in-body split, EXDEV temp
placement, and a phase ordering that ships the personal-file writer before its
`.gitignore` guard) each risk unrecoverable loss on the *gitignored* personal
file. None are critical, but 21 major findings across all eight lenses warrant a
revision pass before implementation.

### Cross-Cutting Themes

- **`set` round-trip corrupts sibling frontmatter** (flagged by: architecture,
  correctness, code-quality, test-coverage) — the strongest signal in the review.
  `Node` is `Scalar(String)` over a `BTreeMap`, and `set` reads the whole
  document, mutates one path, and reserialises everything. Consequences:
  BTreeMap reorders keys alphabetically, all scalars are stringified (`enabled:
  true` → `"true"`, `1.10` → `"1.1"`), YAML sequences and comments have no
  representation and are dropped, and YAML null (`example:`) is unmodelled —
  which also leaves the headline *empty-vs-unset* criterion undefined for the
  most natural hand-authored empty form. Every planned test uses the single
  string value `core.example`, so none would catch this. This is a foundational
  data-transformation decision the parity epic (0011) inherits.

- **Nested walk/insert type-conflict semantics undefined** (flagged by:
  correctness, code-quality, test-coverage) — `set`/`get` behaviour is
  unspecified when a path segment is not a mapping (`set core.example` where
  `core` is a scalar; `get core` where `core` is a block). No `ConfigError`
  variant covers it, leaving silent clobber or panic as the implicit outcomes,
  and no test pins the arbitrary-depth (≥3-level) contract ADR-0003 requires.

- **Store rooted at raw CWD, no project-root discovery** (flagged by:
  architecture, correctness, safety, usability, portability — 5 lenses) —
  `FileConfigStore` roots at the current working directory with no upward walk
  for `.luminosity/`, unlike `git config`. Running from a subdirectory silently
  finds nothing (`get` → NotFound) and scatters a stray `.luminosity/` on `set`
  — which the repo-root-anchored `.gitignore` rule won't cover, making a nested
  personal file committable. All integration tests pin cwd at the root, so the
  subdirectory case is never exercised.

- **Atomic temp-file location unspecified (EXDEV)** (flagged by: safety,
  portability) — the temp+rename write never pins the temp file to the target
  directory. A temp in `std::env::temp_dir()` fails `EXDEV` on any multi-mount
  setup (containers, CI, `/tmp`-on-tmpfs) — routine on the musl-Linux targets.
  The launcher already has the correct exemplar at
  `cli/launcher/src/launch/outbound/resolve/cache.rs:80-92`.

- **Error paths are under-specified and under-tested** (flagged by:
  test-coverage, usability) — the `MalformedFrontmatter`/`Io` variants are never
  surfaced through the CLI in any integration test, and the human-facing message
  text is unspecified (`MalformedFrontmatter` even names a `Level` enum, not the
  file path). A malformed committed config is a common, realistic failure whose
  CLI behaviour is entirely unverified.

- **The architectural ban is the headline deliverable but unguarded** (flagged
  by: test-coverage, correctness) — its only proof is a manual, transient
  "temporarily add serde, revert after verifying" step, so a future loosening
  passes CI silently; and the `serde` `wrappers` allow-list may be incomplete
  (`serde_json`/`serde_yaml_ng` are themselves direct serde dependents), so
  `deny:check` could fail on legitimate edges or not bite at all. First
  `wrappers`-scoped ban in the repo — no working precedent.

### Tradeoff Analysis

- **Fail-loud vs fall-through on a malformed personal file**: Safety wants `set`
  and `get` to fail closed on a malformed existing file (never clobber; the
  personal file is unrecoverable from VCS). Correctness notes that a full-stack
  `get` reading the personal file first will then abort even for team-only keys,
  breaking fall-through for a *present-but-malformed* personal file (it holds
  only for an *absent* one). Recommendation: `set` must fail closed (never
  overwrite a file it couldn't parse); for `get`, decide deliberately — either
  fail-loud (safer, consistent) or skip-malformed-personal-and-fall-through
  (more forgiving) — and test the chosen behaviour. Document the choice.

- **`set` default: team vs personal**: The work item settled on team (committed,
  shared) as the author's call, explicitly flagged for reviewer reconsideration.
  Usability argues personal (gitignored, blast-radius-limited) is the safer
  least-surprise default, matching `git config`'s local default — the
  lowest-friction `set` should not silently mutate shared, version-controlled
  state. Recommendation: reconsider defaulting to personal with explicit
  `--level team` for shared writes; if team is kept, at minimum emit a one-line
  stderr note naming the file written so the shared write is never invisible.

- **`Node` fidelity vs simplicity**: Widening `Node` to preserve typed scalars +
  sequences makes the round-trip loss-free but enlarges the core; scoping it to
  string scalars with an explicit reject-on-non-scalar guard on read keeps the
  model minimal but refuses some real files. Either resolves the corruption
  finding — the plan must pick one and state it.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Architecture / Correctness / Code-Quality / Test-Coverage**: `set`
  round-trip over a string-only `Node`/`BTreeMap` corrupts sibling frontmatter
  and leaves empty-vs-unset undefined for YAML null
  **Location**: Phase 1 (Node domain model); Phase 2 (adapter YAML→Node
  conversion & write)
  Reserialising the whole document reorders keys, stringifies typed scalars,
  drops sequences/comments, and has no representation for `example:` (null) —
  the natural empty form the headline criterion depends on. Un-caught by the
  single-value test fixtures.

- 🟡 **Correctness / Code-Quality / Test-Coverage**: Nested walk/insert
  semantics undefined when a path segment is not a mapping; no error variant, no
  arbitrary-depth test
  **Location**: Phase 1 (`set`/`get`, `Node::set_path`/`get_path`)
  `set core.example` where `core` is a scalar (or `set core` over a block) has
  no defined policy — silent clobber or panic. `get` through a scalar/onto a
  mapping must yield `NotFound` for fall-through to work. ADR-0003's
  drop-the-two-level-cap requirement is never tested (all fixtures are 2-level).

- 🟡 **Safety**: `config set` behaviour on a malformed existing file is
  unspecified — risk of silently clobbering the file (and its body)
  **Location**: Phase 1 (`set` semantics); Phase 2 (`read`/`write`)
  If a `MalformedFrontmatter` read collapses to "start from empty mapping", a
  hand-edited/partially-written file is overwritten, discarding its body — and
  on the gitignored personal file this is unrecoverable.

- 🟡 **Safety**: Body-split on `---` can corrupt or truncate the preserved
  markdown body
  **Location**: Phase 2 (frontmatter isolation & reassembly)
  A body containing a `---` thematic break (legal markdown), a missing trailing
  newline, or a no-frontmatter file can misidentify the boundary on re-read, so
  body is swallowed or lost — compounding across read-modify-write cycles.

- 🟡 **Safety / Portability**: Atomic-write temp-file location unspecified; a
  cross-filesystem temp defeats rename atomicity (EXDEV)
  **Location**: Phase 2 (write: temp-file + rename)
  Temp must be created inside `<root>/.luminosity/` (same dir as target) or
  `rename` fails `EXDEV` on multi-mount Linux/containers. The correct pattern
  already exists at `cache.rs:80-92`, including temp cleanup on error.

- 🟡 **Safety**: Personal-file writer (Phase 4) ships before its `.gitignore`
  guard (Phase 5), yet phases are "independently mergeable"
  **Location**: Phase 4 vs Phase 5 ordering
  Between merges, `set --level personal` creates an untracked-but-not-ignored
  file that `git add .` will stage — the exact leak the split exists to prevent.

- 🟡 **Test-Coverage / Correctness**: The architectural ban — the story's
  headline deliverable — has only a manual, transient verification, and its
  `serde` `wrappers` allow-list may be incomplete
  **Location**: Phase 3 (cargo-deny ban)
  No committed regression guard, so a later loosening passes CI silently.
  `serde_json`/`serde_yaml_ng` are direct serde dependents; the allow-list must
  enumerate every direct dependent (`cargo tree -i serde`), and both the
  positive (add-serde-to-config fails) and negative (clean tree passes) checks
  must be validated empirically.

- 🟡 **Test-Coverage**: Malformed-frontmatter and IO error paths are never
  surfaced through the CLI in any test
  **Location**: Phase 4 Success Criteria / Testing Strategy
  The `From<ConfigError> for kernel::Error` plumbing to non-zero exit +
  clean-stdout stderr is unverified for a malformed committed config file (a
  common failure) and for the Io variant.

- 🟡 **Test-Coverage**: Arbitrary nesting depth beyond two levels is never
  tested, and no test proves `set` preserves unrelated sibling keys
  **Location**: Phase 1 & Phase 2 Success Criteria
  A hard-coded two-level walk would pass every planned test while violating
  ADR-0003; a `set` that drops a pre-existing sibling key would be silent data
  loss on the committed team config with no test to catch it.

- 🟡 **Code-Quality**: `ConfigError` taxonomy has no variant for a nested path
  that traverses an existing scalar
  **Location**: Phase 1 (`error.rs`, `set_path`)
  Leaves an ad-hoc `unwrap`/overwrite in the trickiest core logic. Add an
  explicit `PathConflict { key }` variant with a named test.

- 🟡 **Architecture**: Config inbound boundary is underspecified and diverges
  from the established inbound-port pattern
  **Location**: Phase 1 (ports/service); Phase 4 (dispatch & composition root)
  `version` exposes an inbound port trait taken by `dispatch(&impl …)`; the
  config sketch gives `ConfigService` inherent methods with no inbound port, and
  the wiring text is inconsistent about whether `dispatch` receives the assembled
  service or the two raw ports. This is the load-bearing seam of the
  architectural-proof story.

- 🟡 **Usability**: `set` defaults to the shared, committed team file —
  accidental shared writes
  **Location**: Phase 4 (`set` None → Level::Team); work item Open Questions
  The lowest-friction `set` silently mutates version-controlled shared state;
  the flag's absence also means different things for `get` (resolve all) vs
  `set` (one shared level). See Tradeoff Analysis.

- 🟡 **Usability / Architecture / Correctness / Safety / Portability**: Store
  rooted at raw CWD misbehaves from subdirectories
  **Location**: Phase 4 (composition root)
  No upward walk for a project root; `get` from a subdirectory returns NotFound
  and `set` scatters a stray, un-gitignored `.luminosity/`. See Cross-Cutting
  Themes.

- 🟡 **Usability**: Error-message wording unspecified; `MalformedFrontmatter`
  names a `Level` enum, not the file path
  **Location**: Phase 1 (`error.rs`); Phase 4 (error mapping)
  Exit codes are pinned but message text is open; a developer sees `luminosity:
  <detail>` with no path or `config set` hint. Specify the text and assert
  stderr content, not just exit code.

- 🟡 **Portability**: The YAML crate must stay pure-Rust (no C `libyaml`
  linkage) to preserve the musl static build — an unstated invariant
  **Location**: Implementation Approach / Phase 2 manifest
  `serde_yaml_ng` and `yaml-rust2` both satisfy this, so the choice is fine, but
  a future swap to a `libyaml`-bindings crate would silently break the musl
  target. Record the constraint and confirm the closure passes `deny.toml`'s
  `unmaintained`/license checks.

- 🟡 **Standards**: Plan directs leaving a `deny.toml` comment that embeds a
  work-item reference and narrates a now-completed pending change
  **Location**: Phase 3 (Changes Required #1)
  The comment reads `…the config/config-adapters split (work item 0009) adds the
  first such entry` — contradicting the plan's own restated no-references rule
  and, once the entry lands, describing an already-done change as pending.
  Reword to be state-descriptive and reference-free.

#### Minor

- 🔵 **Correctness**: A malformed *personal* file blocks reads of team-only keys
  (full-stack `get` reads personal first and aborts). Decide fail-loud vs
  skip-and-fall-through. **Location**: Phase 1 precedence + Phase 2 read.
- 🔵 **Correctness / Test-Coverage**: `get_path` must return `NotFound` (not
  error/panic) when traversing a scalar or landing on a mapping; add a
  "personal has a mapping where team has the scalar" fall-through test.
  **Location**: Phase 1.
- 🔵 **Test-Coverage**: Empty-but-set output not pinned to exact bytes — assert
  `stdout == "\n"` (empty-set) vs `stdout == ""` (not-found) so the newline
  contract can't drift. **Location**: Phase 4 Success Criteria.
- 🔵 **Code-Quality**: `set`-default-to-team business rule is buried in the
  side-effecting inbound adapter; extract the `Option<Level>` decision into a
  pure, unit-testable function. **Location**: Phase 4 (inbound adapter).
- 🔵 **Code-Quality**: Not-found is represented twice (`Resolved::NotFound` and
  `ConfigError::NotFound`); clarify that the NotFound→error policy lives solely
  in the inbound adapter. **Location**: Phase 1 domain.
- 🔵 **Code-Quality**: `Key(Vec<String>)` has no described constructor/validation
  for degenerate dotted input (`""`, `"core."`, `"a..b"` → empty segments); add
  a validating `Key::parse`. **Location**: Phase 1 domain.
- 🔵 **Code-Quality**: `FileConfigStore` concentrates discovery, frontmatter
  split, YAML codec, body preservation, and atomic write; extract the pure
  frontmatter/codec transforms as free functions for focused unit tests.
  **Location**: Phase 2.
- 🔵 **Safety**: No guard against concurrent/interleaved `set` (two separate
  reads of the file — service read + adapter body re-read); prefer taking the
  body from the read the service already performed, and document last-writer-wins.
  **Location**: Phase 1/2 read-modify-write.
- 🔵 **Usability**: `config`/`get`/`set`/`--level` carry no `///` doc comments,
  so `--help` entries render blank (unlike `Version`); specify self-teaching doc
  text. **Location**: Phase 4 command tree.
- 🔵 **Usability**: First `set` silently creates `.luminosity/` and a committed
  file with no feedback; emit a short stderr "created …" note (stdout stays
  clean). **Location**: Phase 2 write / Phase 4 contract.
- 🔵 **Portability**: LF-only frontmatter delimiter/reassembly; a CRLF checkout
  (`core.autocrlf=true`) yields `---\r`, risking spurious `MalformedFrontmatter`
  or body corruption. Trim trailing `\r` on the delimiter match; add a CRLF
  fixture. **Location**: Phase 2.
- 🔵 **Standards**: New `serde_yaml_ng` `[workspace.dependencies]` entry has no
  version pin, unlike every existing entry (MSRV-first). Name a concrete
  1.90-compatible pin. **Location**: Phase 1 workspace registration.
- 🔵 **Standards**: `rust-version = "1.90.0"` on both new crates adds two more
  hand-synced MSRV mirrors (kernel omits it, verify keeps it — already
  inconsistent). Pick one and note the sync obligation. **Location**: Phase 1/2
  manifests.
- 🔵 **Standards**: Skill `plugin.json` registration format (path string vs
  object) and category placement unspecified — this is the repo's first skill,
  so it sets the pattern. **Location**: Phase 5 (#2/#3).

#### Suggestions

- 🔵 **Architecture**: The duplicate `Level` enum (clap `ValueEnum` in the
  launcher, domain `Level` in core) is correct, but name the total
  `clap::Level → config::Level` mapping so the two can't drift silently.
  **Location**: Phase 4 command tree / Phase 1.
- 🔵 **Architecture**: `dispatch` + `run()` grow one positional parameter per
  built-in (now heading to 5+); note the linear-growth tradeoff so a future
  built-in triggers a deliberate dependencies-struct refactor. **Location**:
  Phase 4.
- 🔵 **Correctness / Code-Quality**: Define whether empty dotted-key segments are
  rejected or normalised, with tests for the empty-key and trailing-dot cases.
  **Location**: Phase 1 `Key`.
- 🔵 **Test-Coverage**: Plan for small shared helpers in `config.rs`
  (`write_level`, `run_get`/`run_set`) so the ~11 integration cases reduce to
  arrange-act-assert rather than copy-pasted setup. **Location**: Testing
  Strategy.
- 🔵 **Usability**: Specify what the skill's `description`/`argument-hint`
  communicate (get/set, dotted-key convention, team/personal `--level`) — the
  skill's entire discoverability surface. **Location**: Phase 5 (#2).

### Strengths

- ✅ Cross-crate hexagon split faithfully realises ADR-0010 Model 1: core
  depends inward on `kernel` only, adapters own serde/YAML/fs, no dependency
  cycles, and the composition root wires `config-adapters` into the core.
- ✅ Correctly identifies that `From<ConfigError> for kernel::Error` must live in
  the `config` crate (orphan rule), a subtle, correct divergence from `launch`.
- ✅ Correctly diagnoses and fixes the enforcement mechanism — `[[bans.deny]]` +
  `wrappers` (scoped to `config-adapters` and the legitimately-serde-using
  `luminosity`), not the inert `skip`/`skip-tree` — with a temporary-serde
  experiment as the authoritative CI-failure check.
- ✅ Empty-vs-unset modelled as a domain type (`Resolved::Found/NotFound`) in the
  core rather than an exit-code smuggle, keeping the distinction unit-testable.
- ✅ Interface segregation honoured: separate `ReadConfigLevel`/`WriteConfigLevel`
  ports, each trivially faked, mirroring the `version` core.
- ✅ Bad `--level` rejected by a clap `ValueEnum` at parse time — names valid
  values, touches no file, needs no handler-side guard.
- ✅ Genuinely test-first phasing: each phase leaves `mise run` green, is
  independently mergeable, and maps named tests to individual acceptance criteria.
- ✅ Correct test pyramid: pure logic unit-tested against in-memory fakes, CLI
  contract black-box integration-tested with per-test cwd isolation.
- ✅ Manifests faithfully follow the `verify` minimal-member template and keep the
  workspace versionless, with `luminosity` the sole version-bearing crate.
- ✅ Zero cloud/vendor/service lock-in; the serde-free `Node` boundary makes the
  YAML library a fully substitutable detail (the `yaml-rust2` fallback proves it).
- ✅ Strong comment-hygiene posture overall — the plan explicitly corrects the
  misleading `deny.toml` comment and forbids ADR/work-item references.

### Recommended Changes

1. **Resolve the `Node` fidelity decision and prove non-corruption**
   (addresses: `set` round-trip corruption; YAML-null empty-vs-unset;
   sibling-preservation test) — Pick one of: (a) scope `Node` to string scalars
   and add a `ConfigError` variant that *refuses* non-scalar/non-mapping
   frontmatter on read (so `set` never silently mutates it), or (b) widen `Node`
   to preserve typed scalars + sequences for a loss-free round-trip. Either way:
   define how YAML null (`example:`) maps (empty-but-set vs error), preserve
   scalar text verbatim (no re-stringification), and add a test that a
   typed/sequence sibling key and key order survive a `set`.

2. **Specify nested walk/insert semantics and pin arbitrary depth**
   (addresses: type-conflict semantics; missing error variant; depth test) —
   State the collision policy for a path segment that is not a mapping (add
   `ConfigError::PathConflict { key }` or a documented overwrite), state that
   `get` through/onto a non-scalar yields `NotFound`, and add core unit tests for
   a ≥3-level path (walk + create intermediates) and each conflict case.

3. **Harden the write path against data loss** (addresses: malformed-file
   clobber; `---`-in-body split; EXDEV temp placement) — `set` must fail closed
   on a `MalformedFrontmatter`/`Io` read (only `Ok(None)` starts empty); use one
   shared split routine that treats only the first two `---` fences as delimiters
   and never re-scans the body; create the temp file inside `<root>/.luminosity/`
   (reuse the `cache.rs:80-92` pattern with cleanup-on-error). Add tests: set
   against a malformed file leaves it byte-unchanged; a body containing `---`
   round-trips exactly; a no-frontmatter and no-trailing-newline file round-trip.

4. **Fix the personal-file / `.gitignore` phase ordering** (addresses: writer
   ships before its guard) — Move the `.gitignore` edit into (or before) the
   phase that delivers `set --level personal`, or add a hard sequencing note that
   Phase 5's rule must merge no later than the personal-write capability.

5. **Decide and document the store root and the `set` default level**
   (addresses: CWD rooting across 5 lenses; team-vs-personal default) — Either
   walk upward for the nearest `.luminosity/` (git-style) or explicitly document
   CWD-only in "What We're NOT Doing" and add a from-subdirectory integration
   test. Reconsider defaulting `set` to `personal`; if team is kept, emit a
   stderr note naming the file written.

6. **Guard the architectural ban and complete the wrappers list** (addresses:
   manual-only ban verification; incomplete `serde` wrappers) — Enumerate every
   direct serde/serde_json dependent from `cargo tree -i serde` into the
   `wrappers` allow-lists; validate both the positive (add-serde-to-config fails)
   and negative (clean tree passes) checks empirically; add a committed
   regression check (invoke task/scripted test) so a future loosening fails CI.

7. **Specify error messages and cover error paths through the CLI** (addresses:
   unspecified wording; untested malformed/IO paths) — State the text for
   `NotFound` (name the key, hint `config set`), `MalformedFrontmatter` (name the
   file path + serde line/col, not a `Level` enum), and `Io` (path + operation);
   add integration cases asserting stderr content and clean stdout for a
   malformed committed config and, where feasible, an Io failure.

8. **Nail down the inbound boundary and the smaller design/standards gaps**
   (addresses: inbound port divergence; `Key` validation; not-found duplication;
   deny.toml comment; serde_yaml_ng pin; doc comments; skill registration) —
   State the inbound contract explicitly (an inbound port trait taken by
   `dispatch(&impl …)`, consistent with `version`, and assembled in `main.rs`);
   add a validating `Key` constructor; clarify the single owner of the
   NotFound→error policy; reword the `deny.toml` comment reference-free; pin
   `serde_yaml_ng`; specify `///` doc comments and the concrete `plugin.json`
   skill entry.

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: The plan is architecturally sound and well-grounded: it stands up
the workspace's first cross-crate hexagon exactly as ADR-0010 prescribes, keeps
the inward dependency direction clean (config → kernel only), correctly
diagnoses and fixes the enforcement mechanism (cargo-deny bans.deny + wrappers
rather than the inert skip/skip-tree), and models the empty-vs-unset output
contract as a domain type rather than an exit-code smuggle. Two structural
concerns stand out: the string-only Node model plus BTreeMap causes config set to
rebuild the committed team frontmatter (reordering keys, coercing types, dropping
comments), and the inbound boundary contract for the config service is
underspecified and diverges from the established inbound-port pattern without
acknowledgement.

**Strengths**:
- Cross-crate hexagon split faithfully realises ADR-0010 Model 1 (core → kernel
  only; adapters own serde/YAML/fs; no cycles).
- Correctly places `From<ConfigError> for kernel::Error` in the config crate
  (orphan rule), a correct divergence from launch's in-launcher From impl.
- Enforcement mechanism correctly corrected to bans.deny + wrappers, with a
  temporary-serde experiment as the authoritative check.
- Empty-vs-unset modelled as a domain type in the core.
- Clean concern allocation across the serde-free Node boundary.
- Appropriate resilience choices (atomic write, typed malformed error, cheap
  built-in that never touches the resolver).
- Phasing leaves each phase green and independently mergeable.

**Findings**:
- 🟡 **major** (confidence: medium) — String-only Node + BTreeMap rebuilds
  committed team frontmatter on every set. Location: Phase 2 write path / Phase 1
  Node model. BTreeMap reorders keys, non-string scalars coerce to strings,
  comments drop; the committed team file is human-maintained, so a single set
  produces a noisy, semantically-altered diff. Acknowledge the round-trip-fidelity
  tradeoff and note the intended evolution so 0011 isn't silently constrained.
- 🟡 **major** (confidence: medium) — Config inbound boundary underspecified and
  diverges from the inbound-port pattern. Location: Phase 1 ports/service; Phase 4
  dispatch & composition root. `version` exposes `ReportVersion` taken by
  `dispatch(&impl …)`; config gives inherent methods with no port, and the wiring
  text is inconsistent about whether dispatch gets the assembled service or the
  raw ports. Decide and state the inbound contract explicitly.
- 🔵 **suggestion** (confidence: medium) — Duplicate Level enum with unspecified
  core↔clap mapping. Location: Phase 4 / Phase 1. Name a total `clap::Level →
  config::Level` mapping so they can't drift.
- 🔵 **minor** (confidence: low) — FileConfigStore rooted at CWD with no rootward
  search. Location: Phase 4 composition root. From a subdirectory, resolution
  misses the repo-root `.luminosity/` and set scaffolds a second tree. If
  deliberate, note it in "What We're NOT Doing".
- 🔵 **suggestion** (confidence: medium) — dispatch signature grows one parameter
  per built-in. Location: Phase 4. Fine now; note the linear-growth tradeoff for a
  future dependencies-struct refactor.

### Correctness

**Summary**: The plan's core logic is largely sound: precedence resolution
(personal short-circuit, team fall-through), the empty-vs-unset domain type, and
clap-level rejection of bad --level are modelled correctly and satisfy their
criteria. However, several boundary behaviours are left unspecified where
correctness hinges on them — chiefly the representation of YAML null/non-scalar
nodes (which governs empty-vs-unset), the nested walk/insert semantics when a
path element is not a mapping, and the completeness of the cargo-deny serde
wrappers allow-list.

**Strengths**:
- Empty-vs-unset modelled as a domain type; Found("") correctly wins precedence
  over a non-empty team value (last-writer-wins).
- Full-stack resolution order correct (personal short-circuit → team fall-through
  → NotFound).
- Bad --level rejected via clap ValueEnum at parse time — no file touched.
- Each phase leaves `mise run` green and maps named tests to criteria; exact
  output contract reuses the verified `version` pattern.

**Findings**:
- 🟡 **major** (confidence: medium) — YAML null/non-scalar nodes have no
  representation, undermining the empty-vs-unset contract. Location: Phase 1 Node
  / Phase 2 conversion. The natural empty form `example:` parses as null, not "";
  number/bool stringification loses fidelity (`1.10`→"1.1", `007`→"7"). Define the
  empty shape, decide null/sequence mapping, preserve scalar text verbatim.
- 🟡 **major** (confidence: medium) — Nested insert semantics undefined when an
  intermediate/target node is not a mapping. Location: Phase 1 set/set_path. Can
  silently clobber data or panic. Specify a collision policy (overwrite or
  ConfigError) with a test for both cases.
- 🟡 **major** (confidence: medium) — serde wrappers allow-list omits transitive
  dependents, so deny:check may fail on legitimate edges. Location: Phase 3.
  serde_json/serde_yaml_ng are themselves direct serde dependents; enumerate every
  direct dependent from `cargo tree -i serde`; validate positive and negative
  checks empirically (could not run cargo-deny here).
- 🔵 **minor** (confidence: medium) — Path walk must yield NotFound (not
  error/panic) when traversing a scalar or landing on a mapping. Location: Phase 1
  get/get_path. Add a "personal mapping where team has scalar" fall-through test.
- 🔵 **minor** (confidence: low) — A malformed personal file blocks reads of
  team-only keys (full-stack get reads personal first and aborts). Location: Phase
  1 precedence + Phase 2 read. Decide hard-fail vs skip-and-fall-through.
- 🔵 **minor** (confidence: low) — Rooting at CWD (no project-root discovery)
  silently resolves nothing from a subdirectory. Location: Phase 4. Add a nested-
  directory test if a project root is intended.
- 🔵 **suggestion** (confidence: low) — Dotted-key split undefined for empty
  segments (`""`, `".x"`, `"core."`, `"a..b"`). Location: Phase 1 Key. Reject or
  normalise, with tests.

### Test Coverage

**Summary**: The plan is genuinely test-first and maps most acceptance criteria
to named checks, with a sound pyramid: core resolution logic unit-tested against
in-memory fakes, the adapter tested against tempdirs, and the CLI contract
black-box integration-tested per-criterion with per-test cwd isolation. The main
gaps are error-path and mutation-resilience coverage: the architectural ban has
only a manual verification, malformed/IO error paths are never exercised
end-to-end, arbitrary nesting depth is untested, and no test proves that a set
preserves unrelated sibling frontmatter keys.

**Strengths**:
- Strict test-first phasing gated on named, runnable tests mapped to criteria.
- Correct pyramid balance (unit logic vs black-box CLI contract).
- Good isolation (in-memory fakes, tempdirs, per-test cwd) matching existing
  dispatch.rs/version.rs conventions.
- Empty-vs-unset covered at both unit and CLI level.
- Bad --level pushed to clap parse-time with the no-file-touched consequence
  asserted.

**Findings**:
- 🔴/🟡 **major** (confidence: medium) — Architectural ban has only a manual,
  transient verification — no committed regression guard. Location: Phase 3. A
  later loosening passes CI silently. Add a scripted negative check that injects
  serde into config, asserts deny check fails naming serde/config, then reverts.
- 🟡 **major** (confidence: high) — Malformed-frontmatter and IO error paths never
  surfaced through the CLI. Location: Phase 4 / Testing Strategy. Add cases with a
  malformed .luminosity/config.md asserting non-zero exit, empty stdout, legible
  stderr; exercise Io where feasible.
- 🟡 **major** (confidence: high) — Arbitrary nesting depth beyond two levels never
  tested. Location: Phase 1 Success Criteria. Add a ≥3-level (a.b.c.d) walk+set
  test to pin the ADR-0003 arbitrary-depth contract.
- 🟡 **major** (confidence: high) — No test proves set preserves unrelated sibling
  frontmatter keys. Location: Phase 2 Success Criteria. Start from a multi-key
  fixture, set one nested value, assert the others survive.
- 🔵 **minor** (confidence: medium) — Path/type-conflict edge cases unspecified and
  untested (get through a scalar → NotFound; set traversing/overwriting a scalar).
  Location: Phase 1.
- 🔵 **minor** (confidence: medium) — Empty-but-set trailing newline not pinned to
  exact bytes. Location: Phase 4. Assert `stdout == "\n"` vs `stdout == ""`.
- 🔵 **suggestion** (confidence: medium) — ~11 integration cases risk duplicated
  fixture setup; plan shared helpers (write_level, run_get/run_set). Location:
  Testing Strategy.

### Code Quality

**Summary**: A well-structured, design-first hexagon that faithfully mirrors the
version/launch templates: kernel-only core, interface-segregated Read/Write
ports, static-dispatch DI, a rich error enum mapped to kernel::Error at the
boundary, and domain types (Resolved, Level, Node) modelling empty-vs-unset in
the type system. The main maintainability risks are the completeness of the
domain model (Node stringifies scalars and omits sequences, so set's whole-
document round-trip can silently corrupt sibling frontmatter) and an
under-specified error taxonomy for the nested walk/insert.

**Strengths**:
- Clean core/adapter separation across a crate boundary with cargo-deny enforcing
  direction — exemplary dependency inversion.
- Interface segregation (separate Read/Write ports, trivially faked).
- Domain-first empty-vs-unset modelling.
- Error design follows the launch pattern precisely (rich enum + From at
  boundary).
- Strong comment-hygiene adherence (corrects the misleading deny.toml comment,
  forbids references).
- Test-first, phased, independently-mergeable delivery.

**Findings**:
- 🔴/🟡 **major** (confidence: medium) — Node stringifies all scalars and omits
  sequences — set round-trip can corrupt sibling frontmatter. Location: Phase 1
  Node / Phase 2 store. `enabled: true` → `"true"`; lists lost. Either scope to
  string scalars with a reject-on-non-scalar guard, or widen Node to preserve the
  source value; add a test that a typed/sequence sibling survives set.
- 🟡 **major** (confidence: medium) — Error taxonomy has no variant for a nested
  path that traverses an existing scalar. Location: Phase 1 set_path / error.rs.
  Add `PathConflict { key }` with a named test.
- 🔵 **minor** (confidence: medium) — set-default-to-team business rule buried in
  the side-effecting inbound adapter. Location: Phase 4. Extract the Option<Level>
  decision into a pure function.
- 🔵 **minor** (confidence: medium) — Not-found represented twice
  (Resolved::NotFound + ConfigError::NotFound). Location: Phase 1. Clarify the
  single owner of the NotFound→error policy.
- 🔵 **minor** (confidence: low) — Key newtype has no constructor/validation for
  the dotted-path split. Location: Phase 1. Add a validating Key::parse.
- 🔵 **minor** (confidence: low) — FileConfigStore concentrates discovery,
  frontmatter split, YAML codec, body preservation, atomic write. Location: Phase
  2/4. Extract the pure transforms as free functions for focused unit tests.

### Safety

**Summary**: The plan gets the core write-safety shape right — atomic
temp-file+rename, explicit body preservation on read-modify-write, clap-level
rejection of a bad --level before any file is touched, and lazy scaffolding — but
leaves several data-loss and accidental-harm surfaces underspecified on the write
path. The highest-stakes gap is that the plan never states what config set does
when the existing file has malformed frontmatter, and the personal file is
gitignored (so any loss there is unrecoverable from VCS).

**Strengths**:
- Bad --level fails safe at clap parse time (no file created/modified).
- Write path explicitly atomic (temp+rename) and explicitly preserves the body.
- Phase 2 criteria already require body-preservation, malformed-frontmatter, and
  absent-file round-trip tests.
- The team file is committed (recoverable from git); only the personal file is
  gitignored.
- Config reads/writes stay off the launcher's fetch/verify/cache infrastructure —
  small blast radius.

**Findings**:
- 🔴/🟡 **major** (confidence: medium) — config set behaviour on a malformed
  existing file is unspecified — risk of silently clobbering the file. Location:
  Phase 1 set / Phase 2 read/write. Must fail closed; only Ok(None) starts empty.
  Add a criterion: set against a malformed file returns an error and leaves it
  byte-unchanged.
- 🔴/🟡 **major** (confidence: medium) — Body-split on `---` can corrupt/truncate
  the preserved body. Location: Phase 2. Use one split routine treating only the
  first two fences as delimiters; test a body containing `---`, a no-frontmatter
  file, and a no-trailing-newline file.
- 🟡 **major** (confidence: medium) — Atomic-write temp file location unspecified;
  a cross-filesystem temp defeats rename atomicity. Location: Phase 2. Create the
  temp in `.luminosity/`; clean up on failure; consider an integrity re-read.
- 🟡 **major** (confidence: medium) — Personal-file writer (Phase 4) ships before
  its .gitignore protection (Phase 5). Location: Phase 4 vs 5 ordering. Accidental
  commit of personal config between merges. Move the gitignore edit no later than
  the personal-write capability.
- 🔵 **minor** (confidence: medium) — Rooting at raw cwd scatters writes into
  unexpected .luminosity/ directories. Location: Phase 4. Discover a project root
  or document/test cwd-rooting.
- 🔵 **minor** (confidence: low) — No guard against concurrent/interleaved set
  (two separate reads → split-read window). Location: Phase 1/2. Document
  last-writer-wins; take the body from the read the service already performed.

### Usability

**Summary**: Strong on the machine-facing contract (fixed stdout/exit-code,
Found("")/NotFound modelling, git-config-style verbs, clap ValueEnum rejection of
bad --level). The main gaps are human-facing: set defaulting to the committed
shared file is a safe-default risk the work item itself flags, rooting at cwd
misbehaves from a subdirectory, and the plan pins exit codes precisely but leaves
error-message wording, help text, and the skill's invocation surface unspecified.

**Strengths**:
- Bad --level handled by clap ValueEnum — names valid values, touches no file.
- Empty-vs-unset a first-class result giving callers an unambiguous contract.
- get/set verbs, dotted addressing, single-newline output mirror git config /
  version.
- The get/set contract is fully enumerated in Phase 4 criteria.

**Findings**:
- 🟡 **major** (confidence: medium) — set defaults to the shared, committed file —
  accidental shared writes. Location: Phase 4 / work item Open Questions.
  Reconsider defaulting to personal; if team kept, emit a stderr note naming the
  file written.
- 🟡 **major** (confidence: medium) — Store rooted at CWD, not a discovered
  project root — misbehaves from subdirectories. Location: Phase 4 main.rs. Walk
  upward like git, or document and test cwd-only behaviour.
- 🟡 **major** (confidence: medium) — Error-message wording unspecified;
  MalformedFrontmatter names a Level enum, not the file path. Location: Phase 1
  error.rs / Phase 4. Specify text (NotFound names key + hints config set;
  MalformedFrontmatter names the path + line/col; Io names path + operation);
  assert stderr content.
- 🔵 **minor** (confidence: high) — No doc comments on config/get/set/--level →
  empty --help entries. Location: Phase 4. Specify self-teaching doc comments.
- 🔵 **minor** (confidence: medium) — set silently creates a directory and
  committed file with no feedback. Location: Phase 2/4. Emit a first-time-creation
  stderr note; keep stdout clean.
- 🔵 **suggestion** (confidence: low) — Skill invocation surface underspecified
  (description/argument-hint). Location: Phase 5. Name the get/set operations,
  dotted-key convention, and team/personal semantics.

### Standards

**Summary**: Strongly convention-aware: the two new crate manifests faithfully
copy the verify minimal-member template, the workspace stays versionless with the
new library crates at the same non-version-bearing 0.1.0-pre.0 as kernel/verify,
and the deny.toml ban entry format mirrors the live native-tls exemplar. The main
standards issue is comment hygiene: the plan directs leaving a deny.toml comment
that embeds a work-item reference and narrates a pending change, contradicting the
very convention the plan itself restates.

**Strengths**:
- New manifests follow the cli/verify template (edition 2021, rust-version, MIT,
  publish=false, [lints] workspace = true, path-only deps).
- Version coherence respected (versionless workspace; new crates non-version-
  bearing; launcher sole version-bearing crate).
- deny.toml entries reuse the { crate, wrappers } shape and correctly widen
  serde/serde_json wrappers to include luminosity.
- configure SKILL.md specified with the documented frontmatter fields and
  ${CLAUDE_PLUGIN_ROOT} addressing.

**Findings**:
- 🔴/🟡 **major** (confidence: high) — Plan directs leaving a deny.toml comment
  that embeds a work-item reference and narrates a pending change. Location: Phase
  3 #1. Reword to state-descriptive, reference-free (drop the "(work item 0009)"
  parenthetical and "adds the first such entry" narration).
- 🔵 **minor** (confidence: medium) — New serde_yaml_ng workspace.dependencies
  entry has no version pin. Location: Phase 1 #1. Name a concrete
  MSRV-compatible pin matching existing entries.
- 🔵 **minor** (confidence: medium) — New crates add rust-version, multiplying the
  hand-synced MSRV mirror (kernel omits it, verify keeps it). Location: Phase 1/2
  manifests. Pick one and note the sync obligation.
- 🔵 **minor** (confidence: low) — Skill registration format (path vs object) and
  category placement unspecified — repo's first skill sets the pattern. Location:
  Phase 5 #2/#3. State the concrete plugin.json entry and category.

### Portability

**Summary**: Portability-sound in its core design: YAML/serde/filesystem concerns
are quarantined in config-adapters behind a serde-free Node tree, making the YAML
library a fully substitutable detail, and there is zero cloud/vendor lock-in —
only std::fs and a local YAML parser. The main risks are under-specification of
the atomic temp-file+rename semantics (same-directory/EXDEV not pinned despite the
launcher's cache.rs exemplar), an unstated requirement that the YAML crate stay
pure-Rust to preserve the musl static build, and LF-only line-ending assumptions.

**Strengths**:
- The core/adapter split gives excellent vendor independence; the YAML library is
  fully substitutable (yaml-rust2 fallback proves it).
- No cloud/service coupling — purely local filesystem + std.
- Rooting at cwd avoids hardcoded absolute paths (portable, git-like posture).
- cargo-deny graph targets already cover both darwin and both musl-Linux triples,
  so the serde_yaml_ng license/advisory/ban evaluation matches the real targets.

**Findings**:
- 🔴/🟡 **major** (confidence: medium) — Atomic-write temp-file location
  unspecified; a cross-filesystem temp defeats rename atomicity (EXDEV). Location:
  Phase 2 write. Create the temp inside `<root>/.luminosity/` and reuse the
  write_then_rename pattern from cache.rs:80-92 (with cleanup-on-error).
- 🟡 **major** (confidence: medium) — The YAML crate must be pure-Rust (no C
  libyaml linkage) to preserve the musl static build — an unstated invariant.
  Location: Implementation Approach / Phase 2 manifest. Record the constraint;
  confirm serde_yaml_ng's closure passes deny.toml's unmaintained/license checks
  (yaml-rust2 as vetted fallback).
- 🔵 **minor** (confidence: low) — LF-only frontmatter delimiter/reassembly; a
  CRLF checkout yields `---\r`, risking spurious MalformedFrontmatter or body
  corruption. Location: Phase 2. Trim trailing `\r` on the delimiter match; add a
  CRLF fixture.
- 🔵 **minor** (confidence: low) — FileConfigStore rooted at cwd with no ancestor
  search couples resolution to invocation directory (portable but
  context-sensitive under agents/CI/subshells). Location: Phase 4. Document the
  cwd contract; confirm path construction uses Path::join throughout.

---

## Re-Review (Pass 2) — 2026-07-05

**Verdict:** REVISE

The eight recommended changes from Pass 1 were applied in full, and the re-review
confirms **every one of the 21 major findings from Pass 1 is resolved** — the
structural/foundational issues (Node corruption, walk/insert semantics, write-path
data-loss, phase ordering, ban guard, error paths, inbound boundary) are gone, and
the safety, usability, and standards lenses now report only minor/suggestion-level
items. However, the two changes that added the most new surface — project-root
discovery and the gitignore/`set`-default rework (Recommended Changes 4 and 5) —
introduced a second layer of lower-blast-radius findings, plus one pre-existing
minor (CRLF) that was not addressed and has escalated. Verdict remains REVISE on
the ≥3-major threshold, but the character of the findings has shifted decisively:
Pass 1 was foundational/structural; Pass 2 is factual-correction + discovery
follow-ons + edge-case hardening, all localised.

### Previously Identified Issues

- 🟡 **Node round-trip corruption** (arch/correctness/code-quality/test-coverage) — **Resolved** (typed, order-preserving `Node` + `serde-saphyr`; sibling type/order-preservation tests added).
- 🟡 **Nested walk/insert semantics undefined** (correctness/code-quality/test-coverage) — **Resolved** (walk-resolution rule, `PathConflict`, ≥3-level tests).
- 🟡 **`set` clobbers a malformed file** (safety) — **Resolved** (fail-closed `set`; byte-unchanged test).
- 🟡 **Body split on `---`** (safety) — **Resolved** (shared first-two-fences split routine; embedded-`---`/no-trailing-newline tests).
- 🟡 **EXDEV temp location** (safety/portability) — **Resolved** (`.luminosity/tmp/` same-filesystem write-then-rename).
- 🟡 **Writer ships before its `.gitignore` guard** (safety) — **Resolved** (gitignore folded into Phase 4).
- 🟡 **Ban manual-only + incomplete wrappers** (test-coverage/correctness) — **Resolved** (committed pytest regression guard; empirical `cargo tree -i` enumeration; negative check forces completeness).
- 🟡 **Malformed/IO error paths untested through CLI** (test-coverage) — **Resolved** (stderr-content assertions added).
- 🟡 **Arbitrary depth + sibling preservation untested** (test-coverage) — **Resolved** (≥3-level + sibling tests).
- 🟡 **No `PathConflict` variant** (code-quality) — **Resolved**.
- 🟡 **Inbound boundary underspecified** (architecture) — **Resolved** (`ConfigAccess` port; `dispatch(&impl ConfigAccess)`).
- 🟡 **`set` defaults to shared team file** (usability) — **Resolved** (defaults to personal; work item AC updated).
- 🟡 **CWD rooting** (5 lenses) — **Resolved** as a concept (project-root discovery), but the discovery mechanism introduced new follow-on findings (see below).
- 🟡 **Error wording unspecified / `MalformedFrontmatter` names a Level** (usability) — **Resolved** (messages specified; variants carry the file path).
- 🟡 **YAML crate must be pure-Rust (musl)** (portability) — **Partially resolved** — the plan states pure-Rust, but the `serde-saphyr` acceptance gate does not yet include the no-C/`*-sys` static-link dimension explicitly (see New Issues).
- 🟡 **`deny.toml` comment reference/staleness** (standards) — **Resolved** (reword-to-state-descriptive instruction).
- 🔵 **CRLF line endings in frontmatter split** (portability, minor in Pass 1) — **Still present, escalated to major** — Change 3's shared split routine did not add `\r` trimming; a `---\r` fence is misparsed as no-frontmatter.

### New Issues Introduced

Discovery-related (from Recommended Change 5):
- 🟡 **correctness (high)** — The `.gitignore` rationale is factually wrong: `.luminosity/config.local.md` contains a mid-string slash, so Git anchors it to the repo root — it does **not** "match at any depth". A personal file under a discovery-rooted nested `.luminosity/` would be tracked, defeating the never-commit guarantee. Fix: use `**/.luminosity/config.local.md` + `**/.luminosity/tmp/` (or anchor deliberately) and correct the rationale.
- 🟡 **portability/correctness** — Discovery's `.git` "directory-existence check" misses git worktrees/submodules, where `.git` is a *file*. Fix: existence check (file or dir), not `is_dir`; add a `.git`-as-file fixture.
- 🟡 **test-coverage (high)** — The discovery upward-walk can escape a cargo tempdir (under `cli/target/`, inside the real repo) into the real `.git`/`.luminosity`, breaking test isolation. Fix: plant a boundary marker at each tempdir root; state it as an isolation requirement.
- 🟡 **architecture** — Eager `FileConfigStore::discover` in `main.rs` runs a filesystem walk on every invocation (incl. `version` and external dispatch), diverging from the deliberate lazy-built-in pattern (`LazyProductionResolver`). Fix: discover only when `Command::Config` is dispatched.
- 🔵 **architecture (minor)** — Discovery prefers any ancestor `.luminosity/` over a nearer `.git`; nearest-boundary-wins would be less surprising in nested repos.

Fail-loud / write-path:
- 🟡 **correctness** — Fail-loud is asymmetric: full-stack `get` walks personal first and returns on a scalar hit, so a malformed **team** file goes undetected whenever personal resolves — contradicting the "any level involved" claim. Fix: read+validate both levels before resolving; add the symmetric test.
- 🟡 **test-coverage** — The fail-loud-`get` / fail-closed-`set` clobber guard has no **Phase 1 core** unit test (only Phase 2/4). Fix: add a fail-loud `get` (personal reader errors, team holds value → `Err`) and fail-closed `set` (reader errors → writer fake never called).
- 🟡 **architecture / 🔵 safety+correctness** — Concurrent `set` is an unguarded read-modify-write; interleaved writes last-writer-wins on the whole document, silently dropping a key. Fix: document the single-writer assumption, or add an advisory lock.

Dependency / portability:
- 🟡 **portability** — CRLF (above), `.git`-as-file (above), and the `serde-saphyr` musl/no-C-`*-sys` static-link gate need to be explicit acceptance gates.

Code-quality / standards / usability (mostly minor, a few worth a quick pass):
- 🟡 **code-quality** — The `set` nested walk/insert is the highest-complexity unit and is left undecomposed; suggest naming `descend`/`upsert` helpers.
- 🔵 **code-quality** — Scalar→string rendering placed in the core rather than the inbound adapter (diverges from `version`'s render-in-adapter); `Resolved::Found(Scalar)` + adapter rendering would match.
- 🔵 **code-quality** — Two-port `ConfigService<R, W>` is awkward when one `FileConfigStore` implements both; decide reference-holding vs a single `S: Read + Write` bound.
- 🔵 **code-quality** — `Resolved::NotFound` vs `ConfigError::NotFound` share a name across layers; consider `Resolved::Absent`.
- 🔵 **standards** — The illustrative `serde` `wrappers` deny.toml line exceeds 80 cols (no TOML auto-formatter); wrap one entry per line.
- 🔵 **standards** — Pin the concrete `serde-saphyr` version; clarify crate-naming convention (bare `config` is a very common crates.io name).
- 🔵 **test-coverage** — Float rendering/round-trip and null typed-parse under-tested; `InvalidKey` not asserted through the CLI.
- 🔵 **usability** — Not-found states the problem but not the remedy; no `list`/`--show-origin`; `PathConflict` is a CLI dead-end (defer `unset`/`--force` explicitly); help should name the backing files and their committed/gitignored nature.
- 🔵 **safety** — Atomic write lacks fsync/durability and orphaned-temp cleanup on rename-failure/SIGKILL; a `set` outside any repo scaffolds `.luminosity/` at cwd silently.

### Assessment

The plan is now structurally sound and the foundational risk is retired — Pass 2
found **no** structural or data-model defects, and the safety/usability/standards
lenses dropped to minor-only. The remaining REVISE weight is a factual gitignore
error (introduced in Change 5), a fail-loud-symmetry spec gap, an unaddressed CRLF
edge case, and a cluster of discovery follow-ons (worktree `.git`-as-file, test
isolation, eager-vs-lazy, nested-repo precedence). These are all localised and
mostly small edits — a focused third pass on the discovery mechanism, the gitignore
patterns, the fail-loud symmetry, and CRLF would clear the majors and bring the
plan to APPROVE. Recommend one more edit round targeting those, then a light
re-verify of the correctness/portability/test-coverage/architecture lenses.

---
*Re-review generated by /accelerator:review-plan*

---

## Re-Review (Pass 3, light re-verify) — 2026-07-06

**Verdict:** APPROVE

A focused re-verify of the four lenses that carried Pass-2 majors (architecture,
correctness, test-coverage, portability) confirms **all ten Pass-2 majors are
resolved**. The re-verify returned only two fresh majors — both cheap
(one documentation, one a scoping sharpening of a Pass-2 fix) — which have now
been addressed, along with the cheap minors. No structural, data-model, or
data-loss defects remain across any pass. The plan is implementation-ready.

### Previously Identified Issues (Pass 2 majors)

- 🟡 **Eager discovery breaks lazy built-in pattern** (architecture) — **Resolved** (lazy `ConfigAccess` impl defers `discover` to first `config` use, mirroring `LazyProductionResolver`; `version`/external dispatch do no fs walk).
- 🟡 **No concurrency guard on `set`** (architecture) — **Resolved** as an explicit single-writer tradeoff (whole-document last-writer-wins, distinguished from ADR-0003's per-key precedence; atomic temp+rename prevents corruption).
- 🟡 **Gitignore mid-slash anchoring** (correctness) — **Resolved** (`**/.luminosity/config.local.md` + `**/.luminosity/tmp/`, accurate anchoring rationale, nested `check-ignore` assertion).
- 🟡 **Fail-loud asymmetry** (correctness) — **Resolved** (full-stack `get` reads+validates both levels before resolving; symmetric core tests).
- 🟡 **Discovery walk escapes tempdir** (test-coverage) — **Resolved** (explicit Test-isolation note; now scoped to *every* config test).
- 🟡 **No Phase-1 core test for fail-loud/fail-closed** (test-coverage) — **Resolved** (symmetric fail-loud `get` + fail-closed `set` core criteria against fakes).
- 🟡 **CRLF frontmatter split** (portability) — **Resolved** (`\r`-trim on fence detection + CRLF test; write-back LF-normalisation noted).
- 🟡 **`.git`-as-a-file worktrees/submodules** (portability) — **Resolved** (existence check, file-or-dir; `.git`-file test case).
- 🟡 **serde-saphyr musl/no-C gate** (portability) — **Resolved** (explicit pure-Rust/no-C-`*-sys` gate + a standing `cargo tree -p config-adapters` check).

### New Issues (Pass 3) — all now addressed

- 🟡 **architecture** — deny.toml `wrappers` couples to the full transitive graph (an upstream bump adding a direct `serde` parent fails `deny:check` on a legal edge). **Addressed**: documented as an accepted tradeoff with a mechanical recovery procedure (re-run `cargo tree -i`, add the parent — an allow-list gap, not a violation).
- 🟡 **test-coverage** — the isolation requirement was scoped to "discovery/from-subdirectory tests", but *every* config invocation discovers; the absent-file negatives and set-creation tests are the dangerous ones. **Addressed**: isolation note now applies to every config integration test, naming the absent-file and set-creation cases explicitly.
- 🔵 **minors, addressed**: single-pass repo-bounded discovery (`.luminosity/`-then-`.git` per ancestor, enclosing `.git` bounds the walk); null/non-mapping document-root treated as empty `Mapping` for `set`; out-of-`i64` integer added to the type-fidelity caveat; config-crate `luminosity-config` fallback name; concurrency loss clarified as whole-document; `Float` rendering criterion; `InvalidKey` on `set` (creates no `.luminosity/`); i64-overflow parse test; `*-sys`-free standing check; CRLF write-back LF-normalisation note.

### Cosmetic refinements — subsequently applied

Both items initially deferred at Pass 3 were then applied to the plan:

- Scalar→string rendering moved from the core into the inbound adapter: `get` now
  returns `Resolved::Found(Scalar)`, and a pure `render(&Scalar) -> String` on the
  inbound side owns the display rules (unit-tested in the launcher, mirroring
  `version`'s `render`) — aligning with the hexagon template and readying the typed
  value for 0011's schema consumer.
- `Resolved::NotFound` renamed to `Resolved::Absent`, so the domain outcome
  (`Resolved::Absent`) and the boundary error (`ConfigError::NotFound`) no longer
  share a name.

### Assessment

Three passes in, the plan is sound and implementation-ready: no criticals at any
point, every major across all passes resolved, and the remaining items are the two
deferred cosmetic refinements above. The last round of fixes was applied after the
re-verify lens run (not itself re-verified), but all were low-risk documentation /
test-criteria / edge-case edits with no structural impact. Recommend proceeding to
`/implement-plan`.

---
*Re-review generated by /accelerator:review-plan*
