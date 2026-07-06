---
type: plan-review
id: "2026-07-03-0008-static-binary-distribution-and-launcher-review-1"
title: "Plan Review: On-Demand Static-Binary Distribution & Launcher"
date: "2026-07-03T11:16:48+00:00"
author: Toby Clemson
producer: review-plan
status: complete
parent: "plan:2026-07-03-0008-static-binary-distribution-and-launcher"
target: "plan:2026-07-03-0008-static-binary-distribution-and-launcher"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, code-quality, test-coverage, correctness, security, portability, compatibility, safety]
review_number: 1
review_pass: 3
tags: [rust, distribution, launcher, cross-compile, dispatch, minisign, reqwest, cargo-zigbuild]
last_updated: "2026-07-03T14:45:51+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: On-Demand Static-Binary Distribution & Launcher

**Verdict:** REVISE

This is a strong, unusually self-aware plan: it correctly identifies the rustls
trap, treats resolution as a driven port with a fake adapter before the real
one, sequences six independently-mergeable phases coupled through a single
explicit edge, and commits to strict TDD with a hermetic three-layer test
harness. The verdict is REVISE not because the shape is wrong but because a
handful of load-bearing details are under-specified in a domain where the
details *are* the safety guarantee — most importantly, the bootstrap admits the
launcher binary (the root of the entire trust chain) without key-bound
verification in the normal zero-setup case, several integrity checks (cache-hit
re-verify, manifest signing, publish-time signature verification) stop at sha256
where a key-bound check is required, and a cluster of coherence/contract details
(manifest seeding, the checksums-vs-manifest split, the triple→alias map
duplicated across three languages, the manifest schema conventions) will bite at
implementation or first real fetch.

### Cross-Cutting Themes

- **The trust-chain root is weaker than the links it gates** (flagged by:
  security [critical], architecture, safety) — the bootstrap fetches and execs
  the launcher itself with "minisign if the C tool is available, else delegate to
  the launcher's own re-verify." A binary cannot verify its own integrity, and
  the C tool is absent in the zero-setup case, so the most privileged binary is
  admitted on sha256-over-TLS alone — exactly the TLS-only trust model ADR-0002
  rejects. Every downstream sub-binary check is moot if a tampered launcher runs.

- **Integrity checks stop at sha256 where a key-bound check is required**
  (flagged by: security, safety) — the cache-hit path re-verifies only sha256
  (Phase 4), `manifest.json` is fetched over TLS and never key-signed (so it can
  steer resolution / enable rollback), and the publish-time re-download step
  verifies sha256 but the only signature check against the embedded key is
  *manual*. sha256 alone is a corruption check on a user-writable directory, not
  a security boundary.

- **Coherence anchors and cross-language contracts are under-specified**
  (flagged by: correctness, code-quality, compatibility, safety) —
  `manifest.json` is made a version anchor but never seeded (reproducing the
  exact `FileNotFoundError` the plan fixes for `checksums.json`); `checksums.json`
  is written by `version.py` but excluded from `version:check`; the
  triple→platform-alias map is duplicated across Python, Rust, and bash with no
  coherence test; and the manifest's sha256-prefix and release-tag/URL
  conventions are left ambiguous between publisher and launcher.

- **Cache write safety and network resilience are unspecified** (flagged by:
  safety, architecture) — the cache write is not stated to be atomic, a poisoned
  cache entry has no eviction/re-fetch path (bricks the subcommand permanently),
  concurrent invocations can race the same path, and the blocking reqwest fetch
  has no timeout/retry — a hung endpoint hangs the invoking Claude Code command
  indefinitely.

- **musl/host-independence details dropped** (flagged by: portability,
  compatibility) — the work item's explicit musl DNS/getaddrinfo caveat is gone,
  and the reqwest feature set (`rustls-tls`) is not pinned to the bundled
  webpki-roots variant AC7 requires, risking reintroduced host-cert-store and
  host-resolver coupling on the very static binaries meant to be independent.

- **Cache directory contract assumed, not validated** (flagged by: architecture,
  portability, safety) — `${CLAUDE_PLUGIN_ROOT}/bin/` is assumed writable,
  exec-capable, and GC'd-on-upgrade by Claude Code, with no launcher-side
  fallback or reclamation if any of those does not hold.

### Tradeoff Analysis

- **Zero-setup vs. root-of-trust integrity**: The design's zero-toolchain
  promise pushes back on requiring the minisign C tool in the bootstrap, but
  admitting the launcher on TLS alone defeats the whole verification model. These
  are reconcilable — vendor a pure verification step or ship the launcher's
  signature check without an external tool (e.g. verify in-process against a key
  committed inside the plugin package, delivered over the trusted marketplace
  channel). Recommendation: close the root-of-trust hole; do not let zero-setup
  weaken it.

- **Test rigour vs. CLAUDE.md "tests held to the same standard"**: The plan
  itself flags exempting the fixture crate from `[workspace.lints]` and coverage.
  This is a reasonable, contained bend for test scaffolding (a stub calling
  `process::exit` trips `clippy::exit`) — recommend accepting it explicitly with
  a one-line rationale in the plan, since it is a conscious, bounded exception.

### Findings

#### Critical

- 🔴 **Security / Architecture / Safety**: Launcher binary fetched and exec'd
  without key-bound signature verification
  **Location**: Phase 6, §1 (scripts/bootstrap.sh)
  The bootstrap verifies the launcher with "minisign if the C tool is available,
  else delegate all verification to the launcher's own re-verify on first exec."
  In the normal zero-setup case the C tool is absent, so the launcher — which is
  itself what verifies every sub-binary — is admitted on sha256-over-TLS alone,
  and "delegate to the launcher's own re-verify" is incoherent for the launcher
  itself. This downgrades the root of the trust chain to the exact TLS-only model
  ADR-0002 rejects; a MITM'd or tampered launcher runs with full privileges and
  all downstream checks are moot.

#### Major

- 🟡 **Security**: Cache-hit path must re-verify the minisign signature, not only
  sha256
  **Location**: Phase 4, §1–§2
  Resolution is scan-first and only sha256 is re-checked "before every exec"; the
  cached binary and manifest live in user-writable `${CLAUDE_PLUGIN_ROOT}/bin/`.
  A local writer can poison the binary and its matching checksum, passing a
  sha256-only re-check. Only the embedded-key minisign signature is an
  independent anchor — re-verify it on every cache-hit exec.

- 🟡 **Security**: The resolution manifest is not itself signed
  **Location**: Phase 2, §2; Phase 4, §2
  Per-binary signatures authenticate bytes but not *which* version/asset the
  launcher is steered to, and leave the manifest sha256 TLS-only. A tampered or
  stale manifest enables a rollback/freeze attack (pin users to an older validly
  signed but vulnerable sub-binary). Sign `manifest.json` and verify it
  in-process before trusting any field.

- 🟡 **Security**: Signing secret exposed to the full build job and arbitrary
  build scripts
  **Location**: Phase 2, §1
  Signing "after the four-triple build" implies the key shares the environment
  with cargo-zigbuild, which compiles/runs untrusted third-party `build.rs`/proc
  macros. A single compromised transitive build dep can exfiltrate the release
  key. Isolate signing in a minimal job that receives only artifacts + secret and
  runs no crate compilation.

- 🟡 **Safety**: Re-download protective step verifies sha256 but not minisign
  against the embedded public key
  **Location**: Phase 2, §4
  The only end-to-end signature check (`minisign -Vm … -P <pubkey>`) is *manual*.
  A key mismatch (committed public key ≠ signing secret) passes sha256
  re-verification and ships, then fail-opens into universal refusal at every
  user's first run. Make the automated publish step verify each re-downloaded
  binary against the same committed public key the launcher embeds, before
  un-drafting.

