---
type: plan-validation
id: "2026-06-27-0006-establish-rust-toolchain-guard-rails-validation"
title: "Validation Report: Establish Rust Toolchain Guard Rails in mise + CI"
date: "2026-06-28T13:41:49+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: pass
target: "plan:2026-06-27-0006-establish-rust-toolchain-guard-rails"
tags: [rust, tooling, ci, guard-rails, mise, architecture-enforcement]
last_updated: "2026-06-28T13:41:49+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: Establish Rust Toolchain Guard Rails in mise + CI

### Implementation Status

- ✓ **Phase 1: Bootstrap workspace + rustfmt + clippy** — Fully implemented
- ✓ **Phase 2: cargo-nextest + cargo-llvm-cov** — Fully implemented
- ✓ **Phase 3: cargo-deny (supply-chain + architectural ban-lists)** — Fully implemented
- ✓ **Phase 4: cargo-pup nightly lane (blocking)** — Fully implemented
- ✓ **Phase 5: Tie-off — aggregation, docs, branch protection** — Fully implemented

All five phases are committed (`8730530`…`7ede707`) and every automated
success criterion across all phases verifies green on the host (macOS).

### Automated Verification Results

| Check | Command | Result |
|-------|---------|--------|
| Read-only CI mirror | `mise run check` | ✓ exit 0 (incl. `cli:check`, `deny:check`, `pup:check`) |
| Task unit suite | `uv run pytest tests/unit/tasks` | ✓ 133 passed |
| Deny ban regression | `mise run test:integration:deny` | ✓ 1 passed (native-tls correctly rejected) |
| Pup rule regression | `mise run test:integration:pup` | ✓ 2 passed (rule violation fails; real `pup.ron` loads) |
| Host-native release build | `mise run build:cli` | ✓ exit 0 — both darwin triples built, arch verified (`arm64`, `x86_64`) |
| Architecture lane | `pup:check` (within `check`) | ✓ self-provisioned the nightly + cargo-pup 0.1.8, clean exit |

