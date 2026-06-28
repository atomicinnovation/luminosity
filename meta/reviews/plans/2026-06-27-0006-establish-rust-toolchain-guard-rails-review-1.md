---
type: plan-review
id: "2026-06-27-0006-establish-rust-toolchain-guard-rails-review-1"
title: "Plan Review: Establish Rust Toolchain Guard Rails in mise + CI"
date: "2026-06-27T14:12:18+00:00"
author: Toby Clemson
producer: review-plan
status: complete
parent: "plan:2026-06-27-0006-establish-rust-toolchain-guard-rails"
target: "plan:2026-06-27-0006-establish-rust-toolchain-guard-rails"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, code-quality, test-coverage, correctness, security, compatibility, portability, documentation]
review_number: 1
review_pass: 2
tags: [rust, tooling, ci, guard-rails, mise, architecture-enforcement]
last_updated: "2026-06-27T17:00:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: Establish Rust Toolchain Guard Rails in mise + CI

**Verdict:** REVISE

This is a well-researched, disciplined plan that faithfully extends the existing
two-axis mise/invoke task tree, correctly preserves the version-coherence
machinery, and is admirably honest about its own most volatile facts. The reason
for REVISE is not plan quality in the abstract — it is that the plan's central
acceptance criterion (a blocking cargo-pup architecture lane that makes
`mise run check` and `mise run` exit 0) rests on a toolchain mechanism the plan
itself marks "confirmed at impl," and five independent lenses converged on that
same lane as the dominant risk. Secondary themes — the read-only `check`
invariant being broken by coverage and an install side-effect, the musl-static
guarantee never actually being exercised pre-merge, and security gaps in tool/
action pinning — are each individually addressable but collectively warrant a
revision pass before implementation.

### Cross-Cutting Themes

- **The cargo-pup nightly lane is the dominant risk** (flagged by: architecture,
  correctness, security, compatibility, portability) — Every lens that examined
  Phase 4 found a different load-bearing problem with the same component: mise's
  rust backend may not pin a second (nightly) toolchain (`rust-nightly` is not a
  standard tool short-name); the `cargo +nightly-2026-01-22` override syntax is a
  *rustup* feature that may not resolve when mise (not rustup) provisions the
  stable toolchain; `cargo install cargo_pup` is unpinned (no version, no
  `--locked`); the pre-1.0 rustc-driver is ABI-coupled to the exact nightly; and
  the lane is wired as *blocking* while enforcing zero rules until 0007. The plan
  acknowledges this volatility but defers the core mechanism to implementation —
  for a blocking gate on the whole repo's mergeability, the mechanism must be
  resolved (a spike) before the plan is approved.

- **The read-only `check` invariant is broken** (flagged by: correctness,
  architecture) — `check` is documented as "the read-only format, lint, and type
  checks (what CI runs)," but the plan folds an instrumented `cargo llvm-cov`
  build into `cli:check` (which goes into `check`) and gives `pup:check` a
  `depends` edge on the *mutating* `deps:install:pup`. `mise run check` would no
  longer be fast or side-effect-free.

- **Security/architecture config is verified manually, not by regression tests**
  (flagged by: test-coverage, security) — The native-tls ban, the license
  allow-list, the advisories policy, and the CI-job-presence wiring (the only
  automated guard for "a failing Rust check makes a PR non-mergeable") are all
  checked only under "Manual Verification" or marked "optional." These are
  exactly the guard rails that should have automated regression protection.

- **The musl-static guarantee is never exercised pre-merge** (flagged by:
  portability) — Every build/check targets the host (apple-darwin locally,
  linux-gnu on ubuntu CI); the musl cross-compile only runs in push-only release
  jobs. A static-link regression sails through every PR gate, and the crate-name
  ban list plus `all-features = true` do not fully model the as-shipped
  `default-features = false` musl build.

- **Magic constants are duplicated without a drift guard** (flagged by:
  code-quality, test-coverage) — The nightly string and the `-p luminosity`
  crate name appear in mise.toml, multiple task bodies, and CI YAML, with no
  single source of truth a test can pin.

### Tradeoff Analysis

- **Blocking-now vs enforcing-nothing-yet (cargo-pup)**: 0006's acceptance
  criterion explicitly demands a *blocking* cargo-pup lane, but the architecture
  lens notes the lane enforces zero rules until 0007 adds them, so the repo takes
  on the full operational liability of a blocking nightly gate during the window
  it provides no architectural benefit. Recommendation: either run pup advisory
  in the bootstrap window and promote to blocking with 0007's rules, or
  explicitly justify the blocking-with-empty-rules state as a deliberate,
  time-boxed acceptance-criterion satisfaction — and make the advisory/blocking
  toggle a first-class, tested knob either way.

- **Strict license allow-list (fails-closed) vs forward friction**: The minimal
  allow-list is the *safe* direction (it cannot admit an unsafe license), but it
  will hard-fail the first real-dependency story (0007's reqwest/rustls/tokio/
  clap stack pulls ISC, BSD-2-Clause, Zlib, Unicode-DFS-2016, etc.). The risk is
  reactive broadening under merge pressure. Recommendation: pre-seed the known-
  safe permissive licenses the ADR-0010 stack requires, and require any future
  copyleft/MPL/GPL addition to be justified per-crate via
  `[[licenses.exceptions]]`.

### Findings

#### Critical