- 🟡 **Safety**: Cache write is not atomic and a poisoned entry has no recovery
  path
  **Location**: Phase 4, §2
  A killed/partial download or two racing invocations can leave a truncated file
  at the final cache name; the scan then finds it, re-verify refuses (good), but
  nothing evicts/re-fetches — the subcommand is bricked until manual deletion.
  Fetch to a temp file, verify there, atomically rename into the checksum-keyed
  name; on cache-hit verification failure, evict and re-fetch once.

- 🟡 **Architecture**: No timeout, retry, or backoff on the network fetch
  **Location**: Phase 4, §3 / Performance Considerations
  Blocking reqwest sets no default timeout, so a hung GitHub endpoint hangs the
  launcher — and the Claude Code invocation that spawned it — indefinitely, and a
  transient blip fails with no recovery. Set connect/read timeouts and add
  bounded retry-with-backoff (safe, since resolution is checksum-keyed).

- 🟡 **Architecture / Portability / Safety**: Cache lifecycle relies on an
  unvalidated external contract
  **Location**: Decision 2 / Phase 4, §2
  `${CLAUDE_PLUGIN_ROOT}/bin/` is assumed writable, exec-capable, and
  GC'd-on-upgrade by Claude Code. None is verified; read-only/immutable installs
  (Nix, container layers) or `noexec` mounts break caching or exec, and if Claude
  Code does not prune, binaries accumulate unbounded. Validate the contract and
  add an XDG-cache fallback or bounded self-eviction.

- 🟡 **Architecture**: New hexagon cores not covered by the ADR-0009
  inward-dependency enforcer
  **Location**: Phase 3, §5 / Key Discoveries
  cargo-pup constrains only `version::core`; the new resolution/dispatch/help
  cores would rest on review discipline, not the automated enforcer ADR-0009
  designates as sole guard. Add a `*_core_imports_only_permitted` rule for the new
  core module path.

- 🟡 **Code Quality**: `kernel::Error` becomes a cross-subdomain god-enum
  **Location**: Phase 3, §2
  Seven launcher-resolution variants land directly in the shared `kernel::Error`;
  none concern `version`, and each future subdomain (config/0009…) would keep
  editing the kernel. Prefer a launcher-local resolution error mapped into a
  small, genuinely cross-cutting `kernel::Error` at the boundary.

- 🟡 **Code Quality**: Error variants have no specified payloads
  **Location**: Phase 3, §2 / Phase 4, §3
  Variants are named but carry no data, yet the ACs require diagnostics that name
  the missing target and distinguish mismatches. Specify payloads (target triple
  + URL on fetch/asset-not-found; expected vs actual sha256 on checksum mismatch;
  asset name on signature mismatch).

- 🟡 **Code Quality / Architecture**: External dispatch left in the `version`
  module as a "consider", not decided
  **Location**: Phase 3, §3
  Launcher-wide routing and the ResolveBinary port are not `version` concerns;
  leaving relocation optional risks the `version` hexagon accreting launcher
  responsibilities and inviting a pup violation. Commit firmly to a launcher-level
  `dispatch`/`launch` module as a Phase 3 deliverable.

- 🟡 **Code Quality / Correctness / Compatibility / Safety**: `checksums.json`
  and `manifest.json` are overlapping sources of truth; `checksums.json` is
  written but not audited
  **Location**: Phase 1, §3 / Phase 2, §2–§3
  Both hold per-binary sha256; `version.py` `write()` writes `checksums.json`'s
  version but `version:check` audits only plugin.json / Cargo.toml / manifest.json,
  so `checksums.json` can drift undetected. Either fold `checksums.json` into
  `manifest.json` (single source) or scope each file's responsibility and bring
  every version-bearing file the writer touches under `version:check`.

- 🟡 **Correctness**: `manifest.json` is made a version anchor but never seeded
  → `FileNotFoundError`
  **Location**: Phase 2, §3
  `_render_*_version` reads the file to preserve other keys, so an unseeded
  `manifest.json` reproduces the exact `FileNotFoundError` the plan fixes for
  `checksums.json`, breaking Phase 2's own "`version:check` exits 0" criterion.
  Seed `manifest.json` (`{"version": "<current>", "binaries": {}}`) in Phase 2.

- 🟡 **Correctness**: Runtime source of the manifest is unspecified; AC3 and AC4
  conflict for the cache-hit-while-offline case
  **Location**: Phase 4, §2
  If the manifest is fetched every invocation, a manifest-fetch failure on an
  already-cached sub-binary hits AC4 (exit non-zero) even though AC3 says a cached
  binary must be reused. State that the manifest is bundled per-plugin-version
  under `${CLAUDE_PLUGIN_ROOT}` (consistent with Decision 2 / "no self-update")
  and define behaviour when a cached binary exists but the network is down.

- 🟡 **Correctness**: clap's derive `--help` exits before the launcher can inject
  the manifest-derived section
  **Location**: Phase 5, §1
  `Cli::parse()` intercepts `--help`, prints static help, and exits before any
  launcher code runs; derive `after_help` takes only a compile-time string. AC6
  (manifest-derived `foo`/`Bar tool` line) is not implementable as written.
  Restructure to build the command dynamically
  (`Cli::command().after_help(runtime_section)` + `get_matches()`) or catch
  `ErrorKind::DisplayHelp` from `try_parse`, reading the manifest before parsing.

- 🟡 **Correctness**: `CARGO_BIN_EXE_<name>` does not resolve a bin in a separate
  fixture crate on stable cargo
  **Location**: Phase 3, §4
  Cargo sets `CARGO_BIN_EXE_<name>` only for bins in the *same package* under
  test (why `version.rs` works). A bin in a distinct `cli/testfixtures/` crate is
  not exposed via that env var on stable (artifact/bindeps are nightly). Every
  Phase 3–6 dispatch/exec test would fail to compile. Either declare the fixture
  `[[bin]]`s inside the launcher crate, or resolve the path via
  `build.rs`/`OUT_DIR`, `escargot`, or a target-dir derivation.

- 🟡 **Compatibility**: New deps unpinned with no MSRV enforcement
  **Location**: Phase 3, §1
  reqwest/tokio/sha2 use placeholder versions and only an informal "MSRV ≤ 1.90";
  `clippy.toml`'s `msrv` governs lints, not resolution. A `cargo update` could
  pull a transitive crate needing Rust >1.90, breaking the musl-static build with
  no signal. Pin exact versions, add `rust-version = "1.90.0"` to the
  version-bearing crate, and add a CI leg that builds on the pinned MSRV.

- 🟡 **Compatibility / Portability**: reqwest feature set not pinned to
  bundled webpki-roots
  **Location**: Phase 4, §2 (features = ["rustls-tls", "blocking"])
  AC7 and the work item require host-cert-store independence, but plain
  `rustls-tls` can bring native root discovery. On musl-static this may fail TLS
  on minimal hosts and pull Security.framework on darwin cross-builds. Declare the
  webpki-roots variant explicitly and assert via `cargo tree` that no
  native-cert crate enters the tree.

- 🟡 **Portability / Compatibility**: The musl DNS/getaddrinfo caveat is dropped
  **Location**: Phase 4 / Performance Considerations
  The work item flags musl DNS behaviour explicitly; the plan omits it. reqwest's
  default resolver calls `getaddrinfo`, which on musl-static lacks some
  glibc behaviours (TCP fallback pre-1.2.4, nsswitch/search-domain handling). The
  otherwise-independent binary still depends on the host resolver. Enable a
  pure-Rust resolver (hickory-dns) or add a real-DNS check to the CI-gated smoke
  on a musl target.

