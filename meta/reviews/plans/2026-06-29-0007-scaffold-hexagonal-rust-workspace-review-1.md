---
type: plan-review
id: "2026-06-29-0007-scaffold-hexagonal-rust-workspace-review-1"
title: "Plan Review: Scaffold the Hexagonal Rust Workspace with a version Subcommand"
date: "2026-06-28T23:38:45+00:00"
author: "Toby Clemson"
producer: review-plan
status: complete
parent: "plan:2026-06-29-0007-scaffold-hexagonal-rust-workspace"
target: "plan:2026-06-29-0007-scaffold-hexagonal-rust-workspace"
reviewer: "Toby Clemson"
verdict: "APPROVE"
lenses: [architecture, code-quality, test-coverage, correctness, standards, portability, compatibility]
review_number: 1
review_pass: 2
tags: [rust, cli, hexagonal, scaffold, cargo-pup, vergen, mise]
last_updated: "2026-06-29T00:07:40+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Plan Review: Scaffold the Hexagonal Rust Workspace with a version Subcommand

**Verdict:** REVISE

This is a disciplined, convention-aware plan: it realises ADR-0009's hexagon
faithfully (ports as traits in the core, thin adapters, a composition root, an
in-memory fake proving the port boundary), is explicitly TDD-driven, phases the
work into three independently-mergeable steps in correct dependency order, and
respects the project's lint wall and task-tree conventions. The reason for
REVISE is concentrated in one subsystem: the vergen build-metadata mechanism.
A compile-time `env!("VERGEN_GIT_SHA")` read combined with the `gitcl` backend's
"git is present everywhere" premise is a **build-breaking** correctness risk in
git-less / shallow / tarball build contexts, and the black-box test assertions
around SHA, build date, and triple are fragile (wall-clock windows, format
mismatches, build-script caching, self-referential comparisons). Fixing the
metadata sourcing and re-grounding the tests against the build-baked values
resolves the bulk of the findings.

### Cross-Cutting Themes

- **vergen/git build-metadata is fragile across build contexts** (flagged by:
  correctness, portability, compatibility) — `env!` on the VERGEN vars is a hard
  compile error if the var is unset; the `gitcl` backend assumes a `git` binary
  plus a real `.git` in every build context (false for tarball/vendored/minimal
  contexts); the no-git fallback path is undefined. This is the single most
  important area to revise.
- **Build-metadata test assertions are fragile or self-referential** (flagged
  by: test-coverage, correctness, portability) — the "recent window" date check
  is wall-clock-dependent and flaky under build-script caching; the SHA-equals-
  `git rev-parse HEAD` check assumes full-length, clean, exactly-formatted
  agreement and depends on a git binary on the test host; the host-triple check
  compares vergen's value against itself. The consistent fix recommended across
  lenses: compare against `env!("VERGEN_*")` baked into the *same* build instead
  of re-shelling git or using `now()`.
- **The sole inward-direction enforcer is not proven against the real hexagon**
  (flagged by: architecture, test-coverage, correctness, compatibility) — the
  pup probe-mirror proves the rule *shape* on a throwaway crate; the only
  automated check on the real `pup.ron` asserts it parses, not that its regex
  binds to the real `version::core` module path. A wrong path silently enforces
  nothing while staying green.
- **The version field bypasses the outbound port** (flagged by: architecture,
  code-quality) — three build facts flow through `BuildMetadata`, but `version`
  is read directly via `env!("CARGO_PKG_VERSION")` in the core, an unacknowledged
  asymmetry that also makes that field un-fakeable.
- **The empty kernel error enum makes its mandated test vacuous** (flagged by:
  architecture, code-quality, test-coverage) — a never-constructed enum cannot
  exercise `Display`, so the promised "rendered message" test cannot exist as
  described.
- **Dual-toolchain / MSRV dependency compatibility is unreconciled** (flagged
  by: compatibility, standards) — placeholder dep pins are not validated against
  the `msrv = 1.90.0` mirror, and the new vergen build-dep must *also* compile
  under cargo-pup's pinned `nightly-2026-01-22`.

### Tradeoff Analysis

- **`gitcl` (lighter deps, git-CLI assumption) vs `gix`/`vergen-gix`
  (self-contained, heavier transitive tree)**: The plan defers this to a
  `deny:check` dep-weight/licence outcome and defaults to `gitcl`. Portability
  and correctness lenses prefer `gix` (no external git binary) or, at minimum, a
  graceful `option_env!` fallback; compatibility and the project's
  dependency-resisting ethos prefer `gitcl`. **Recommendation:** keep `gitcl` as
  the default *but* make git-absence a first-class case (vergen
  `fail_on_error(false)` / default emit + `option_env!` fallback in the adapter),
  so the choice is a deliberate portability decision rather than an implicit host
  dependency.

### Findings

#### Critical

- 🔴 **Correctness**: `env!("VERGEN_GIT_SHA")` fails to compile when vergen omits the var (no-git / shallow / failed git)
  **Location**: Phase 2, Section 4 (version/outbound/build_metadata.rs) + Section 3 (build.rs)
  `env!` is a hard compile error if the variable is unset, and vergen's git
  emitters do not unconditionally emit `VERGEN_GIT_SHA` (no `.git`, tarball/
  vendored builds, certain shallow/detached states, or `git` absent for gitcl).
  This can pass CI (where `git rev-parse HEAD` succeeds) yet break a real release
  build. Use `option_env!` with an explicit fallback, or configure vergen to
  always emit a default on error.

#### Major

