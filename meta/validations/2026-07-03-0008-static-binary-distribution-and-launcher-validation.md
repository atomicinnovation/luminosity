---
type: plan-validation
id: "2026-07-03-0008-static-binary-distribution-and-launcher-validation"
title: "Validation Report: On-Demand Static-Binary Distribution & Launcher Implementation Plan"
date: "2026-07-04T20:06:46+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: partial
target: "plan:2026-07-03-0008-static-binary-distribution-and-launcher"
tags: [rust, distribution, launcher, minisign, cross-compile, validation]
last_updated: "2026-07-04T20:06:46+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: On-Demand Static-Binary Distribution & Launcher

**Verdict: PARTIAL.** Every automated check is green — the full local CI mirror
(`mise run`, bare default) exits 0 — and all six phases are implemented against
their explicit success-criteria checkboxes. The report is `partial` (not `pass`)
because: (a) the plan's own blocked operational criteria remain unchecked by
design; (b) several load-bearing elements described in the Phase 4 / Phase 6
design bodies are simplified or absent (advisory file locking, download
size/free-space bounding, fine-grained fetch timeouts, https-scheme
enforcement, single-sourced cache-root resolution); and (c) one real
correctness gap in the release publish path contradicts an explicit Phase 2
safety requirement.

### Implementation Status

- ✓ **Phase 1** — Four-triple cross-compile via cargo-zigbuild + staging — Fully implemented
- ⚠️ **Phase 2** — minisign signing + manifest + version-coherence — Implemented; one publish-path correctness gap + two documented design substitutions
- ⚠️ **Phase 3** — Launcher deps, kernel error, external dispatch + exec — Implemented; one minor deviation (ring provider `Result` discarded, not mapped)
- ⚠️ **Phase 4** — Fetch → verify → cache — Explicit criteria met; several design-body correctness measures absent (locking, size cap, timeout granularity, scheme pin)
- ⚠️ **Phase 5** — Manifest-driven help + `--help` delegation — Implemented; missing two end-to-end tests for behaviours that are unit-tested only
- ⚠️ **Phase 6** — Entry point + packaging + smoke — Implemented; one undocumented deviation (cache-root re-implemented in bash) + operational e2e blocked

### Automated Verification Results

Authoritative run: `mise run` (bare default, full local CI mirror) — **exit 0**.

- ✓ `test:unit:cli` — 50 Rust tests pass (dispatch, resolution, help, kernel)
- ✓ `test:unit:tasks` + `test:integration:tasks` — Python distribution suites pass
- ✓ `test:integration:scripts` — 8 entry-point tests pass hermetically
- ✓ `test:integration:deny` — native-tls/openssl/aws-lc closure absent; `ring` present
- ✓ `cli:check` — rustfmt + clippy (pedantic/nursery/restriction, `-D warnings`)
- ✓ `deny:check` — advisories/bans/licenses/sources ok (the **rustls trap is not sprung**)
- ✓ `pup:check` — all three crates including `luminosity-verify`; no launcher code under `version::core`
- ✓ `build:launcher` — both host darwin triples verified to link only system libraries
- ✓ `build-system:check` / `types:check` — ruff + pyrefly strict + actionlint

Independently re-verified: `cargo tree -e features -p luminosity` resolves
`reqwest feature "rustls-tls-webpki-roots-no-provider"` + `rustls feature "ring"`
with no `openssl`/`native-tls`/`aws-lc-rs`.

### Code Review Findings

#### Matches Plan

- **Phase 1**: `build.release` iterates all four `TARGETS` via `cargo zigbuild`,
  stages `luminosity-{platform}` + `.debug.tar.gz`, writes prefixed sha256 into
  `checksums.json`; host-aware `_verify_output` strategy map (darwin-on-Linux via
  `llvm-objdump --macho`); `MACOSX_DEPLOYMENT_TARGET` set explicitly; seed
  `checksums.json` committed; wired into `*_prepare`.
- **Phase 2**: `tasks/sign.py` detach-signs each binary and emits the name-keyed,
  per-platform `manifest.json` (bare-hex `sha256`, inline signature read back
  from the emitted `.minisig` — single generation point, no drift); `manifest.json`
  itself signed; `version:check` reads all four anchors and names mismatching
  files, wired into `mise run check` and enforced as a fail-closed precondition
  before publish; upload path re-downloads and minisign-verifies every asset +
  the manifest before un-drafting.