- 🟡 **Portability / Code Quality**: Cross-built darwin binaries are
  linkage-unverified and arch-verified via the host's `file`
  **Location**: Phase 1, §2 (_verify_output)
  On a Linux build host the darwin "only system libraries" `otool -L` check runs
  only on the macOS leg, and arch verification depends on host libmagic Mach-O
  support. A release cut from Linux ships darwin binaries whose static guarantee
  is unverified. Use `llvm-otool`/`llvm-lipo` from the provisioned
  `llvm-tools-preview` for host-independent arch + load-command verification, and
  model the (build-host, target-family) → strategy mapping explicitly.

- 🟡 **Compatibility**: triple→platform-alias map duplicated across Python, Rust,
  and bash with no coherence check
  **Location**: Phase 4 / Phase 6
  `TARGETS` lives only in `tasks/shared/targets.py`; the launcher and bootstrap
  need the same map. Three independent copies can silently diverge (publisher
  uploads `luminosity-linux-arm64`, launcher requests a different name) → a
  platform-specific fetch failure. Single-source it (generate the Rust/bash
  tables, or add a cross-language coherence test).

- 🟡 **Compatibility**: manifest schema conventions ambiguous (sha256 prefix,
  release tag/URL scheme)
  **Location**: Phase 2, §2
  `checksums.json` stores `sha256:<hex>` but the manifest example shows bare
  `<hex>`; the release tag is `v{version}` (github.py) but the launcher's URL
  construction rule is unstated. Either disagreement rejects a correct binary or
  fails to find the release. Pin the field shapes and the tag/URL rule with a
  round-trip test (Python writer output parsed by the Rust reader via a shared
  fixture).

- 🟡 **Safety**: `version:check` wired into PR CI but not stated as a hard gate on
  the publish path
  **Location**: Phase 2, §3
  AC8 requires the *release pipeline* to enforce coherence, but the plan only
  wires `version:check` into `mise run check` (PR CI). A release cut with mismatched
  anchors could publish. Invoke `version:check` as a fail-closed precondition
  inside `release_prepare`/`_publish` before upload.

- 🟡 **Test Coverage**: Re-verify-before-exec on a cache hit is only manually
  verified
  **Location**: Phase 4, Success Criteria (Manual)
  The most security-critical guarantee — a tampered cached binary is never exec'd —
  has no automated regression; a refactor that verifies only on fetch would pass
  the whole suite. Add a hermetic test: cache a valid signed fixture, mutate its
  bytes, re-invoke, assert non-zero + no exec.

- 🟡 **Test Coverage**: No stated assertion mechanism proves cache reuse without
  re-fetch (AC3)
  **Location**: Phase 4, Success Criteria
  "cache-reuse-no-refetch" as specified could pass even if the launcher re-fetched
  every time. Assert the mock server received exactly one request across two
  invocations, not just that both succeed.

- 🟡 **Test Coverage**: Bootstrap test strategy leaves the fetch boundary
  unspecified
  **Location**: Phase 6 (test-bootstrap.sh)
  The bootstrap does a real network fetch; the plan does not describe how it is
  stubbed under test, so the suite is either untested on its core logic or flaky.
  Specify a stub seam (overridable downloader var or pre-seeded cache) and
  enumerate hermetic cases: triple detection, cache-present short-circuit, arg/exit
  forwarding.

#### Minor

- 🔵 **Architecture**: Central orchestration module's home left as "consider"
  **Location**: Phase 3, §3 — commit to a named launcher-level orchestration
  module boundary as a first-class deliverable.

- 🔵 **Architecture / Safety**: Concurrent invocations can race on cache writes
  **Location**: Phase 4, §2 — specify atomic write + advisory lock so concurrent
  resolvers converge idempotently. (Overlaps the atomic-write major.)

- 🔵 **Correctness**: TOCTOU window between verify and exec
  **Location**: Phase 4, §1/§3 — acknowledge; if the threat model warrants, exec
  from an already-open verified fd (`fexecve`/`/proc/self/fd`).

- 🔵 **Code Quality**: darwin verification host/target matrix growing complex
  **Location**: Phase 1, §2 — model (build-host, target-family) → strategy as a
  dispatch table; settle the `file` vs `llvm-otool` choice.

- 🔵 **Code Quality**: minisign signature stored twice (inline + detached asset)
  **Location**: Phase 2, §2 — derive the inline field from the emitted `.minisig`
  (single generation point); document which the launcher reads.

- 🔵 **Compatibility**: manifest deserialisation strictness unspecified
  **Location**: Phase 4/5 — specify lenient (ignore-unknown-fields) parsing +
  a test, for forward compatibility given "no self-update".

- 🔵 **Compatibility**: direct `tokio` dep with `macros` feature for a
  blocking-only launcher
  **Location**: Phase 3, §1 — blocking reqwest manages its own runtime; confirm a
  direct tokio dep is needed, else drop it (or reduce to `rt`).

- 🔵 **Security**: enforce HTTPS + constrain redirects on the fetch path
  **Location**: Phase 4, §2 — pin `https`, constrain host to the releases origin,
  low/zero redirect limit (defence in depth).

- 🔵 **Security**: bootstrap download/exec safety not specified
  **Location**: Phase 6, §1 — mandate cert-verified downloads, quote expansions,
  exec argv directly, add a test.

- 🔵 **Security**: manifest `description` rendered into help unsanitised
  **Location**: Phase 5, §1 — strip control/escape chars before terminal render
  (compounds with the unsigned-manifest finding).

- 🔵 **Safety**: no fetch timeout on the launcher's reqwest calls
  **Location**: Phase 4, §2 — set connect/total timeouts (overlaps the resilience
  major).

- 🔵 **Portability**: bootstrap system-tool assumptions undocumented
  **Location**: Phase 6, §1 — specify arch normalisation (`arm64`/`aarch64`,
  `x86_64`/`amd64`), a portable sha256 path (`shasum -a 256` → `sha256sum`), and a
  fetcher-availability check.

- 🔵 **Portability**: no macOS deployment target pinned for darwin cross-builds
  **Location**: Phase 1, §2 — pin a minimum `MACOSX_DEPLOYMENT_TARGET` and record
  the supported macOS range.

- 🔵 **Safety**: bootstrap `CLAUDE_PLUGIN_ROOT` handling should match the
  launcher's named-error fail-safe
  **Location**: Phase 6, §1 — validate + emit a named diagnostic rather than a raw
  `set -u` unbound-variable error.

- 🔵 **Test Coverage**: signal-propagation test lacks a synchronisation strategy
  **Location**: Phase 3, §4 — define a readiness handshake (fixture prints a
  sentinel before blocking) rather than a timing assumption.

- 🔵 **Test Coverage**: exec exit/signal tests must be black-box subprocess tests
  **Location**: Phase 3, Success Criteria — state they spawn `CARGO_BIN_EXE_…`
  (not in-process, which exec would destroy).

- 🔵 **Test Coverage**: the e2e smoke's "real test release" has no described
  provenance/maintenance
  **Location**: Phase 6, §3 — describe how the test release + key are
  provisioned/refreshed; clarify whether a network-dependent check should gate
  merges.

- 🔵 **Test Coverage**: `version:check` test should assert the mismatching file
  names, not just non-zero exit
  **Location**: Phase 2, Success Criteria.

