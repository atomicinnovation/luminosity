---
type: plan
id: "2026-07-03-0008-static-binary-distribution-and-launcher"
title: "On-Demand Static-Binary Distribution & Launcher Implementation Plan"
date: "2026-07-03T10:46:27+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0008"
parent: "work-item:0008"
derived_from: ["codebase-research:2026-07-03-0008-static-binary-distribution-and-launcher"]
relates_to: ["plan:2026-06-29-0007-scaffold-hexagonal-rust-workspace"]
tags: [rust, distribution, launcher, cross-compile, dispatch, minisign, reqwest, cargo-zigbuild]
revision: "453a8575c24464e238925d555d24967c140ccd7b"
repository: "luminosity"
last_updated: "2026-07-03T16:54:31+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# On-Demand Static-Binary Distribution & Launcher Implementation Plan

## Overview

Turn the pre-cut skeleton into a working launcher + distribution pipeline: build
fully static `luminosity` binaries for the four Unix triples from one host,
minisign-sign and publish them with a release manifest under enforced version
coherence, and implement the Rust launcher (external-subcommand dispatch,
fetch → verify → cache → exec, manifest-driven help) behind a thin bash
bootstrap.

## Current State Analysis

The repository is a **well-prepared skeleton, not a partial implementation**.
Every seam this story needs was deliberately pre-cut; the load-bearing machinery
is absent.

- **Rust scaffold** (`cli/`) ships only `version` as a textbook hexagon. The
  `Command` enum has one variant, `Version` (`cli/launcher/src/version/inbound/cli.rs:17-21`);
  `dispatch` is already fallible (`:41-51`); `main.rs:18` matches an uninhabited
  `kernel::Error` via `match error {}`; `kernel::Error` is `enum Error {}`
  (`cli/kernel/src/lib.rs:9`). No `external_subcommand`, no reqwest/rustls/tokio,
  no minisign, no sha2.
- **Supply-chain policy** (`cli/deny.toml:57-61`) hard-bans
  `native-tls`/`openssl`/`openssl-sys` and evaluates the graph **as the release
  ships it** (`:15-20`, not `--all-features`). Licences for the reqwest/rustls/
  tokio/clap closure are pre-seeded (`:34-44`).
- **Distribution tasks** (`tasks/`) are a skeleton with a hole in the middle.
  `tasks/build.py` builds **host-native only** via plain `cargo build`
  (`:78-87`) with static/arch verification (`is_statically_linked`,
  `has_expected_arch`); **cargo-zigbuild is unused** though provisioned
  (`pyproject.toml:16-17`). `tasks/github.py:upload_and_verify` (`:135-177`) does
  a full draft → upload → re-download-and-SHA-verify → publish flow but consumes
  artifacts nothing produces (no copy to `cli/launcher/bin/`, no checksums, no
  archives, **no minisign**). `tasks/version.py:write` (`:71-80`) enforces
  coherence by construction across `plugin.json` / `cli/launcher/Cargo.toml` /
  `checksums.json`, but `checksums.json` **does not exist on disk** so
  `version:write`/`version:bump` currently raise `FileNotFoundError`. There is
  **no `version:check` audit task**.
- **CI** (`.github/workflows/main.yml`) has a two-leg `build-launcher` matrix
  (`:138-183`) and a full release topology (`:241-363`) with three SLSA
  `attest-build-provenance` steps — but the release jobs **never build or
  checksum binaries**, and the attestation is SLSA, not minisign.
- **Bootstrap / plugin runtime surface is greenfield.** No `hooks/`; `scripts/`
  holds only `lint-bashisms.sh`; `plugin.json` has no `bin`/`hooks`/`scripts`
  reference. The runtime cache path does not exist.

## Desired End State

`mise run` is green end-to-end and:

- One host cross-compiles all four triples into fully static binaries, each
  published as a GitHub Release asset with a `.sha256` checksum and a `.minisig`
  signature, plus a **signed** release manifest (`manifest.json` +
  `manifest.minisig`).
- The `luminosity` launcher routes unknown subcommands through
  `External(Vec<OsString>)`, resolves the host-triple asset (fetch → verify sha256
  **and** minisign in-process → atomic cache write keyed by name+version+checksum
  → exec), reuses the cache on repeat (re-verifying the signature before **every**
  exec, including cache hits), refuses on any checksum/signature mismatch or fetch
  failure, propagates exit codes and signals, and renders manifest-driven
  discoverable help with `--help` delegation.
- `version` and `config`-shaped built-ins stay compiled in; the launcher tree is
  free of OpenSSL/native-tls (verified by `cargo tree -e features` and the musl
  static check).
- Version coherence across `plugin.json`, `cli/launcher/Cargo.toml`, and the
  release manifest is enforced by a check task that names mismatching files.
- The `bin/luminosity` entry point (a thin bash bootstrap named for the command
  it fronts) fetches the launcher binary itself on first use and verifies its
  minisign signature against a plugin-committed key before exec (fail-closed), so
  the root of the trust chain is key-bound, not TLS-bound. Consumers invoke it by
  path (`${CLAUDE_PLUGIN_ROOT}/bin/luminosity`).

### Key Discoveries

- **The rustls trap** — because `deny.toml` evaluates the shipped feature set
  (`cli/deny.toml:15-20`), reqwest **must** be declared `default-features =
  false` with rustls features or its default `native-tls` feature trips the ban
  (`:57-61`). This is the single most important dependency-declaration constraint.
- **Fixtures are the intended vehicle, not a product sub-binary** (research
  §follow-up). The ACs are phrased around observable behaviours a throwaway stub
  satisfies (`exit 42`; SIGTERM → `$?`=143; a sentinel `--help` string; a
  synthetic manifest listing `foo`/`Bar tool`; fetch failures induced by URL
  redirection). A single arg-driven fixture crate located via
  `env!("CARGO_BIN_EXE_<name>")` — the idiom `cli/launcher/tests/version.rs:23`
  already uses — plus a local mock HTTP server serves all three test layers.
- **Restriction lints bite new code** — `unwrap_used`/`expect_used`/`panic` are
  deny-level warnings (`cli/Cargo.toml:22-27`). All HTTP/IO/error code must
  propagate `Result` through `kernel::Error`, never unwrap.
- **`match error {}` breaks by design** (`cli/launcher/src/main.rs:18`) the moment
  `kernel::Error` gains a variant — the compiler flags exactly where to handle it.
- **The `version` core + in-memory fake** (`cli/launcher/src/version/core.rs:49-78`)
  is the copy-me pattern for any new port and its fake.
- **cargo-pup constrains only `version::core`** (`cli/pup.ron`); new subdomain
  code is unconstrained unless placed under that module path.

### Decisions settled for this plan (recommended defaults; flagged for review)

These four were open in the work item / research. I proceeded on the recommended
default for each — call out any you want changed:

1. **Release manifest** → a **new `manifest.json`** distinct from
   `checksums.json`, carrying per-binary name/version/sha256/minisign-signature/
   description, added to version coherence. Keeps the launcher's read contract
   clean rather than overloading a checksum file.
2. **Cache directory** → **`${CLAUDE_PLUGIN_ROOT}/bin/` with an XDG fallback**
   (your call). `${CLAUDE_PLUGIN_ROOT}` points at the running plugin version's
   install path, so Claude Code reclaims cached binaries on plugin upgrade. That
   cleanup contract, and that the directory is writable and mounted exec-capable,
   are **load-bearing assumptions the plan must verify at runtime, not infer**:
   read-only/immutable installs (Nix store paths, container layers) and `noexec`
   mounts break write-or-exec. When the plugin root is not writable+exec-capable,
   the launcher falls back to an XDG cache dir (`$XDG_CACHE_HOME/luminosity/` or
   `~/.cache/luminosity/`) and bounds growth there with a small cap on retained
   versions, since the host does not GC it. Distinct from the in-repo
   release-staging `cli/launcher/bin/` (build output); this is the runtime cache
   on the user's machine. The launcher resolves the root at runtime (the
   bootstrap has `${CLAUDE_PLUGIN_ROOT}` and passes it through to the exec'd
   launcher). Resolution stays keyed by name+version+checksum within the chosen
   directory (ADR-0010).
3. **SLSA attestation** → **kept alongside minisign**. ADR-0002 parked in-process
   SLSA *verification*, not the attestation itself; the steps already work and
   are complementary server-side provenance.