- **Phase 3**: dependency stack exactly as specified (`default-features = false`,
  rustls/ring/webpki-roots/hickory-dns, no direct tokio, `resolver = "3"`,
  `rust-version = "1.90.0"`); shared `kernel::Error` with a launcher-local
  `ResolutionError` taxonomy mapping at the boundary; `match error {}` replaced;
  `#[command(external_subcommand)] External(Vec<OsString>)` with dispatch
  relocated to a dedicated `launch` module; in-crate fixture `[[bin]]`; exec via
  `CommandExt::exec`; black-box exit-42 / SIGTERM-15 tests with readiness
  handshake; non-UTF-8 `OsString` preserved through exec; `ResolveBinary` port +
  fake + new `launch::core` pup rule.
- **Phase 4**: embedded key via `build.rs` → `OUT_DIR` (single source);
  verify-any-of trusted-key set; manifest signature + version-equality +
  `schema_version` gate verified before any field is trusted; **pre-exec
  re-verify on cache hits** present, with evict-and-refetch self-heal; bounded
  retry (5xx-then-200 recovers, persistent-5xx gives up after 3); redirect
  allowlist to `*.githubusercontent.com`; atomic temp-in-cache-dir + rename;
  scan-first resolve; evict-oldest-by-mtime; cache-root probe (writable **and**
  exec, catching `noexec`) with XDG fallback + `LUMINOSITY_CACHE_DIR` override +
  named terminus; hermetic std-only mock server + test keypair + non-release key;
  no `.unwrap()`/`.expect()`/`panic!` in production code.
- **Phase 5**: lazy help path (`try_parse` → only on `ErrorKind::DisplayHelp`
  read+verify manifest) keeps built-ins decoupled from the manifest; control/escape
  sanitisation of manifest-derived strings; `foo --help` delegated to child
  (sentinel-asserted).
- **Phase 6**: `bin/luminosity` bash-3.2-clean bootstrap; fail-closed root of
  trust via the vendored per-triple `minisign-verify` shim invoked by absolute
  path; atomic + self-healing launcher cache; shim + launcher copied into the
  writable+exec cache root for `noexec`/read-only plugin roots; `cli/verify/`
  third workspace member (genuinely lint-compliant, not exempted); shell tooling
  globs extended to the extensionless entry point with a coverage test; four
  per-triple shims + public key committed; `CONTRIBUTING.md` documents key
  rotation / compromise response / roots-refresh / shim-refresh duties.

#### Deviations from Plan

- **`version:write` provisioning of minisign** — pinned via mise **`ubi`** backend,
  not the specified `aqua` backend (`mise.toml:12-15`); an inline comment explains
  the aqua registry entry self-verifies with an unset template var and fails to
  install. Functional, documented deviation.
- **Key-coherence check omitted** (`tasks/version.py:132-135`) — the plan
  (decision 7) called for an assertion that the plugin-committed key is
  byte-identical to the launcher-embedded key, wired into `check` with a
  divergence test. The implementation instead makes divergence *impossible*
  (`build.rs` copies the one committed key into `OUT_DIR`), so the check is
  deliberately dropped. Sound in effect, but `mise.toml:295` still advertises the
  removed check (stale description).
- **Phase 4 fetch timeouts** — a single total-request timeout (120 s) is used
  (`fetcher.rs:13-14,83-84`), which is precisely the "single fixed total-request
  timeout" the plan warned against; the separate connect + read/idle + aggregate
  deadline is not implemented.
  **PARTIALLY ADDRESSED (2026-07-04, post-validation):** the total was widened
  to a generous **300 s aggregate deadline** so a large asset over a
  slow-but-progressing link is no longer false-failed (the plan's stated
  concern). A true per-read/idle timeout remains **not implemented**: the
  blocking `reqwest` builder the launcher uses exposes only `connect_timeout`
  and a whole-request `timeout` — `read_timeout` exists solely on the async
  builder, and adding it would mean a direct `tokio` dependency, reversing a
  deliberate design decision. ADR-0010 is accepted/immutable, so this constraint
  is recorded here rather than in the ADR.
- **Phase 4 https-scheme pin** — `is_https` is defined and unit-tested but **never
  called** in the fetch path (`fetcher.rs:38-41`); scheme is not enforced.
  (Downloads are still signature-gated, so this is defence-in-depth, not the
  security boundary.)
  **✓ RESOLVED (2026-07-04, post-validation):** the production `Fetcher::new`
  now pins the scheme — `get` refuses a non-https URL before any connection
  (the test constructor keeps `http` for the local mock). Covered by
  `production_fetcher_refuses_non_https_urls`.