#### Suggestions

- 🔵 **Architecture / Security**: support a small set of trusted embedded keys
  (rotation overlap window) and add `schema_version` to `manifest.json`
  **Location**: Phase 4, §1 / Phase 2, §2 — enables key rotation without a hard
  cutover and safe manifest evolution; document a concrete compromise-response
  procedure, not only a standing note.

- 🔵 **Architecture**: make the manifest/release-URL discovery contract explicit
  and single-sourced
  **Location**: Implementation Approach / Phase 4, §2 — compile it from the same
  version anchor and assert in a coherence test.

### Strengths

- ✅ Hexagonal discipline preserved and correctly sequenced — resolution as a
  driven port with a fake adapter (Phase 3) before the real fetch/verify/cache
  adapter (Phase 4), so dispatch/exec merge without the network stack.
- ✅ In-process, key-bound minisign verification against an embedded public key,
  with an explicit test that a valid-sha256/non-release-key artifact is refused —
  correctly making trust rest on "signed by our key", not TLS.
- ✅ rustls-only stack with a live, regression-tested `deny.toml` ban, and
  explicit awareness of *both* the reqwest default-features trap and the
  cargo-deny dev-dependency TLS trap.
- ✅ Six independently-mergeable phases, each leaving `mise run` green, with the
  distribution/launcher halves coupled through a single explicit edge (the
  manifest schema).
- ✅ Compiler-driven error handling — populating `kernel::Error` intentionally
  breaks `main.rs`'s `match error {}`, localising exactly where handling lands;
  all IO/HTTP paths commit to `Result` under the deny-level restriction lints.
- ✅ Cache root injected as a driven-port input so tests use a temp dir, and an
  unset `CLAUDE_PLUGIN_ROOT` is a named error, not a silent fallback.
- ✅ Strong test architecture: a three-layer decomposition with the right
  mechanism per layer, a hermetic mock-HTTP + test-keypair (plus non-release-key)
  harness, refusal/error paths as first-class criteria, and exactly one CI-gated
  real-network smoke.
- ✅ The fixture-crate lint/coverage exemption and the SLSA-alongside-minisign
  and tokio-cost tradeoffs are surfaced explicitly rather than smuggled in.

### Recommended Changes

1. **Close the root-of-trust hole in the bootstrap** (addresses: Launcher binary
   fetched/exec'd without key-bound verification; launcher self-verification
   silently skipped). Verify the launcher's minisign signature in-process against
   a public key committed inside the plugin package (delivered over the trusted
   marketplace channel) before exec, with no dependence on an optional host tool;
   fail closed with a named diagnostic otherwise.

2. **Make every pre-exec verification key-bound, and sign the manifest**
   (addresses: cache-hit re-verifies only sha256; manifest not signed;
   description rendered unsanitised). Re-verify the minisign signature (not just
   sha256) on every exec including cache hits; sign `manifest.json` and verify it
   in-process before trusting any field; sanitise manifest-derived strings before
   terminal render.

3. **Harden the publish path** (addresses: signing secret exposed to build job;
   re-download verifies sha256 not minisign; version:check not a publish gate).
   Isolate signing in a minimal job with no crate compilation; make the automated
   re-download step verify each binary against the committed public key before
   un-drafting; run `version:check` as a fail-closed precondition inside the
   release orchestration.

4. **Make the cache write atomic and self-healing, and bound the fetch**
   (addresses: cache write not atomic / no recovery; concurrent race; no
   timeout/retry; cache-dir contract unvalidated). Temp-file + verify + atomic
   rename; evict-and-refetch-once on cache-hit verification failure; set
   connect/read timeouts + bounded retry; validate the plugin-dir writable/exec/GC
   contract and add an XDG fallback or bounded self-eviction.

5. **Resolve the coherence-anchor and manifest-contract details** (addresses:
   manifest not seeded; checksums-vs-manifest overlap/audit gap; manifest runtime
   source; sha256-prefix + tag/URL conventions; triple→alias duplication). Seed
   `manifest.json`; decide the single source of truth for per-binary sha256 and
   bring every version-bearing file under `version:check`; state the manifest is
   bundled per-plugin-version and define offline cache-hit behaviour; pin the
   manifest field shapes + tag/URL rule with a round-trip test; single-source the
   triple→alias map across the three languages.

6. **Fix the two implementability blockers** (addresses: clap `--help` runtime
   injection; `CARGO_BIN_EXE` for a separate fixture crate). Build the clap
   command dynamically (or catch `DisplayHelp`) so the manifest section can be
   appended at runtime; resolve fixture bins without relying on
   `CARGO_BIN_EXE_<name>` across crates (in-crate `[[bin]]` or `OUT_DIR`/escargot).

7. **Restore the musl/host-independence guarantees** (addresses: musl DNS caveat
   dropped; reqwest webpki-roots not pinned; darwin cross-build unverified; MSRV
   unenforced). Pin the webpki-roots reqwest feature and assert no native-cert
   crate; adopt hickory-dns or add a real-DNS musl smoke check; verify darwin
   binaries with `llvm-otool`/`llvm-lipo` on the Linux host; pin dep versions +
   `rust-version` + an MSRV CI leg.

8. **Firm up the module boundaries and pup enforcement** (addresses: dispatch in
   `version`; kernel god-enum; error payloads; new cores not pup-enforced).
   Commit to a launcher-level `dispatch`/`launch` module; keep resolution error
   detail launcher-local mapped into a small cross-cutting `kernel::Error` with
   specified payloads; add a pup rule for the new core module path.

9. **Strengthen the test criteria** (addresses: cache-reuse assertion; re-verify
   automated; bootstrap fetch seam; black-box exec tests; signal sync;
   version:check file-naming). Assert exactly-one server hit for cache reuse;
   automate the corrupt-cache-refuses test; specify the bootstrap fetch stub;
   mark exec/signal tests black-box; add a readiness handshake; assert the named
   files in the `version:check` mismatch output.

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: Architecturally disciplined — hexagonal port/adapter sequencing,
six independently-mergeable phases coupled through a single explicit edge, and a
centralised error taxonomy in the dependency-light kernel. Weakest areas:
resilience of the runtime fetch path (no timeout/retry), the trust-chain root
(bootstrap verifies the launcher weaker than the launcher verifies sub-binaries),
and an enforcement gap where new cores are not covered by cargo-pup. Several
core-shaping decisions (orchestration module home, cache concurrency, key
rotation) are left implicit or "consider".

**Strengths**: port-before-adapter sequencing keeps the core testable without
I/O; strong phase decomposition with one explicit cross-edge; centralised
compiler-driven error taxonomy; cache root injected as a port input; tradeoffs
explicitly acknowledged; recognising dispatch is no longer version-specific.

**Findings**:
- 🟡 major (medium): Trust-chain root weaker than the sub-binaries it gates —
  Phase 6 §1. Bootstrap admits the launcher on sha256/TLS when the minisign C
  tool is absent; a binary cannot verify its own integrity.
- 🟡 major (medium): No timeout/retry/backoff for the network fetch — Phase 4 §3.
  Blocking reqwest has no default timeout; a hung endpoint hangs the invocation.
- 🟡 major (medium): New hexagon cores not covered by the ADR-0009 enforcer —
  Phase 3 §5. pup constrains only `version::core`.
- 🟡 major (medium): Cache lifecycle delegated to an unvalidated external contract
  — Decision 2 / Phase 4 §2. Writable/GC assumptions unverified.
- 🔵 minor (medium): Central orchestration module home left as "consider" —
  Phase 3 §3.