- 🟡 **Architecture**: The sole inward-direction enforcer is never automatically verified against the real hexagon's module paths
  **Location**: Phase 3, Section 2 (cargo-pup probe)
  The probe-mirror exercises a throwaway crate; the only automated check on the
  real config (`test_repo_pup_ron_actually_loads`) asserts it parses, not that
  the rule rejects a real violation. A typo in the real module-path regex stays
  green while enforcing nothing.

- 🟡 **Correctness**: Build-script caching breaks both the "recent window" date assertion and the "SHA changes after a commit" check
  **Location**: Phase 2, Section 5 (AC5 date assertion) + Manual Verification
  Cargo reuses cached build-script output when `rerun-if-*` inputs are unchanged,
  so a valid incremental build can carry a stale timestamp/SHA — making the
  window test flaky and the SHA-changes invariant silently false. Verify vergen
  emits `rerun-if-changed` for the git ref files and relax the date assertion.

- 🟡 **Correctness**: Printed SHA == `git rev-parse HEAD` assumes full-length, clean, exact format agreement
  **Location**: Phase 2, Section 5 (AC5 black-box test)
  vergen may emit a short SHA and/or a `-dirty` suffix on a dirty working tree
  (the jj-colocated working copy is exactly that condition), while
  `git rev-parse HEAD` returns the full clean 40-char hash — a spurious-failure /
  too-weak-equality risk. Compare against `env!("VERGEN_GIT_SHA")` instead.

- 🟡 **Correctness**: Claim that git is present in every build context is not universally true
  **Location**: Implementation Approach, Decision 2 + Phase 2, Section 3
  Minimal release/CI containers, source-tarball, and vendored-crate builds
  frequently lack the `git` CLI; with `gitcl` that triggers the no-git path,
  which combines with the `env!` issue into a silent compile failure in the
  leanest (often release) environment.

- 🟡 **Portability**: Default `gitcl` backend bakes a "git binary present" assumption into every build context
  **Location**: Implementation Approach, Decision 2; Phase 2, Section 3
  (Merges with the correctness git-present finding from a portability angle.)
  `gix`/`vergen-gix` is self-contained and removes the hidden host-tool
  prerequisite; if any non-git-checkout build context is plausible, prefer it, or
  document the prerequisite explicitly.

- 🟡 **Portability**: Compile-time `env!()` on vergen vars turns a missing-metadata build into a hard failure with no fallback
  **Location**: Phase 2, Section 4 (version/outbound/build_metadata.rs)
  (Same root cause as the critical correctness finding, from the portability
  lens.) Use `option_env!(...)` with an `"unknown"` fallback so the binary stays
  buildable in degraded environments.

- 🟡 **Test Coverage**: The black-box build-date assertion is time-dependent and under-specified
  **Location**: Phase 2, Section 5 (build-date assertion)
  A wall-clock "within a generous recent window" check can both falsely fail
  (slow/cached builds) and give false confidence (too-generous window). Tie the
  assertion to the build (compare against `env!("VERGEN_BUILD_TIMESTAMP")`) plus
  "not in the future", rather than `now()`.