- **Phase 4 manifest caching** — the verified manifest is **not** persisted
  alongside the binary; offline reuse instead relies on the checksum-in-filename
  + `.minisig` sidecar. Goal (offline cache-hit resolves + re-verifies) is met and
  tested; mechanism differs from the plan.
- **Phase 3 ring provider** — `install_crypto_provider` discards the install
  `Result` (`let _ = ...`) and unconditionally returns `Ok(())` (`tls.rs:8-13`)
  rather than mapping the fallible call into `kernel::Error` as specified.
  Documented as intentional and safe (failure only means "already installed").
- **Phase 6 cache-root resolution (undocumented)** — the plan states the bootstrap
  does **not** re-implement the writable+exec probe / XDG-fallback chain, single-
  sourcing it from the launcher. The bootstrap **does re-implement** the whole
  chain in bash (`bin/luminosity:70-106`). This duplication is exactly what the
  plan set out to avoid and is **not** among the three documented Phase 6
  deviations — a genuine divergence risk (launcher and bootstrap can now disagree
  on cache location with no coherence test guarding them).
- **Phase 6 `BASH_SOURCE` resolution** — root is resolved from `CLAUDE_PLUGIN_ROOT`
  directly, not `BASH_SOURCE`. Consistent with the by-path invocation contract;
  benign technique substitution.
- **Documented Phase 6 deviations all match reality**: (1) corruption folded into
  the shim signature check + URL pinned to `v{version}` (no bash sha256/JSON
  parsing); (2) reproducible-build byte-identity check deferred to a CI follow-up;
  (3) CI e2e smoke not wired.

#### Potential Issues

1. **Publish path can destroy the pushed tag on a download timeout (correctness
   gap).** `download_and_verify_signature` (`tasks/github.py:144-174`) calls
   `download_release_asset` (lines 166-167) **without** wrapping
   `subprocess.TimeoutExpired`, unlike the sha256 path `download_and_verify`
   (lines 135-138) which does. A `gh release download` timeout during the
   signature re-verify therefore propagates into the generic `except Exception`
   (line 233), which runs `gh release delete --cleanup-tag --yes` and destroys
   the pushed tag — the exact outcome Phase 2 says must never happen for a
   tool-invocation failure, and contrary to the function's own docstring
   ("timeout ... surfaces as `AssetVerificationError`"). Untested.
   **✓ RESOLVED (2026-07-04, post-validation):** both `download_release_asset`
   calls in `download_and_verify_signature` are now wrapped in
   `try/except subprocess.TimeoutExpired → AssetVerificationError`, mirroring
   the sha256 path, so a download timeout takes the draft-preserving branch. A
   regression test (`TestDownloadAndVerifySignatureTimeout`) covers it.
2. **`version:check` under-reports on an even anchor split.** `_mismatching_anchor_files`
   (`tasks/version.py:118-121`) uses `Counter.most_common(1)` as the "majority";
   on a 2-2 tie the majority is decided by dict-insertion order, so only two of
   four mismatching files are named. Still exits non-zero and names *some* files
   (satisfies the literal AC), but the reported set is order-dependent. Tests
   cover only single-file desync.
   **✓ RESOLVED (2026-07-04, post-validation):** `_mismatching_anchor_files`
   now names **every** anchor when there is no strict majority (even split or
   all-distinct), rather than an order-dependent subset. Covered by
   `test_even_split_names_every_anchor`.
3. **Phase 4 concurrency + resource bounding absent.** No advisory `flock`/`fcntl`
   locking exists anywhere in the launcher (grep-clean), so the plan's per-key
   lock, re-scan-on-acquire/timeout, and FD_CLOEXEC-before-exec are unimplemented;
   concurrent first-use is unguarded. No download size cap / free-space check
   before the streamed write — `try_get` reads the whole body into a `Vec`
   (`fetcher.rs:135-138`), so an oversized response is unbounded. These were
   design-body correctness measures, not explicit success-criteria checkboxes, so
   `mise run` stays green — but they are real gaps against the plan's intent.
   **DECISION (2026-07-04, post-validation): deliberately deferred, not
   implemented.** Advisory locking is judged disproportionate for a single-user
   CLI cache: the cache already writes via atomic temp+rename, so concurrent
   first-use is *safe* (worst case a duplicate idempotent fetch; last rename
   wins; both exec a verified binary), and the only residual is a narrow
   eviction TOCTOU that fails cleanly with `ENOENT`, never a wrong/tampered
   binary. The download size cap / free-space check was also deferred (the
   manifest carries no size field, so it could only be a fixed cap; an `ENOSPC`
   on write already errors cleanly). Recorded here rather than in the
   accepted/immutable ADR-0010.