- 🔵 minor (medium): Concurrent invocations can race on cache writes — Phase 4 §2.
- 🔵 suggestion (low): Single embedded key + unversioned manifest limit safe
  evolution — Phase 4 §1 / Phase 2 §2.
- 🔵 suggestion (low): Manifest/release-URL discovery contract left implicit —
  Implementation Approach / Phase 4 §2.

### Code Quality

**Summary**: Well-structured for maintainability — ports before adapters, cache
root as a port input, reuse of the version hexagon template, compiler-driven
error handling. Main risks are design-placement decisions left tentative: whether
resolution errors belong in shared `kernel::Error`, whether dispatch moves out of
`version`, and the overlapping checksums/manifest responsibilities. Error payloads
are unspecified despite context-naming diagnostic ACs.

**Strengths**: strong testability design (fake port before real adapter, temp-dir
cache root, hermetic mock server); compiler-driven, lint-aware error handling;
specific failure taxonomy; independently-mergeable phases; the fixture-crate
exemption flagged rather than smuggled.

**Findings**:
- 🔴/🟡 major (medium): `kernel::Error` becomes a cross-subdomain god-enum —
  Phase 3 §2.
- 🟡 major (medium): External dispatch added to the `version` module; relocation
  only "considered" — Phase 3 §3.
- 🟡 major (medium): checksums.json + manifest.json overlapping sources of truth;
  the coherence check omits a file the writer touches — Phase 2 §2–3.
- 🟡 major (medium): error variants lack specified payloads — Phase 3 §2 /
  Phase 4 §3.
- 🔵 minor (medium): `_verify_output` host×target verification matrix growing
  complex — Phase 1 §2.
- 🔵 minor (low): minisign signature stored twice (inline + detached) — Phase 2 §2.

### Test Coverage

**Summary**: Unusually strong — strict TDD, a three-layer decomposition with a
mechanism per layer, a hermetic mock-HTTP + test-keypair harness with the cache
root injected, and refusal/error paths as first-class. Gaps: the security-critical
re-verify-before-exec on a cache hit is only manually verified, the "no re-fetch"
assertion has no stated mechanism, and several subprocess/signal/network tests
lack described isolation/synchronisation.

**Strengths**: explicit red-green-refactor with fixtures as infrastructure; clear
three-layer decomposition; hermetic architecture (mock server, injected cache
root, second non-release key); refusal/error paths first-class; good pyramid
balance; reuse of existing repo idioms.

**Findings**:
- 🔴 major (high): re-verify-before-exec on a cache hit only manually verified —
  Phase 4 Manual.
- 🟡 major (medium): no stated assertion mechanism for cache-reuse-no-refetch
  (AC3) — Phase 4 Success Criteria.
- 🟡 major (medium): bootstrap test strategy leaves the fetch boundary
  unspecified — Phase 6.
- 🔵 minor (medium): signal-propagation test lacks a synchronisation strategy —
  Phase 3 §4.
- 🔵 minor (medium): exec exit/signal tests must be black-box subprocess tests,
  filed under unit — Phase 3 Success Criteria.
- 🔵 minor (medium): the e2e smoke's "real test release" has no described
  provenance/maintenance — Phase 6 §3.
- 🔵 minor (low): `version:check` test should assert mismatching file names —
  Phase 2 Success Criteria.

### Correctness

**Summary**: Logically well-structured — Unix exec for faithful exit/signal
propagation, verify-before-every-exec ordering with a non-release-key refusal
test, a checksum-folded cache key, an enumerated failure set. Concrete gaps:
manifest.json added as an anchor without being seeded (re-introducing
FileNotFoundError), the runtime manifest source is unspecified so AC3 vs AC4
conflict for cache-hit-offline, clap's derive `--help` exits before help
injection, and `CARGO_BIN_EXE_<name>` does not resolve a separate fixture crate's
bin on stable.

**Strengths**: `CommandExt::exec` is correct for AC5; verify ordering explicit
and correct; clean injectable cache-root design; failure paths enumerated with a
never-exec-wrong-binary invariant.

**Findings**:
- 🔴 major (high): manifest.json made a version anchor but never seeded →
  FileNotFoundError — Phase 2 §3.
- 🟡 major (medium): runtime manifest source unspecified; AC3 vs AC4 conflict for
  cache-hit-offline — Phase 4 §2.
- 🟡 major (medium): clap derive `--help` exits before manifest help injection —
  Phase 5 §1.
- 🟡 major (medium): `CARGO_BIN_EXE_<name>` doesn't resolve a separate fixture
  crate's bin on stable — Phase 3 §4.
- 🔵 minor (medium): `_verify_output` calls `lipo` for darwin even on a Linux host
  — Phase 1 §2.
- 🔵 minor (medium): TOCTOU window between verify and exec — Phase 4 §1/§3.
- 🔵 minor (low): checksums.json coherence-anchor status left unclear — Phase 2 §3
  vs Phase 1 §3.

### Security

**Summary**: Core integrity model sound where it matters — in-process key-bound
minisign against an embedded key, a live rustls-only ban with dev-dep-trap
awareness, and a non-release-key refusal test. But the trust chain has a critical
hole at the bootstrap (the launcher itself is admitted on TLS + sha256 in the
zero-setup case), and secondary gaps: unsigned resolution manifest (rollback/
freeze), ambiguity over signature re-verification on cache hits, and the signing
secret exposed to the full build job.

**Strengths**: in-process key-bound verification with a non-release-key refusal
test; rustls-only with a regression-tested ban and both TLS traps recognised;
refuse-on-mismatch with named diagnostics and CLAUDE_PLUGIN_ROOT as a named
error; release-environment approval gate scoping the secret; hermetic
mismatch/refusal tests.

**Findings**:
- 🔴 critical (high): launcher binary fetched/exec'd without key-bound signature
  verification — Phase 6 §1.
- 🟡 major (medium): cache-hit path must re-verify the minisign signature, not
  only sha256 — Phase 4 §1–2.
- 🟡 major (high): the resolution manifest is not itself signed — Phase 2 §2 /
  Phase 4 §2.
- 🟡 major (medium): signing secret exposed to the full build job + build scripts
  — Phase 2 §1.
- 🔵 minor (medium): single embedded key, no rotation overlap or revocation —
  Decision 4 / Phase 4 §1.
- 🔵 minor (medium): enforce HTTPS + constrain redirects on the fetch path —
  Phase 4 §2.
- 🔵 minor (medium): bootstrap download/exec safety not specified — Phase 6 §1.
- 🔵 minor (low): manifest `description` rendered into help unsanitised —
  Phase 5 §1.

### Portability

**Summary**: Pursues genuine environment independence (static musl, rustls, a
bash-3.2 bootstrap, named error on unset CLAUDE_PLUGIN_ROOT) — all well-judged.
But it silently drops the musl DNS/getaddrinfo caveat the work item flagged;
darwin arch/linkage verification couples to the host `file`/libmagic and leaves
cross-built darwin binaries linkage-unverified; the runtime cache assumes the
plugin dir is writable + exec-capable; and bootstrap system-tool assumptions are
undocumented.

**Strengths**: fully static musl binaries; rustls with no OpenSSL/native-tls;
named-error cache-root resolution with an injected port input; bash-3.2 floor
honoured with optional-tool bootstrap; Windows consciously out of scope.

**Findings**:
- 🔴 major (medium): musl DNS/getaddrinfo caveat dropped — Phase 4 / Performance.
- 🟡 major (medium): cache dir assumes writable + exec-capable plugin dir —
  Decision 2 / Phase 4.
