---
type: plan-review
id: "2026-06-27-0006-establish-rust-toolchain-guard-rails-review-2"
title: "Plan Review: Establish Rust Toolchain Guard Rails in mise + CI"
date: "2026-06-27T19:54:34+00:00"
author: Toby Clemson
producer: review-plan
status: complete
parent: "plan:2026-06-27-0006-establish-rust-toolchain-guard-rails"
target: "plan:2026-06-27-0006-establish-rust-toolchain-guard-rails"
relates_to: ["plan-review:2026-06-27-0006-establish-rust-toolchain-guard-rails-review-1"]
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, code-quality, test-coverage, correctness, security, compatibility, portability, documentation]
review_number: 2
review_pass: 3
tags: [rust, tooling, ci, guard-rails, mise, architecture-enforcement]
last_updated: "2026-06-28T11:00:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: Establish Rust Toolchain Guard Rails in mise + CI

**Verdict:** REVISE

This remains a disciplined, convention-faithful plan, and review 1's blocking
findings stay resolved (the cargo-pup nightly mechanism, coverage out of
read-only `check`, family-style tests, SHA-pinning, the executable wiring guard).
The REVISE verdict is driven by **new issues introduced by the post-approval
revisions made this session** — the coverage fold-in, the `LUMINOSITY_PUP_MODE`
env-sourcing, and the `build:cli` rename/OS-aware/matrix/`default` changes. Two of
those changes interact badly: the env toggles are now read at module-import time
and re-bound via `from … import`, which makes **both** `LUMINOSITY_COVERAGE` and
`LUMINOSITY_PUP_MODE` inert at runtime *and* unexercised by the very tests meant to
pin them (flagged independently by correctness and code-quality). On top of that,
the new host-native `build:cli` strategy structurally diverges from ADR-0002's
committed `cargo-zigbuild` release model and will go red the moment 0007's C-FFI
stack lands, and the two highest-value regression tests skip-to-green in CI as
placed. None are structural dead-ends; this is a focused correctness/wiring pass.

### Cross-Cutting Themes

- **The env-toggle escape hatches don't actually work** (flagged by: correctness,
  code-quality) — `COVERAGE`/`PUP_MODE` are computed at import time in
  `tasks/shared/rust.py` and bound into consumers via `from tasks.shared.rust
  import COVERAGE`. Setting the env var at invocation has no effect, and the
  planned tests (`monkeypatch.setenv` / patch the constant) cannot drive both
  branches. This silently disables the documented fast-inner-loop and the
  pup advisory fallback — the latter being review 1's *accepted mitigation* for
  the nightly SPOF, so the SPOF acceptance is undermined.
- **The cargo-pup nightly remains the dominant fragility** (flagged by:
  architecture, security, compatibility, portability) — recurs from review 1,
  where it was accepted as a deliberate tradeoff *backed by the `PUP_MODE=warn`
  toggle*. This review escalates it: (a) the toggle is inert (theme above), and
  (b) `PUP_MODE=warn` never covered a *toolchain-unavailable* failure anyway (a
  GC'd dated nightly fails the install step before any check runs).
- **`build:cli` validates a build path the release won't use** (flagged by:
  portability, architecture) — host-native `cargo build --target` per OS diverges
  from ADR-0002's `cargo-zigbuild` cross-compile-from-one-host model, and rests on
  self-contained linking that breaks on the first C-FFI dependency (0007's
  reqwest/tokio/rustls stack).
- **Supply-chain graph has a host-triple blind spot** (flagged by: architecture,
  security, portability) — recurs from review 1 as a documented follow-up;
  `deny.toml [graph] targets` covers only the four shipped triples, so a
  ban/advisory violation reachable only on the dev/CI host triple
  (`x86_64-unknown-linux-gnu`, `aarch64-apple-darwin`) is built and run but never
  evaluated.
- **Doc surface (`tasks/README.md`) lags the structural change** (flagged by:
  documentation) — the canonical "task-tree shape" file gets no concrete edits for
  the Rust component, the `build:*` family, or the now-inaccurate "check is exactly
  what CI runs" claim.

### Tradeoff Analysis