4. **minisign key ownership** → **this story owns it** (keypair generated,
   secret stored in the GitHub `release` environment). Switch to a carve-out
   `blocked_by` prerequisite if a separate ops/security owner controls release
   secrets.

5. **Launcher root of trust** → the plugin package ships a **tiny, statically-
   linked `minisign-verify` shim (one per triple) plus the release public
   key(s)**, delivered over the trusted marketplace channel. The bootstrap fetches
   the launcher on demand (preserving ADR-0010's model), then runs the vendored
   shim to **verify the launcher's minisign signature against the committed key
   before exec, failing closed** if verification cannot complete. This is feasible
   where in-bash Ed25519 is not, keeps zero-setup (no host tool required), and
   keeps the package small (the shim is sub-MB pure-Rust; the *large* launcher —
   which carries the reqwest/rustls/tokio/hickory stack — is fetched, not
   vendored). The shim is built, signed, and pinned by the same four-triple
   pipeline as the launcher; its trust basis is the marketplace channel (same as
   the bootstrap script and the public key). It does **not** delegate the
   launcher's integrity to the launcher's own re-verify (a binary cannot verify
   itself). *(This adds a vendored verifier component to ADR-0010's launcher
   distribution — note it as an ADR-0010 consequence to record.)* The bootstrap
   re-verifies on cache-hit too, so a locally-poisoned cached launcher is refused,
   not exec'd.

6. **Signed manifest + version binding** → `manifest.json` is **itself
   minisign-signed** (`manifest.minisig`) and verified in-process against the
   embedded release key before any field is trusted. The per-binary signatures
   authenticate bytes; the manifest signature authenticates *which* asset the
   launcher is steered to. Because a signature proves authenticity but not
   *freshness*, rollback/freeze is blunted by an **explicit, tested
   version-equality check**: after verifying `manifest.minisig`, the launcher
   refuses (named non-zero) a manifest whose `version` ≠ its plugin-derived
   expected version, and the bootstrap pins the launcher/manifest URL to the
   plugin's own `v{version}` tag rather than "latest". The manifest also carries
   `schema_version` (a bare integer); the launcher **asserts it equals a supported
value** — belt-and-braces against a stale cached manifest, since strict
`v{version}` tag-pinning means a launcher only ever reads its own generation's
manifest so version skew is effectively unreachable — and fails
   closed on an unrecognised higher major (lenient only on *additive* unknown
   fields).

7. **Coherence anchors** → `checksums.json` is **kept as checksum-only release
   staging** and `manifest.json` as the launcher's read contract; each has a
   distinct, non-overlapping responsibility. Every version-bearing file the
   single-writer `write()` touches — `plugin.json`, `cli/launcher/Cargo.toml`,
   `checksums.json`, and `manifest.json` — is brought under `version:check` so
   none can drift. A companion **key-coherence assertion** (also wired into `mise
   run check`) confirms the public key(s) committed in the plugin package are
   byte-identical to the key(s) the launcher embeds via `include_str!`, so the
   bootstrap-verifier key and the launcher-embedded key cannot silently diverge.

8. **musl DNS independence** → the launcher uses reqwest's **`hickory-dns`**
   pure-Rust resolver rather than the system `getaddrinfo`, so name resolution
   **bypasses nsswitch/getaddrinfo** — the real musl-static caveat — mirroring the
   webpki-roots decision for certificates. hickory still reads `/etc/resolv.conf`
   for nameservers, so this reduces rather than eliminates host coupling; when
   `resolv.conf` is absent (minimal containers) the launcher surfaces a named
   resolution error rather than silently querying an implicit default.

9. **Test fixtures** → the arg-driven fixture is a **`[[bin]]` inside the
   `launcher` crate**, located from tests via `env!("CARGO_BIN_EXE_<name>")` (the
   idiom `tests/version.rs` already uses). Cargo only sets `CARGO_BIN_EXE_<name>`
   for bins in the package under test, so a separate `testfixtures` crate would
   not resolve on stable — the in-crate `[[bin]]` is the correct mechanism.

## What We're NOT Doing

- **No launcher self-update** (ADR-0010) — a new plugin version drives a new
  launcher via the bootstrap. Within a fixed plugin version the manifest is
  **immutable** (version-pinned), so a cache hit reuses without re-fetching; the
  "re-fetch on manifest-hash change" mechanism applies **across plugin-version
  bumps** (a new version → new pinned manifest → new cache keys), not within one.
- **No `config` subcommand implementation** — that is story 0009. The launcher
  is built to accommodate a second built-in but `config` is not added here.
- **No product sub-binaries** — external dispatch is proven entirely against the
  in-launcher-crate test fixture `[[bin]]`; `version` remains the only real
  subcommand. (The vendored `minisign-verify` shim is a **tooling** artifact for
  the bootstrap's root-of-trust check, not a product sub-binary — a new tiny crate
  kept minimal so it does not pull the launcher's heavy dependency closure.)
- **No Windows** — all four targets are Unix; exec-only.
- **No in-process Sigstore/SLSA verification** — parked by ADR-0002.
- **No `cross` fallback** — the launcher is pure Rust + rustls; cargo-zigbuild
  alone covers all four triples.
- **No new subdomain crates** — the deny/pup cross-crate ban-lists stay inert;
  activating them is 0009/0012. The `minisign-verify` shim crate is **tooling,
  not a subdomain**, so it does not trip the architectural layering rules (which
  target subdomain-to-subdomain imports); confirm the ban-lists ignore it rather
  than mistaking its addition for the workspace split.

## Implementation Approach

Six phases, each independently mergeable and leaving `mise run` green. They map
to the two internally-tracked sub-deliverables the work item allows:
**distribution** (Phases 1–2, Python + CI) and **launcher** (Phases 3–6, Rust +
shell). Distribution and launcher are largely independent; the only cross-edge is
the `manifest.json` schema (Phase 2) that resolution (Phase 4) and help (Phase 5)
read, so the linear order is safe.

TDD throughout: red (failing test) → green (minimum code) → refactor. The fixture
crate is treated as test infrastructure — scaffolded first, then the failing
dispatch/resolution tests are written against it. Hexagon discipline: resolution
is a driven port with a fake adapter (Phase 3) before the real fetch/verify/cache
adapter (Phase 4), so dispatch/exec merge without the network stack.

---

## Phase 1: Four-triple cross-compile via cargo-zigbuild + artifact staging

### Overview

Produce all four fully static triples from one host with cargo-zigbuild, stage
them where the publish flow expects, and seed the checksum file so version tasks
stop raising. The existing host-native `build:launcher` guard is retained as the
fast native static-link canary; a new release build does the four-triple work.

### Changes Required

#### 1. Provision zig + cargo-zigbuild, pinned

**File**: `tasks/deps.py`, `mise.toml`

Add `deps:install:zigbuild` (mirroring `install_rust_targets`) verifying the
`ziglang` / `cargo-zigbuild` build-group deps are importable and rustup targets
present. They are already in `pyproject.toml:16-17`; pin exact versions there and
assert coherence in `tests/unit/tasks/test_mise_wiring.py` alongside the existing
pins.

#### 2. Four-triple release build

**File**: `tasks/build.py`, `tasks/shared/paths.py`

Add a `build.release` task iterating **all** of `TARGETS` (not `host_targets`)
via `cargo zigbuild --release --bin luminosity --target {triple}`, then for each:
copy `target/{triple}/release/luminosity` → `binary_path(platform)`
(`cli/launcher/bin/luminosity-{platform}`), create the `.debug.tar.gz` archive
(`debug_archive_path`), and write `sha256:<hex>` into `checksums.json["binaries"]`
via `compute_sha256`. `build:launcher` (host-native, native `file`/`ldd`/`lipo`
verification) is untouched — it stays the local + CI static-link canary. (The
per-triple `minisign-verify` **shim** — Phase 6's bootstrap root-of-trust
verifier, decision 5 — is cross-built the same way, but its crate, build step,
tests, and packaging all land in Phase 6 so Phase 1 stays independently
mergeable.)

```python
@task
def release(context: Context) -> None:
    """Cross-build all four shipped triples from one host via cargo-zigbuild."""
    with context.cd(str(WORKSPACE_ROOT)):
        for triple, platform in TARGETS:
            result = context.run(
                f"cargo zigbuild --release --bin {LAUNCHER_CRATE} "
                f"--target {triple}",
                warn=True, pty=False,
            )
            if result.exited != 0:
                raise Exit(f"release build failed: {triple}", code=1)
            _verify_output(context, triple)
            _stage_artifacts(context, triple, platform)
    _write_checksums(...)
```

`_verify_output` is made **host-aware** — it branches on `(build-host,
target-family)`, not the target triple alone, modelled as an explicit
strategy mapping rather than nested `if`s. On macOS it uses `lipo -archs` +
`otool -L`. On a Linux build host the two darwin binaries are verified with **`llvm-objdump`
`--macho`** from the provisioned `llvm-tools-preview` (which travels with the
pinned toolchain, so verification is host-independent rather than dependent on
the build distro's `file`/libmagic): `llvm-objdump --macho` reports the arch and
`llvm-objdump --macho --dylibs-used` confirms **only system libraries are
linked** — so the cross-built darwin binaries get a real linkage guarantee on the
very host that produces them, not just an arch string. (`llvm-objdump` is in the
`llvm-tools-preview` inventory; `llvm-lipo`/`llvm-otool` are *not*, so relying on
them would silently require a full LLVM install — the phase pins the concrete
tool inventory it depends on.) The macOS `build-launcher` leg still
build- and execution-verifies its host darwin triple. All four are
build-verified (arch **and** linkage); runtime criteria are execution-verified
on host triples (AC1's explicit allowance).

The darwin cross-builds set an explicit minimum `MACOSX_DEPLOYMENT_TARGET` so
the artifacts' supported macOS range is a conscious, reproducible choice rather
than an implicit host-toolchain default; the supported range is recorded
alongside the target map.

#### 3. Seed the checksum file and wire the release prepare tasks

**File**: `cli/launcher/bin/checksums.json` (new), `tasks/release.py`

Commit a seed `checksums.json` (`{"version": "<current>", "binaries": {}}`) so
`version:write` stops raising `FileNotFoundError`. Call `build.release` from
`prerelease_prepare`/`release_prepare` (`tasks/release.py:32-57`), which today
only bump the version despite `mise.toml:285/294` claiming they build.

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:tasks` passes (new `build.release` / staging / checksum
      unit tests, mocked `context.run`, per `tests/unit/tasks/test_build.py`).
- [x] `mise run build-system:check` passes (ruff + pyrefly strict + actionlint).
- [x] `mise run version:write -- 0.1.0-pre.1` no longer raises and rewrites all
      three anchors coherently.
- [x] `mise run build:launcher` still passes (host-native canary unchanged).
- [x] `mise run` (bare default) exits 0.

#### Manual Verification

- [x] On one host, `mise run build.release` produces four
      `cli/launcher/bin/luminosity-{platform}` + four `.debug.tar.gz` +
      populated `checksums.json`.
- [x] `file`/`ldd` on the two musl binaries confirm "statically linked" / "not a
      dynamic executable"; on macOS `otool -L` on the host darwin binary lists
      only system libraries.

---

## Phase 2: minisign signing + release manifest + version-coherence check

### Overview

Add the load-bearing middle: sign each artifact with minisign, emit the
`manifest.json` the launcher reads, and enforce version coherence with a check
task. Local `mise run` stays green because signing runs only in the CI
prepare/publish path; unit tests use a fixture keypair.

### Changes Required

#### 1. Provision the minisign signing tool + keypair

**File**: `mise.toml`, `tasks/deps.py`, GitHub `release` environment secret

Pin the `minisign` CLI (jedisct1) via the mise `aqua` backend (as
`cargo-deny`/`nextest` are). Generate the release keypair once; store the secret
key as a `release`-environment secret (`MINISIGN_SECRET_KEY` +
`MINISIGN_KEY_PASSWORD`); commit the **public** key. Document as standing
operational responsibilities in `CONTRIBUTING.md` (AC9): `.minisig` publishing;
**key rotation** using the verify-any-of overlap window (add the new key, ship a
plugin release trusting both, then drop the old) with the window **bounded**; the
**compromise response** — because there is no launcher self-update, revoking a
leaked key requires cutting a plugin release that drops it, so exposure lasts
until users upgrade; and a **bundled-roots refresh cadence** — bumping
`webpki-roots` on each release cut so the frozen Mozilla root snapshot cannot go
stale against GitHub's TLS chain under no-self-update; and the **vendored shim**
(its `minisign-verify` pin) as a trusted, no-self-update component with its own
refresh/compromise procedure — a shim-side verification flaw likewise persists
until users upgrade the plugin.

#### 2. Sign artifacts and build the manifest

**File**: `tasks/sign.py` (new), `tasks/build.py`, `tasks/shared/paths.py`

After the four-triple build, sign each binary (`minisign -S`) producing
`luminosity-{platform}.minisig`, and write `manifest.json`:

The manifest is **keyed by binary name, with a per-platform inner map**, so it
expresses both the launcher itself and future on-demand sub-binaries (each
resolved *by name*, each with its own per-platform checksum/signature and a
`description` for the synthesised help — AC6). A platform-keyed shape could not
list `foo`/`bar` each with its own description, so the name-keyed shape is the
contract:

```json
{
  "schema_version": 1,
  "version": "0.1.0-pre.1",
  "binaries": {
    "luminosity": {
      "description": "The luminosity launcher",
      "platforms": {
        "darwin-arm64": {
          "sha256": "<hex>",
          "signature": "untrusted comment: ...\n<base64>\ntrusted comment: ...\n<base64>"
        }
      }
    }
  }
}
```

The field shapes are **pinned** as the publisher↔launcher contract: `sha256` is
the bare lowercase hex digest (no `sha256:` prefix — distinct from
`checksums.json`'s prefixed form, which the launcher never reads); the release is
tagged `v{version}` and the launcher constructs the manifest/asset URL with that
`v` prefix. A **round-trip test** consumes a shared fixture manifest — covering
both the launcher entry and a synthetic sub-binary entry (`foo`/`"Bar tool"`) —
in both the Python writer suite and the Rust reader suite so the two cannot
silently diverge.

The `signature` field is **derived from the emitted `.minisig` file** (one
generation point, read back into the manifest) so the inline copy and the
detached asset cannot drift; the launcher reads the inline copy, the detached
`.minisig` is a publish-side convenience asset.

`manifest.json` is **itself signed** — after the manifest is written, sign it
to produce `manifest.minisig` (decision 6), so the launcher can verify the
manifest against the embedded key before trusting any field. Add `schema_version`
(bare integer, per the `meta/` convention) to the manifest so the read contract
can evolve; the launcher deserialises **leniently** (unknown fields ignored) to
stay forward-compatible under "no launcher self-update".

Seed a committed `manifest.json` (`{"schema_version": 1, "version":
"<current>", "binaries": {}}`) exactly as Phase 1 seeds `checksums.json`, so
adding it to the single-writer `write()` (below) does not raise
`FileNotFoundError` on a fresh tree; `write()`/`version:check` tolerate an empty
`binaries` map.

**Signature-generation isolation (CI):** signing runs in a **minimal, separate
job** that receives only the built artifacts + the release secret and runs **no
crate compilation** — the four-triple cargo-zigbuild step (which compiles and
runs untrusted third-party `build.rs`/proc-macro code) never shares an
environment with `MINISIGN_SECRET_KEY`, so a compromised build dependency cannot
exfiltrate the signing key.

#### 3. Version-coherence check task

**File**: `tasks/version.py`, `mise.toml`

Add `manifest.json` to `version.py`'s single-writer `write()` (`:71-80`) and a
new **`version:check`** task that reads **every version-bearing file the writer
touches** — `plugin.json`, `cli/launcher/Cargo.toml`, `checksums.json`, and
`manifest.json` (decision 7) — and exits non-zero **naming the mismatching
files** when they disagree, proceeding silently when they agree (AC8). Wire it
into `mise run check`.

`version:check` is **also invoked as a fail-closed precondition inside the
release orchestration** (`release_prepare`/`_publish`, before `create_release`/
`upload_and_verify`), not only in the PR-time `mise run check`. AC8 requires the
*release pipeline* to enforce coherence, so a release cut with desynced anchors
outside a normal PR (a manual edit, a partial bump) is blocked on the publish
path itself.

#### 4. Upload signatures + manifest

**File**: `tasks/github.py`

Extend `upload_and_verify` (`:135-177`) to upload each `.minisig`,
`manifest.json`, and `manifest.minisig` alongside the binary + debug archive.
The re-download-and-verify step is extended beyond sha256 to **verify each
re-downloaded binary's minisign signature against the committed release public
key — the same bytes the launcher embeds** — and to verify `manifest.minisig`,
failing the publish **before** un-drafting if any asset does not verify. This
closes the loop that the key the launcher trusts actually validates the shipped
artifacts, so a key mismatch (committed public key ≠ signing secret) is caught
at publish time rather than fail-opening into universal refusal at every user's
first run. **Every** new verification failure mode — a signature/manifest mismatch **and**
any tool-invocation failure (`FileNotFoundError` for an absent minisign,
`subprocess.TimeoutExpired`, a non-zero exit for any reason) — is wrapped into
`AssetVerificationError` (the existing **preserve draft + tag for triage** path,
`github.py:164-170`), so no transient tooling hiccup can fall into the generic
`except Exception` branch that runs `gh release delete --cleanup-tag` and destroys
the pushed tag. A test stubbing an absent/failing minisign asserts the draft+tag
survive. Keep SLSA attestation in CI
(decision 3).

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:tasks` passes (sign/manifest/`version:check` unit tests
      using a fixture keypair; a desync test asserts the **specific mismatching
      filename(s)** appear in the output, not merely a non-zero exit; agreement →
      ok; a signed-manifest round-trip; the shared-fixture manifest parses in the
      Rust reader). *(Rust reader consumes the shared fixture in Phase 4; the
      Python writer side of the round-trip is asserted here.)*
- [x] `mise run build-system:check` passes.
- [x] `mise run version:check` exits 0 on a coherent tree and non-zero naming the
      desynced file when any of the four anchors (`plugin.json`,
      `cli/launcher/Cargo.toml`, `checksums.json`, `manifest.json`) is hand-desynced
      in a test; a **key-coherence** test fails when the plugin-committed key
      diverges from the launcher-embedded key.
- [x] `test_github.py` asserts a re-downloaded artifact signed by a **non-matching
      key** makes `upload_and_verify` raise `AssetVerificationError` and **leave
      the release drafted** (un-draft not called, tag preserved).
- [x] `test_release.py` asserts `release_prepare`/`_publish` invokes `version:check`
      and **aborts before `create_release`/`upload_and_verify`** when an anchor is
      hand-desynced.
- [x] `mise run` exits 0.

#### Manual Verification

- [x] With the fixture key, the pipeline emits four binary `.minisig` files, a
      `manifest.json`, and a `manifest.minisig`; `minisign -Vm <binary> -P
      <pubkey>` verifies each binary and `minisign -Vm manifest.json -P <pubkey>`
      verifies the manifest. *(Verified locally with the placeholder keypair.)*
- [ ] The GitHub `release` environment holds the secret; the committed public key
      matches it (the automated re-download step verifies this, not only manual
      inspection). *(BLOCKED — operational: the committed key is a placeholder;
      the real keypair must be generated and `MINISIGN_SECRET_KEY` /
      `MINISIGN_KEY_PASSWORD` provisioned as GitHub secrets. See CONTRIBUTING.md.)*

---

## Phase 3: Launcher dependencies, kernel error taxonomy, external dispatch + exec

### Overview

Populate the empty Rust seams: add the HTTP/verification dependency stack, give
`kernel::Error` real variants, add the `External(Vec<OsString>)` arm, and prove
dispatch + exec (exit/signal propagation) against a new fixture crate — all
without the network, behind a driven resolution port with a fake adapter.

### Changes Required

#### 1. Dependency stack (the rustls trap)

**File**: `cli/Cargo.toml`, `cli/launcher/Cargo.toml`

Add to `[workspace.dependencies]`, consumed by `launcher` via `workspace = true`
(kernel stays light):

```toml
reqwest = { version = "<pin>", default-features = false, features = ["rustls-tls-webpki-roots-no-provider", "blocking", "hickory-dns"] }
rustls = { version = "<pin>", default-features = false, features = ["ring"] }
minisign-verify = "0.2.5"
sha2 = "<pin>"
```

`default-features = false` is mandatory — a default-feature reqwest pulls
native-tls → openssl-sys and trips `deny.toml`. The TLS root source is the
**bundled webpki-roots** variant, so the static binary carries its own roots and
does not read the host cert store (AC7) or pull
`rustls-native-certs`/`security-framework` on the darwin cross-builds.
`hickory-dns` makes name resolution bypass the host `getaddrinfo`/nsswitch
(decision 8).

**Crypto provider — `ring`, selected explicitly.** reqwest/rustls 0.23+ default
to `aws-lc-rs` (C + per-arch assembly, awkward to cross-compile and a native-C
build step — a direct threat to the four-triple cargo-zigbuild matrix). Merely
naming `ring` is not enough: the plain `rustls-tls-*` reqwest features pull the
default provider, so the launcher uses the **`-no-provider` reqwest feature**
plus a direct `rustls` dep with `features = ["ring"]`, and installs the ring
provider once at startup via `CryptoProvider::install_default(...)` — a **fallible
call mapped into `kernel::Error`**, never `.unwrap()` (restriction lints). The
`cargo tree -e features` regression asserts `ring` is present and `aws-lc-rs`
absent, alongside the native-tls/native-cert assertions; a startup test asserts a
TLS request succeeds (proving the provider is actually installed). The license
closures of the new deps (`hickory-dns` + its `hickory-proto`/`-resolver` tail,
`sha2`, `minisign-verify`) are verified against `cli/deny.toml`'s allow-list up
front — extending the allow-list or adding `[[licenses.exceptions]]` in this
phase rather than discovering a `deny:check` failure mid-implementation.

The launcher uses **blocking** reqwest, whose `blocking` feature manages its own
internal runtime — so **no direct `tokio` dependency is declared** (and certainly
not the `macros`/async-entrypoint feature). If a transitive `tokio` surfaces via
reqwest it is not a first-party dep. `cargo tree` asserts (in the deny regression
test) that neither `native-tls`/`openssl-sys` nor a native-cert crate enters the
launcher tree.

**Version safety is enforced, not asserted informally.** Versions are **pinned**
in `[workspace.dependencies]` (exact/caret per the existing vergen-style
convention) and `rust-version = "1.90.0"` is added to the version-bearing
`cli/launcher/Cargo.toml`. For that `rust-version` to actually drive **MSRV-aware
version selection** the workspace must be bumped to **`resolver = "3"`** (cargo
1.84+; the current `resolver = "2"` ignores `rust-version` at resolution) — do
that here. As a belt-and-braces guard a **CI leg builds/tests on the pinned
MSRV** so an MSRV-breaking transitive bump (the reqwest/rustls closure moves
fast) fails loudly in CI rather than at a user's first fetch; its required-check
registration is load-bearing. `cli/clippy.toml`'s `msrv` governs only lints, so
it is not sufficient alone.

#### 2. Populate `kernel::Error`

**File**: `cli/kernel/src/lib.rs`

`kernel::Error` is the **cross-cutting** contract, so keep it **small and
genuinely shared** rather than dumping every subdomain's private failures into
it: the launcher-resolution failure taxonomy (fetch/network, checksum mismatch,
signature mismatch, asset-not-found, release-unavailable, IO/cache, exec) lives
in a **launcher-local resolution error** that **maps into a small `kernel::Error`
at the boundary**. This keeps the `version` subdomain from compiling against
fetch/signature variants it can never produce, and stops `config` (0009) and
later subdomains from each having to edit the kernel.

Each variant **carries the payload its diagnostic needs** — the ACs require
diagnostics that name the missing target and distinguish mismatches, so:
target-triple + URL on fetch/asset-not-found/release-unavailable; expected vs
actual sha256 on checksum mismatch; asset name (and key context) on signature
mismatch; path on IO/cache. Keep the kernel dependency-light (std only). Populating
the error makes `main.rs:18`'s `match error {}` fail to compile — replace it with
real handling that prints the diagnostic to stderr and returns a non-zero
`ExitCode` (AC4 "exits non-zero with a diagnostic").

#### 3. External-subcommand dispatch

**File**: `cli/launcher/src/version/inbound/cli.rs` (or a new dispatch module)

Add the arm and prove clap's derive enables it on the pinned clap 4.6.1:

```rust
#[derive(Subcommand)]
pub enum Command {
    Version,
    #[command(external_subcommand)]
    External(Vec<std::ffi::OsString>),
}
```

A test parsing `["luminosity", "frobnicate", "--flag"]` must reach the `External`
arm with `["frobnicate", "--flag"]` (AC5 routing). *(This retires the spike's one
to-confirm consequence.)*

Dispatch **moves into a dedicated launcher-level `dispatch`/`launch` module** (a
first-class Phase 3 deliverable, not an optional consideration): it owns
`External` routing, the `ResolveBinary` port, exec, and (Phase 5) help
synthesis. `version/inbound/cli.rs` is left responsible for the `version`
command only, so the `version` hexagon stays clean and no launcher code sits
under `version::core` (which cargo-pup would reject). This module is the
launcher's imperative shell — an explicit, named boundary with an inward-only
dependency direction.

#### 4. Fixture crate + exec

**File**: `cli/launcher/Cargo.toml` (a `[[bin]]` entry), fixture bin source, exec
impl

One arg-driven fixture **`[[bin]]` declared inside the `launcher` crate**
(decision 9) exposing behaviours by argument: `exit-42`, `block-on-sigterm`,
`print-help-sentinel`. It is located from tests via `env!("CARGO_BIN_EXE_<name>")`
— which cargo sets only for bins in the package under test, so the fixture must
live in the launcher crate, **not** a separate `testfixtures` crate (that env var
is not set cross-crate on stable). Implement exec with
`std::os::unix::process::CommandExt::exec` (process-replacing).

Because `exec` **replaces the current process**, the exit/signal-propagation
tests must be **black-box tests that spawn `CARGO_BIN_EXE_luminosity` as a
child** (as `tests/version.rs` already does) — never in-process, which would
replace the test runner. Tests: a fixture exiting 42 → `luminosity <sub>` exits
42; a fixture killed by SIGTERM → caller's `$?` = 143 (AC5). The SIGTERM test
uses a **readiness handshake** — `block-on-sigterm` prints a sentinel line before
blocking and the test waits for that line before signalling — rather than a
timing assumption, so it is not racy. In Phase 3 the resolver is a **fake
adapter** returning the fixture's path directly (no fetch).

**Fixture lint/coverage scoping (settled):** the fixture bin is **not** opted
into `[workspace.lints]` (a stub calling `process::exit` trips `clippy::exit`
under the restriction lints) and is **excluded from `cargo llvm-cov nextest`
coverage**. This is a deliberate, bounded exception to CLAUDE.md's "tests held to
the same standard" stance for test scaffolding — recorded here so the exemption
is a conscious decision, not an oversight, and consciously supersedes the
research's separate-crate preference (which the cross-crate `CARGO_BIN_EXE`
constraint rules out). It is named unambiguously as a fixture, and the release
build/packaging (Phase 1's `build.release` → `cli/launcher/bin/`) stages **only
the `luminosity` binary**, so the fixture never enters a shipped artifact even
though a plain `cargo build` compiles it.

#### 5. Resolution port

**File**: launcher subdomain module

Define the driven port `trait ResolveBinary { fn resolve(&self, name, args) ->
Result<PathBuf, kernel::Error> }` with a fake adapter (returns a cached fixture
path). The real adapter lands in Phase 4. This keeps Phase 3 mergeable.

Extend `cli/pup.ron` with a `*_core_imports_only_permitted` rule for the new
resolution core module path (analogous to the existing `version::core` rule), so
the new hexagon core gets the same **automated** inward-dependency guarantee
rather than resting on review discipline — cargo-pup is ADR-0009's sole
inward-direction enforcer, and an unconstrained core could let I/O or adapter
code leak inward silently.

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:cli` passes (dispatch routing to `External`; a
      **non-UTF-8 `OsString` argument routed through `External` survives verbatim
      to the exec'd child** — the reason `Vec<OsString>` was chosen over
      `Vec<String>`; exec exit-42 + SIGTERM-143 against fixtures; kernel error
      unit coverage).
- [x] `mise run cli:check` passes (rustfmt + clippy pedantic/nursery/restriction,
      -D warnings).
- [x] `mise run deny:check` passes — **the rustls trap is not sprung**;
      `cargo tree -e features -p luminosity` shows no `openssl-sys`/`native-tls`
      (a parametrised deny regression test asserts the whole native-tls/native-
      cert/aws-lc closure is absent and `ring` is present).
- [x] `mise run pup:check` passes (no launcher code under `version::core`; the
      new `launch::core` gets its own inward-only rule).
- [x] `mise run` exits 0.

#### Manual Verification

- [x] `cargo tree -e features -p luminosity` visibly resolves reqwest with
      rustls only. *(Verified; also asserted by the deny regression test.)*
- [x] `luminosity frobnicate` (fake-resolved to the fixture) propagates a
      non-zero exit and SIGTERM as expected. *(Proven by the black-box
      exit-42 / SIGTERM-143 dispatch tests.)*

---

## Phase 4: Launcher resolution — fetch → verify → cache (hermetic)

### Overview

Implement the real driven adapters: reqwest fetch, sha256 + in-process minisign
verification (against the embedded public key), cache write keyed by
name+version+checksum, and resolve-once-and-cache scan. All tests hermetic
against a local mock HTTP server + a test keypair (plus a second non-release key).

### Changes Required

#### 1. Embed the release public key + verify in-process

**File**: launcher outbound adapter

`include_str!` the committed release public key(s). Support a **small set of
trusted keys** (verify-any-of) rather than a single hard-coded key, so key
rotation has an overlap window (old + new both trusted) instead of a hard cutover
after a compromise; the concrete rotation/compromise-response procedure is
documented in `CONTRIBUTING.md` (AC9), not only noted.

The **minisign signature is the security boundary; sha256 is a corruption
check.** Both the cached binary and any cached manifest live in the user-writable
cache dir, so a local writer could poison the binary *and* its matching
checksum — a sha256-only re-check would pass. Therefore verify the `.minisig`
with `minisign-verify` against the trusted keys **before every exec, including
cache hits** (not only on fetch), and re-check sha256 alongside for corruption
(AC2, AC4). First verify the **manifest** signature (`manifest.minisig`) against
the trusted keys before trusting any of its fields (decision 6). A valid sha256
with a signature made by a **non-release key** must be refused (AC4 — proves
key-bound, not TLS-bound).

#### 2. Fetch + cache adapters

**File**: launcher outbound adapters

The resolution adapter is **composed of small, separately-testable
collaborators** rather than one monolith — a `Fetcher` (transport + retry + URL
policy), a `Verifier` (manifest signature + version binding, then per-binary
sha256 + minisign), a `CacheStore` (atomic write, lock, scan, evict), and a
`CacheRootResolver` (plugin-root vs XDG fallback + growth cap) — each behind its
own small interface so the adapter orchestrates them and each is unit-testable in
isolation.

**Fetcher.** Blocking reqwest (rustls/`ring` + hickory-dns) fetch of the
host-triple asset. It sets a **connect timeout plus a read/idle (per-chunk stall)
timeout and an aggregate resolution deadline** — not a single fixed
total-request timeout, which would false-fail a large binary on a slow-but-
progressing link — and does **bounded retry-with-backoff** on transient/5xx
failures (safe because resolution is idempotent, keyed by name+version+checksum),
so a hung endpoint surfaces as the same named fetch error rather than hanging the
invoking Claude Code command. It **pins the `https` scheme** and follows
redirects only to a **`*.githubusercontent.com` host-suffix allowlist** (plus the
GitHub release origin), since GitHub 302-redirects asset downloads to rotating
CDN hosts under that suffix; a strict same-origin or exact-host pin would reject
real downloads and — since there is **no launcher self-update** — a future CDN
host rename would brick every deployed launcher. The suffix match tolerates that
rotation. A redirect off that suffix is refused (the binary is still
signature-gated, so this is defence in depth, not the security boundary). The host-triple→platform-alias map is **single-sourced
from `TARGETS`** in `tasks/shared/targets.py` (launcher + bootstrap tables
generated from it, or asserted equal by a cross-language coherence test), so the
asset-naming contract cannot drift across publisher, launcher, and bootstrap.

**Manifest provenance (Verifier).** The manifest is a **signed release asset**
(Phase 2). On a cache **miss** the launcher fetches the manifest for its
plugin-pinned `v{version}` release, **verifies `manifest.minisig` and the
`version`-equality binding** (decision 6) before trusting any field, resolves the
requested binary by name, and **caches the verified manifest alongside** the
binary. On a cache **hit** it reuses the cached binary+manifest **without
re-fetching** — so an already-resolved sub-binary works **offline** (reconciling
AC3's cache-reuse with AC4: a manifest/network failure only reaches AC4 on a
cache miss; there is no offline resolution of a *never-fetched* binary, per the
ADR-0002 caveat). Deserialise the manifest **leniently** for additive unknown
fields, but **assert `schema_version`** is supported and fail closed on an
unrecognised higher major.

**CacheStore.** Writes are **atomic and self-healing**: fetch into a unique temp
file **created inside the resolved cache directory** (so the `rename(2)` is always
intra-filesystem — a temp file in a different mount would fail `EXDEV`, and a
copy-fallback would reintroduce torn files), verify sha256 + minisign there, then
**atomically rename** into the name+version+checksum cache name, so only
fully-verified bytes ever appear under the final path. It also **caps download
size and checks free space** before the streamed write (the expected size is known
from the manifest), so an oversized/slow-drip response cannot exhaust the cache
filesystem. Concurrency is guarded by an **OS-level advisory lock**
(`flock`/`fcntl`), **per cache key** (not one cache-wide lock, so unrelated
sub-binaries never serialise) and **scoped to the fetch/verify/rename critical
section**: the lock fd is `FD_CLOEXEC`/explicitly closed **before `exec`**, so it
never spans the exec'd child's lifetime (an flock survives `execve` otherwise, and
a long-running child would wedge peers). On acquiring the lock — and on an
acquisition **timeout** (≥ the aggregate resolution deadline) — the resolver
**re-scans** and reuses a valid entry a peer just populated before fetching or
degrading to a named error, so concurrent first-use blocks-then-reuses rather than
spuriously failing; auto-release on process exit means a crash mid-fetch cannot
wedge later invocations. On a **cache-hit verification failure** the orchestrator
evicts (via CacheStore) and re-fetches once (via Fetcher) then re-verifies —
recovery is the orchestrator's, keeping CacheStore's remit to primitive
write/lock/scan/evict. Scan-first resolve-once-and-cache (AC3). Real
`ResolveBinary` adapter replaces Phase 3's fake.

**CacheRootResolver.** The cache root is a driven port input, so tests inject a
temp dir. A missing/unset `CLAUDE_PLUGIN_ROOT` is a named non-zero error. When
the plugin root is **not writable+exec-capable** (probed, not inferred), the
launcher falls back to `$XDG_CACHE_HOME/luminosity/` → `~/.cache/luminosity/`
(`~/Library/Caches/luminosity/` on darwin), **probing the fallback dir for
exec-capability too** (hardened hosts mount home/tmp `noexec`); a
`LUMINOSITY_CACHE_DIR` override gives operators on unusual mounts an explicit
terminus, and if nothing is resolvable the launcher emits a named error (no
undefined terminus). The XDG dir is not host-GC'd, so growth is bounded by a
retained-versions cap; eviction runs **under the same per-key advisory lock**,
removes the **oldest by mtime**, and skips any entry currently locked/in-flight or
being resolved, running only after the target is successfully staged — so a peer's
in-use entry is never unlinked from under it.

#### 3. Failure paths

**File**: launcher

Unreachable host (network error), Release lacking the host-triple asset (no
asset), missing Release (unavailable) → exit non-zero with a diagnostic naming
the missing target; never exec a stale/wrong binary (AC4).

There is an inherent time-of-check-to-time-of-use window between hashing/verifying
the cached file and the kernel loading it for `exec`. The cache dir is user-owned
(same trust boundary as the caller), so the practical risk is bounded and the
window is **acknowledged rather than mandated away** — an fd-based verify-and-exec
(`fexecve`) would close it but is not portable across both target families
(`/proc/self/fd` is absent on darwin), so it is not required here. Atomic writes
plus the pre-exec re-verify keep the invariant strong for the realistic threat.

#### 4. Hermetic test harness

**File**: launcher tests, dev-dependencies

Local mock HTTP server serving fixture bytes; failure cases induced by pointing
the launcher's URL at it (404 / absent asset / connection refused). Test minisign
keypair generated in the fixture + a second non-release key. **Dev-dep vs the TLS
ban (the main trap):** cargo-deny scans dev-deps too, so the mock server /
signing dev-deps must be rustls-only / TLS-free, or set `exclude-dev`
deliberately in `deny.toml`. Recommend rustls-only test deps to keep the ban
maximally strict; call it out at review.

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:cli` passes: fetch→verify→cache→exec happy path;
      **cache reuse asserts the mock server received exactly one request across
      two invocations** (not merely that both succeed — proving no re-fetch, AC3);
      **a cached valid signed binary mutated on disk is refused on re-invocation
      with no exec** (the pre-exec re-verify, promoted from manual), while a
      **cache-hit verification failure then evicts and re-fetches a clean copy and
      execs it** (the self-healing path); checksum mismatch refused;
      non-release-key signature refused; tampered-manifest signature refused; a
      **validly-signed but wrong-`version` manifest refused** (anti-rollback);
      **`5xx-then-200` recovers in a single successful resolve and persistent-5xx
      gives up after the bounded attempts** (asserting the attempt count); a
      **cross-host redirect to the allowed CDN host succeeds and a redirect to a
      disallowed host is refused**; **cache-root branches** — unset
      `CLAUDE_PLUGIN_ROOT` → named error, a read-only/noexec injected root → XDG
      fallback, exceeding the retained-versions cap evicts the oldest;
      unreachable/no-asset/unavailable each exit non-zero with a target-naming
      diagnostic and no exec; an offline cache-hit still resolves and execs.
- [x] `mise run deny:check` passes (dev-deps do not spring the native-tls ban).
- [x] `mise run cli:check` passes.
- [x] `mise run` exits 0.

#### Manual Verification

- [x] Against the mock server, a first invocation fetches+caches and a second
      reuses the cache (observable via server hit count / cache mtime).
- [x] Interrupting a fetch mid-download leaves no file at the final cache name
      (atomic rename), and a later invocation fetches cleanly.

---

## Phase 5: Discoverable surface — manifest-driven help + `--help` delegation

### Overview

Make the surface discoverable despite external subcommands being absent until
fetched: render clap's built-in help plus a synthesised external-subcommands
section from the manifest's `description` field, and delegate per-command
`--help` by re-exec'ing the child.

### Changes Required

#### 1. Synthesised help

**File**: launcher

`luminosity --help` renders clap help for built-ins **plus** an "external
subcommands" section built from `manifest.json` `description` entries (no
executing untrusted binaries). A manifest listing `foo` / `"Bar tool"` yields a
line matching both `foo` and `Bar tool` (AC6).

The derive `Cli::parse()` intercepts `--help` and exits before any launcher code
runs, and derive `after_help` takes only a compile-time string — so the
manifest-derived section **cannot** be appended that way. Use the **lazy path**:
`try_parse`, and **only** on `ErrorKind::DisplayHelp` read the manifest and
re-render the augmented help (`Cli::command().after_help(section)`). This must be
lazy, not eager: appending the section *before* parsing would force a
manifest read+verify on **every** invocation, coupling offline built-ins like
`luminosity version` to manifest availability — a regression. Non-help and
built-in invocations therefore never touch the manifest.

Because the manifest is signature-verified before its fields are trusted
(decision 6) the descriptions are key-authenticated, but they are still rendered
to a terminal, so **strip control/escape characters** from manifest-derived
strings before printing (defence against terminal-escape injection).

#### 2. `--help` delegation

**File**: launcher dispatch

`luminosity foo --help` resolves + re-execs the child with `--help`, emitting the
child's own help — verified by a sentinel string only the `print-help-sentinel`
fixture emits (AC6).

### Success Criteria

#### Automated Verification

- [x] `mise run test:unit:cli` passes: `--help` output contains built-ins + a
      manifest-derived `foo`/`Bar tool` line; `foo --help` emits the fixture's
      sentinel; a fixture manifest description containing **control/escape
      sequences** renders sanitised — the raw escape bytes are absent **and** the
      legitimate printable description text still appears (not over-stripped); and
      **`luminosity version` succeeds with no manifest present** (built-ins do not
      depend on the manifest — the lazy help path).
- [x] `mise run cli:check` passes.
- [x] `mise run` exits 0.

#### Manual Verification

- [x] `luminosity --help` reads coherently with the synthesised section beneath
      the built-ins.

---

## Phase 6: `bin/luminosity` entry point + package assembly + real end-to-end smoke

### Overview

Write the `bin/luminosity` entry point — a thin bash bootstrap, named for the
command it fronts, that fetches the launcher binary itself on first use —
document its by-path invocation contract (`${CLAUDE_PLUGIN_ROOT}/bin/luminosity`),
assemble the plugin package (key + shims), and add exactly one CI-gated smoke test
that fetches a real signed asset from a real test release — honouring the true
end-to-end AC without coupling the whole suite to the network.

### Changes Required

#### 1. `bin/luminosity` (the entry point)

**File**: `bin/luminosity` (new)

The entry point is named for the command it fronts: consumers invoke
`${CLAUDE_PLUGIN_ROOT}/bin/luminosity <args>` (see §3), so the path reads as
invoking `luminosity`, not a `bootstrap.sh` implementation detail. It is still a
thin bash bootstrap — it fetches → verifies → execs the real launcher — but the
bootstrap role is now internal to a command-named entry point.

Bash 3.2 (`set -uo pipefail`, `BASH_SOURCE` root resolution, `case` matching; no
associative arrays, `${x,,}`, `mapfile`, etc.). Because the entry point is
**extensionless** (`bin/luminosity`, not `*.sh`), the shell tooling globs must be
extended to cover it explicitly: `scripts/lint-bashisms.sh`, shfmt, and ShellCheck
all target tracked `*.sh` today, so `bin/luminosity` must be added to their file
lists — the bash-3.2 floor matters most on this file. It: validates
`CLAUDE_PLUGIN_ROOT` is set and points at an
existing directory, emitting a **named diagnostic and non-zero exit** matching
the launcher's own fail-safe (not a raw `set -u` unbound-variable message);
detects the host triple → platform alias (explicit `case` arms normalising
`uname -m` — `arm64`/`aarch64`, `x86_64`/`amd64` — and `uname -s`, from the
single-sourced alias map); fetches the launcher binary if absent; **verifies its
minisign signature with the vendored per-triple verify shim against the
plugin-committed key** (decision 5), re-verifying on cache-hit too; caches it; and
execs it forwarding `"$@"` (with `CLAUDE_PLUGIN_ROOT` present in the launcher's
environment so it can resolve the same cache root for sub-binaries).

**Cache root, shared with the launcher.** The bootstrap does **not**
re-implement the writable+exec probe and XDG-fallback chain — that logic is
single-sourced (the launcher owns the authoritative `CacheRootResolver`; the
bootstrap either invokes a `luminosity --print-cache-root`-style resolution or
shares a generated table, guarded by the same cross-language coherence test as
the alias map) so the two can never diverge on cache location. Because the plugin
root may be `noexec`/read-only (decision 2), **both the launcher and the shim are
copied into the resolved writable+exec cache root before execution** — the shim's
bytes arrive over the trusted marketplace channel, so copying is trust-preserving,
and this stops the root-of-trust step from bricking exactly the noexec/read-only
installs the fallback exists for. The shim is invoked **by absolute path** under
the resolved root, never via `PATH` (a `PATH`-planted decoy must not be able to
stand in for the root verifier).

**Launcher cache is atomic and self-healing**, mirroring the launcher's
`CacheStore`: fetch into a temp file in the resolved cache dir, verify, then
atomic-rename into place; on a cache-hit verification failure evict and re-fetch
once before failing closed (re-fetch is safe — the source is signature-gated) — so
an interrupted first download cannot leave a partial launcher that wedges every
later invocation.

**Launcher freshness binding.** So the launcher inherits the manifest's
anti-rollback guarantee (not just authenticity), the bootstrap fetches and
verifies `manifest.minisig` + the `version`-equality check, then requires the
fetched launcher's sha256 to match the manifest's `luminosity` entry **in addition
to** the shim's signature check — closing the replay of an older validly-signed
launcher at the pinned tag.

**Root of trust (critical).** The launcher is the binary that verifies every
sub-binary, so admitting it on sha256-over-TLS alone would collapse the whole
trust model to "served over TLS" — the model ADR-0002 rejects — and "delegate to
the launcher's own re-verify" is incoherent (a tampered launcher cannot verify
itself). The bootstrap therefore verifies the launcher's `.minisig` against the
**plugin-committed public key** before exec using the **vendored per-triple
`minisign-verify` shim** (decision 5), **failing closed** with a named diagnostic
if the shim is unrunnable or verification fails — never silently downgrading to
TLS-only. This path depends on neither the fetched launcher nor a host-installed
minisign tool. sha256 remains a corruption check on top.

**Bootstrap tool + download safety.** Prerequisites are checked explicitly: a
portable sha256 (prefer `shasum -a 256`, fall back to `sha256sum`) and a fetcher
(`curl` or `wget`), with a named error if neither is present. Downloads are
certificate-verified (never `curl -k`/`--no-check-certificate`); all expansions
are quoted; the launcher is exec'd with an argv list, not via a shell string, so
no derived triple/URL value is interpolated into a shell command.

#### 2. The `minisign-verify` shim crate

**File**: `cli/verify/` (new workspace member), `cli/Cargo.toml` members, `tasks/build.py`

The shim is **first-party code**, not free vendoring — `minisign-verify` 0.2.5 is
a *library*, so the shim is a tiny CLI (read pubkey + `.minisig` + target, verify,
exit 0/non-zero) written under the same `-D warnings` + restriction lints as the
rest of the workspace, so its verify path must propagate `Result` (no
`.unwrap()`). It is a **third `cli/` workspace member** (`cli/verify/`) with its
own `[package]` and `rust-version = "1.90.0"`, included in the MSRV CI leg; it is
**tooling, not a subdomain**, so it stays out of the pup layering rules and does
not activate the deny cross-crate ban-lists (confirm they ignore it). Being pure
`minisign-verify` it links statically with no heavy closure.

`build.release` (Phase 1) is extended here to cross-build the shim for all four
triples and stage the per-triple shims into the plugin package. Because the shim
is the **root verifier** and ships as a committed/packaged binary, its provenance
is brought under an automated check analogous to key-coherence (decision 7): CI
**reproducibly rebuilds the shim from its pinned source and asserts byte-identity
with the shipped artifact**, so the opaque blob is provably the pinned source, not
trusted-by-provenance. The shim is not itself minisign-signed (a root of trust
cannot be verified by anything it roots — its trust basis is the marketplace
channel); the byte-identity check is what guards it.

**Tests (the shim is the most trust-critical node, so it is directly tested):**
black-box tests run the compiled shim against a test keypair asserting exit 0 on a
valid signature, non-zero on a tampered payload, and non-zero on a non-release-key
signature; the lint/coverage exemption mirrors the fixture bin's (a CLI stub).

#### 3. Entry-point contract + package assembly

**File**: `bin/luminosity` (path contract), plugin package assembly (key + shims);
`.claude-plugin/plugin.json` reviewed but unchanged for CLI invocation in 0008

`plugin.json` has no field that registers a CLI as an invokable command — it
declares components (`skills`, `agents`, `hooks`, …) as paths under
`${CLAUDE_PLUGIN_ROOT}`. The invocation contract is therefore **by path**: the
entry point lives at a stable, documented location, `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`,
and consuming skills/hooks call it directly — a `SKILL.md` body runs it via the
`!` preprocessor (`` !`${CLAUDE_PLUGIN_ROOT}/bin/luminosity <args>` ``) and hooks
exec the same path. Each such call spawns a fresh process that does the
cache-hit → verify → `exec`; there is no daemon and no global registration. This
story fixes and documents that path contract; the **skills/hooks that consume it
arrive in later stories**, so in 0008 the entry point is built and tested
standalone (nothing in production invokes it yet).

The plugin package also ships the **release public key(s)** and the **four
per-triple `minisign-verify` shims** so both ride the trusted marketplace channel
and are available to the entry point's launcher-signature verification (decision 5)
— the key(s) byte-identical to those the launcher embeds (key-coherence check,
decision 7). The shims are produced and pinned by the same four-triple pipeline as
the launcher (Phase 1/2). (If `plugin.json` later gains no suitable field, the
path contract stands on its own; no `bin`/`commands` schema entry is required for
0008.)

#### 4. Real end-to-end smoke (CI-gated)

**File**: launcher tests or a dedicated CI job

One test fetching a real signed asset from a real test release, gated so the
normal suite stays hermetic. The test release and its signing key are
**provisioned by the pipeline itself** (not hand-maintained), so it refreshes
with the manifest/asset schema and cannot drift into false failures. Because it
depends on the network, it runs **out-of-band** (scheduled / on release) rather
than as a merge-blocking required check, so transient GitHub/network issues never
block merges; the hermetic suite is what gates PRs. If a new CI job *is* made a
required check, register it per the `CONTRIBUTING.md` runbook (a manual
repo-settings action — an unregistered job silently fails to gate merges).

### Success Criteria

#### Automated Verification

- [ ] `mise run scripts:check` passes (shfmt + ShellCheck + bashisms) **with the
      extensionless `bin/luminosity` added to each tool's target list** — a test
      asserts `bin/luminosity` is actually covered, so it cannot silently escape
      the bash-3.2 floor.
- [ ] `bash scripts/test-luminosity-entrypoint.sh` (new standalone suite, per the
      shell test convention) passes **hermetically**: the fetch is stubbed via an overridable
      downloader (or a pre-seeded cache dir) so no case hits the network, covering
      host-triple detection + arch normalisation, cache-present short-circuit (no
      fetch), **a pre-seeded but tampered cached launcher is refused with the
      fail-closed named error (cache-hit re-verify, not exec'd)**, a
      launcher-signature-verification failure → fail-closed named error, the
      **verify shim being unrunnable → fail-closed named error** (not a silent
      TLS-only downgrade), a **read-only/noexec injected plugin root** → shim and
      launcher are copied to the writable+exec fallback and still run, a
      **`PATH`-planted decoy named like the shim is not used** (absolute-path
      invocation), unset/invalid `CLAUDE_PLUGIN_ROOT` → named error, and
      argument/exit-code forwarding; the **shim black-box tests** (valid/tampered/
      wrong-key exit codes) run against the real compiled shim.
- [ ] `mise run` exits 0.
- [ ] The gated e2e smoke passes in CI against a real test release.

#### Manual Verification

- [ ] On a clean machine with no cached binary, invoking
      `${CLAUDE_PLUGIN_ROOT}/bin/luminosity version` fetches, verifies, caches, and
      runs the launcher's `version` output.
- [ ] The new CI job is registered as a required check (repo settings).

---

## Testing Strategy

### Unit Tests

- **Python (`tests/unit/tasks/`)**: `build.release` command shape + staging +
  checksum writing (mocked `context.run`, per `test_build.py`) **including the
  four-triple shim build and the `MACOSX_DEPLOYMENT_TARGET` flag**; host-aware
  darwin verification across each (build-host, target-family) cell
  (darwin-on-Linux via `llvm-objdump --macho`, asserting the linkage check
  rejects a non-system-library dylib); sign/manifest emission + manifest signing
  with a fixture keypair; the **publish-time signature re-verify aborting with
  `AssetVerificationError` (draft+tag preserved)**; the **`release_prepare`/
  `_publish` coherence gate aborting before publish** on a desynced anchor;
  `version:check` agreement + mismatch **asserting the specific desynced
  filename** across all four anchors + **key-coherence**; mise-wiring coherence
  for the new pins.
- **Rust (`cli/`)**: dispatch routing to `External` + **non-UTF-8 `OsString`
  argument preservation** through exec; exec exit/signal propagation as
  **black-box tests spawning `CARGO_BIN_EXE_luminosity`** (readiness handshake for
  SIGTERM); launcher-resolution error taxonomy + boundary mapping into
  `kernel::Error`; manifest-signature + **version-binding refusal** + `schema_version`
  gate + sha256 + minisign verify (happy + mismatch + non-release-key +
  tampered-manifest); atomic cache scan/write/reuse (exactly-one-fetch assertion)
  + corrupt-cache-refuses + **evict-and-refetch recovery** + offline cache-hit;
  **retry (5xx-then-200, persistent-5xx)**; **cross-host-redirect allow/deny**;
  **cache-root branches** (unset error, read-only/noexec → XDG, cap eviction);
  failure-path diagnostics; help synthesis (lazy dynamic command build) +
  **escape-stripping** + **built-ins work with no manifest** + `--help`
  delegation; the shared-fixture manifest round-trip (launcher + sub-binary
  entries) against the Python writer. Each resolution collaborator (Fetcher /
  Verifier / CacheStore / CacheRootResolver) is unit-tested in isolation —
  including Fetcher timeouts (stalled → named error; slow-but-progressing → not
  aborted; 404/no-asset not retried) and CacheStore concurrency (held lock →
  wait-then-reuse or named acquisition-timeout; lock from an exited process is
  reacquirable). The **`minisign-verify` shim** has its own black-box tests
  (valid → 0, tampered/wrong-key → non-zero) plus a **reproducible-build
  byte-identity** check against the shipped artifact. Copy the
  `version/core.rs` port+fake pattern; keep cores infrastructure-free for pup.

### Integration Tests

- **Hermetic launcher resolution** against a local mock HTTP server (fetch,
  verify, cache, refuse, fetch-failure, offline cache-hit), with a test keypair +
  a second non-release key.
- **cargo-deny regression** (`tests/integration/deny/`) — confirm the
  native-tls/openssl ban still holds with the new (and dev) dependency closure,
  and assert via `cargo tree` that no native-cert crate
  (`rustls-native-certs`/`security-framework`) enters the launcher tree.
- **Cross-language contract coherence** — the triple→platform-alias map agrees
  across `tasks/shared/targets.py`, the launcher, and the bootstrap.

### Manual / CI-gated

- One real end-to-end fetch of a signed asset from a pipeline-provisioned test
  release, run out-of-band rather than as a merge gate (Phase 6).
- Static-link + arch verification on real per-OS runners (`build:launcher` legs).
- A **pinned-MSRV build/test leg** so an MSRV-breaking transitive bump fails in
  CI, not at a user's first fetch.

## Performance Considerations

- Blocking reqwest pulls a transitive `tokio` into the launcher (accepted,
  ADR-0010) — a heavier tree than sync-only, the price of one HTTP stack
  workspace-wide; the launcher declares no direct `tokio` dependency.
- Resolve-once-and-cache makes first use pay a network fetch (bounded by explicit
  timeouts + bounded retry); steady state is a cache-hit scan + verify + exec,
  which works **offline** for already-cached sub-binaries. A cache *miss* with no
  network fails cleanly (no offline fallback for an uncached binary — ADR-0002
  caveat).
- `cargo zigbuild` compiles four triples per release build; CI cache
  (`Swatinem/rust-cache`, `workspaces: cli`) already scopes `cli/target`.

## Migration Notes

- Seeding `checksums.json` (Phase 1) unblocks `version:write`/`version:bump`,
  which raise today; seeding `manifest.json` (Phase 2) keeps them unblocked once
  the manifest joins the single-writer, avoiding a re-introduced
  `FileNotFoundError`.
- Populating `kernel::Error` intentionally breaks `main.rs:18`'s `match error {}`
  — this is the compiler pointing at the code to update, not a regression.
- Retiring the spike's clap to-confirm consequence: the dispatch routing test is
  the observable proof; note it in the plan validation.

## References

- Work item: `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md`
- Research: `meta/research/codebase/2026-07-03-0008-static-binary-distribution-and-launcher.md`
- Spike (canonical design source, §1–§4):
  `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- Scaffold plan: `meta/plans/2026-06-29-0007-scaffold-hexagonal-rust-workspace.md`
- Insertion points: `cli/launcher/src/version/inbound/cli.rs:17-21,41-51`;
  `cli/launcher/src/main.rs:12-20`; `cli/kernel/src/lib.rs:9`;
  `cli/Cargo.toml:5-12`; `cli/deny.toml:15-20,57-61`; `tasks/build.py:68-88`;
  `tasks/github.py:135-177`; `tasks/version.py:71-80`; `tasks/shared/targets.py:3-8`.