- 🟡 major (medium): cross-built darwin binaries linkage-unverified; arch check
  via host `file` — Phase 1 §2.
- 🔵 minor (medium): bootstrap system-tool assumptions undocumented (uname -m,
  sha256, fetcher) — Phase 6 §1.
- 🔵 minor (low): reqwest root source (webpki vs native) not spelled out —
  Phase 3 §1.
- 🔵 minor (low): no macOS deployment target pinned for darwin cross-builds —
  Phase 1 §2.

### Compatibility

**Summary**: Unusually contract-aware — identifies the rustls trap, the manifest
cross-language contract, version coherence, and the clap 4.6.1 to-confirm risk.
Weakest: dependency-version safety (new deps unpinned, no MSRV enforcement) and
shared contracts duplicated across Python/Rust/bash (triple→alias map, sha256
prefix, release-tag/URL scheme) with no coherence check. The reqwest feature set
also risks reintroducing host-cert-store dependence on musl-static.

**Strengths**: the reqwest default-features constraint called out and verified;
the dev-dep TLS-ban interaction surfaced; version coherence extended coherently;
clap derive risk treated as a to-confirm with an observable proof; Unix-only scope
bounded.

**Findings**:
- 🔴 major (high): new deps unpinned, no MSRV enforcement — Phase 3 §1.
- 🟡 major (high): reqwest feature set not pinned to bundled webpki-roots —
  Phase 4 §2.
- 🟡 major (high): triple→alias map duplicated across three languages, no
  coherence check — Phase 4 / Phase 6.
- 🟡 major (high): manifest schema ambiguities (sha256 prefix, tag/URL scheme) —
  Phase 2 §2.
- 🔵 minor (medium): manifest deserialisation strictness unspecified —
  Phase 4/5.
- 🔵 minor (medium): checksums.json seed vs manifest.json coherence audit gap —
  Phase 1 & 2.
- 🔵 minor (medium): direct tokio dep with `macros` for a blocking-only launcher —
  Phase 3 §1.
- 🔵 minor (medium): musl DNS on the fetch path not addressed — Phase 4 /
  Technical Notes.

### Safety

**Summary**: Unusually safety-conscious — a never-exec-a-stale-or-wrong-binary
guarantee (sha256 + in-process minisign re-verified before every exec,
refuse-not-fallback, non-release-key rejection) and a named error on unset
CLAUDE_PLUGIN_ROOT. Material gaps are operational: the cache write is not atomic
with no poisoned-entry recovery, the launcher's own signature verification can be
silently skipped in the bootstrap, and the coherence / re-verify protective steps
are described as PR-CI checks without a stated hard gate on the publish path.

**Strengths**: strong never-exec-wrong-binary guarantee with a non-release-key
test; explicit named-error fail-safe on missing config; refuse rather than
degrade on verification failure; the existing release protective posture retained
(draft/tag preserved on verification error); coherence enforced by construction
plus a naming audit.

**Findings**:
- 🔴 major (high): cache write not atomic; poisoned entry has no recovery path —
  Phase 4 §2.
- 🟡 major (medium): launcher's own minisign verification can be silently skipped
  — Phase 6 §1.
- 🟡 major (medium): version:check wired into PR CI but not a hard gate on the
  publish path — Phase 2 §3.
- 🟡 major (medium): re-download protective step may verify sha256 but not
  minisign against the embedded key — Phase 2 §4.
- 🔵 minor (medium): no fetch timeout on the launcher's reqwest calls — Phase 4 §2.
- 🔵 minor (medium): checksums.json written by the coherence writer but excluded
  from the audit — Phase 2 §3.
- 🔵 minor (low): cache cleanup relies on unverified Claude-Code-prunes-on-upgrade
  assumption — Decision 2.
- 🔵 minor (low): bootstrap CLAUDE_PLUGIN_ROOT handling should match the
  launcher's named-error fail-safe — Phase 6 §1.

## Re-Review (Pass 2) — 2026-07-03

**Verdict:** REVISE

The revision is a substantial improvement: the **critical root-of-trust finding
is resolved at the policy level** (fail-closed, key-bound launcher verification
that explicitly rejects self-verification and optional host tools), and **every
other Pass-1 major was addressed** — cache-hit signature re-verify, signed
manifest, isolated signing job, publish-time key-bound re-verify, atomic cache
write with self-healing recovery, pinned deps + MSRV CI leg, webpki-roots,
hickory-dns, single-sourced alias map, dynamic `--help`, in-crate fixture, the
`version:check` publish gate, and the strengthened test criteria. The verdict
stays REVISE because the fixes opened a new cluster of majors — mostly
second-order consequences of the changes — of which a few would fail in
production or leave the headline fix unrealisable: the bootstrap verifier
*mechanism* is still undefined (bash can't verify Ed25519, and the two escape
hatches are banned), the host-pinned redirect policy would reject GitHub's real
cross-host asset redirect, the pinned manifest schema can't express per-sub-binary
resolution/descriptions (AC6), and the rustls crypto provider is unpinned for the
four-triple cross-compile.

### Previously Identified Issues

- 🔴 **Security/Architecture/Safety**: launcher fetched/exec'd without key-bound
  verification — **Partially resolved.** Policy is now fail-closed and key-bound
  (decision 5), but the *verifier mechanism* is unspecified and may be infeasible
  as written — see new finding below (re-flagged by 4 lenses).
- 🟡 **Security**: cache-hit re-verifies only sha256 — **Resolved** (signature
  re-verified before every exec).
- 🟡 **Security**: manifest not signed — **Resolved** (signed + verified), but see
  new rollback/version-binding finding.
- 🟡 **Security**: signing secret exposed to build job — **Resolved** (isolated
  signing job).
- 🟡 **Safety**: re-download verifies sha256 not minisign — **Resolved** (verifies
  against committed key before un-drafting), but see new tag-deletion finding.
- 🟡 **Safety**: cache write not atomic / no recovery — **Resolved**
  (temp+verify+rename, evict-and-refetch-once), but see EXDEV and evict-vs-refuse
  findings.
- 🟡 **Architecture**: no timeout/retry — **Resolved**, but retry is untested and
  a fixed total-request timeout can false-fail large downloads.
- 🟡 **Architecture/Portability/Safety**: cache-dir contract unvalidated —
  **Resolved** (runtime probe + XDG fallback), but the fallback branches are
  untested and the eviction policy is under-specified.
- 🟡 **Architecture**: new cores not pup-enforced — **Resolved**.
- 🟡 **Code Quality**: kernel god-enum — **Resolved** (launcher-local error
  mapped in), but the boundary mapping is under-specified (stringly-typed risk).
- 🟡 **Code Quality**: error payloads unspecified — **Resolved**.
- 🟡 **Code Quality/Correctness/Compatibility/Safety**: checksums/manifest overlap
  + audit gap — **Resolved** (all four anchors audited); minor residue: per-binary
  digests in the two files aren't cross-checked.
- 🟡 **Correctness**: manifest not seeded — **Resolved**.
- 🟡 **Correctness**: manifest runtime source AC3/AC4 conflict — **Partially
  resolved.** Behaviourally reconciled, but manifest provenance/population is still
  unspecified — see new finding.
- 🟡 **Correctness**: clap `--help` exits before injection — **Resolved** (dynamic
  command build), but the unconditional-read variant couples built-ins to the
  manifest — see new finding.