`mise run` (the full bare default) was not run end-to-end as a single
invocation, but every component it aggregates was exercised individually and
passes: `check` (which is a superset of `default`'s static checks), the full
`test` roll-up (via the unit suite + both integration regressions), and
`build:cli`. The full default's only un-combined element is the simultaneous
`format:fix` mutation, which is unchanged from the established Python/shell
pattern.

### Code Review Findings

#### Matches Plan

- **Root `Cargo.toml`** — workspace lint levels exactly as enumerated
  (`[workspace.lints.rust] warnings = "deny"`, pedantic/nursery at
  `priority = -1`, the cherry-picked restriction opt-ins, the two `allow`
  exceptions). Versionless, `[package]`-free workspace manifest as specified.
- **Bootstrap `cli` crate** — `describe_release` is a branched (`if/else`) pure
  function with both arms covered by tests, satisfying the "coverage measures
  more than one line" insurance the plan called for. No `unwrap`/`panic`.
  Version `0.1.0-pre.0` carried in `cli/Cargo.toml` per the version-coherence
  contract.
- **`rustfmt.toml` / `clippy.toml`** — `max_width = 80`, `edition = "2021"`,
  `msrv = "1.90.0"`, with the "levels live in Cargo.toml, this is config only"
  comment the plan specifically requested (the work item's own mistake).
- **`deny.toml`** — `[graph] targets` include the four shipped triples plus the
  two dev triples; native-tls/openssl/openssl-sys bans; permissive license
  allow-list; scaffolded-inert `skip`/`skip-tree`. Matches the plan verbatim.
- **`pup.ron`** — intentionally empty (`lints: []`) with the 0007 pointer.
  `.pup/` gitignored.
- **`tasks/shared/rust.py`** — `coverage_enabled()` / `pup_mode()` as
  **call-time functions** (not import-frozen constants), normalising input and
  fail-closed on unrecognised pup mode with a visible `WARNING:`. `CLI_CRATE`,
  `PUP_NIGHTLY`, `PUP_VERSION` are the single source of truth the tests assert
  against.
- **`tasks/shared/targets.py`** — `host_targets()` partitions the single
  `TARGETS` tuple by OS substring and `Exit`s on an unsupported host (no
  silent-empty false-green).
- **`tasks/build.py`** — builds with `--bin {CLI_CRATE} --target <triple>`,
  pure `is_statically_linked` / `has_expected_arch` verdict helpers, per-leg
  `_verify_output` enforcing static-linkage (musl) and single-arch (darwin).
- **`tasks/deps.py install_pup`** — three discrete checked steps (nightly
  install with the GC bump message, presence-probe-guarded `cargo install` via
  ANSI-stripped token equality, `+nightly --version` pre-flight), composed from
  the shared constants.
- **mise wiring** — the final enumerated `check` / `default` / `cli:check` /
  `test:unit` arrays match the plan exactly; `pup:check` `depends` on
  `deps:install:pup`; no `coverage:*` task or edge exists.
- **CI workflow** — `check-cli`, `build-cli` (dual-OS matrix), `check-supply-chain`,
  `check-architecture` all present, least-privileged, gating the
  prerelease/release `needs:`. Top-level `permissions: { contents: read }`
  default added; every third-party action SHA-pinned with a version comment;
  the musl cross-linker step staged as a commented, ready-to-enable block for
  0007.
- **Tests** — `test_mise_wiring.py` and `test_workflows.py` are the executable
  backstops for the whole wiring; the deny/pup regressions hard-fail (not skip)
  under `CI`.
- **Docs** — `CLAUDE.md`, `tasks/README.md`, and a new `CONTRIBUTING.md`
  branch-protection runbook all landed, cross-linked, and lint-clean.

#### Deviations from Plan

All deviations are sound and, where the plan anticipated them, explicitly
sanctioned by it:

1. **cargo-pup CI binary cache dropped in favour of rebuild-from-source**
   (`check-architecture`). The plan described an elaborate cache-poisoning-guarded
   binary cache with a per-OS SHA-256 map committed to `tasks/shared/rust.py`,
   but offered an explicit fallback: *"If a trustworthy out-of-band checksum
   cannot be maintained, drop the binary cache and rebuild from source every
   run — correctness over speed for a compiler plugin."* The implementation took
   that fallback and documents it inline in the workflow. Consequence: the
   checksum map and its "every cached OS has an entry" unit test do not exist —
   correctly, since there is no cache to guard. This trades CI minutes for a
   smaller attack surface, consistent with a supply-chain story.

2. **Pup/deny regression partitioning by directory, not pytest markers.** The
   plan specified a `@pytest.mark.requires_pup` marker + `--strict-markers` +
   `-m "not requires_pup"` / `-m requires_pup` filters. The implementation
   instead isolates the suites in dedicated directories
   (`tests/integration/{deny,pup}/`) run by dedicated mise tasks
   (`test:integration:deny`, `test:integration:pup`), with `test:integration:pup`
   deliberately excluded from the `test:integration` roll-up and run explicitly
   in `check-architecture`. This achieves the same goal (keep the nightly-only
   suite out of the general integration job) with arguably less machinery, and
   the wiring/workflow tests assert the *implemented* mechanism rather than the
   planned one — so the guard is intact.

3. **Tool pins use explicit aqua backend refs** (e.g.
   `"aqua:nextest-rs/nextest/cargo-nextest"`) rather than bare short-names. This
   pins the resolution backend precisely and is an improvement over the plan's
   "short-name pins" framing.

4. **`cli/Cargo.toml` adds `license = "MIT"`** (not in the plan's snippet). This
   is necessary for the cargo-deny `licenses` check to evaluate the local crate
   cleanly — a correct, required addition.

#### Potential Issues

- **None blocking.** The full bare `mise run` was validated by its constituent
  parts rather than one invocation; if a single end-to-end run is desired before
  relying on the "done" definition, run `mise run` once. (All constituents are
  green, so this is belt-and-braces only.)
- The dropped pup binary cache means `check-architecture` pays a from-source
  cargo-pup build on every cache-cold CI run. This is the documented, accepted
  trade-off, not a defect.

### Manual Testing Required

The plan's "manual" items are largely automated by the regression tests above.
The genuinely manual residue (requires a live PR / repo settings) remains:

1. Branch protection:
   - [ ] Register the five Rust required-check names — `Check cli`,
     `Build cli (ubuntu-latest)`, `Build cli (macos-latest)`,
     `Check supply chain`, `Check architecture` — per the new
     `CONTRIBUTING.md` runbook, then confirm a failing Rust check makes a PR
     non-mergeable.
2. CI behaviour on a real PR:
   - [ ] Break `cli` formatting / introduce a clippy `-D warnings` violation →
     `check-cli` red.
   - [ ] Introduce a darwin-only build break → `build-cli (macos-latest)` red
     while `build-cli (ubuntu-latest)` stays green.
   - [ ] Confirm the `test-unit` coverage summary appears on both the ubuntu and
     macOS legs.

### Recommendations

- **Register the branch-protection required checks now** (CONTRIBUTING.md
  runbook). This is the one gap between "jobs exist" (proven by
  `test_workflows.py`) and "jobs gate" — until the names are registered, a red
  Rust job does not block merges.
- **Track the two owed follow-ups** the plan records as travelling with this
  work: (a) the ADR amending/superseding ADR-0002 to ratify the host-native
  per-OS matrix build model, raised *before* 0008 implements the release build;
  and (b) 0007 enabling the staged musl cross-linker step when the C-FFI stack
  lands, so `build-cli (ubuntu-latest)` does not silently redden on that merge.
- **Update work item 0006's first acceptance criterion** per the plan's "AC
  reconciliation note" — "tests (with coverage) run in `mise run`", not "in
  `mise run check`" — so the AC matches the repo's check/test separation.
- No code changes required before merge; the implementation is complete and
  internally consistent.