- **Self-provisioning `pup:check` (depends on `deps:install:pup`) vs. read-only
  `check` purity**: this session re-added the `depends` edge that review 1 had
  removed (recorded in review 1's post-approval amendment). Correctness now flags
  that the "idempotent no-op" justification is overstated for
  `cargo install … --locked` (it resolves/inspects, can rebuild or hit the
  network), so a read-only `mise run check` can intermittently do real work or
  fail offline. The convention-consistency win (mirrors `deps:install:python`) is
  real; the recommendation is to keep the edge **but** gate the install behind a
  presence probe so the steady-state path is a genuine no-op — getting both the
  convention and the read-only invariant.
- **Blocking cargo-pup with empty rules vs. SPOF cost** (carried from review 1):
  still an accepted tradeoff, but its mitigation (the toggle) is currently broken
  (see themes). Fix the toggle and the original acceptance holds; alternatively
  default `PUP_MODE=warn` until 0007 lands real rules so the empty-rule window
  carries no blocking exposure.

### Findings

#### Critical

- 🔴 **Test Coverage**: Skip-gated regression tests live in `test-integration` but
  the plan asserts they run in `check-supply-chain`/`check-architecture`
  **Location**: Phase 3 §5 / Phase 4 §5 (vs `.github/workflows/main.yml`
  `test-integration` job)
  The cargo-deny ban test and cargo-pup rule test sit under
  `tests/integration/tasks/` (run by `mise run test:integration`), but that job
  never provisions cargo-deny or the cargo-pup nightly, so their `skipif` gate is
  true and both silently skip-to-green — defeating the "live from day one / must
  not silently regress" intent for the two highest-value regressions in the plan.

#### Major

- 🟡 **Correctness / Code Quality**: Env toggles read at import time and re-bound
  via `from`-import are inert at runtime and untestable
  **Location**: Phase 2 §2 / Phase 4 §1 (`tasks/shared/rust.py`); Testing Strategy
  `COVERAGE`/`PUP_MODE` are evaluated once at import and copied into consumers'
  namespaces; `monkeypatch.setenv` after import is ignored and patching the source
  constant doesn't rebind the imported copy. Both escape hatches silently do
  nothing and the toggle tests pass against a path production never takes. Fix:
  read the env at call time via `coverage_mode()`/`pup_mode()` functions (matching
  the existing call-time env idiom in `tasks/release.py`).
- 🟡 **Portability**: `build:cli` host-native strategy diverges from ADR-0002's
  committed `cargo-zigbuild` cross-compile release model
  **Location**: Phase 1 §6
  ADR-0002 commits the release to zigbuild-from-one-host; `build:cli` does per-OS
  native `cargo build --target` across a matrix, so the PR guard exercises a
  different linker/sysroot path than the shipping build — a change can pass
  `build-cli` yet break the real release (or vice versa). Make it a conscious
  decision: supersede/amend ADR-0002, or have `build:cli` use zigbuild so the
  guard mirrors the release toolchain.
- 🟡 **Portability**: Self-contained-linking assumption breaks on the first C-FFI
  dependency (0007's reqwest/tokio/rustls stack)
  **Location**: Phase 1 §6 (linker prerequisite) / §7 (build-cli job)
  The guard is green only because the crate is empty; 0007 immediately lands a
  stack that typically needs a musl cross-linker (and the macOS SDK for the
  cross-arch darwin slice). The matrix goes red on 0007 with no provisioning
  staged. Pre-stage the `musl-tools`/linker step (commented, ready to enable) and
  note 0007 must turn it on; consider pinning the TLS backend now.
- 🟡 **Correctness / Portability**: OS-aware target filter yields a
  silently-passing empty build on an unrecognised platform
  **Location**: Phase 1 §6 / §9
  Only `Darwin`/`Linux` branches are specified; any other `platform.system()`
  returns an empty triple list, runs no `cargo build`, and exits 0 — a false-green
  on the authoritative static-link guard. Have host-target selection `Exit` when it
  resolves to zero triples, and test that branch.
- 🟡 **Compatibility**: cargo-pup/nightly coupling has no in-tree fallback when the
  dated nightly is garbage-collected
  **Location**: Phase 4 (cargo-pup lane) / Key Discoveries
  `nightly-2026-01-22` both builds and runs the rustc-driver; nightlies are GC'd
  from static.rust-lang.org over time. If the install can't resolve it,
  `deps:install:pup` (hence every `pup:check`, `mise run check`, and CI) breaks —
  and `PUP_MODE=warn` covers *findings* failures, not a toolchain-unavailable
  install failure. Document the recovery (bump `PUP_NIGHTLY`+`PUP_VERSION`
  together) and lean on the CI built-binary cache.
- 🟡 **Security**: cargo-pup pre-1.0 source-only rustc-driver is a code-execution
  trust anchor on the read-only `check` path and in CI
  **Location**: Phase 4 §1
  `--locked` pins only the declared graph, not the integrity of `cargo_pup`/its
  build-script closure, which runs with full filesystem access on every dev machine
  and runner. Constrain exposure (keep it out of the default local `check` path via
  the — currently broken — toggle; verify the source).
- 🟡 **Security**: The `cargo-pup` built-binary cache is a poisoning →
  code-execution vector
  **Location**: Phase 4 §4
  The `check-architecture` job restores a *built* `cargo-pup`/`pup-driver` from an
  Actions cache keyed on `(PUP_NIGHTLY, PUP_VERSION, OS)` with no content hash and
  then executes it; a poisoned cache entry under that key runs arbitrary code.
  Verify a recorded SHA256 before exec, confirm the cache isn't writable from
  `pull_request` contexts, or rebuild from `--locked` source.
- 🟡 **Architecture / Security / Portability**: cargo-deny graph covers only the
  four release triples, leaving the host/CI dev triple's closure un-evaluated
  **Location**: Phase 3 §2 ([graph] targets / Known follow-ups)
  A dependency or banned crate pulled in *only* on `x86_64-unknown-linux-gnu`
  (CI) / `aarch64-apple-darwin` (local) is built, tested, and run but never
  deny-evaluated — a blind spot exactly where code executes. Recurs from review 1
  as a documented follow-up; add the two host triples to `[graph] targets`.
- 🟡 **Test Coverage**: The skip-gate is the single point of failure for CI
  coverage but its correctness is never asserted
  **Location**: Phase 3 §5 / Phase 4 §5
  A typo in the probed binary name makes the regression test skip permanently and
  silently, green in CI and locally. Make skip a hard failure under CI (`CI=true`),
  or assert the probe resolves against the provisioning step.
- 🟡 **Test Coverage**: `test_workflows.py` is named the sole automated guard for
  non-mergeability but cannot assert branch-protection
  **Location**: Phase 5 §2
  It can only assert job presence / `needs:` edges; the actual enforcement
  (required-checks branch protection) is manual and untested, so the AC's real
  guarantee is overstated. Reframe honestly and consider a scripted `gh api`
  branch-protection audit.
- 🟡 **Architecture**: Whole-repo mergeability is a SPOF on the least-mature tool
  **Location**: Phase 4 (cargo-pup lane); Desired End State
  Recurs from review 1 (accepted tradeoff). Re-flagged because its mitigation (the
  `PUP_MODE` toggle) is currently inert and never covered the install-failure mode.
  Consider defaulting `warn` until 0007's rules land.
- 🟡 **Compatibility**: cargo-deny 0.19.8 `[advisories]` schema risk
  (`unmaintained = "all"`)
  **Location**: Phase 3 §2
  A wrong/removed key makes cargo-deny error on config rather than evaluate,
  blocking every merge. The plan already flags this for impl-time verification and
  gates it with a clean-`deny:check` success criterion — largely mitigated;
  recorded for completeness.
- 🟡 **Documentation**: `tasks/README.md` component table and family-aggregate
  prose are not updated for Rust
  **Location**: Phase 1 §8 / Phase 5 §1
  The canonical "task-tree shape" file (which CLAUDE.md points to) gets no concrete
  edits for the `cli` component, the workspace-scope deny/pup roll-ups, the
  `build:*` family, or the `test`/coverage path — only generic "describe deny:check"
  phrasing. Schedule the specific table/prose edits.
- 🟡 **Documentation**: The "check is exactly what CI runs" claim becomes
  inaccurate and is only half-reconciled
  **Location**: Phase 1 §8 / Phase 5 §1 (`tasks/README.md` line 20, CLAUDE.md
  line 24)
  CI now also runs `build-cli` and the cli tests (`test-unit`), neither in
  `mise run check`. The plan fixes the CLAUDE.md framing only in prose and never
  touches `tasks/README.md`'s blunter "(this is what CI runs)". Schedule the
  qualifying edit so "green check ⇒ green CI" isn't a false contract.

#### Minor

- 🔵 **Architecture**: `clippy.toml` `msrv` is a fourth hand-mirrored copy of the
  mise rust pin with no automated coherence check — add a `tomllib` assertion in
  `test_mise_wiring.py` that msrv/edition match the pin. **Location**: Phase 1 §3/§8
- 🔵 **Architecture**: `build:cli` is the repo's first cargo release-build path and
  may diverge from 0008's shipping build — note in Migration Notes that 0008 should
  share its target/flag derivation. **Location**: Phase 1 §6
- 🔵 **Architecture**: Coverage instrumentation is invisible in the task graph
  (env-toggle inside a leaf) — ensure the docs make the default-on behaviour
  prominent. **Location**: Wiring model
- 🔵 **Code Quality**: Advisory/warn paths (`pup:check` warn mode, clippy `--fix`
  non-zero) use bare `print()` — route through a `warning:`-marked helper so a
  downgraded gate is visibly distinct. **Location**: Phase 4 §3 / Phase 1 §4
- 🔵 **Code Quality / Test Coverage**: Extract a pure `host_targets(system)` helper
  in `tasks/shared/targets.py` so OS selection is unit-tested without patching
  `platform`, and so the monkeypatch boundary is call-time. **Location**: Phase 1
  §6 / §9
- 🔵 **Code Quality**: The `test:unit:cli` leaf maps to a function named `check()`
  that runs tests — blurs the check/test vocabulary; prefer a `run`-style verb.
  **Location**: Phase 2 §2
- 🔵 **Correctness**: `build:cli` should constrain to the binary (`--bin`/`--bins`)
  so it always exercises the link step the guard exists for. **Location**:
  Phase 1 §6
- 🔵 **Correctness**: `deps:install:pup` idempotency is overstated for
  `cargo install --locked` (resolves/inspects, can rebuild/network) — gate the
  install behind a presence probe so the read-only `check` path is a true no-op.
  **Location**: Phase 4 §1/§3
- 🔵 **Correctness**: Confirm `cargo llvm-cov nextest --summary-only` propagates the
  inner test exit code (a deliberately-failing test must redden the default path).
  **Location**: Phase 2 §2
- 🔵 **Test Coverage**: Give the bootstrap cli test at least one branch so the
  instrumented run demonstrably measures more than a straight-line function.
  **Location**: Phase 1 §2
- 🔵 **Test Coverage**: The pup regression test uses its own config; add an
  assertion that the committed `pup.ron` actually loads/parses (e.g. `cargo pup
  print-modules`) so an unread config isn't indistinguishable from "no rules".
  **Location**: Phase 4 §5
- 🔵 **Security**: `rustup toolchain install` fetches the nightly with no explicit
  checksum/signature note — document that rustup's verification is in effect.
  **Location**: Phase 4 §1
- 🔵 **Security**: cargo-pup's own build closure is never advisory-scanned — note
  it as an accepted-risk boundary or periodically `cargo audit` the tool tree.
  **Location**: Phase 4 §1
- 🔵 **Compatibility**: Confirm the arm64 `macos-latest` runner actually links
  `x86_64-apple-darwin` (cross-arch slice), not just compiles. **Location**:
  Phase 1 §6
- 🔵 **Compatibility**: Verify the cargo-llvm-cov 0.8.7 ↔ cargo-nextest 0.9.138
  composition at the pinned pair; record the known-good pairing. **Location**:
  Phase 2 §1
- 🔵 **Compatibility**: Confirm each pinned tool resolves to an aqua prebuilt on
  **both** ubuntu and macos-arm (else macOS legs fall back to slow source builds).
  **Location**: Phase 2 §1 / Phase 3/4
- 🔵 **Compatibility**: SHA-pinned actions never auto-patch — pair with a refresh
  cadence (Dependabot/Renovate preserving the pin). **Location**: Phase 1 §7
- 🔵 **Portability**: Source-only cargo-pup is CI-validated only on ubuntu yet runs
  in every macOS developer's default `check` — matrix `check-architecture` onto
  macOS, or document it as developer-validated-only. **Location**: Phase 4 §4
- 🔵 **Documentation**: Document the `build:*` family convention (verb-less,
  binary-crates-only, in `default` not `check`) in `tasks/README.md`. **Location**:
  Phase 1 §6
- 🔵 **Documentation**: The single-test command `cargo nextest run -p luminosity
  <test>` bypasses the default coverage path and uses ambiguous filter syntax —
  show the real nextest filter form and note it's uninstrumented. **Location**:
  Phase 1 §8
- 🔵 **Documentation**: CLAUDE.md's inline tool inventory (line ~66) is already
  stale and should gain the three new registry tools + the nightly exception.
  **Location**: Phase 4 §6
- 🔵 **Documentation**: Add a brief Rust subsection to CLAUDE.md Architecture
  mapping each new config file (Cargo.toml/clippy.toml/deny.toml/pup.ron) to its
  role, including the inert-ban-list and empty-pup.ron caveats. **Location**:
  Phase 1/3/4 config files

#### Suggestions

- 🔵 **Portability**: Add a positive static-linkage assertion to the `build-cli`
  musl leg (`file`/`ldd` must report statically linked) so the invariant is
  verified directly, not inferred from the absence of banned crates. **Location**:
  Phase 1 §6 / Phase 3 bans note
- 🔵 **Code Quality**: Optional `run_checked(context, command, *, fail_message)`
  helper to collapse the repeated `cd`/`warn`/`Exit` boilerplate across the six new
  Rust leaves. **Location**: Implementation Approach / Phases 1–4

### Strengths

- ✅ Faithful extension of the established two-layer mise+invoke pattern and the
  component-leads/family-trails naming convention — Rust joins as first-class
  components rather than a bolted-on `rust:` prefix.
- ✅ Single-source-of-truth constants (`tasks/shared/rust.py`) with command-string
  tests asserting against the same constants, so mise.toml/task-body/test drift
  cannot pass green (and the `-p <crate>` pin fails loudly on the 0007 rename).
- ✅ Wiring prose is turned into executable assertions: `test_mise_wiring.py`
  (`tomllib`-parsed) and `test_workflows.py` close the gap that no existing test
  read `mise.toml`, including negative assertions (no `coverage:check` task,
  `test:unit:cli` absent from `check`).
- ✅ Strong supply-chain headline controls: full 40-char SHA-pinning of *every*
  third-party action, a workflow-wide `permissions: { contents: read }` default
  with elevated release jobs kept explicit, the native-tls/OpenSSL ban live from
  day one with a regression test, explicit advisories/licenses/bans/sources policy,
  and advisory-DB freshness.
- ✅ Genuinely cross-platform: the host-native `build-cli` matrix covers all four
  shipped triples pre-merge (closing the darwin-release-only gap), coverage runs on
  both OS test legs, and the mise→rustup `+toolchain` mechanism is correctly
  reasoned and guarded by a PATH pre-flight.
- ✅ `Cargo.lock` committed and generated with the pinned 1.90.0 cargo so the
  lockfile format is accepted under `--locked`/`--frozen` in CI.
- ✅ Evolutionary fitness designed in: a new crate adds one `<crate>:check`
  roll-up + family edges + a `test:unit:<crate>` leaf, with library-vs-binary
  distinguished (only binary crates get `build:<crate>`).
- ✅ Documentation-conscious: phase-distributed docs, the `msrv` fourth-mirror
  hazard recorded, and a dedicated `CONTRIBUTING.md` runbook capturing the
  matrix-leg-per-check and appears-only-after-first-run branch-protection gotchas.
- ✅ Tradeoffs are named with fallbacks (the blocking-pup SPOF, the test-free
  `check`, the nightly fragility) rather than hidden.

### Recommended Changes

1. **Read the env toggles at call time, not import time** (addresses: the
   import-time env toggle critical-adjacent major). Replace the module-level
   `COVERAGE`/`PUP_MODE` constants with `coverage_mode()`/`pup_mode()` functions
   (or have consumers reference `rust.COVERAGE` by attribute), matching the
   call-time env idiom already in `tasks/release.py`. Update the toggle tests to
   `monkeypatch.setenv` + invoke so both branches are genuinely exercised. This
   also restores the `PUP_MODE=warn` fallback that the rest of the plan (and review
   1) relies on.
2. **Make the deny/pup regression tests actually run in CI** (addresses: the
   critical skip-to-green finding + the unasserted-skip-gate major). Either run
   them in the jobs that provision the tools (`check-supply-chain` /
   `check-architecture`) or provision cargo-deny + the cargo-pup nightly in
   `test-integration`; have `test_workflows.py` assert the running job also
   provisions the tool, and make `skipif` a hard failure under `CI=true`.
3. **Reconcile `build:cli` with the real release build path** (addresses: the
   zigbuild-divergence and self-contained-linking majors). Decide explicitly:
   adopt `cargo-zigbuild` in `build:cli` to mirror ADR-0002, or amend/supersede
   ADR-0002 to a host-native matrix model — and pre-stage the musl
   cross-linker/SDK provisioning that 0007 will require, with a positive
   static-linkage assertion (`file`/`ldd`) on the musl leg.
4. **Make the OS-aware build fail loudly on an unknown host** (addresses: the
   silent-empty-build major + the host-detection minor). Have `host_targets()`
   raise an actionable `Exit` on any non-Darwin/Linux `platform.system()`, extract
   it as a pure helper, and test all three branches.
5. **Harden the cargo-pup trust/availability surface** (addresses: the nightly-GC,
   binary-cache-poisoning, and trust-anchor majors). Document the
   nightly-unavailable recovery (bump `PUP_NIGHTLY`+`PUP_VERSION` together),
   integrity-check the restored cargo-pup binary (SHA256) before exec and confirm
   the cache isn't writable from `pull_request`, and gate the install behind a
   presence probe so the read-only `check` path is a true no-op.
6. **Close the deny-graph host-triple blind spot** (addresses: the multi-lens deny
   coverage major). Add `x86_64-unknown-linux-gnu` and `aarch64-apple-darwin` to
   `deny.toml [graph] targets` (extra targets are cheap to evaluate), and track it
   as a work-item edge rather than only a deny.toml comment.
7. **Bring `tasks/README.md` and the "check = CI" claim up to date** (addresses:
   the two documentation majors). Schedule concrete `tasks/README.md` edits — a
   `cli` row, the workspace-scope deny/pup entries, the `build:*` family, the
   `test`/coverage path — and qualify the "(this is what CI runs)" framing in both
   `tasks/README.md` and CLAUDE.md so a green `check` is not advertised as implying
   a green CI.

## Per-Lens Results

### Architecture

**Summary**: The plan is architecturally strong: it consistently extends the
established two-layer mise+invoke task pattern, the component-leads/family-trails
naming convention, and the repo's check/default separation rather than inventing a
parallel structure for Rust. Coupling is well-managed through a single-source-of-
truth constants module, the inward-dependency-direction enforcement (cargo-pup +
cargo-deny ban-lists) is structurally faithful to ADR-0009/0010, and tradeoffs are
explicitly acknowledged with named fallbacks. The main architectural risks are
concentration of mergeability risk on a single immature nightly tool, the
documented deny-graph coverage gap on host-dev triples, and a growing manual-sync
surface (now a fourth hand-mirrored value) with no automated guard.

**Strengths**:
- Faithful extension of the two-layer task architecture and component naming
  convention — Rust joins as first-class components (cli, deny, pup).
- Single-source-of-truth design (tasks/shared/rust.py) with tests asserting the
  same constants.
- Architecturally correct ADR-0009 split: cargo-pup intra-crate, cargo-deny
  ban-lists at crate boundaries, both scoped as workspace-level roll-ups.
- Evolutionary fitness: a future kernel crate adds one roll-up + edges + a
  test:unit leaf, with library-vs-binary crates distinguished.
- Tradeoffs acknowledged with concrete fallbacks rather than hidden.
- Wiring prose converted to executable assertions (test_mise_wiring.py,
  test_workflows.py).

**Findings**:
- 🟡 (major, high) Whole-repo mergeability becomes a SPOF on the least-mature tool
  (cargo-pup blocking nightly in check + default). Recurs from review 1; mitigated
  by the PUP_MODE=warn toggle — consider defaulting warn until 0007's rules land.
- 🟡 (major, medium) cargo-deny graph covers only the four release triples, leaving
  the host-dev triple's dependency closure un-evaluated; documented follow-up but
  should be a tracked work-item edge.
- 🔵 (minor, high) A fourth hand-mirrored value (clippy msrv) with no automated
  coherence check; add a coherence assertion to test_mise_wiring.py.
- 🔵 (minor, medium) build:cli introduces the repo's first cargo release-build path,
  structurally separate from the (future) release pipeline; note 0008 should share
  its derivation.
- 🔵 (minor, medium) Coverage instrumentation is structurally invisible in the task
  graph, reachable only via an env toggle inside a leaf.

### Code Quality

**Summary**: The plan adheres closely to the repo's established invoke task idiom,
reuses a single shared-constants source of truth, and lands TDD command-string
tests with each phase. The main code-quality risks are concentrated in
tasks/shared/rust.py: environment toggles read into module-level constants at
import time create hidden global state that is awkward to test, and the resulting
branch-in-task-body pattern plus the OS-aware build:cli logic introduce the only
real new complexity over the existing branch-free task bodies.

**Strengths**:
- New task bodies faithfully mirror the established exemplars (warn=True, pty=False,
  manual exit-code check, Exit naming the fix task).
- Magic literals centralised in tasks/shared/rust.py and asserted in tests.
- check/test/build separation captured as executable assertions.
- Comments reserved for genuinely non-obvious "why".
- Deliberately improves on the fix-body idiom (clippy --fix logs a warning on
  non-zero rather than silently swallowing).

**Findings**:
- 🟡 (major, high) Env toggles captured as module-level constants at import time +
  from-import create hidden global state and brittle tests; expose call-time
  functions.
- 🔵 (minor, medium) Advisory/warn path uses bare print() rather than structured
  logging.
- 🔵 (minor, medium) OS-aware target selection couples build.cli to host detection;
  extract a pure host_targets() helper.
- 🔵 (minor, low) test:unit:cli leaf named check() with a docstring that no longer
  matches the task's job (blurs check/test vocab).
- 🔵 (minor, low) Repeated cd/warn/exit boilerplate across every new Rust leaf;
  optional run_checked() helper.

### Test Coverage

**Summary**: The plan is unusually strong on test provisions: every invoke task
ships TDD command-string tests asserted against shared constants, both toggle
branches are pinned, the mise wiring is made executable, CI job topology is guarded,
and the two manual "breaking it fails CI" steps are converted into executed
regression tests. The most significant gap is a skip-gating reliability hole: the
cargo-deny and cargo-pup behavioural regression tests live under
tests/integration/tasks/ (run by the existing test-integration matrix job) yet the
plan claims they "run, not skip" in check-supply-chain/check-architecture — with no
provision guaranteeing those tools are present where the tests execute, they
silently skip-to-green.

**Strengths**:
- Constants-as-single-source-of-truth with command-string tests closes the
  mise.toml/task-body drift gap and survives the 0007 rename.
- Both env-toggle branches explicitly tested (COVERAGE on/off, PUP_MODE deny/warn)
  with defaults asserted (but see the import-time caveat from correctness/code-
  quality).
- test_mise_wiring.py turns depends/aggregate edges into executable assertions,
  including negative assertions.
- The two "breaking it fails the build" manual steps converted into executed
  regression tests.
- Negative assertion that the coverage command carries no --fail-under.
- OS-aware build task tested for both Darwin and Linux deterministically.

**Findings**:
- 🔴 (critical, high) Skip-gated regression tests live in test-integration but the
  plan asserts they run in check-supply-chain/check-architecture — they skip-to-
  green in CI as placed.
- 🟡 (major, high) The skip-gate is the single point of failure for CI coverage but
  its correctness is never asserted (a misnamed probe skips permanently/silently).
- 🟡 (major, medium) test_workflows.py is named the sole guard for non-mergeability
  but cannot assert branch-protection.
- 🔵 (minor, medium) OS-aware build test determinism hinges on call-time
  evaluation, left underspecified.
- 🔵 (minor, medium) Coverage tooling validated only against a trivial straight-line
  test; give the bootstrap test a branch.
- 🔵 (minor, low) The pup regression test asserts the tool can fail, not that the
  committed pup.ron is wired/parsed correctly.

### Correctness

**Summary**: The task-tree wiring is internally consistent across the five
incremental phases — the enumerated arrays reconcile with the per-phase additions,
and the mise-name to invoke-path mappings are sound against existing precedents.
The most serious correctness defect is the coverage/pup-mode toggle being read at
module-import time and re-bound via a from-import, which makes both env toggles
non-functional at runtime and silently un-monkeypatchable in the specified tests. A
secondary concern is the OS-aware target filter producing a silently-passing empty
build on an unrecognised platform.

**Strengths**:
- Incremental wiring is internally consistent; the per-phase additions converge on
  the enumerated final arrays without contradiction.
- mise-name to invoke-path mappings correct against precedent (build:cli→build.cli,
  deps:install:pup→deps.install-pup).
- The cargo +nightly override mechanism correctly reasoned and guarded by a
  pre-flight version check.
- The clippy --fix non-zero edge case explicitly handled.

**Findings**:
- 🟡 (major, high) Env toggles read at import time and re-bound via from-import are
  inert at runtime and untestable.
- 🟡 (major, medium) OS-aware target filter yields a silently-passing empty build on
  an unrecognised platform.
- 🔵 (minor, medium) deps:install:pup idempotency claim for cargo install --locked
  is overstated; affects every read-only check run.
- 🔵 (minor, medium) build:cli -p builds lib+bin; constrain to --bin/--bins so it
  always exercises the link step.
- 🔵 (minor, low) cargo llvm-cov nextest --summary-only must still propagate the
  underlying test exit code; assert it.

### Security

**Summary**: Judged as a supply-chain hardening story, the plan gets the headline
controls right: full SHA-pinning of every third-party action, a workspace-wide
least-privilege permissions default with elevated release jobs kept explicit, a
native-tls/OpenSSL ban, an explicit cargo-deny policy with unknown-registry/git =
deny, and a call to keep the advisory DB fresh. The principal residual concerns are
the trust surface of the source-only nightly cargo-pup toolchain, the integrity of
the cargo-pup binary cache the plan introduces, and the absence of checksum
verification on the new fetch paths.

**Strengths**:
- SHA-pins every third-party action to a full 40-char commit, closing the
  re-pointable-tag vector in the high-privilege release/attest jobs.
- Top-level workflow contents: read default; only push-only release jobs keep an
  explicit elevated block.
- cargo-deny policy set explicitly (yanked=deny, unknown registry/git=deny,
  permissive-only license allow-list, native-tls ban live day one).
- Advisory-DB freshness called out directly (fetch fresh, fail not warn if
  unavailable).
- cargo-pup pinned to an exact version with --locked and a pinned nightly.

**Findings**:
- 🟡 (major, medium) cargo-pup is a pre-1.0 source-only rustc-driver executed on the
  read-only check path and in CI; --locked doesn't verify the tool's own integrity.
- 🟡 (major, medium) The cargo-pup built-binary cache (keyed without a content hash)
  is a cache-poisoning → code-execution vector.
- 🔵 (minor, medium) rustup toolchain install fetches the nightly with no explicit
  signature/checksum note.
- 🔵 (minor, high) deny.toml [graph] targets covers only the four release triples;
  advisory/ban coverage has a hole on the dev/CI triple.
- 🔵 (minor, medium) cargo-pup's own build closure is never advisory-scanned.

### Compatibility

**Summary**: This is fundamentally a dependency- and environment-integration plan,
so the compatibility lens is highly applicable. The plan is rigorous about
cross-environment behaviour (host-native matrix, coverage on both OSes, the
mise→rustup mechanism, SHA-pinning) and explicitly flags several version-schema
risks for implementation-time verification. The residual concerns are concentrated
in version-pin mutual compatibility: the cargo-deny 0.19.8 [advisories] schema, the
pre-1.0 cargo-pup/nightly coupling that gates mergeability, and the macOS-arm host
building x86_64-apple-darwin.

**Strengths**:
- Cross-platform build genuinely covered (host-native matrix, all four triples);
  coverage on both OSes.
- Version pins explicit and centralised with command-string tests.
- mise/rustup +toolchain mechanism correctly identified and guarded by pre-flight.
- Cargo.lock committed and generated with the pinned cargo.
- deny.toml graph evaluates the release configuration, avoiding false-positive bans.
- First-class advisory↔blocking toggle (subject to the import-time caveat).

**Findings**:
- 🟡 (major, medium) deny.toml [advisories] schema (unmaintained="all") must be
  verified against 0.19.8 or deny:check errors on config; plan already gates this.
- 🟡 (major, high) cargo-pup/nightly coupling has no in-tree fallback when the dated
  nightly is GC'd; PUP_MODE=warn doesn't cover an install-step failure.
- 🔵 (minor, medium) macОС-arm runner building x86_64-apple-darwin needs SDK
  x86_64 slice; verify the cross-arch link, not just compile.
- 🔵 (minor, medium) cargo-llvm-cov 0.8.7 ↔ cargo-nextest 0.9.138 composition must
  agree on the nextest CLI surface; verify the pair.
- 🔵 (minor, medium) mise short-name resolution must carry prebuilts for both
  ubuntu and macos-arm.
- 🔵 (minor, high) SHA-pinned actions never auto-patch; pair with a refresh cadence.
- 🔵 (minor, low) branch-protection matrix-leg check names are GitHub-controlled;
  copy exact names from a completed run.

### Portability

**Summary**: The plan establishes a Rust toolchain across a macOS-primary dev
environment and a two-OS CI matrix, and it is genuinely portability-conscious:
host-native builds, coverage on both OSes, and no new platform-specific shell. The
main portability risks are (1) the PR-time build:cli strategy structurally diverges
from ADR-0002's committed cargo-zigbuild cross-compile model, so the merge guard
validates a build path the release pipeline will not use; (2) the macOS/cross-arch
second-arch reliance on a self-contained-linking assumption that breaks the moment a
C-FFI dependency lands; and (3) deny.toml/dev-triple coverage gaps.

**Strengths**:
- Host-native build matrix is the correct portability move (sidesteps cross-linking
  both directions, covers all four triples).
- Coverage folded into the test run executes on every test OS, retiring the prior
  ubuntu-only carve-out.
- deny.toml graph pinned to the four shipped triples, evaluated as shipped.
- rustup-vs-mise interaction correctly resolved with a PATH pre-flight, validated
  on a clean ubuntu runner.
- native-tls/OpenSSL ban live from day one with a regression test.
- Honest framing of the inherent one-machine-is-one-OS local/CI gap.

**Findings**:
- 🟡 (major, high) build:cli host-native strategy diverges from ADR-0002's committed
  cargo-zigbuild cross-compile-from-one-host model; the guard validates a different
  build path than ships.
- 🟡 (major, high) Self-contained-linking assumption breaks on the first C-FFI
  dependency (0007's reqwest/tokio stack); the matrix goes red on 0007 with no
  provisioning staged.
- 🔵 (minor, high) Host dev triple (linux-gnu / cross-arch darwin) is built and
  tested but never deny-evaluated.
- 🔵 (minor, medium) platform.system() host detection has no handling for
  unsupported developer OSes.
- 🔵 (minor, medium) Source-only nightly cargo-pup validated only on ubuntu yet runs
  in every macOS developer's default check.
- 🔵 (suggestion, medium) musl static-link guarantee covers only the TLS vector; add
  a positive static-linkage assertion (file/ldd) to the musl leg.

### Documentation

**Summary**: The plan is documentation-conscious: it lands docs in the same phase
as each surface, enumerates the CLAUDE.md spots, calls out the msrv fourth-mirror
hazard, documents both env toggles where developers look, and adds a CONTRIBUTING.md
runbook for the manual branch-protection step. The main weaknesses are in
documentation-consistency: the new build:cli/build:* family and the Rust component
are not reflected in tasks/README.md's component table, family-aggregate prose, or
conventions, and the existing "check is the exact read-only set CI runs" framing
becomes inaccurate in ways the plan only partially reconciles.

**Strengths**:
- Phase-distributed documentation is deliberate and well-reasoned.
- Both env toggles documented where a developer would look, with a single source of
  truth in tasks/shared/rust.py.
- The msrv fourth-mirror hazard added to Conventions; clippy.toml carries a
  steering comment.
- The CONTRIBUTING.md branch-protection runbook captures the genuinely non-obvious
  operator knowledge (exact-name match, matrix-leg-per-check, appears-after-first-
  run).
- Recognises pre-existing forward references (rustfmt.toml already listed) and
  rewords rather than duplicates.

**Findings**:
- 🟡 (major, high) tasks/README.md component table and family-aggregate prose not
  updated for Rust (the canonical task-tree-shape file CLAUDE.md points to).
- 🟡 (major, high) The "check is exactly what CI runs" claim becomes inaccurate and
  is only half-reconciled (build-cli and test-unit run in CI but not in check).
- 🔵 (minor, medium) The new build family is introduced without documenting the
  build:* namespace convention.
- 🔵 (minor, medium) Documented single-test command bypasses the default coverage
  path and uses ambiguous nextest filter syntax.
- 🔵 (minor, medium) cargo-pup [tools]-exception note is well-aimed but the inline
  tool inventory list also needs refreshing.
- 🔵 (minor, low) New root config files are not added to any discoverability index
  (a Rust subsection in CLAUDE.md Architecture).

---
*Review generated by /accelerator:review-plan*

## Re-Review (Pass 2) — 2026-06-28T09:45:00+00:00

**Verdict:** REVISE

The revision is a strong, high-quality pass: the **pass-1 critical is resolved**
(the deny/pup behavioural regressions are repartitioned so each runs where its tool
is provisioned, with hard-fail-skip under CI), and the **large majority of pass-1
majors are closed** — call-time env toggles, `host_targets()` Exit-on-unknown-OS,
the staged musl-tools step, `--bin` + static-linkage assertion, the expanded deny
`[graph]` targets, the honest `test_workflows.py` reframing, the cargo-pup
nightly-GC recovery note, and the concrete `tasks/README.md` / "check ≠ CI" doc
edits. The verdict stays REVISE only because the deeper pass surfaced a tight
cluster of **new gaps introduced by the fixes themselves** — most concretely a
mis-targeted invoke registration that would break `mise run`, the `requires_pup`
marker being neither registered nor wired into the `test:integration` run command,
and an undefined `log` collaborator that the print→logging change left dangling.
This is a "one more small pass" REVISE, not a structural one.

### Previously Identified Issues

- 🔴 **Test Coverage** (pass-1 critical): regression tests skip-to-green in CI —
  **Resolved in design** (deny → `test-integration` where cargo-deny is a `[tool]`,
  hard-fail-skip under CI; pup → `check-architecture` via a `requires_pup` marker).
  Its *plumbing* surfaced two new majors below.
- 🟡 **Correctness / Code Quality**: import-time env toggles inert/untestable —
  **Resolved** (call-time `coverage_enabled()`/`pup_mode()`; both-branch tests via
  `monkeypatch.setenv`). Residual value-semantics minors below.
- 🟡 **Portability**: `build:cli` diverges from ADR-0002 zigbuild — **Addressed**
  (recorded decision, ADR amendment owed, 0008-alignment + shared `host_targets()`
  derivation). Still a standing major until the ADR lands; re-review recommends
  making the ADR a hard prerequisite, not "owed".
- 🟡 **Portability**: self-contained linking breaks on 0007's C-FFI stack —
  **Resolved** (`musl-tools` staged as a commented, ready-to-enable step).
- 🟡 **Correctness / Portability**: OS-aware empty build → false green —
  **Resolved** (`host_targets()` `Exit`s on unsupported OS; tested).
- 🟡 **Compatibility**: cargo-pup nightly-GC, no in-tree fallback — **Addressed**
  (recovery note: bump `PUP_NIGHTLY`+`PUP_VERSION` together). Residual: no
  escape-valve for a *permanently* GC'd nightly wedging `check` (minor below).
- 🟡 **Security**: cargo-pup binary-cache poisoning — **Partially resolved**
  (SHA-256 verify + not-writable-from-PR added) — but the scheme is weak as
  specified; see new issue.
- 🟡 **Security**: cargo-pup pre-1.0 trust anchor — **Addressed** (trust-boundary
  note; accepted risk recorded).
- 🟡 **Architecture / Security / Portability**: deny graph host-triple blind spot —
  **Resolved** (`x86_64-unknown-linux-gnu` + darwin added to `[graph] targets`).
- 🟡 **Test Coverage**: skip-gate correctness unasserted — **Resolved** (hard-fail
  under `CI`).
- 🟡 **Test Coverage**: `test_workflows.py` overstated as mergeability guard —
  **Resolved** (reframed as job-topology only; `gh api` branch-protection audit
  recommended as follow-up).
- 🟡 **Architecture**: blocking cargo-pup SPOF — **Still present (accepted)**;
  recurs from review 1. Its mitigation (the toggle) now actually functions, which
  was the real gap.
- 🟡 **Compatibility**: cargo-deny 0.19.8 `[advisories]` schema — **Mitigated**
  (already gated by an impl-time clean-`deny:check` criterion).
- 🟡 **Documentation**: `tasks/README.md` not updated for Rust — **Resolved**
  (concrete cli/deny/pup/`build:*` table edits specified).
- 🟡 **Documentation**: "check is exactly what CI runs" inaccurate — **Resolved**
  (qualification scheduled for both `tasks/README.md` and CLAUDE.md).
- 🔵 (pass-1 minors): print→logging, `pup.ron`-loads assertion, llvm-cov exit-code
  test, bootstrap test branch, `msrv` coherence test, SHA-pin refresh cadence,
  tool-pairing/prebuilt verification, macOS cross-arch verification — **Resolved /
  folded in** (the print→logging fix introduced a new issue, below).

### New Issues Introduced (or surfaced by the deeper pass)

- 🟡 **Correctness** (new): `tasks/test/cli.py` is to be registered in
  `tasks/__init__.py`, but `test` is a sub-package whose Collection is assembled in
  **`tasks/test/__init__.py`**. As written, `invoke test.cli.run` would not
  resolve and `mise run test:unit:cli` (hence the whole `test` roll-up) would fail.
  Fix the file reference (register in `tasks/test/__init__.py`).
- 🟡 **Test Coverage** (new): the `requires_pup` deselection is never wired into the
  `test:integration:tasks` mise `run` line (still a bare `uv run pytest
  tests/integration/tasks -v`), so the pup regression would run — and hard-fail —
  in the unprovisioned `test-integration` job. Add `-m "not requires_pup"` and
  assert it.
- 🟡 **Test Coverage** (new): the `requires_pup` marker is never registered in
  `pyproject.toml` `[tool.pytest.ini_options] markers`; an unregistered/typo'd
  marker silently selects/deselects nothing. Register it (with `--strict-markers`).
- 🟡 **Code Quality** (new, from the print→logging fix): the advisory paths now
  mandate `log.warning(...)` / "the module's logger", but `tasks/` uses no logging
  and the snippets show a bare `log` with no `getLogger`/import or configured
  handler — so the message may not surface and the "assert the log record" tests
  have no defined target. Pin the logging approach (or revert to `print` + assert
  stdout).
- 🟡 **Security** (new): the cargo-pup cache SHA-256 is recorded *in* the same
  writable Actions cache it protects — self-checking against an attacker-writable
  checksum is not tamper detection. Anchor the expected hash out-of-band (a
  committed constant tied to `PUP_VERSION`) and make the not-writable-from-PR
  property a concrete assertion.
- 🟡 **Security** (new): `Swatinem/rust-cache` (compiled `target/`) is added to the
  PR-triggered jobs without the same cache-poisoning analysis applied to the pup
  binary cache — restored compiled artifacts are executed. Apply the analysis /
  record the accepted-risk boundary.
- 🟡 **Portability** (new/sharpened): `x86_64-apple-darwin` link coverage on the
  arm64 `macos-latest` runner is verified only by a manual checkbox; promote to an
  automated arch assertion (`lipo -archs`/`file`) so runner-SDK drift reddens CI.
- 🔵 (new minors): `coverage_enabled()` treats only the literal `"off"` as
  disabling (other falsey values stay on); `pup_mode()` matches only exact
  `"warn"` (a typo silently stays blocking) — normalise both; the `deps:install:pup`
  presence probe's `grep -q "0.1.8"` is an unanchored substring match; `rustup
  toolchain install` should `Exit` with the nightly-GC bump message *before* the
  `+nightly` pre-flight; `host_targets()` should partition the single `TARGETS`
  source (assert the union equals the shipped set); add a triple-union test and a
  pure static-linkage-verdict helper test; reconcile CLAUDE.md's inline tool list
  fully (drop `node`/`jj`, add `gh`/`actionlint`); cross-link CONTRIBUTING.md from
  CLAUDE.md; reconcile the existing "unrelated to the `build:*` namespace" note;
  consider pinning `macos-14` over `macos-latest` and committing a Dependabot/Renovate
  config; decide the rustls TLS backend (ring vs aws-lc-rs) now.

### Assessment

The plan moved from "REVISE on a critical + 14 majors" to "sound and nearly ready"
— the structural decisions are right and the pass-1 critical is closed. The
remaining work is a focused, low-risk pass dominated by **implementation-plumbing
gaps the fixes introduced**: the wrong registration file (would break `mise run`),
the `requires_pup` marker registration + `test:integration` deselection wiring, and
the undefined logger from the print→logging change. Addressing those three, plus
the two security hardening items (out-of-band cache checksum; rust-cache poisoning
analysis) and the macOS cross-arch assertion, would clear the way to APPROVE. The
recurring majors (cargo-pup SPOF, the ADR-0002 divergence) are accepted, conscious
tradeoffs — the ADR-0002 amendment should be tracked as a hard prerequisite for
0008 rather than left "owed".

## Re-Review (Pass 3) — 2026-06-28T10:30:00+00:00

**Verdict:** REVISE (converging — diminishing returns)

The pass-2 batch is **resolved**: the `tasks/test/__init__.py` registration is
correct, the `requires_pup` partition is now fully wired and tamper-evident (marker
registration + `--strict-markers`, the `-m "not requires_pup"` filter on
`test:integration:tasks`, the explicit `-m requires_pup` step in
`check-architecture`, both backed by wiring/workflow assertions), the print→logging
revert is cited as a *strength*, the env toggles normalise correctly, and the
x86_64-darwin arch check is automated. No critical, and no pass-2 major survives.

The verdict stays REVISE only because the deeper pass surfaced a tail of **smaller,
second-order issues — several introduced by the pass-2 fixes themselves** (the
classic fix-introduces-finding dynamic). These are concrete and cheap, but they are
also exactly the class of thing TDD/implementation will surface immediately, so the
plan is at the point of diminishing review returns.

### Previously Identified Issues (pass-2 → now)

- 🟡 Correctness: `test.cli` wrong `__init__.py` — **Resolved** (now
  `tasks/test/__init__.py`, confirmed correct).
- 🟡 Test Coverage: `requires_pup` deselection unwired — **Resolved** (3-edit
  plumbing + assertions; now tamper-evident).
- 🟡 Test Coverage: marker unregistered — **Resolved** (registered + `--strict-markers`).
- 🟡 Code Quality: undefined logger — **Resolved** (reverted to `print("WARNING:")`
  + `capsys`; now cited as a strength).
- 🟡 Security: cache checksum co-located with writable cache — **Partially resolved**
  (now out-of-band) — but a new per-OS keying gap surfaced (below).
- 🟡 Portability: x86_64-darwin link coverage manual-only — **Resolved** (automated
  `lipo`/`file` arch assertion).
- 🟡 Architecture: cargo-pup SPOF; provisioning-in-`check` — **Still present
  (accepted)**, mitigations now functional.
- 🟡 Documentation: `tasks/README.md` / "check ≠ CI" — **Resolved**.
- 🔵 minors (coverage_enabled/pup_mode normalisation, host_targets partition,
  unanchored grep, tool-inventory reconcile, CONTRIBUTING cross-ref) — **Resolved /
  folded in** (the grep fix overcorrected — see new issues).

### New Issues Introduced (or surfaced by the deeper pass)

- 🟡 **Security / Correctness** (from the pass-2 cache-checksum fix): the out-of-band
  checksum is keyed `(PUP_NIGHTLY, PUP_VERSION)` but the cache and binaries are
  **per-OS** — a single SHA can't exact-match both legs. Make the committed checksum
  a per-OS map keyed `(PUP_NIGHTLY, PUP_VERSION, OS)`. Relatedly, the version-string
  presence probe cannot detect a *same-version* poisoned binary, so the "force
  absent on mismatch" wiring must actually delete/rehash the restored binary, not
  rely on the `--version` probe.
- 🟡 **Compatibility / Correctness** (from the pass-2 grep fix): `grep -Fqx
  "cargo-pup 0.1.8"` is a whole-line exact match that likely won't match real
  `cargo pup --version` output (trailing metadata / name form), so the probe always
  reports "absent" and the multi-minute install runs every time — breaking the
  idempotence the probe exists for (and `pup:check` is in `check`). Relax to a
  tolerant version-token match verified against captured real output.
- 🟡 **Portability** (sharpened): the staged `musl-tools` step covers only the
  x86_64 musl linker; **`aarch64-unknown-linux-musl` needs an aarch64 cross-linker**
  (`gcc-aarch64-linux-gnu` + `CARGO_TARGET_*_LINKER`). The staged step must provision
  it, or the arm64 musl leg breaks on the 0007 C-FFI merge.
- 🟡 **Documentation** (phase-distribution inconsistency): the CLAUDE.md tool-inventory
  reconcile is wholly deferred to Phase 4, contradicting the plan's own
  "docs land in the introducing phase" principle — after Phases 2/3 merge, the
  inventory is stale. Split it: cargo-nextest/llvm-cov in Phase 2, cargo-deny in
  Phase 3, cargo-pup + node/jj-drop in Phase 4.
- 🟡 **Security**: `Swatinem/rust-cache` poisoning is downgraded to an accepted-risk
  note rather than fail-closed; it restores executed `target/` artifacts on the
  push/release lane that produces the *attested* binary. Disable rust-cache on the
  release-lane build (or assert it never restores a PR-writable key).
- 🔵 (new minors): `host_targets()` must unpack `TARGETS` pairs and handle
  `platform.system()` case (`"Darwin"` vs lowercase `darwin` substring) — fail
  closed on an empty partition; verdict-helper tests should include
  malformed/empty/universal-binary inputs (fail closed); mirror the existing
  `_KNOWN_BAD_SHAPES` parametrization for the new `test_workflows.py` assertions
  (avoid positive-only tautology); pin runners to dated images
  (`ubuntu-24.04`/`macos-15`) over `-latest`; document `LUMINOSITY_*` toggles in
  `tasks/README.md`; annotate ADR-0002 itself with a forward-pointer; split the
  msrv-coherence assertion into its own test module; commit the Dependabot/Renovate
  config rather than leaving "cadence" unowned.

### Assessment

The plan is **fundamentally sound and converging** — three review passes have driven
it from "critical + 14 majors" to "a tail of second-order implementation details."
Crucially, the new majors are no longer design flaws; they are fix-introduced
overcorrections (the grep probe, the per-OS checksum) and provisioning specifics
(the aarch64 musl linker) that **TDD will surface on the first implementation run**
— the probe test fails immediately if the match is wrong; the per-OS checksum fails
the macOS leg immediately; the aarch64 link fails the moment 0007 lands. This is the
point of diminishing returns for *plan* review: further passes will keep finding
ever-finer implementation nuance that the build itself catches faster.

Recommended path: do one **final, narrow fix** for the four concrete new majors that
would otherwise cause real CI breakage (per-OS checksum keying + force-absent wiring;
the grep probe relaxation; the aarch64 musl cross-linker; the doc phase-distribution
split), treat the rest as accepted/implementation-time, and **proceed to
implementation** — where the remaining nuance is cheaper to catch than in another
review round. The recurring cargo-pup SPOF and ADR-0002 divergence remain conscious,
documented tradeoffs.

## Approval — 2026-06-28T11:00:00+00:00

**Verdict: APPROVE.** The pass-3 recommended final narrow fix has been applied to
the plan, resolving the four concrete new majors:

- ✅ **Per-OS cache checksum + force-absent wiring** (Phase 4 §4): the out-of-band
  checksum is now a per-OS map keyed `(PUP_NIGHTLY, PUP_VERSION, OS)` with a
  unit-test that every cached OS has an entry, and a mismatch now **deletes** the
  restored binaries so the probe genuinely sees "absent" (integrity no longer rests
  on the version-string probe, which cannot detect same-version tampering).
- ✅ **Presence-probe relaxation** (Phase 4 §1): replaced the brittle `grep -Fqx`
  whole-line match with a Python version-token equality check, fixing both the
  substring false-match and the whole-line brittleness that would have forced a
  reinstall every run.
- ✅ **aarch64 musl cross-linker** (Phase 1 §6/§7): the staged step now provisions
  `gcc-aarch64-linux-gnu` + `CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER`
  alongside `musl-tools`, so the arm64 musl leg does not break on the 0007 merge.
- ✅ **Doc phase-distribution** (Phases 2/3/4): the CLAUDE.md tool-inventory
  reconcile is split to land with each tool's introducing phase, honouring the
  plan's own per-phase docs principle.

All blocking findings across the three passes are resolved. The remaining items are
deliberate, documented tradeoffs (the blocking cargo-pup nightly SPOF; the ADR-0002
per-OS-native-vs-zigbuild divergence, with an amending ADR tracked as a hard
prerequisite for 0008) and fine-grained implementation-time nuance (dated-runner
pinning, rust-cache on the release lane, `host_targets` case-handling,
verdict-helper edge inputs) that TDD/implementation will surface faster than further
plan review. The plan is approved for implementation; status remains `ready`.