- 🟡 **Correctness**: CARGO_BIN_EXE cross-crate — **Resolved** (in-crate `[[bin]]`).
- 🟡 **Compatibility**: deps unpinned / no MSRV — **Resolved**.
- 🟡 **Compatibility/Portability**: reqwest not webpki-roots — **Resolved**, but
  the rustls crypto provider is now unpinned for cross-compile — see new finding.
- 🟡 **Portability/Compatibility**: musl DNS dropped — **Resolved but overstated**
  (hickory still reads resolv.conf) — see new finding.
- 🟡 **Portability/Code Quality**: darwin cross-build verification — **Resolved in
  approach**, but the named llvm tools may not ship in `llvm-tools-preview` — see
  new finding.
- 🟡 **Compatibility**: triple→alias map duplication — **Resolved**.
- 🟡 **Compatibility**: manifest schema conventions ambiguous — **Resolved for
  field shapes**, but the schema can't express per-sub-binary entries — see new
  finding.
- 🟡 **Safety**: version:check not a publish gate — **Resolved** (fail-closed
  precondition), but the integration point is untested.
- 🟡 **Test Coverage** (cache reuse assertion, corrupt-cache refuse) — **Resolved**.
- All Pass-1 minors/suggestions — addressed in the revision.

### New Issues Introduced

#### Major

- 🟡 **Security/Architecture/Portability/Safety**: The bootstrap's
  launcher-signature verifier mechanism is undefined and may be infeasible —
  Decision 5 / Phase 6 §1. Bash 3.2 can't verify Ed25519; a host minisign tool
  and launcher self-verification are both explicitly banned; the only remaining
  option is a per-triple native verify shim vendored in the plugin package, which
  contradicts "nothing vendored per-triple" and is itself unverified at first use
  and subject to the same noexec/read-only constraints. This is the linchpin of
  the critical fix — if left undefined, implementation risks regressing to a
  banned (TLS-only) path.
- 🟡 **Correctness/Security/Compatibility**: Host-pinned redirect policy rejects
  GitHub's legitimate cross-host asset redirect — Phase 4 §2. Release-asset
  downloads 302 to a different CDN host (`objects.githubusercontent.com` / signed
  URL); constraining to the release origin fails every real fetch while passing
  the same-host mock tests.
- 🔴 **Correctness**: The pinned manifest schema can't express per-sub-binary
  resolution or descriptions — Phase 2 §2 vs Phase 4/5 / AC6. `binaries` is
  keyed by *platform* with one `name: "luminosity"`; but resolution is *by
  sub-binary name* and AC6 renders a help line per sub-binary. A name→platform
  →{sha256,signature}+description shape is needed, and the round-trip fixture
  gives false confidence testing only the launcher-distribution shape.
- 🟡 **Correctness/Architecture**: Manifest runtime provenance/population
  unspecified — Phase 4 §2. "Bundled per-plugin-version under the cache root" is
  stated but nothing says what writes it or when; the first-offline-run and
  cached-binary-but-missing-manifest cases have an initialisation gap, and the
  XDG-fallback path may have no manifest to read.
- 🟡 **Correctness/Security**: Manifest signature alone doesn't blunt rollback
  without a version-equality check — decision 6 / Phase 4 §1. A validly-signed
  older manifest can be replayed; the "version bound to plugin version" claim
  needs a concrete, tested `manifest.version == expected` refusal (and the
  bootstrap pinning the fetch to the `v{plugin_version}` tag).
- 🟡 **Correctness**: Unconditional manifest read couples built-ins to manifest
  availability — Phase 5 §1. Appending the manifest section before parsing forces
  a manifest read+verify on *every* invocation, breaking offline `luminosity
  version`; the lazy `DisplayHelp`-catch path is not equivalent and should be the
  one specified.
- 🟡 **Compatibility**: rustls crypto provider (aws-lc-rs vs ring) unpinned for
  the four zigbuild triples — Phase 3 §1. reqwest/rustls 0.23+ default to
  `aws-lc-rs` (C + per-arch asm), which is hard to cross-compile — a cross-compile
  break risk for the two-musl/two-darwin matrix.
- 🟡 **Compatibility/Portability**: hickory-dns "host-config-independent" is
  overstated — decision 8 / Phase 3 §1. hickory removes the getaddrinfo/NSS
  coupling (the real musl win) but still reads `/etc/resolv.conf`; behaviour when
  it's absent (minimal containers) is a silent default, not eliminated coupling.
- 🟡 **Portability**: `llvm-lipo`/`llvm-otool` may not ship in
  `llvm-tools-preview` — Phase 1 §2. The rustup component curates a subset; if
  those two are absent the darwin-on-Linux check silently needs a full LLVM
  install, reintroducing host coupling. (Consider `llvm-objdump --macho`.)
- 🟡 **Code Quality**: Phase 4 resolution adapter concentrates too many
  responsibilities — Phase 4. Fetch+retry+URL-hardening, verify (sha256+manifest
  +binary), atomic write+lock+scan+evict, cache-root resolve+XDG+cap all under
  one adapter — name the collaborators (Fetcher / Verifier / CacheStore /
  CacheRootResolver) so each is unit-testable.
- 🟡 **Safety**: Atomic rename assumes temp shares the cache filesystem — Phase 4
  §2. A temp file in system `$TMPDIR` on a different mount fails `rename(2)` with
  EXDEV (or copy-fallback reintroduces torn files); mandate the temp file inside
  the resolved cache dir.
- 🟡 **Safety**: New minisign publish-verification could hit the destructive
  tag-deletion branch — Phase 2 §4 / github.py. Non-`AssetVerificationError`
  exceptions fall to `gh release delete --cleanup-tag`; the new check must raise
  the preserve-for-triage error class, not delete the pushed tag on a tooling
  hiccup.
- 🟡 **Test Coverage**: Several revision-introduced behaviours lack test criteria
  — retry/backoff (5xx-then-200, persistent-5xx), evict-and-refetch recovery,
  cache-root branches (unset/noexec/XDG cap), terminal-escape stripping,
  publish-time signature re-verify abort, the release-path coherence gate, and
  non-UTF-8 `OsString` argument preservation.

#### Minor

- 🔵 **Code Quality**: kernel error-boundary mapping under-specified (bloat vs
  stringly-typed collapse) — Phase 3 §2.
- 🔵 **Architecture/Code Quality**: fixture `[[bin]]` in the shipped crate — gate
  behind `required-features`/cfg so plain/release `cargo build` doesn't produce it.