- 🟡 **Test Coverage**: AC1's "one of the four shipped triples" property is asserted by no automated test
  **Location**: Phase 2, Section 5 (triple assertion vs AC1)
  Softening to host-triple equality is sound for the gnu runner, but it leaves
  the four-triple-membership AC unverified anywhere; the host-equality check is
  self-referential (vergen's value vs itself). Add a release-build assertion that
  the embedded triple is one of the four, or explicitly cite where `build:cli`
  covers it.

- 🟡 **Standards**: Plan omits updating `tasks/README.md`, the documented SSOT for task-tree shape
  **Location**: Phase 1, Section 3
  A new `kernel` component, its `kernel:check` roll-up, and `test:unit:kernel`
  change the shape the README documents, but the plan never updates it — defeating
  the "learn the shape once" convention.

- 🟡 **Standards**: `kernel:check` departs from the documented "`<component>:check` folds into `check`" pattern
  **Location**: Implementation Approach, Decision 1; Phase 1, Section 3
  It is the first component roll-up *not* part of aggregate `check`. The
  departure is justified (avoid a second per-crate tool startup) but should be
  documented in the task `description` string and the README, not only in test
  comments.

- 🟡 **Compatibility**: Placeholder dependency pins not validated against the MSRV (1.90.0)
  **Location**: Phase 2, Section 1 (central dependency pinning)
  `clap`/`vergen`/`time` advance their own MSRV across releases; Cargo can
  resolve to a version whose `rust-version` exceeds 1.90.0 and break the pinned
  toolchain. Make MSRV-compatibility an explicit pin criterion and rely on a
  committed `Cargo.lock`.

- 🟡 **Compatibility**: vergen build-dependency must also compile under cargo-pup's pinned `nightly-2026-01-22`
  **Location**: Phase 2, Section 3 + Phase 3 (pup print-modules)
  `pup:check` compiles `cli` (including `build.rs` and its build-deps) under the
  older nightly. A dep version that builds on stable 1.90.0 may fail on the
  pinned nightly, breaking the architecture lane while the product build is
  green. Verify `cargo +nightly-2026-01-22 pup print-modules` compiles after the
  build-dep is added; bump `PUP_NIGHTLY`/`PUP_VERSION` if required.

#### Minor

- 🔵 **Architecture**: The authored pup rule is narrower than the stated inward dependency rule
  **Location**: Phase 3, Section 1 (pup.ron)
  The RON only denies `version::inbound`/`version::outbound` imports; it does not
  prevent the core importing infrastructure crates (`clap`, `vergen`, etc.). In
  the single-crate phase the cross-crate deny ban-list is inert, so this is the
  whole guard. Prefer an `allowed_only` allow-list for the core.

- 🔵 **Architecture / Code Quality**: Build-time facts split inconsistently — version read via `env!` in the core
  **Location**: Phase 2, Section 4 (VersionReport) + Section 5 (AC4 fake test)
  Three facts go through the `BuildMetadata` port; `version` is read directly in
  the core, so it cannot be varied by the fake. Route it through the port too, or
  explicitly document why `CARGO_PKG_VERSION` is treated as an intrinsic compile
  constant.

- 🔵 **Architecture / Code Quality / Test Coverage**: Empty `kernel::Error` enum makes the mandated `Display`/`Error` test vacuous
  **Location**: Phase 1, Section 2 (kernel/src/lib.rs)
  A never-constructed enum cannot exercise rendering, so the promised "rendered
  message" test cannot exist as described, and the dispatch seam is type-level
  only. Defer the test (and the variant) until TDD pressure produces a real
  variant, and drop the Phase 1 claim that `Display` behaviour is tested.

- 🔵 **Correctness**: pup regex matchers may under-/over-match the core module
  **Location**: Phase 3, Section 1 (pup.ron matchers)
  If the `^luminosity::version::core` path differs from what `print-modules`
  reports, the rule silently matches nothing yet shows green. Assert the probe
  against the exact path strings `print-modules` emits for the real crate.

- 🔵 **Correctness / Code Quality**: `&str` port vs `String` report — specify infallible `to_owned()` assembly
  **Location**: Phase 2, Section 4 (BuildMetadata trait + VersionReport)
  The `&str`-returning port presupposes `'static`-backed storage and forces a
  copy into the `String` report; a careless conversion could trip the
  `unwrap`/`expect` ban. Specify infallible `to_owned()` assembly, or return
  owned `String`/`Cow<'_, str>` from the port for future dynamic adapters.

- 🔵 **Test Coverage**: Host-triple equality assertion is self-referential
  **Location**: Phase 2, Section 5 (host-triple assertion)
  Both sides derive from the same vergen output, so a wrong-but-non-empty triple
  passes. Pair the plumbing check with an independent reference (host triple from
  `std`/`cfg`) where feasible.

- 🔵 **Test Coverage**: pup probe-mirror proves rule shape, not real-path binding
  **Location**: Phase 3, Section 2
  (Reinforces the architecture major from a coverage angle.) Have
  `test_repo_pup_ron_actually_loads` (or a sibling) assert the real
  `version::core` path appears in `print-modules` output and is matched by the
  configured regex.

- 🔵 **Test Coverage / Portability**: Black-box SHA test couples to an external `git` binary on the test host
  **Location**: Phase 2, Section 5 (AC5 SHA assertion)
  Re-shelling `git rev-parse HEAD` makes the suite non-portable to git-less test
  environments and couples it to HEAD state at test time (which may differ from
  the built artefact). Compare against `env!("VERGEN_GIT_SHA")` baked into the
  build.

- 🔵 **Standards**: `tasks/test/kernel.py` snippet references `KERNEL_CRATE` without the import / full structural mirror
  **Location**: Phase 1, Section 3
  Under ruff `ALL` + pyrefly strict, the module must be a full structural copy of
  `tasks/test/cli.py` (imports, docstring, `REPO_ROOT` cd, `Exit` handling), not
  just the differing line. Note this in the plan.

- 🔵 **Standards**: Two-location registration in `__init__.py` collections is glossed as one step
  **Location**: Phase 1, Section 3
  Family `__init__.py` imports *and* the hand-built `ns_format`/`ns_lint`
  Collections in top-level `tasks/__init__.py` both need `kernel` lines; missing
  the latter leaves `format.kernel.*`/`lint.kernel.*` unresolvable. Make both
  explicit.

- 🔵 **Standards**: Module-file style (`version/mod.rs` vs sibling-file) sets a precedent — make it deliberate
  **Location**: Phase 2, Section 4 (module layout)
  No in-repo precedent exists; this scaffold sets the style every later subdomain
  copies. Record the choice rather than leaving it incidental.

- 🔵 **Compatibility**: License allow-list may need per-crate exceptions for vergen/gix transitive crates
  **Location**: Phase 2, Section 1 + Success Criteria (deny:check)
  `gitcl` (the default) avoids the gix tree and is safe; if `gix` is chosen, run
  `deny:check` first and add any surfaced licences strictly via per-crate
  `[[licenses.exceptions]]` (never the blanket `allow`), per deny.toml's policy.

- 🔵 **Compatibility**: cargo-pup v0.1.8 `Module`/`RestrictImports` syntax is asserted, not yet exercised
  **Location**: Phase 3, Section 1
  The RON shape is a hard contract with the pinned binary and is not used by the
  existing probe (which uses `Struct`/`Name`). Make "the real `pup.ron` parses
  and loads non-empty" an explicit gating assertion before relying on the syntax.

#### Suggestions

- 🔵 **Code Quality**: Pin output formatting to a single rendering function in the inbound adapter
  **Location**: Phase 2, Section 4 (version/inbound/cli.rs)
  Keep a single `render(&VersionReport) -> String` in the adapter so the
  composition root only wires/dispatches and rendering is independently testable.

- 🔵 **Code Quality / Test Coverage**: Extract shared Rust task-command construction to reduce per-crate duplication
  **Location**: Phase 1, Section 3-4
  The kernel task modules and their command-string tests duplicate the cli ones
  verbatim except `-p kernel`. Consider a parameterised helper in
  `tasks/shared/rust.py` (and crate-parametrised tests) so the convention lives
  once as crates multiply.

- 🔵 **Architecture**: Make the vergen backend choice an explicit resilience decision, not only a licence outcome
  **Location**: Implementation Approach, Decision 2
  Record which build contexts the `gitcl` git-present assumption relies on.

- 🔵 **Compatibility / Standards**: Consider hoisting `edition`/`rust-version` into `[workspace.package]`
  **Location**: Phase 1, Section 2 + Phase 2 (manifests)
  Inheriting a shared edition + `rust-version = "1.90.0"` makes the MSRV/edition
  contract uniform and gives Cargo an MSRV-aware resolver signal.

- 🔵 **Portability**: Validate the chosen vergen backend under the ADR-0002 zigbuild release path (story 0008)
  **Location**: Phase 1 wiring + build model
  `build:cli` is host-native; the actual release path cross-compiles via
  zigbuild. Note that the backend must be confirmed working there too, not only
  host-native.

- 🔵 **Portability / Standards**: Reconcile work-item AC1 text with the plan's host-triple softening
  **Location**: Work item 0007 AC1 vs Phase 2 Tests
  Record that four-triple membership is a release-build shape property while the
  runtime self-report is host-triple-correct, so the divergence is documented at
  the AC.

### Strengths

- ✅ Ports are correctly modelled as traits living with the core (both
  `ReportVersion` inbound and `BuildMetadata` outbound in `version/core.rs`),
  matching ADR-0009's "ports live with the domain" rule.
- ✅ The composition root constructs the core against the trait, never the
  concrete adapter, preserving dependency inversion and enabling the AC4 fake —
  the port boundary is proven real, not decorative.
- ✅ Presentation is kept out of the core (`VersionReport` is a value object;
  formatting lives in the clap adapter); `main.rs` is a thin composition root.
- ✅ Test-first is baked into every phase with explicit red-before-green
  sequencing, and each acceptance criterion is mapped to a specific named test.
- ✅ The three phases each leave `main` green and are independently mergeable, in
  correct dependency order (kernel → hexagon → pup rule).
- ✅ The lint wall (no `unwrap`/`expect`/`panic`) is correctly extended to the
  build script and tests, with concrete guidance to use `?`/`assert_eq!`/`match`.
- ✅ The kernel manifest faithfully mirrors `cli` (edition 2021, MIT,
  `[lints] workspace = true`); naming follows the entity-first roll-up convention
  and the "no `<component>:fix`" / "library crates get no `build:*`" rules.
- ✅ Correctly identifies the gnu-vs-musl host divergence and the need to extend
  the deny licence allow-list, and reuses existing CI jobs so no new
  branch-protection registration is required.
- ✅ Defaults to the lighter `gitcl` backend over the heavy gix tree, honouring
  the dependency-resisting ethos and sidestepping native-tls risk.

### Recommended Changes

1. **Make build-metadata sourcing resilient to git-less / missing-var builds**
   (addresses: the critical `env!` finding, "git present in every context",
   "gitcl bakes git assumption", "env!() no fallback"). In the adapter, replace
   `env!("VERGEN_*")` with `option_env!("VERGEN_*").unwrap_or("unknown")`-style
   reads, and configure vergen (`fail_on_error(false)` / default-emit) so a
   git-less build degrades gracefully instead of failing to compile. Record the
   gitcl-vs-gix decision explicitly as a resilience/portability call.

2. **Re-ground the black-box tests on the build-baked values, not live git /
   wall-clock** (addresses: SHA format mismatch, build-script caching,
   date-window flakiness, SHA test git-host coupling, host-triple
   self-reference). Compare the printed SHA/date/triple against
   `env!("VERGEN_GIT_SHA")` / `env!("VERGEN_BUILD_TIMESTAMP")` /
   `env!("VERGEN_CARGO_TARGET_TRIPLE")` read in the test, and relax the date
   assertion to "parses as RFC 3339 and not in the future". Verify vergen emits
   `rerun-if-changed` for the git ref files so the SHA-changes invariant holds.

3. **Prove cargo-pup binds to the real module path, not just a mirror**
   (addresses: the architecture major, the coverage probe-mirror gap, the regex
   under-match risk, the RON-syntax-asserted risk). Upgrade
   `test_repo_pup_ron_actually_loads` to assert the real `version::core` path
   appears in `print-modules` output and is matched by the configured rule;
   broaden the rule toward an `allowed_only` allow-list so it fails closed as the
   hexagon grows.

4. **Validate the new deps against both the MSRV pin and the pup nightly**
   (addresses: placeholder-pins-vs-MSRV, build-dep-under-nightly). For each dep,
   pick a version whose `rust-version` ≤ 1.90.0, commit `Cargo.lock`, and add an
   explicit step verifying `cargo +nightly-2026-01-22 pup print-modules` compiles
   after the build-dep is added.

5. **Document the task-tree shape changes** (addresses: README omission,
   `kernel:check` exclusion departure, the `__init__.py` two-location
   registration, the `tasks/test/kernel.py` full-mirror requirement). Add a
   Phase 1 change updating `tasks/README.md` (kernel row + the `kernel:check`-
   excluded-from-`check` rationale), put the rationale in the mise task
   `description`, and spell out the two-location collection registration.

6. **Resolve the version-field asymmetry and the empty-enum test** (addresses:
   version-bypasses-port, vacuous kernel test). Either route `version` through
   the `BuildMetadata` port or document why it is an intrinsic compile constant;
   defer the kernel `Display` test (and its first variant) to genuine TDD
   pressure and drop the Phase 1 claim that `Display` behaviour is tested.

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: The plan realises ADR-0009's hexagon faithfully: ports are traits
living with the core, the inbound clap adapter and outbound vergen adapter are
thin, a composition root binds concretions to traits, and an in-memory fake
proves the outbound port boundary. It respects ADR-0010's binary axis and is
phased into three independently-mergeable steps in correct dependency order. The
principal architectural risks are that the sole single-crate inward-direction
enforcer (cargo-pup) is never automatically exercised against the real hexagon's
module paths, that the authored pup rule is narrower than the stated inward rule,
and that build-time facts are split inconsistently between an outbound port and a
direct `env!` read inside the core.

**Strengths**:
- Ports correctly modelled as traits living with the core (ADR-0009 compliant).
- Composition root depends on the trait, never the concrete adapter — DI
  preserved, fake enabled, boundary proven real.
- Presentation kept out of the core; `main.rs` a thin composition root.
- Three phases each leave `main` green, correctly sequenced.
- ADR-0010 binary axis respected; over-splitting resisted.
- Indirection overhead for a trivial command is an explicitly justified tradeoff.

**Findings**:
- 🟡 (major, high) *The sole inward-direction enforcer is never automatically
  verified against the real hexagon's module paths* — Phase 3, Changes #2. The
  automated proof uses a throwaway mirror crate; the only real-config check
  asserts `print-modules` exits 0 (parses), not that the rule rejects a real
  violation. A regex typo stays green and enforces nothing — the ADR-0009
  negative consequence the plan relies on pup to prevent. Add an automated check
  that the real config fails on an injected real-core violation and passes on
  removal.
- 🟡 (major, medium) *The authored pup rule is narrower than the stated inward
  rule* — Phase 3, Section 1. The RON only denies `version::inbound`/`outbound`
  imports; it does not stop the core importing infrastructure (`clap`, `vergen`,
  `std::fs`, future adapter modules). With the cross-crate deny ban-list inert,
  this is the whole guard. Prefer `allowed_only` for the core so it fails closed.
- 🔵 (minor, medium) *Build-time facts split inconsistently* — Phase 2,
  `core.rs`. `version` read via `env!("CARGO_PKG_VERSION")` in the core while the
  other three go through the port; un-fakeable. Route through the port or document
  the intent.
- 🔵 (minor, high) *`kernel::Error` empty enum makes the dispatch seam vacuous* —
  Phase 1. Acceptable for a scaffold, but ensure the error→exit-code mapping
  genuinely consumes the taxonomy so adding the first variant is compiler-guided.
- 🔵 (minor, medium) *vergen backend choice deferred to a supply-chain result* —
  Decision 2. gitcl vs gix are materially different external-dependency profiles;
  make the choice an explicit resilience judgement, not solely a licence outcome.

### Code Quality

**Summary**: Unusually disciplined for a scaffold — explicitly TDD-driven, a
clean ports-and-adapters hexagon with traits defining boundaries, a thin CLI
adapter, and the lint wall respected across production, build script, and tests.
The main concerns are minor: the version-field sourcing asymmetry (`env!` in the
core vs the port), an empty error enum whose `Display`/`Error` impls and tests
strain the "minimal but real" line, and maintainability sync-hazards from the new
per-crate task duplication.

**Strengths**:
- Test-first with red-before-green sequencing; core exercised against an
  in-memory fake of the outbound port.
- Boundaries as traits; `VersionReporter<M: BuildMetadata>` depends only on the
  trait — clean DI and isolated testability.
- Presentation kept out of the core; thin composition root.
- Honest scope ("What We're NOT Doing"); YAGNI on the error variant.
- Lint wall extended to build script and tests with concrete guidance.

**Findings**:
- 🔵 (minor, high) *Version field bypasses the port* — Phase 2, Sections 4-5.
  Inconsistent sourcing model; version can't be substituted by the fake. Route
  through the port (`fn crate_version(&self) -> &str`) or document the asymmetry.
- 🔵 (minor, medium) *`&str` return types on the port may force lifetime/ownership
  friction* — Phase 2, Section 4. Returns-borrow presupposes `'static`-backed
  storage; a future dynamic adapter would be constrained. Consider `String`/`Cow`.
- 🔵 (minor, medium) *Empty error enum with match-on-never Display is a smell* —
  Phase 1, Section 2. Test can only assert structural facts. Prefer introducing
  the first variant under TDD pressure; keep the explanatory doc comment if it
  must ship empty.
- 🔵 (minor, medium) *Copy-paste of per-crate Rust task modules is a sync hazard*
  — Phase 1, Section 3. Extract command construction into `tasks/shared/rust.py`
  helpers so per-crate modules become thin bindings.
- 🔵 (suggestion, low) *Pin output-formatting location* — Phase 2, Section 4. Keep
  a single `render(&VersionReport)` in the inbound adapter for testability.

### Test Coverage

**Summary**: Unusually test-conscious — each AC is mapped to a specific named
test, conventions are mirrored faithfully, and the pyramid is balanced (unit
core, black-box integration, behavioural pup probe). The main risks are
concentrated in the black-box binary test: the build-date window assertion is
under-specified and time-sensitive, the softened triple assertion leaves AC1's
"one of four" property unverified anywhere, and the pup probe-mirror proves rule
shape on a parallel crate rather than the real module paths. The kernel
error-taxonomy test risks being vacuous given the never-constructed empty enum.

**Strengths**:
- Each AC mapped to a specific named test — coverage is traceable.
- Explicit red-green ordering matching the non-negotiable TDD convention.
- The in-memory fake substitutes only at the true port boundary (AC4 intent).
- Conventions faithful to the codebase (inline `#[cfg(test)]`, pinned arrays,
  per-task command-string tests including the coverage branch).
- pup probe reuses the established teeth-proving philosophy.

**Findings**:
- 🟡 (major, high) *Black-box build-date assertion is time-dependent and
  under-specified* — Phase 2, Section 5. Tie to `env!("VERGEN_BUILD_TIMESTAMP")`
  plus "not in the future", not `now()`.
- 🟡 (major, medium) *Triple-membership (AC1) asserted by no automated test* —
  Phase 2, Section 5. The host-triple check is self-referential; add a
  release-build membership assertion or cite where `build:cli` covers it.
- 🔵 (minor, medium) *Host-triple equality is self-referential* — Phase 2,
  Section 5. Pair with an independent reference from `std`/`cfg`.
- 🔵 (minor, medium) *kernel error taxonomy test is vacuous* — Phase 1, Section 2.
  An empty enum cannot exercise `Display`; defer the test/variant or add one real
  variant now, test-first.
- 🔵 (minor, medium) *pup probe-mirror vs real paths* — Phase 3, Section 2.
  Assert the real `version::core` path appears in `print-modules` output and is
  matched by the configured regex.
- 🔵 (minor, low) *Black-box SHA equality and test isolation* — Phase 2, Section
  5. Compare against `env!("VERGEN_GIT_SHA")` baked into the same build rather
  than re-shelling `git rev-parse HEAD`.
- 🔵 (suggestion, medium) *kernel task command-string tests duplicate cli's* —
  Phase 1. Parametrise over crate name against a shared helper.

### Correctness

**Summary**: The architectural logic is sound and the empty-enum `Display` impl
is correct, but several build-metadata correctness assumptions are unsafe. The
most serious are the unconditional compile-time `env!("VERGEN_GIT_SHA")` (fails
to compile when vergen omits the var) and the black-box assertions that conflate
vergen's SHA/timestamp formats and ignore Cargo build-script caching. The
version-correctness logic (CARGO_PKG_VERSION as SSOT, the port boundary) is
correct.

**Strengths**:
- The empty-enum `match *self {}` Display impl is logically correct (uninhabited
  type, statically unreachable).
- The gnu-vs-musl host-triple reasoning is correct.
- Sourcing the version from `CARGO_PKG_VERSION` is a sound SSOT choice with no
  missing-value path.
- Each phase leaves `main` green; Phase 3's rule is authored against compliant
  code, so no transient broken state.

**Findings**:
- 🔴 (critical, high) *`env!("VERGEN_GIT_SHA")` fails to compile when vergen omits
  the var* — Phase 2, Sections 3-4. Hard compile error in no-git/shallow/tarball
  contexts; can pass CI yet break a real release build. Use `option_env!` with a
  fallback or configure vergen to always emit a default.
- 🟡 (major, high) *Printed SHA == `git rev-parse HEAD` assumes full-length,
  clean, exact format* — Phase 2, Section 5. vergen may emit short SHA / `-dirty`
  suffix; the jj working copy is exactly the dirty condition. Pin vergen's SHA
  kind and compare against the baked value.
- 🟡 (major, high) *Build-script caching breaks the date window and the
  SHA-changes check* — Phase 2, Section 5 + Manual Verification. Verify
  `rerun-if-changed` tracks the git ref files; relax the date assertion.
- 🟡 (major, medium) *"git present in every build context" is not universally
  true* — Decision 2 + Phase 2, Section 3. Treat git-absence as first-class
  regardless of backend.
- 🔵 (minor, medium) *pup regex matchers may under-/over-match* — Phase 3,
  Section 1. Assert the probe against exact `print-modules` path strings.
- 🔵 (minor, medium) *`&str` port vs `String` report assembly unspecified* —
  Phase 2, Section 4. Specify infallible `to_owned()` to stay lint-clean.

### Standards

**Summary**: Strongly convention-aware — mirrors the entity-first roll-up naming,
the workspace-scoped check model, the coverage-gated per-crate test task, the
lint-wall constraints, and the "every Rust task module ships parallel unit tests"
convention; the kernel manifest is faithful to cli. The main gaps are
documentation-of-shape (the plan never updates `tasks/README.md`) and two
deliberate-but-under-flagged departures (`kernel:check` excluded from `check`; a
new component without the documented per-component-table entry).

**Strengths**:
- kernel manifest mirrors cli (`edition 2021`, MIT, `[lints] workspace = true`).
- `kernel:check` follows entity-first naming; leaves trail correctly.
- Honours "no `<component>:fix`" and "library crates get no `build:*`".
- Commits to per-task command-string tests and pinned-array updates.
- Lint wall applied to every new file including `build.rs`.
- `KERNEL_CRATE` placed alongside `CLI_CRATE` with the same convention comment.

**Findings**:
- 🟡 (major, high) *Omits updating `tasks/README.md`, the documented SSOT for
  task-tree shape* — Phase 1, Section 3. Add a kernel row + rationale for the
  `check` exclusion.
- 🟡 (major, medium) *`kernel:check` departs from "`<component>:check` folds into
  `check`"* — Decision 1 / Phase 1. Justified, but document it in the task
  `description` and README, not only test comments.
- 🔵 (minor, medium) *`test/kernel.py` snippet references `KERNEL_CRATE` without
  the import / full mirror* — Phase 1, Section 3. Note it is a full structural
  copy of `test/cli.py`.
- 🔵 (minor, high) *Register kernel modules in the `__init__.py` collections
  explicitly* — Phase 1, Section 3. Two-location registration (family `__init__`
  + hand-built `ns_format`/`ns_lint` in top-level `tasks/__init__.py`).
- 🔵 (minor, medium) *`mod.rs` nesting vs sibling-file — make the precedent
  deliberate* — Phase 2, Section 4. Record the chosen module-file style.

### Portability

**Summary**: Operates entirely within a Unix-only, four-triple (musl/darwin)
build model that is consciously chosen and well-documented, and correctly
recognises the gnu-vs-musl host divergence. The main risks are in the vergen
adapter: the default `gitcl` backend bakes a "git binary on PATH plus a usable
`.git`" assumption into every build, and the adapter's compile-time `env!` reads
turn any missing build-metadata var into a hard build failure with no graceful
degradation.

**Strengths**:
- Correctly asserts host-triple equality rather than "one of four" to avoid a
  false failure on the gnu runner.
- deny.toml evaluates the graph across all four shipped triples plus the two host
  triples.
- The static-linking guarantee is preserved (vergen is build-only, no runtime
  dep); native-tls/openssl bans remain the guard.
- Version sourced from `CARGO_PKG_VERSION` — no runtime environment coupling.
- Unix-only scope is an explicit, ADR-backed boundary.

**Findings**:
- 🟡 (major, high) *Default `gitcl` bakes a "git binary present" assumption into
  every build context* — Decision 2 / Phase 2, Section 3. Prefer `vergen-gix`
  (self-contained) if any non-git-checkout context is plausible, or document the
  prerequisite.
- 🟡 (major, high) *Compile-time `env!()` on vergen vars is a hard failure with no
  fallback* — Phase 2, Section 4. Use `option_env!` with an `"unknown"` fallback.
- 🔵 (minor, medium) *Black-box SHA test assumes git CLI + non-shallow HEAD on the
  test host* — Phase 2, Section 5. Compare against the build-script-injected value.
- 🔵 (minor, high) *Triple-membership AC is non-portable to the gnu host; promote
  the softening to the AC* — AC1 vs Phase 2. Reconcile the work-item text.
- 🔵 (suggestion, medium) *`build:cli` host-native already diverges from ADR-0002
  zigbuild; validate the backend against the release path too (story 0008)* —
  build model.

### Compatibility

**Summary**: Dependency-aware and inherits a well-structured pinning/supply-chain
regime. The principal risks are unresolved at plan time: the dependency versions
are placeholders with no stated MSRV-compatibility check against `msrv = 1.90.0`,
and the vergen build-dependency must compile under cargo-pup's separate pinned
`nightly-2026-01-22` toolchain — a second toolchain the plan never reconciles.
The native-tls ban and triple graph are honoured by defaulting to the `gitcl`
backend, the correct conservative choice.

**Strengths**:
- Introduces `[workspace.dependencies]` for central pinning before the tree grows.
- Defaults to the lighter `gitcl` backend, sidestepping the gix tree and
  native-tls risk.
- Correctly anticipates the gnu-vs-musl CI host mismatch.
- Commits to extending the deny licence allow-list via `[[licenses.exceptions]]`
  if needed.
- Reuses workspace-scoped checks so no new CI job / branch-protection is needed.

**Findings**:
- 🟡 (major, high) *Placeholder pins not validated against MSRV (1.90.0)* — Phase
  2, Section 1. Pick versions whose `rust-version` ≤ 1.90.0; commit `Cargo.lock`.
- 🟡 (major, medium) *vergen build-dep must also compile under
  `nightly-2026-01-22`* — Phase 2, Section 3 + Phase 3. Verify
  `cargo +nightly-2026-01-22 pup print-modules` compiles after the build-dep is
  added; bump `PUP_NIGHTLY`/`PUP_VERSION` if required.
- 🔵 (minor, medium) *License allow-list may need exceptions for vergen/gix* —
  Phase 2, Section 1. Keep gitcl; if gix, add per-crate `[[licenses.exceptions]]`.
- 🔵 (minor, high) *Edition 2021 consistency is correct; consider hoisting to
  `[workspace.package]`* — manifests. Inherit a shared edition + `rust-version`.
- 🔵 (minor, medium) *cargo-pup v0.1.8 RestrictImports syntax asserted, not
  exercised* — Phase 3, Section 1. Make "real `pup.ron` parses + loads non-empty"
  an explicit gating assertion.

## Re-Review (Pass 2) — 2026-06-29

**Verdict:** COMMENT

The plan was edited to address the pass-1 findings, and a second pass of all
seven lenses confirms **every pass-1 finding is resolved** — including the lone
🔴 critical (the `env!("VERGEN_GIT_SHA")` compile-failure, now
`option_env!(...).unwrap_or("unknown")` + `fail_on_error(false)`). The verdict
moves **REVISE → COMMENT**: the plan is sound and implementable as-is. The
second pass surfaced only minor/suggestion-level observations, all cheaply
addressable, none blocking. The one recurring (cross-lens) accuracy issue worth
correcting before implementation is the description of vergen's
`fail_on_error(false)` behaviour (it suppresses the build error; it does **not**
itself emit an `"unknown"` sentinel — the fallback comes solely from the
adapter's `option_env!...unwrap_or`).

### Previously Identified Issues (all resolved)

- 🔴 **Correctness**: `env!("VERGEN_GIT_SHA")` compile-failure — **Resolved**
  (`option_env!(...).unwrap_or("unknown")` + `fail_on_error(false)`).
- 🟡 **Architecture**: enforcer not verified against real module paths —
  **Resolved** (`test_real_inward_rule_binds_to_a_real_module`).
- 🟡 **Architecture**: pup rule narrower than the inward rule — **Resolved**
  (fail-closed `allowed_only` allow-list).
- 🟡 **Correctness**: build-script caching breaks date/SHA-change checks —
  **Resolved** (`rerun-if-changed` note; date assertion relaxed).
- 🟡 **Correctness**: SHA == `git rev-parse HEAD` mismatch — **Resolved**
  (compares the build-baked value).
- 🟡 **Correctness**: "git present everywhere" false — **Resolved** (git-absence
  first-class).
- 🟡 **Portability**: gitcl bakes a git assumption — **Resolved** (explicit
  resilience decision; gix fallback recorded).
- 🟡 **Portability**: `env!()` hard failure — **Resolved** (`option_env!`).
- 🟡 **Test Coverage**: date-window flakiness — **Resolved** (window dropped).
- 🟡 **Test Coverage**: AC1 four-triple membership unverified — **Resolved**
  (documented as a `build:cli` structural guarantee).
- 🟡 **Standards**: `tasks/README.md` not updated — **Resolved** (new Phase 1
  step 4).
- 🟡 **Standards**: `kernel:check` exclusion undocumented — **Resolved**
  (rationale in the mise task `description` + README).
- 🟡 **Compatibility**: pins not MSRV-validated — **Resolved** (MSRV-first
  pinning + `Cargo.lock` + cross-check criterion).
- 🟡 **Compatibility**: build-dep under the pup nightly — **Resolved** (explicit
  `cargo +nightly-2026-01-22 pup print-modules` criterion + bump fallback).
- 🔵 All pass-1 minors (version-through-port, vacuous kernel test, `&str`
  assembly, pup regex, render-fn location, `__init__.py` two-location,
  `test/kernel.py` full-mirror, mod.rs precedent, licence exceptions) —
  **Resolved**.

### New Issues Introduced (all minor/suggestion)

- 🔵 **Correctness / Portability** (cross-lens): the plan says `fail_on_error(false)`
  makes vergen *emit* an `"unknown"` sentinel var; in fact vergen leaves the var
  unset/idempotent-default and the `"unknown"` comes only from the adapter's
  `option_env!...unwrap_or`. Reword so the adapter fallback is the authoritative
  mechanism. *(highest-value correction — a factual accuracy fix.)*
- 🔵 **Correctness / Test Coverage** (cross-lens): the black-box assertions
  compare each printed field against the *same* `option_env!/env!` expression the
  adapter uses, so in the git-less/sentinel case both sides collapse to
  `"unknown"` and the SHA check proves nothing; the real `VergenBuildMetadata`
  adapter (non-fakeable SSOT) has no independent oracle. Add symmetry-breaking
  assertions (fields non-empty + mutually distinct on a real build; assert
  not-sentinel on a git-present build).
- 🔵 **Compatibility**: vergen 8.x (git feature on the main crate) vs 9.x
  (companion `vergen-gitcl`/`vergen-gix`, different builder API) is unstated; the
  `build.rs`/manifest shape depends on the major line — pin it.
- 🔵 **Compatibility**: the probe-mirror test should use the exact `allowed_only`
  rule shape (not a generic deny-list) so the pinned v0.1.8 binary's acceptance
  of `allowed_only: Some([...])` is gated by an automated test.
- 🔵 **Standards**: the `__init__.py` two-location guidance conflates the
  format/lint pattern with the test family — the test module's second location is
  `tasks/test/__init__.py` (`Collection.from_module(kernel)`), not a line in the
  top-level Collections block (which pulls the test family wholesale).
- 🔵 **Architecture / Correctness**: the `allowed_only` list anchors on
  `version::core` only; a legitimate intra-slice value-type module hoisted to
  `version::` level would be rejected. Confirm against `print-modules`, or keep
  core-consumed value types under `version::core` (the deny-list fallback is an
  adequate escape hatch).
- 🔵 **Test Coverage**: the extracted pure `render(&VersionReport) -> String` is
  described as "independently unit-testable" but no test is planned — add a small
  exact-string test or drop the justification.
- 🔵 **Code Quality**: the port still returns `&str` (assembly is now infallible
  `to_owned()`, resolving the unwrap concern), baking a `'static`-source
  assumption; a future runtime-sourced adapter would hit lifetime friction.
  Consider owned `String`/`Cow`, or note why `&str` was kept.
- 🔵 **Portability** (suggestion): record the "git on PATH at build time" gitcl
  prerequisite in `CONTRIBUTING.md` / build-system docs; reconsider gix as the
  default given the zero-dependency ethos.
- 🔵 **Architecture** (suggestion): the single `BuildMetadata` port now mixes an
  always-available fact (`crate_version`) with degradable ones; note the differing
  semantics in the port doc comment.

### Assessment

The plan is in good shape and ready for implementation. The pass-1 risks — the
build-breaking metadata sourcing, the toothless-enforcer gap, the flaky tests,
and the unvalidated dependency/toolchain matrix — are all closed. The pass-2
observations are refinements, not blockers; the most worthwhile to fold in before
coding are the vergen `fail_on_error` wording correction, the symmetry-breaking
test assertions, pinning the vergen major line, and the `__init__.py` test-family
registration correction. None change the plan's shape or phasing.

---
*Re-review generated by /accelerator:review-plan*

## Approval — 2026-06-29

**Verdict:** APPROVE (reviewer override of the pass-2 COMMENT)

The four highest-value pass-2 corrections were folded into the plan after pass 2
(vergen `fail_on_error` wording, symmetry-breaking black-box assertions, the
vergen 9.x major-line pin, and the `__init__.py` test-family registration fix).
With the pass-1 critical and all majors resolved and those corrections applied,
the reviewer approves the plan for implementation. The remaining pass-2 items
(`&str` port note, a `render()` unit test, allow-list intra-slice scope, the
gitcl-prerequisite docs, and the `BuildMetadata` semantics doc-comment) are
optional polish to handle during implementation; none gate approval.