- 🔴 **Correctness / Compatibility / Portability**: cargo-pup nightly mechanism
  (`+toolchain` syntax + mise second-toolchain pin + rustup coupling) may not
  work as written
  **Location**: Phase 4 §1 & §3 — Pin the nightly + install step; pup:check body
  The `pup:check` body runs `cargo +nightly-2026-01-22 pup`, but `+toolchain` is
  a rustup feature that resolves against rustup-managed toolchains, while the repo
  provisions stable rust through mise's own backend; the `"rust-nightly"` `[tools]`
  line is not a standard mise short-name and is annotated "confirmed at impl." If
  the nightly is not rustup-registered (or rustup's cargo shim is not on PATH),
  the command fails with "toolchain not installed," the lane can never exit 0, and
  the Desired End State (`mise run check`/`mise run` → 0) is false. This should be
  resolved as a blocking spike, not deferred to implementation.

#### Major

- 🟡 **Architecture**: Blocking nightly cargo-pup lane is a single point of
  failure with an under-specified provisioning mechanism
  **Location**: Phase 4 — cargo-pup nightly lane
  A blocking gate depending on a pre-1.0 rustc-driver built under a pinned nightly
  makes the most volatile, least-mature component gate the entire repo's
  mergeability across all three languages. The advisory fallback is a prose risk
  note, not a designed switchable mechanism.

- 🟡 **Architecture**: Blocking architecture gate enforces nothing yet but
  carries full cost
  **Location**: Phase 4 §2 (pup.ron) + "What We're NOT Doing"
  `pup.ron` ships empty (real rules land in 0007), yet the lane is blocking in
  `check`/`default`, inverting cost/benefit until the paired story lands.

- 🟡 **Correctness**: Folding coverage into the read-only `check` contradicts its
  "read-only / fast" invariant
  **Location**: Wiring model + Phase 2 §3
  `coverage:cli:check` (an instrumented `cargo llvm-cov` build) is folded into
  `cli:check`, which is added to top-level `check` — defined as "read-only format,
  lint, and type checks (what CI runs)." This makes `check` heavy and runs
  coverage in both `check` and `default`.

- 🟡 **Correctness**: `pup:check` depends on the mutating `deps:install:pup`
  inside the read-only `check`
  **Location**: Phase 4 §3 + check aggregation
  `deps:install:pup` installs a nightly toolchain + `cargo install cargo_pup` — a
  multi-minute mutating side-effect — so `mise run check` is no longer
  side-effect-free and will fail for provisioning/network reasons unrelated to
  code correctness.

- 🟡 **Correctness**: "coverage subsumes the test run" reasoning conflates two
  run scopes
  **Location**: Phase 2 §3 + "Wiring model"
  The subsumption holds only within `cli:check`, not across the tree; a future
  reader trusting it could drop `test:unit:cli` and silently remove Rust tests
  from the fast `test`/CI lane.

- 🟡 **Security**: cargo-pup installed via unpinned `cargo install cargo_pup` (no
  version, no `--locked`)
  **Location**: Phase 4 §1
  For a story whose purpose is supply-chain pinning, the architecture-enforcement
  tool itself is an unpinned, mutable entry point (resolves latest 0.1.x + full
  transitive graph fresh, outside cargo-deny's scope) — breaking reproducibility
  and creating a code-execution vector that runs as a rustc-driver everywhere.

- 🟡 **Security**: New/existing third-party GitHub Actions pinned by mutable tag,
  not commit SHA
  **Location**: Phase 1 §6 / Phase 4 §4 / Performance Considerations
  `Swatinem/rust-cache@v2` (new), `jdx/mise-action@v4.1.0`, `actions/checkout@v5`,
  `actions/attest-build-provenance@v2` are tag-pinned; a re-pointed tag is a live
  CI code-execution vector, especially on `pull_request`-triggered jobs and the
  release jobs that sign/attest binaries.

- 🟡 **Security**: cargo-deny `[advisories]` relies entirely on implicit,
  version-sensitive defaults
  **Location**: Phase 3 §2 (deny.toml)
  Only `ignore = []` is set; vuln/unmaintained/yanked behaviour is left to
  defaults that have shifted across versions (`unmaintained` moved to
  `"workspace"`-only). Success criteria check only that sections "run," not that
  an advisory turns the build red.

- 🟡 **Code Quality**: Per-leaf test files diverge from the established
  one-file-per-family-module convention
  **Location**: Phase 1 §7, Phase 2 §5, Phase 3 §5, Phase 4 §5
  The plan proposes `test_format_cli.py`, `test_lint_cli.py`, etc., but the suite
  organizes tests one-per-family-module (`test_format.py` covers
  `tasks/format/scripts.py`, grouping cases into classes). Following the plan
  fragments Rust tests while shell/Python stay consolidated.

- 🟡 **Test Coverage**: CI-job presence assertion is the only automated guard for
  a core acceptance criterion, yet marked optional
  **Location**: Phase 5 §2
  "A failing Rust check makes a PR non-mergeable" has no automated test except the
  Phase 5 presence/`needs:` assertion, which is labelled optional — and branch
  protection itself is manual. A dropped job would silently disable a guard rail
  with nothing red.

- 🟡 **Test Coverage**: deny.toml ban-list and pup.ron correctness verified only
  manually
  **Location**: Phase 3 Success Criteria; Phase 4 §2
  The native-tls ban, license allow-list, and pup rules are checked only under
  "Manual Verification." Nothing automated reproduces a ban violation, so a future
  edit loosening `[bans] deny` passes green.

- 🟡 **Test Coverage**: The most fragile component (nightly install-step
  composition) has the vaguest test spec
  **Location**: Phase 4 §1 & §5
  "Assert the install-step composition" does not enumerate the required rustup
  commands, the `rust-src rustc-dev llvm-tools-preview` component set, or the
  toolchain string — so a dropped component (cargo-pup won't build) goes
  uncaught.

- 🟡 **Compatibility**: mise second-toolchain (nightly) pinning mechanism is
  unconfirmed and likely will not resolve as written
  **Location**: Phase 4 §1
  (Closely related to the Critical finding; recorded here for the
  compatibility-specific angle that there is no standard `rust-nightly` mise
  short-name and the `[tools]` line should likely be dropped in favour of an
  install task.)

- 🟡 **Compatibility**: cargo-pup rustc-driver is tightly coupled to the exact
  nightly + rustc-dev components; drift breaks the whole lane
  **Location**: Phase 4 §1
  A driver linking `rustc_private` refuses to load under any nightly but the one
  it was built against; DataDog/cargo-pup's known-good nightly may have moved.
  Recommend caching the *built* binary keyed on the nightly.

- 🟡 **Portability**: Nothing ever compiles the bootstrap crate for the musl
  targets the plan claims to protect
  **Location**: Phase 1 & 2 Success Criteria; Implementation Approach
  All checks target the host; the musl cross-compile runs only in push-only
  release jobs. A static-link regression passes every PR gate. Add a musl
  `cargo build --target x86_64-unknown-linux-musl` to PR-time checks.

- 🟡 **Portability**: Crate-name ban does not fully guarantee the musl-static
  invariant
  **Location**: Phase 3 §2 ([bans] deny list)
  Banning native-tls/openssl(-sys) catches the TLS vector but not other
  system-C-linking `*-sys` crates (libgit2-sys, curl-sys, libsqlite3-sys,
  libz-sys). The list is necessary-but-not-sufficient for static linking.

- 🟡 **Portability**: `all-features = true` evaluates a graph that diverges from
  the `default-features = false` release build
  **Location**: Phase 3 §2 ([graph])
  cargo-deny analyses feature combinations the shipped musl binaries never enable
  (ADR-0010 mandates `default-features = false`), so the only pre-merge musl guard
  judges a different build configuration than the one shipped.

- 🟡 **Portability**: cargo-pup lane couples the build to rustup, conflicting with
  mise-managed rust across environments
  **Location**: Phase 4 §1 & §3
  (Related to the Critical finding; the portability angle is the local-vs-CI
  divergence — passes locally where rustup exists, fails on a clean ubuntu runner
  or vice versa.)

- 🟡 **Documentation**: Phase 5 misses CLAUDE.md's now-inaccurate descriptions of
  what `check` and `default` run
  **Location**: Phase 5 §1
  CLAUDE.md line 24 calls `check` "format + lint + types across all components"
  and line 20 omits coverage/deny/pup from `default`; the mise.toml `check`/
  `default` descriptions drift the same way. Phase 5's edit list doesn't cover
  them.

- 🟡 **Documentation**: All docs deferred to Phase 5 while Phases 1–4 are
  independently mergeable — guaranteed interim doc drift
  **Location**: Implementation Approach (phasing) vs Phase 5
  If Phase 1 merges alone, CLAUDE.md still lists only `build-system, scripts` and
  README omits `cli` until Phases 2–5 land. Move doc edits into the phase that
  introduces each surface.

#### Minor

- 🔵 **Architecture**: `cli:check` diverges from the established
  `<component>:check` fold semantics (folds coverage, omits plain test) — make it
  explicit in tasks/README.md.
  **Location**: Wiring model + Phase 2 §1

- 🔵 **Architecture**: Version-coherence machinery is single-point-coupled to
  `cli/Cargo.toml` across an anticipated workspace split — consider centralizing
  "the version-bearing manifest" behind the new `WORKSPACE_MANIFEST` seam.
  **Location**: Migration Notes + Phase 1 §2

- 🔵 **Architecture**: Growing manual sync surface between `check`, discrete CI
  jobs, and branch protection — treat the Phase 5 presence assertion as
  non-optional.
  **Location**: Current State Analysis + Phases 1/3/4 CI jobs

- 🔵 **Architecture**: Bootstrap crate puts exercise-code in `cli` (the launcher
  composition root) — keep maximally trivial and comment that `cli` holds no
  domain logic.
  **Location**: Phase 1 §2

- 🔵 **Code Quality**: `deps:install:pup` body under-specified and would deviate
  from the single-`context.run` deps.py idiom — specify the concrete multi-step
  body with one checked `run` per step.
  **Location**: Phase 4 §1

- 🔵 **Code Quality**: Inline comments explaining standard clippy-priority/TOML
  mechanics sit in tension with comments-as-last-resort — keep only the
  genuinely-non-obvious "why" (ADR-0010 ban, nightly risk).
  **Location**: Phase 1 §1, Phase 3 §2, Phase 4 §2

- 🔵 **Code Quality**: Split version ownership (versionless root + version in
  `cli/Cargo.toml`) is a latent trap — record in CLAUDE.md/README that the root
  workspace manifest is intentionally versionless.
  **Location**: Implementation Approach / Migration Notes

- 🔵 **Correctness**: `cargo deny check` Cargo.lock precondition unstated —
  decide and document whether `Cargo.lock` is committed.
  **Location**: Phase 3 §3

- 🔵 **Correctness**: `default`/`check` final `depends` arrays described
  narratively, not enumerated — show the literal final edge sets so an incomplete
  edit can be diffed.
  **Location**: Phase 4 §3 + Phase 5 §1

- 🔵 **Correctness**: The `-p luminosity` literal must equal `[package] name`
  (not the bin name) — document the invariant so a 0007 rename is caught by task
  tests.
  **Location**: Phase 1 §2 / Migration Notes

- 🔵 **Test Coverage**: `fix`-variant command strings left unspecified despite
  the existing suite asserting them (TestFormatFix) — require each fix variant's
  string to be asserted.
  **Location**: Phase 1 §7 + Testing Strategy

- 🔵 **Test Coverage**: Magic nightly/crate-name constants duplicated across
  mise.toml and task bodies have no drift guard — source from a shared constant
  and assert against it.
  **Location**: Phase 4 §3 + Phase 2

- 🔵 **Test Coverage**: No assertion that coverage stays report-only (no
  accidental `--fail-under`) — add a negative-flag assertion mirroring the
  existing idiom.
  **Location**: Phase 2 §5 + Desired End State

- 🔵 **Test Coverage**: Single trivial Rust test gives near-zero coverage signal
  — fine for bootstrap; ensure the 0007 handoff owns meaningful coverage.
  **Location**: Phase 1 §2 + Testing Strategy

- 🔵 **Security**: New PR-triggered check jobs declare no least-privilege
  `permissions:` block — add `permissions: { contents: read }`.
  **Location**: Phases 1–4 CI jobs

- 🔵 **Security / Compatibility**: License allow-list omits licenses the
  ADR-0010 stack (reqwest/rustls/tokio/clap) will pull in (ISC, BSD-2-Clause,
  Zlib, Unicode-DFS-2016, MPL-2.0) — pre-seed known-safe permissive licenses and
  gate copyleft via per-crate exceptions.
  **Location**: Phase 3 §2 ([licenses])

- 🔵 **Security**: Running architecture enforcement on a volatile nightly widens
  the trusted-toolchain surface — accepted trade-off; verify nightly via rustup's
  signed channel and apply least-privilege to the lane.
  **Location**: Phase 4

- 🔵 **Compatibility**: Cross-OS coverage behaviour (ubuntu vs macOS) is
  acknowledged but not pinned down — state explicitly that coverage is ubuntu-only
  in CI / best-effort on macOS.
  **Location**: Phase 2 §4 + Testing Strategy

- 🔵 **Compatibility**: Strict license allow-list will break the build when 0007's
  deps land — note it in 0007's expected changes or pre-seed now (overlaps the
  security finding above).
  **Location**: Phase 3 §2

- 🔵 **Compatibility**: nursery lints are unstable across toolchains and
  `clippy.toml` `msrv` is a third hand-synced location — note the sync obligation;
  consider nursery as `warn` not denied to decouple from rust bumps.
  **Location**: Phase 1 §1 & §3

- 🔵 **Portability**: Local `mise run check` runs the heavy nightly cargo-pup
  build on macOS while CI runs it only on ubuntu — run the lane in the macOS
  matrix too, or document it as Linux-validated with a Mac skip/cache path.
  **Location**: Phase 4 CI nightly lane

- 🔵 **Portability**: `cargo install cargo_pup` from source is unpinned and
  environment-sensitive — pin the exact version `--locked` and cache the built
  binary keyed on (nightly + version + OS) (overlaps the security pinning
  finding).
  **Location**: Phase 4 CI nightly lane

- 🔵 **Documentation**: CLAUDE.md already lists `rustfmt.toml` as an 80-col
  location — Phase 5's "it now exists" framing is inaccurate; reword to "verify
  it's now real."
  **Location**: Phase 1 §3 / Phase 5 §1

- 🔵 **Documentation**: No Rust entry added to the "Running a single test"
  guidance — add `cargo nextest run -p luminosity <test-name>`.
  **Location**: Phase 5 §1

- 🔵 **Documentation**: The `lint:fix` / "shell has no autofixer" framing change
  (clippy `--fix` now in `lint:fix`) is updated only in README, not CLAUDE.md —
  mirror it and confirm the no-`<component>:fix` convention still holds.
  **Location**: Phase 5 §1

- 🔵 **Documentation**: Branch-protection step lists job names but is not a usable
  runbook — capture a durable procedure (Settings path, names-match-YAML, job
  must run once first).
  **Location**: Phase 5 §3

#### Suggestions

- 🔵 **Code Quality**: Magic literals (nightly toolchain, crate name) embedded in
  command strings — define named constants (e.g. `tasks/shared/rust.py`) and
  compose commands from them.
  **Location**: Phase 4 §3 / Phase 2 §2

- 🔵 **Code Quality**: clippy `--fix --allow-dirty --allow-staged` weakens the
  "fix is mechanical/safe-only" contract the rest of the tree upholds — document
  the machine-applicable-only and dirty-tree behaviour.
  **Location**: Phase 1 §4

- 🔵 **Documentation**: `clippy.toml` deserves a one-line "lint levels live in
  [workspace.lints] in Cargo.toml; this file is config only" comment — the plan's
  own Key Discoveries had to correct this exact misconception.
  **Location**: Phase 1 §3 / Phase 4 §2

### Strengths

- ✅ The wiring model respects the existing architecture precisely: per-crate
  `cli:check` mirrors `build-system:check`/`scripts:check`, and workspace-scope
  `deny:check`/`pup:check` are modeled on the existing standalone
  `lint:workflows:check` — a justified, explicit divergence for genuinely
  workspace-scoped concerns.
- ✅ Phase boundaries are independently mergeable and each leaves `mise run check`
  green, with the bootstrap crate explicitly throwaway and clear seams for
  0007/0009/0012 (a new crate adds "one `kernel:check` roll-up + its family edges,
  nothing more").
- ✅ The version-coherence preservation reasoning is correct and verified:
  `tasks/version.py` indexes `data["package"]["version"]`, so keeping `[package]`
  in `cli/Cargo.toml` and a `[package]`-free root manifest keeps the release
  machinery working unchanged.
- ✅ The proposed invoke task bodies faithfully reproduce the established idiom
  (`warn=True`, `pty=False`, manual exit-code check, `Exit` naming the exact
  `:fix` task), so the new Rust tasks read as native to the codebase.
- ✅ TDD is treated as a first-class constraint: the bootstrap crate's Rust test
  is explicitly written test-first (red→green) and avoids unwrap/panic to stay
  restriction-clean; every task module ships a command-string test in the same
  phase.
- ✅ The clippy lint-level placement (`[workspace.lints]` with `priority = -1` on
  groups so per-lint overrides win) is correct, and the plan correctly corrects
  the work item's `clippy.toml`-as-levels misconception.
- ✅ The cargo-deny design is sound and well-targeted: the native-tls/openssl ban
  + `wildcards = "deny"`, the locked `[sources]` (deny unknown registry/git), and
  a strict fail-closed license allow-list close real supply-chain vectors from day
  one.
- ✅ The cargo-deny 0.19.8 schema described (no top-level version, `[graph]`
  targets matching the four release triples exactly) is correct and modern, and
  edition 2021 / `[workspace.lints]` are fully supported by rust 1.90.0.
- ✅ Keeping the product build and every non-architecture check on stable while
  quarantining only cargo-pup to the nightly correctly minimizes the nightly's
  blast radius.
- ✅ The plan is documentation-aware: Phase 5 owns docs, config files carry
  "why" comments where the comment policy permits, and the branch-protection step
  is consistently flagged as manual.

### Recommended Changes

1. **Resolve the cargo-pup nightly mechanism before approval — treat it as a
   blocking spike** (addresses: the Critical finding plus the architecture/
   compatibility/portability nightly findings). Concretely settle: (a) whether
   mise can pin a parallel nightly toolchain at all — if not, drop the
   `"rust-nightly"` `[tools]` line and own the nightly in `deps:install:pup` via
   `rustup toolchain install` so rustup resolves `+nightly`; (b) verify
   `nightly-2026-01-22` against DataDog/cargo-pup's current `rust-toolchain`;
   (c) make the advisory↔blocking demotion a one-line, tested toggle; (d) confirm
   the lane resolves on both a clean macOS and a clean ubuntu runner.

2. **Pin the cargo-pup install and all third-party actions** (addresses: the two
   security pinning findings + the portability install findings). Use
   `cargo install cargo_pup@<exact.version> --locked`, record the version beside
   the nightly pin, cache the built binary keyed on (nightly + version + OS), and
   pin every GitHub Action to a full commit SHA with a version comment.

3. **Restore the read-only `check` invariant** (addresses: the two correctness
   `check` findings). Put plain `test:unit:cli` (not coverage) into `cli:check`
   and wire `coverage:check` only into `default`; make `pup:check` assume a
   provisioned toolchain (provisioning is a mise/CI concern, not a `depends` edge
   on a mutating install). Enumerate the final literal `check`/`default` `depends`
   arrays.

4. **Make the security/architecture config self-verifying** (addresses: the
   test-coverage manual-only findings + the advisories-defaults security finding).
   Promote the CI-job presence/`needs:` assertion from optional to required; add
   fixture-based tests that a native-tls dependency fails `cargo deny check bans`
   and that coverage carries no `--fail-under`; and set explicit
   advisories/licenses policy (`yanked = "deny"`, a conscious `unmaintained`
   level, pre-seeded permissive licenses for the ADR-0010 stack).

5. **Exercise the musl-static invariant pre-merge** (addresses: the three
   portability musl findings). Add a `cargo build --target
   x86_64-unknown-linux-musl` step to the PR-time Rust checks via the existing
   `deps:install:rust-targets`, align `deny.toml`'s feature evaluation with the
   `default-features = false` release build (or justify `all-features = true` as a
   deliberate stricter superset), and document the ban list as
   necessary-but-not-sufficient for static linking.

6. **Distribute documentation into the phases that change each surface**
   (addresses: the two documentation findings + minors). Update CLAUDE.md/README
   in Phase 1 (component table, `lint:cli:fix`), Phase 3 (deny), Phase 4
   (pup/nightly); fix the `check`/`default` descriptions in both CLAUDE.md and
   mise.toml; add Rust single-test guidance; reword the `rustfmt.toml` "now
   exists" framing; and capture a durable branch-protection runbook.

7. **Align tests and constants with existing conventions** (addresses: the
   code-quality test-layout finding + magic-constant findings). Add cli cases as
   `TestFormatCli`/`TestLintCli` classes in the existing family test files rather
   than per-leaf files, and source the nightly string and crate name from shared
   constants the command-string tests assert against.

## Per-Lens Results

### Architecture

**Summary**: The plan is architecturally sound and unusually disciplined: it
faithfully extends the established two-axis task tree, models workspace-scope
checks on the existing standalone `lint:workflows:check` precedent, and explicitly
defers cross-crate concerns to 0007/0009/0012 with clear seams. The dominant
architectural risks are concentrated in the cargo-pup nightly lane (an
under-specified, single-point-of-failure toolchain that is blocking yet enforces
nothing in the bootstrap) and in a structural divergence in `cli:check` semantics.

**Strengths**:
- Wiring model respects the existing pattern precisely (per-crate roll-up mirrors
  build-system/scripts; workspace-scope checks modeled on lint:workflows:check).
- Phase boundaries independently mergeable; strong evolutionary fitness with
  documented seams for future crates.
- Two-layer task discipline (ADR-0006) honored throughout.
- cargo-deny bans vs cargo-pup roles kept distinct and correctly scoped.
- Version-coherence coupling consciously preserved.

**Findings**:
- 🟡 (major, high) Blocking nightly cargo-pup lane is a single point of failure
  with under-specified provisioning. The most volatile/least-mature component
  gates the whole repo; advisory fallback is a prose note, not a designed
  mechanism. Make the fallback a first-class switchable knob; resolve the mise
  nightly mechanism before committing the phase.
- 🟡 (major, medium) Blocking gate enforces nothing yet: `pup.ron` ships empty,
  yet the lane is blocking, inverting cost/benefit until 0007. Consider running
  advisory in the bootstrap window or explicitly justify the time-boxed tradeoff.
- 🔵 (minor, high) `cli:check` diverges from `<component>:check` fold semantics
  (folds coverage, omits plain test); make explicit in tasks/README.md.
- 🔵 (minor, high) Version-coherence machinery single-point-coupled to
  cli/Cargo.toml across the anticipated split; centralize the
  "version-bearing manifest" notion behind WORKSPACE_MANIFEST.
- 🔵 (minor, medium) Growing manual sync surface between `check`, CI jobs, and
  branch protection; treat the Phase 5 presence assertion as non-optional.
- 🔵 (minor, low) Bootstrap crate puts exercise-code in `cli` (the launcher
  composition root); keep trivial and comment that cli holds no domain logic.

### Code Quality

**Summary**: Unusually well-aligned with the codebase's quality idioms — task
bodies reproduce the warn=True + manual exit-code + Exit-naming-fix-task pattern,
fully-annotated fixtures are called out, and the bootstrap crate's TDD red-green
loop is explicit. Main concerns: a test-file organization that diverges from the
one-file-per-family-module convention, inline comments contradicting
comments-as-last-resort, and an under-specified `deps:install:pup` body.

**Strengths**:
- Proposed task bodies precisely mirror the established idiom.
- TDD treated as first-class (failing Rust test before impl; command-string tests
  same phase).
- Fix-task error messages name the exact remediation command.
- DDD-aligned naming (workspace-scope as top-level roll-ups; component-leading
  per-crate checks).
- Throwaway scaffolding explicitly flagged with a 0007 handoff.

**Findings**:
- 🔴 (major, high) Per-leaf test files diverge from the one-file-per-family-module
  convention (test_format.py covers tasks/format/scripts.py with TestFormatCheck/
  TestFormatFix classes). Add TestFormatCli/TestLintCli classes in existing files
  or justify the new layout.
- 🔵 (minor, high) `deps:install:pup` body under-specified; deviates from the
  single-`context.run` deps.py idiom. Specify the concrete steps and centralize
  the nightly version constant.
- 🔵 (minor, medium) Inline comments explaining standard clippy-priority/TOML
  mechanics sit in tension with comments-as-last-resort; keep only genuine "why".
- 🔵 (minor, medium) Split version ownership (versionless root + version in cli)
  is a latent trap; record it in CLAUDE.md/README.
- 🔵 (suggestion, medium) Magic literals (nightly, crate name) embedded in command
  strings; define named constants and compose from them.
- 🔵 (suggestion, low) clippy `--fix --allow-dirty --allow-staged` weakens the
  "fix is mechanical/safe-only" contract; document the behaviour.

### Test Coverage

**Summary**: Honours the TDD mandate and command-string assertion convention well
— every task module is paired with a test, and the bootstrap crate's test is
explicitly test-first. But test specs are uneven: fix-variant strings unspecified,
the security-critical deny/pup config verified only manually, the fragile nightly
install-step test vague, and the CI-job presence assertion (the only automated
guard for "CI must fail / PR non-mergeable") marked optional.

**Strengths**:
- Every new task module ships a paired test asserting the command string and
  Exit-on-failure.
- Bootstrap crate's Rust test explicitly test-first; written without unwrap/panic.
- Fully-annotated fixtures consistent with the no-relaxed-profile rule.
- Testing Strategy correctly distinguishes unit (command strings) from the
  integration gate.

**Findings**:
- 🟡 (major, high) CI-job presence assertion is the only automated guard for a
  core acceptance criterion, yet marked optional. Promote to required, mirroring
  the `_KNOWN_BAD_SHAPES` pattern.
- 🟡 (major, high) deny.toml ban-list and pup.ron correctness verified only
  manually. Add fixture-based tests reproducing a ban violation.
- 🟡 (major, medium) The most fragile component (nightly install-step) has the
  vaguest test spec. Enumerate exact commands, components, and toolchain string.
- 🔵 (minor, high) fix-variant command strings left unspecified despite the
  existing TestFormatFix precedent.
- 🔵 (minor, medium) Magic constants duplicated across mise.toml and task bodies
  have no drift guard.
- 🔵 (minor, medium) No assertion that coverage stays report-only (no
  `--fail-under`); add a negative assertion.
- 🔵 (minor, low) Single trivial Rust test gives near-zero coverage signal; ensure
  the 0007 handoff owns meaningful coverage.

### Correctness

**Summary**: Task-tree wiring is largely sound and the version-coherence
preservation is correct (tasks/version.py indexes data["package"]["version"]).
Real gaps: the cargo-pup nightly mechanism (`+nightly` override depends on
rustup-managed toolchains mise may not provide) and aggregation-edge
inconsistencies where `mise run`/`mise run check` would not be green/read-only as
claimed.

**Strengths**:
- Version-coherence preservation verified against tasks/version.py.
- `-p luminosity` scoping correct (package name; bin-name collision is legal).
- clippy lint-level placement (priority = -1 on groups) correct.
- Command strings for rustfmt/clippy/cargo-deny syntactically valid and match the
  warn=True idiom.

**Findings**:
- 🔴 (critical, medium) `cargo +nightly-2026-01-22 pup` override syntax is a rustup
  feature that may not resolve under mise-provisioned rust; the `rust-nightly`
  `[tools]` line is hand-waved. Treat as a blocking spike: have deps:install:pup
  run `rustup toolchain install` (or `rustup run ... cargo pup`) and verify
  resolution.
- 🟡 (major, high) Folding coverage (instrumented llvm-cov) into the read-only
  `check` contradicts its read-only/fast invariant; put plain test:unit:cli into
  cli:check and wire coverage:check only into default.
- 🟡 (major, high) `pup:check` depends on the mutating `deps:install:pup` inside
  the read-only `check`; make install a provisioning concern, not a depends edge.
- 🟡 (major, medium) "coverage subsumes the test run" conflates two run scopes;
  state test:unit:cli is the canonical Rust test edge and not removable.
- 🔵 (minor, medium) `cargo deny check` Cargo.lock precondition unstated.
- 🔵 (minor, high) `default`/`check` final depends arrays described narratively,
  not enumerated; show the literal final edge sets.
- 🔵 (minor, medium) `-p luminosity` must equal `[package] name`; document the
  invariant so a 0007 rename is caught by tests.

### Security

**Summary**: The plan is itself a supply-chain guard rail and the core cargo-deny
design is sound and well-targeted. But it undermines its own posture: cargo-pup is
installed via unpinned `cargo install` (no version, no `--locked`), and every
GitHub Action — including the new Swatinem/rust-cache@v2 — is pinned by mutable
tag, not SHA. The `[advisories]`/`[licenses]` sections lean on implicit,
version-sensitive defaults.

**Strengths**:
- `[bans]` deny-list for native-tls/openssl(-sys) + wildcards=deny is a strong,
  verified control.
- `[sources]` locks origin (deny unknown registry/git + explicit crates.io allow).
- License enforcement uses a fail-closed allow-list.
- Product/other checks on stable; only cargo-pup on the pinned nightly.
- Tool versions pinned exactly per the pin-so-local-mirrors-CI discipline.

**Findings**:
- 🟡 (major, high) cargo-pup installed via unpinned `cargo install cargo_pup`
  (no version, no `--locked`) — an unpinned mutable entry point running as a
  rustc-driver everywhere. Use `cargo install cargo_pup@<exact> --locked`.
- 🟡 (major, high) Newly-introduced and existing third-party actions pinned by
  mutable tag, not commit SHA — a live CI code-execution vector. Pin to 40-char
  SHAs with version comments.
- 🟡 (major, medium) `[advisories]` relies entirely on implicit version-sensitive
  defaults; make vuln/unmaintained/yanked policy explicit and verify an advisory
  actually fails CI.
- 🔵 (minor, medium) New PR-triggered check jobs declare no least-privilege
  `permissions:` block; add `contents: read`.
- 🔵 (minor, medium) License allow-list omits licenses the ADR-0010 stack will
  pull in; pre-seed known-safe permissive licenses and gate copyleft via per-crate
  exceptions.
- 🔵 (minor, low) Running architecture enforcement on a volatile nightly widens
  the trusted-toolchain surface; accepted tradeoff — verify via rustup's signed
  channel and apply least-privilege.

### Compatibility

**Summary**: Stable-toolchain choices are mutually compatible and well-targeted
(nextest/llvm-cov/deny on 1.90.0/edition 2021; workspace.lints supported; deny
0.19.x schema correct). The genuine risk concentrates in the cargo-pup nightly
lane (pre-1.0 rustc-driver, unconfirmed mise second-toolchain pin) and cross-OS
behaviour between ubuntu and macOS runners.

**Strengths**:
- Edition 2021 + [workspace.lints] fully supported by rust 1.90.0.
- cargo-deny 0.19.8 schema described correctly (no top-level version; [graph]).
- Nightly quarantined to cargo-pup; product on stable.
- llvm-tools-preview folded into the rust components pin.
- The most volatile fact (nightly compat) is explicitly flagged with a fallback.

**Findings**:
- 🔴 (major, high) mise second-toolchain (nightly) pinning mechanism unconfirmed
  and likely won't resolve as written (no standard `rust-nightly` short-name).
  Verify mise support or commit to the deps:install:pup rustup path and drop the
  misleading [tools] line.
- 🟡 (major, medium) cargo-pup rustc-driver tightly coupled to the exact
  nightly/rustc-dev components; drift breaks the whole lane. Verify the nightly;
  cache the built binary.
- 🔵 (minor, medium) Cross-OS coverage (ubuntu vs macOS) acknowledged but not
  pinned down; state the contract explicitly.
- 🔵 (minor, medium) Strict license allow-list will break the build when 0007's
  deps land; note in 0007 or pre-seed.
- 🔵 (minor, low) nursery lints unstable across toolchains and clippy.toml msrv is
  a third hand-synced location; note the sync obligation; consider nursery warn.

### Portability

**Summary**: Correctly mirrors the four release triples in cargo-deny's [graph]
targets and lands a live native-tls/OpenSSL ban from day one. But the ban is
incomplete as a musl-static guarantee (covers named crates, not other C-linking
*-sys vectors; `all-features = true` diverges from the real
`default-features = false` build), and — most significantly — nothing ever
compiles the bootstrap crate for musl, so the static build is never exercised
pre-merge. The cargo-pup lane introduces a rustup-vs-mise coupling and an
OS-asymmetric local-vs-CI experience.

**Strengths**:
- [graph] targets exactly match tasks/shared/targets.py's four triples.
- native-tls/OpenSSL ban live from day one (not deferred).
- Product/release build on stable; nightly quarantined.
- Tools pinned in mise.toml for identical provisioning.

**Findings**:
- 🔴 (major, high) Nothing ever compiles the bootstrap crate for the musl targets
  the plan claims to protect; add a musl `cargo build --target` to PR-time checks.
- 🟡 (major, medium) Crate-name ban doesn't fully guarantee the musl-static
  invariant (other *-sys vectors uncovered); document as
  necessary-but-not-sufficient.
- 🟡 (major, medium) `all-features = true` evaluates a graph diverging from the
  `default-features = false` release build; align or justify.
- 🟡 (major, medium) cargo-pup lane couples the build to rustup, conflicting with
  mise-managed rust across environments; settle the dual-toolchain mechanism.
- 🔵 (minor, high) Local `mise run check` runs the heavy nightly pup build on
  macOS while CI runs it only on ubuntu; run on macOS matrix too or document/skip.
- 🔵 (minor, medium) `cargo install cargo_pup` from source is unpinned and
  environment-sensitive; pin `--locked` and cache keyed on (nightly+version+OS).

### Documentation

**Summary**: Documentation-aware in spirit — Phase 5 owns docs, config files
carry "why" comments where most needed, and branch protection is flagged manual.
But Phase 5's described edits are under-scoped (the now-inaccurate check/default
descriptions, single-test guidance, the 80-col list), and the biggest structural
risk is deferring all docs to Phase 5 while Phases 1–4 are independently
mergeable.

**Strengths**:
- Phase 5 explicitly owns docs and names both surfaces + specific facts.
- New config files carry "why" comments exactly where the exception applies.
- Branch-protection step consistently flagged manual across the plan.
- pup.ron specified to carry a comment recording 0007 adds the rules.

**Findings**:
- 🔴 (major, high) Phase 5 misses CLAUDE.md's now-inaccurate descriptions of what
  `check` (line 24) and `default` (line 20) run, and the mise.toml descriptions;
  add them to the edit list.
- 🟡 (major, high) All docs deferred to Phase 5 while Phases 1–4 are independently
  mergeable — guaranteed interim drift. Move edits into the introducing phase.
- 🔵 (minor, high) CLAUDE.md already lists rustfmt.toml as an 80-col location;
  Phase 5's "it now exists" framing is inaccurate — reword to "verify it's now
  real."
- 🔵 (minor, medium) No Rust entry in "Running a single test" guidance; add the
  nextest invocation.
- 🔵 (minor, medium) The `lint:fix`/"shell has no autofixer" change (clippy --fix)
  is updated only in README, not CLAUDE.md; mirror and confirm no-`<component>:fix`.
- 🔵 (minor, medium) Branch-protection step lists names but is not a usable
  runbook; capture a durable procedure.
- 🔵 (suggestion, low) clippy.toml deserves a one-line "levels live in
  [workspace.lints]; config only" comment — the plan's own Key Discoveries had to
  correct this misconception.

---
*Review generated by /accelerator:review-plan*

## Re-Review (Pass 2) — 2026-06-27T15:13:09+00:00

**Verdict:** REVISE

The revision is a large, high-quality step. The **critical is resolved** (the
cargo-pup nightly mechanism is now confirmed and concretely specified), and the
**large majority of the original 20 majors are closed** — coverage out of
read-only `check`, the mutating-install `depends` edge removed, family-style
tests, the required CI-presence assertion, the native-tls ban regression test,
explicit advisories policy, pre-seeded licenses, release-aligned deny graph, the
musl smoke build, cargo-pup pinned `--locked`, docs distributed into phases, and
the stale `check`/`default` descriptions targeted. The verdict stays REVISE only
because the deeper pass surfaced **one new critical** (the mise.toml wiring the
plan claims its tests verify is, in the existing test architecture, asserted by
no test) plus a tail of mostly second-order hardening majors. This is a
"one more small pass" REVISE, not a structural one.

### Previously Identified Issues

- 🔴 **Correctness/Compatibility/Portability**: cargo-pup nightly mechanism may
  not work — **Resolved** (web research confirmed mise→rustup + `+toolchain`
  override; `0.1.8` / `nightly-2026-01-22` pinned; rustup-based install). Residual
  PATH-ordering caveat downgraded to major (see new issues).
- 🟡 **Correctness**: coverage folded into read-only `check` — **Resolved**
  (coverage now `default`-only; `cli:check` runs plain `test:unit:cli`).
- 🟡 **Correctness**: `pup:check` depends on mutating `deps:install:pup` —
  **Resolved** (no `depends`; provisioning decoupled). New angle raised below.
- 🟡 **Correctness**: "coverage subsumes the test run" conflation — **Resolved**
  (now explicit distinct, non-substitutable edges).
- 🟡 **Code Quality**: per-leaf test files — **Resolved** (family-style
  `TestFormatCli`/`TestLintCli`; now cited as a strength).
- 🟡 **Test Coverage**: CI-presence assertion optional — **Resolved** (promoted to
  required).
- 🟡 **Test Coverage**: deny/pup config manual-only — **Partially resolved** (deny
  ban-violation regression test added; cargo-pup still has no behavioural test —
  see new issues).
- 🟡 **Test Coverage**: vague nightly install-step test — **Resolved** (exact
  component/version assertions specified).
- 🟡 **Security**: cargo-pup unpinned install — **Resolved** (`0.1.8 --locked`).
- 🟡 **Security**: actions tag-pinned — **Partially resolved** (new `rust-cache`
  SHA-pinned; pre-existing release-job actions still deferred — see new issues).
- 🟡 **Security**: `[advisories]` implicit defaults — **Resolved** (explicit
  `unmaintained`/`yanked`; verify-at-impl noted).
- 🟡 **Compatibility**: mise second-toolchain unconfirmed — **Resolved**
  (rustup-managed; invalid `[tools]` line removed).
- 🟡 **Compatibility**: cargo-pup/nightly coupling — **Resolved/mitigated**
  (pinned pair + built-binary cache; minor driver-propagation residual).
- 🟡 **Portability**: nothing compiles musl pre-merge — **Resolved**
  (`build:cli:musl:check`). Residual: only 1 of 4 triples — see new issues.
- 🟡 **Portability**: `all-features=true` mismatch — **Resolved** (release-aligned
  graph).
- 🟡 **Portability**: crate-name ban incomplete — **Addressed** (documented
  necessary-but-not-sufficient; broader `*-sys` ban tracked as follow-up).
- 🟡 **Portability**: rustup-vs-mise coupling — **Mitigated** (mechanism
  confirmed); residual macOS-local/PATH major below.
- 🟡 **Documentation**: Phase 5 misses `check`/`default` descriptions — **Resolved**
  (explicitly targeted in CLAUDE.md + mise.toml).
- 🟡 **Documentation**: docs deferred to Phase 5 — **Resolved** (distributed into
  Phases 1/3/4).
- 🔵 (minors) clippy.toml level comment, Cargo.lock decision, versionless-root
  note, single-test guidance, `-p`=package-name invariant, coverage no-`--fail-under`
  — **Resolved** (all folded in).

### New Issues Introduced (or surfaced by the deeper pass)

- 🔴 **Test Coverage** (new critical): The plan repeatedly states its unit tests
  verify the mise wiring (`pup:check` has no `depends`; `cli:check` folds
  `test:unit:cli`; coverage in `default` not `check`), but the existing test
  architecture mocks invoke's `Context` and asserts command strings only — **no
  test reads `mise.toml`**, so every aggregate/`depends` edge is unbacked. Add a
  `tomllib`-based `test_mise_wiring.py` asserting the enumerated `check`/`default`/
  `cli:check` arrays. (Cheap, high-value; this is the main reason the verdict
  stays REVISE.)
- 🟡 **Architecture / Code Quality / Portability**: `PUP_MODE` defaults to `"deny"`
  while `pup.ron` is empty (SPOF with no enforcement benefit yet); it is a
  committed module-level global (no env override) and its `"warn"` branch silently
  swallows the result. Suggested: default `"warn"` until 0007 adds rules; source
  from an env var; log in the advisory branch.
- 🟡 **Security**: pre-existing actions in the high-privilege release jobs remain
  tag-pinned, and there is no workflow-level `permissions: { contents: read }`
  default (existing PR jobs inherit the repo default). Both are cheap to close in
  this supply-chain story.
- 🟡 **Test Coverage**: the blocking cargo-pup lane has no behavioural test (its
  core AC — a violation fails the build — is manual-only until 0007); and the
  tool-presence skip mechanism for the deny/pup integration tests is unspecified
  (risk of silent skip-to-green).
- 🟡 **Portability / Architecture**: the musl smoke build covers only
  `x86_64-unknown-linux-musl` (1 of 4 shipped triples), its leaf `depends` on
  `deps:install:rust-targets` (pulls in darwin targets) and assumes a musl
  cross-linker (`musl-tools`) the plan does not state as a prereq.
- 🟡 **Correctness / Compatibility**: residual cargo-pup PATH/shim caveat — add an
  explicit `cargo +{PUP_NIGHTLY} --version` pre-flight; and `cargo-deny 0.19.8`
  `[advisories]` schema keys (`unmaintained = "all"`) should be validated as a
  Phase 3 automated criterion (a wrong key errors the whole check).
- 🔵 (minors) `build:cli:musl:check` mise-name vs `build.cli.check` invoke-path
  segment mismatch; bootstrap `cli/Cargo.toml` `0.0.0` vs `plugin.json`
  `0.1.0-pre.0` transient incoherence; `Cargo.lock` should be generated with the
  pinned 1.90.0; CLAUDE.md component prose (lines 26–27), `msrv`-sync convention,
  cargo-pup-nightly tool inventory, and the runbook home (no CONTRIBUTING exists)
  not explicitly enumerated as edits.

### Assessment

The plan moved from "blocked on an unresolved, possibly-unworkable nightly
mechanism" to "sound, concrete, and implementable." None of the new findings are
structural — the architecture, wiring, and mechanism are now right. The new
critical (untested wiring) and the cluster of cheap majors (PUP_MODE default +
env override, workflow `permissions` default + SHA-pin release actions, a
cargo-pup behavioural test, musl linker prereq / second triple) are a focused,
low-risk final pass. Recommend addressing the new critical and the security/
PUP_MODE majors, then this is ready to implement.

### Post-Pass-2 edits (folded in 2026-06-27T15:13Z)

The following pass-2 findings were addressed in the plan immediately after this
re-review:

- 🔴→✅ **New critical (untested mise wiring)**: added
  `tests/unit/tasks/test_mise_wiring.py` (`tomllib`-parsed), introduced in Phase 1
  and extended each phase, asserting the enumerated `check`/`default`/`cli:check`
  arrays, that `pup:check` has no `depends`, and that `coverage:check` is absent
  from `check`. Added to Testing Strategy and the Phase 1/5 success criteria.
- 🟡→✅ **Security (SHA-pinning + token default)**: SHA-pinning is now in scope —
  Phase 1 §7 SHA-pins the pre-existing `actions/checkout`, `jdx/mise-action`, and
  `actions/attest-build-provenance` (release jobs) plus the new `rust-cache`, and
  adds a workflow-level `permissions: { contents: read }` default (release jobs
  keep their explicit elevated block).
- 🟡→✅ **PUP_MODE**: now sourced from `LUMINOSITY_PUP_MODE` (env-overridable
  without a source edit), and the `"warn"` branch logs the advisory findings
  rather than silently returning. Default kept `"deny"` to honour AC6's blocking
  requirement, with the reasoning documented (empty `pup.ron` ⇒ `"deny"` passes
  trivially; the only blocking exposure is a toolchain break, recoverable via the
  env override / one-line flip).

**All remaining pass-2 residuals subsequently folded in** (2026-06-27T15:40Z):

- ✅ cargo-pup **behavioural** regression test (`test_pup_rules.py`) — a throwaway
  crate violating a trivial `restrict_imports` rule asserts `pup:check` reddens
  under `PUP_MODE="deny"`, making AC6 self-verifying in 0006; skip-gated but must
  run in CI.
- ✅ musl: build **both** musl triples; documented the cross-linker prerequisite
  (self-contained linking suffices for the pure-Rust bootstrap; `musl-tools`
  needed once C-FFI lands).
- ✅ cargo-pup **PATH pre-flight** (`cargo +{PUP_NIGHTLY} --version` in
  `deps:install:pup`, now a Phase 4 criterion) + **split error messages**
  (provisioning-missing vs rule-violation via a probe).
- ✅ cargo-deny **advisories-schema validation** as a Phase 3 automated criterion
  (`cargo deny --version` 0.19.8 + clean `deny:check` validates the keys).
- ✅ doc/naming: `build:cli:musl:check` → **`build:cli:check`** (segment-aligned);
  bootstrap `cli/Cargo.toml` seeded to the plugin version (not `0.0.0`);
  `Cargo.lock` generated with the pinned 1.90.0; CLAUDE.md component prose,
  `msrv`-sync convention, the cargo-pup-not-in-`[tools]` inventory exception, and
  the local-vs-CI carve-outs enumerated; runbook homed in a new `CONTRIBUTING.md`.
- ✅ lower-priority notes: advisory-DB freshness, `multiple-versions` tightening
  follow-up, host-triple deny-coverage gap, `default` depends-ordering, and the
  clippy `--fix` log-on-failure note all captured.

**Net state:** the original critical and all 20 original majors are resolved or
mitigated, the pass-2 critical is closed, and the pass-2 majors plus their minor
tail are folded in. The plan is assessed ready to implement.

## Approval — 2026-06-27T15:45:00+00:00

**Verdict: APPROVE.** The review's blocking findings (the original critical + 20
majors, and the pass-2 critical + majors) have all been resolved or mitigated in
the plan, with the cargo-pup nightly mechanism settled by web research and the
mise/CI wiring now backed by automated tests. The remaining items are
deliberate, documented tradeoffs and follow-ups (cross-crate ban-lists for
0009/0012, the darwin static-link gap, `multiple-versions` tightening) rather
than open defects. Two facts are gated by automated criteria to fail loudly if
wrong at implementation time (cargo-pup's `pup --version` probe and the
cargo-deny 0.19.8 `[advisories]` schema), not left as silent assumptions.

The plan is approved for implementation; plan status moved to `ready`.

## Post-Approval Amendment — 2026-06-27T17:00:00+00:00

After approval, the plan author revised the mise/CI task wiring in several ways:
`check` is now test-free (tests moved to the `test` roll-up via per-suite
aggregates); coverage is folded **into** the test run (`test:unit:cli` runs
`cargo llvm-cov nextest` by default, on every test OS, with a
`LUMINOSITY_COVERAGE=off` toggle) rather than a separate `coverage:check` task; and
the release-build guard was renamed `build:cli` (verb-less), made OS-aware, run as a
`[ubuntu-latest, macos-latest]` matrix in CI (covering all four shipped triples
pre-merge), and folded into the bare `mise run` default.

Most of these are refinements consistent with this review's spirit, but **one
deliberately reverses a finding this review previously recorded as resolved**, so
it is documented here for traceability:

- **`pup:check` now `depends` on `deps:install:pup`.** Pass 1 raised this as a
  Major correctness finding ("`pup:check` depends on the mutating `deps:install:pup`
  inside the read-only `check`"), Recommended Change #3 had the plan *remove* the
  edge ("make `pup:check` assume a provisioned toolchain — provisioning is a
  mise/CI concern, not a `depends` edge on a mutating install"), and Pass 2 recorded
  it **Resolved (no `depends`)**. The plan now re-adds the edge.

  **Rationale for the reversal:** it restores consistency with the repo's own
  convention — every Python check `depends` on `deps:install:python` — and the
  idempotency concern that drove the original finding does not actually distinguish
  `deps:install:pup` from that precedent: `rustup toolchain install` and
  `cargo install … --version … --locked` both no-op when the pinned versions are
  already present, exactly as `uv sync --frozen` does ahead of every Python check.
  The benefit is a self-provisioning fresh checkout (`mise run check` /
  `mise run pup:check` install the nightly + cargo-pup on first run, no-op
  thereafter), with the in-body provisioning probe removed as redundant. The
  decision is now guarded by `test_mise_wiring.py`, which asserts the `depends`
  edge so a future *removal* — which would make a clean checkout's `pup:check` fail
  for a missing toolchain — is caught.

This amendment supersedes the relevant part of Pass 1's finding and Recommended
Change #3; the rest of the approval stands.