4. **Bootstrap trusts a single key, defeating verify-any-of rotation.** The
   bootstrap passes one committed key to the shim (`bin/luminosity:64`;
   `cli/verify/src/main.rs:30-37`), so the overlap-window rotation documented in
   `CONTRIBUTING.md` is achievable only at the launcher layer, not the bootstrap
   root-of-trust layer. A rotation would strand the bootstrap on the old key.
5. **The committed release key is a placeholder** (`CONTRIBUTING.md:72-73`) — the
   real keypair and GitHub `release`-environment secrets are not yet provisioned
   (expected; see blocked criteria).

### Manual Testing Required

Operational items the plan itself leaves unchecked (`[ ]`) — none are creatable
from the repository and all are correctly deferred:

1. Release secret provisioning:
  - [ ] Generate the real minisign keypair; provision `MINISIGN_SECRET_KEY` /
        `MINISIGN_KEY_PASSWORD` as GitHub `release`-environment secrets; commit the
        matching public key (replacing the placeholder).
2. End-to-end distribution:
  - [ ] Run the CI-gated e2e smoke against a real pipeline-provisioned test release.
  - [ ] On a clean machine with no cache, confirm
        `${CLAUDE_PLUGIN_ROOT}/bin/luminosity version` fetches → verifies → caches → runs.
3. CI configuration:
  - [ ] Register the pinned-MSRV leg (and any new e2e job) as a required check in
        repo branch-protection settings, per the `CONTRIBUTING.md` runbook.

### Recommendations

- **Fix Potential Issue #1 before the first real release cut** — wrap the two
  `download_release_asset` calls in `download_and_verify_signature` in the same
  `try/except subprocess.TimeoutExpired → AssetVerificationError` guard the sha256
  path already uses, and add a test stubbing a download timeout that asserts the
  draft + tag survive.
- **Reconcile the Phase 4 design gaps with the plan** — either implement the
  advisory lock + size/free-space bounding + fine-grained timeouts + scheme
  enforcement, or amend the plan/ADR-0010 to record these as conscious
  simplifications (with the concurrency/DoS risk accepted). Right now the code
  silently diverges from a richly-specified design.
- **Close the undocumented Phase 6 cache-root duplication** — either route the
  bootstrap through a `luminosity --print-cache-root`-style call (the plan's
  intent) or add the cross-language coherence test the plan required, so launcher
  and bootstrap cannot drift on cache location.
- **Remove dead code / stale docs** — drop the unused `is_https` or wire it in;
  fix the `mise.toml:295` `version:check` description that still claims key-coherence.
- **Add the two missing Phase 5 end-to-end tests** (`--help` renders the
  manifest-derived section; `luminosity version` succeeds with no manifest) and
  the Phase 6 shim-unrunnable + invalid-(non-dir)-plugin-root entry-point tests,
  so the implemented behaviours are guarded end-to-end.
- **Revisit bootstrap key rotation** — let the shim/bootstrap accept multiple
  committed keys so the documented overlap-window rotation actually works at the
  root-of-trust layer.

### Post-validation follow-up (2026-07-04)

Actioned after the report was written (each with a red→green test where a
behaviour changed):

- ✓ **Potential Issue #1** — `gh` download timeout in the signature re-verify
  now maps to `AssetVerificationError` (draft + tag preserved).
- ✓ **Potential Issue #2** — `version:check` names every anchor on a no-majority
  split.
- ✓ **https-scheme pin** — production `Fetcher` refuses non-https URLs (the dead
  `is_https` is now wired in).
- ✓ **Stale docs** — the `mise.toml` `version:check` description no longer
  claims key-coherence.
- ✓ **Phase 5 / Phase 6 test gaps** — added end-to-end tests: `version` works
  with no manifest, `--help` degrades gracefully; entry-point invalid-plugin-root
  and unrunnable-shim fail-closed. (The manifest-derived `--help` section stays
  a unit test — the binary pins the embedded key, so a test cannot sign a
  manifest under it.)
- ⚠️ **Fetch timeout** — total widened to a 300 s aggregate deadline; a true
  per-read/idle timeout is not feasible on blocking `reqwest` without a direct
  `tokio` dep (see Deviations).
- ◻︎ **Deliberately deferred** — advisory locking and download size/free-space
  bounding (see Potential Issue #3 for rationale).
- ◻︎ **Not actioned this pass** — Phase 6 cache-root duplication and bootstrap
  single-key rotation remain open.