- 🔵 **Architecture/Safety**: XDG eviction policy (retention cap, ordering,
  don't-evict-in-use) under-specified — Phase 4 §2 / decision 2.
- 🔵 **Security**: no check that the plugin-committed key equals the
  launcher-embedded key — add a coherence assertion into `mise run check`.
- 🔵 **Correctness/Safety**: fixed total-request timeout false-fails large/slow
  downloads — prefer connect + read/idle (stall) timeout plus an aggregate
  deadline.
- 🔵 **Safety**: advisory lock must be OS-level (auto-release on crash), timeout-
  bounded, and in a writable dir.
- 🔵 **Compatibility**: `schema_version` added but not validated on read — assert
  a known/supported value, fail closed on an unrecognised higher major.
- 🔵 **Compatibility/Portability**: bundled webpki-roots snapshot can go stale
  under no-self-update — record a refresh cadence in CONTRIBUTING.md.
- 🔵 **Compatibility**: hickory/sha2/minisign-verify license closures not yet
  verified against the pre-seeded deny.toml allow-list.
- 🔵 **Security**: key-rotation overlap window is lengthened by no-self-update —
  bound it in the compromise procedure.
- 🔵 **Portability**: bootstrap must apply the same writable+exec probe / XDG
  fallback for the launcher binary itself, single-sourcing the directory contract.

### Assessment

The plan is markedly stronger than at Pass 1 — the critical is closed in policy
and all prior majors are addressed. It is **not yet ready**: one theme (the
bootstrap verifier mechanism) must be pinned down because the headline fix
depends on it, and four concrete issues would fail in production or against AC6
(GitHub cross-host redirect, per-sub-binary manifest schema, rustls crypto
provider for cross-compile, manifest provenance). Most of the rest are targeted
refinements and test-criteria additions. A further revision pass — anchored on a
decision about the root-of-trust verifier — would bring it to APPROVE.

---
*Re-review generated by /accelerator:review-plan*

## Re-Review (Pass 3) — 2026-07-03

**Verdict:** REVISE

Pass-2's edits resolved **every** Pass-2 major; the root-of-trust verifier is now
concretely a **vendored per-triple `minisign-verify` shim**. Pass 3 surfaced a new
batch, but the character has shifted decisively toward implementation-grade
detail: two were genuine technical errors in the Pass-2 edits (the `ring` provider
was not actually selected by the named feature; `rust-version` does not feed the
resolver under `resolver = "2"`), a cluster were ramifications of the shim
decision (its crate topology, creation step, own tests, provenance, and — most
substantively — that it can't execute from a `noexec`/read-only plugin root), and
the remainder were fine concurrency/lifecycle refinements. All were addressed in a
third edit pass. The verdict remains REVISE only by the major-count threshold; the
trajectory (critical → 0, and each pass's majors resolved with progressively finer
successors) indicates convergence, and the residual items are implementation
decisions rather than plan-level gaps.

### Previously Identified Issues (Pass-2 new issues)

- 🟡 bootstrap verifier mechanism undefined — **Resolved**: vendored per-triple
  `minisign-verify` shim (decision 5, Phase 6 §2), with its own crate, tests, and
  reproducible-build byte-identity check.
- 🟡 host-pinned redirect breaks GitHub CDN — **Resolved**: `*.githubusercontent.com`
  suffix allowlist (Phase 4 §2).
- 🔴 manifest schema can't express sub-binaries — **Resolved**: name-keyed schema
  with per-platform inner map (Phase 2 §2).
- 🟡 manifest runtime provenance — **Resolved**: signed release asset, fetched on
  cache miss, cached alongside, offline after first online (Phase 4 §2).
- 🟡 manifest signature ≠ rollback — **Resolved**: version-equality check + `v{version}`
  pinning (decision 6).
- 🟡 unconditional manifest read couples built-ins — **Resolved**: lazy DisplayHelp
  path (Phase 5 §1).
- 🟡 rustls crypto provider unpinned — **Resolved this pass**: `-no-provider`
  reqwest feature + explicit `rustls` ring dep + `CryptoProvider::install_default`
  (Phase 3 §1).
- 🟡 hickory overstated — **Resolved**: claim narrowed (decision 8).
- 🟡 llvm-lipo/otool absent — **Resolved**: `llvm-objdump --macho` (Phase 1 §2).
- 🟡 Phase 4 adapter too much — **Resolved**: Fetcher/Verifier/CacheStore/CacheRootResolver.
- 🟡 EXDEV atomic rename — **Resolved**: temp inside cache dir.
- 🟡 tag-deletion branch — **Resolved & extended this pass**: all tool-invocation
  failures wrapped into `AssetVerificationError` (Phase 2 §4).
- 🟡 test-coverage gaps — **Resolved**: criteria added across phases.

### New Issues Introduced (Pass 3) — all addressed in the third edit pass

- 🟡 **Compatibility/Correctness**: `ring` not actually selected by
  `rustls-tls-webpki-roots` (0.23+ defaults to aws-lc-rs) — **fixed**: `-no-provider`
  feature + ring rustls dep + fallible `install_default`.
- 🟡 **Compatibility**: `rust-version` ignored under `resolver = "2"` — **fixed**:
  bump to `resolver = "3"`; CI MSRV leg is the belt-and-braces guard.
- 🟡 **Portability/Correctness/Compatibility**: vendored shim can't run from a
  `noexec`/read-only plugin root, nullifying the XDG fallback — **fixed**: bootstrap
  copies shim + launcher into the resolved writable+exec dir before running.
- 🟡 **Architecture/Test/Security**: shim had no crate home, creation step, own
  tests, or provenance check — **fixed**: `cli/verify/` workspace member with
  rust-version, black-box tests, and a reproducible-build byte-identity check
  (Phase 6 §2).
- 🟡 **Correctness/Security**: launcher authenticity-verified but not
  freshness-bound — **fixed**: bootstrap matches the fetched launcher's sha256
  against the signed, version-bound manifest (Phase 6 §1).
- 🟡 **Correctness**: advisory lock held across `exec` serialises unrelated
  invocations — **fixed**: per-key lock, `FD_CLOEXEC`/closed before exec, re-scan
  on acquire/timeout (Phase 4 §2).
- 🟡 **Correctness**: cache-hit-skips-manifest vs "re-fetch on manifest-hash
  change" — **fixed**: within-version manifest immutability stated; re-fetch applies
  across version bumps (What We're NOT Doing).
- 🟡 **Portability/Compatibility**: hardcoded CDN allowlist brittle under
  no-self-update — **fixed**: suffix match.
- 🟡 **Architecture/Compatibility**: cache-root probe duplicated bash↔Rust —
  **fixed**: launcher owns the authoritative resolver; bootstrap defers to it,
  coherence-tested (Phase 6 §1).
- 🟡 **Safety**: bootstrap launcher cache lacked atomic-write/self-heal — **fixed**:
  mirrors CacheStore (Phase 6 §1).
- 🔵 minors — shim invoked by absolute path (not PATH); download size/free-space
  cap; eviction under the per-key lock skipping in-use entries; XDG fallback
  exec-probed with a `LUMINOSITY_CACHE_DIR` override and darwin `~/Library/Caches`;
  `schema_version` simplified (belt-and-braces under tag-pinning); shim added to
  the CONTRIBUTING compromise runbook — all addressed.

### Residual (implementation-time, not plan-level)

- Concrete `MACOSX_DEPLOYMENT_TARGET` value still to be chosen and recorded.
- Marketplace channel as the irreducible trust anchor: document its assumptions
  (whatever plugin-integrity Claude Code provides) rather than only relying on it.
- Value-object modelling of sha256/signature/alias (DDD nicety) and the
  dispatch-module internal seam — style refinements, safe to settle during TDD.

### Assessment

Three passes in, the plan has converged: the Pass-1 critical and all Pass-1/Pass-2
majors are closed, and Pass-3's findings were either bugs in the intervening edits
(now fixed) or fine-grained refinements a competent implementer would resolve
during red-green-refactor. The remaining residuals are implementation decisions,
not design gaps. **Recommendation: stop reviewing and implement** — further review
passes will keep finding ever-finer detail at diminishing value. The plan is
sound, internally consistent, and thoroughly test-specified.

### Final verdict — APPROVE (maintainer decision)

The Pass-1 critical and all Pass-1/Pass-2 majors are closed, and Pass-3's
findings were resolved in the third edit pass. The three named residuals (concrete
`MACOSX_DEPLOYMENT_TARGET` value, documenting the marketplace channel as the trust
anchor, optional value-object modelling) are accepted as **implementation-time**
items to settle during red-green-refactor, not plan-level blockers. The maintainer
therefore overrides the count-based REVISE to **APPROVE**; the plan is marked
`ready`.

---
*Re-review generated by /accelerator:review-plan*
