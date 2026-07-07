---
type: codebase-research
id: "2026-07-03-0008-static-binary-distribution-and-launcher"
title: "Research: Codebase readiness for story 0008 (on-demand static-binary distribution & launcher)"
date: "2026-07-03T09:47:02+00:00"
author: Toby Clemson
producer: research-codebase
status: complete
work_item_id: "0008"
parent: "work-item:0008"
relates_to: ["codebase-research:2026-06-28-0007-scaffold-hexagonal-rust-workspace", "codebase-research:2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate", "codebase-research:2026-06-27-0006-rust-toolchain-guard-rails"]
topic: "On-demand static-binary distribution & launcher (story 0008)"
tags: [research, codebase, rust, distribution, launcher, cross-compile, dispatch, minisign, reqwest, cargo-zigbuild]
revision: "94f58a31755760fe6dbe17f1c4b0b2644001dd42"
repository: "luminosity"
last_updated: "2026-07-03T10:07:14+00:00"
last_updated_by: Toby Clemson
last_updated_note: "Added follow-up research on the test-fixture strategy for launcher dispatch/resolution when no real sub-binary exists"
schema_version: 1
---

# Research: Codebase readiness for story 0008 (on-demand static-binary distribution & launcher)

**Date**: 2026-07-03T09:47:02+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: 94f58a31755760fe6dbe17f1c4b0b2644001dd42
**Branch**: main (jj-colocated working copy)
**Repository**: luminosity

## Research Question

For the story at `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md`:
what does the codebase already provide that story 0008 builds on, and what must
0008 create from scratch? 0008 delivers (a) fully static `luminosity` binaries
for four Unix triples, cross-compiled from one host; (b) a hand-rolled
invoke + `gh` release pipeline that checksums, **minisign**-signs, and publishes
per-platform assets plus a release manifest, enforcing version coherence;
(c) a Rust **launcher resolution** pipeline (fetch → verify → cache → exec) with
clap `external_subcommand` dispatch; and (d) a thin bash bootstrap that fetches
the launcher binary itself on first use.

## Summary

The repo is a **well-prepared skeleton, not a partial implementation**. Almost
every seam 0008 needs has been deliberately pre-cut, but the load-bearing
machinery is absent:

- **Rust scaffold (`cli/`)** — a two-crate workspace (`launcher` = bin
  `luminosity`; `kernel` = cross-cutting contracts) shipping only a `version`
  subcommand as a textbook hexagon. There is **no `external_subcommand` arm, no
  reqwest/rustls/tokio, no minisign, and `kernel::Error` is uninhabited**. The
  clap enum, the fallible `dispatch` signature, and the empty error type are the
  exact insertion points for 0008.
- **Supply-chain policy (`cli/deny.toml`)** — the rustls-only guarantee is
  **live and regression-tested**: `native-tls`/`openssl`/`openssl-sys` are hard
  `deny` bans. Licences for the reqwest/rustls/tokio/clap closure are
  pre-seeded. The cross-crate architectural ban-lists are present but **inert**
  until the workspace splits (0009/0012).
- **Distribution tasks (`tasks/`)** — a release *skeleton* exists: version
  coherence across three files (`version.py`), the four-triple definition
  (`targets.py`), a host-native release build with static-link/arch verification
  (`build.py`), and a complete `gh` draft → upload → re-download-and-SHA-verify →
  publish flow (`github.py`) plus a prepare/finalise release orchestration
  (`release.py`). **But nothing produces the artefacts that flow consumes**:
  no four-triple cross-compile, no cargo-zigbuild use, no artefact placement into
  `cli/launcher/bin/`, no `checksums.json` population, no debug archives, and
  **no minisign signing at all**.
- **CI (`.github/workflows/main.yml`)** — full guard-rail jobs and a full
  release topology (prerelease → approval gate → release) with **SLSA
  build-provenance attestation** already exist. But the release jobs never build
  or checksum binaries, and attestation is SLSA — **0008 mandates minisign
  instead** (SLSA is explicitly parked).
- **Bootstrap / plugin runtime surface** — **does not exist yet.** No
  `hooks/`, no `skills/`, no bash library, no `bootstrap.sh`, no `${CLAUDE_PLUGIN_ROOT}`
  usage in real files, and `plugin.json` has empty `skills` and no binary
  reference. The runtime managed cache/bin directory is an open question. 0008
  builds the bootstrap and the runtime fetch/cache path from scratch.

The canonical design source is the **done spike (0002)**, whose §3 (launcher)
and §4 (cross-compile & distribution) give concrete, still-current decisions the
ADRs only summarise. Note the spike built **no prototypes** — 0008 carries
first-time validation risk for the clap derive behaviour and the exec path.

## Detailed Findings

### 1. Rust workspace scaffold (`cli/`)

Two crates only. The version-only vertical slice is a genuine hexagon so later
subdomains have a template.

**Workspace manifest** `cli/Cargo.toml`:
- `[workspace]`-only, versionless, `[package]`-free (`:1`); `resolver = "2"`;
  `members = ["launcher", "kernel"]` (`:3`).
- `[workspace.dependencies]` (`:5-12`): `clap = { version = "4.6", features = ["derive"] }`;
  `vergen = "=9.0.6"` (exact pin, with a comment explaining the 9.1/10.x
  breakage); `vergen-gitcl = "1"`; `time = "0.3"` (dev only).
  **reqwest / rustls / tokio are absent** from both manifest and `Cargo.lock` —
  they appear only in `deny.toml` comments as the anticipated stack.
- `[workspace.lints]` (`:14-29`): rust `warnings = "deny"`; clippy `pedantic` +
  `nursery` at `warn` (priority -1); restriction lints `unwrap_used`,
  `expect_used`, `panic`, `dbg_macro`, `todo`, `unimplemented` at `warn`. These
  **will bite new HTTP/error code** (`.unwrap()` etc. become deny-level warnings).
- Resolved pins (`cli/Cargo.lock`): clap **4.6.1**, vergen 9.0.6,
  vergen-gitcl 1.0.8. `anyhow`/`thiserror`/`serde`/`serde_json`/`camino` exist
  only as transitive deps of the tooling — no first-party crate declares them.

**Launcher crate** `cli/launcher/`:
- `Cargo.toml`: `[package] name = "luminosity"`, `version = "0.1.0-pre.0"`,
  `edition = "2021"`, `publish = false` (the last also lets cargo-deny's
  `allow-wildcard-paths` exempt the `kernel` path dep). `[[bin]] name = "luminosity"`.
  Deps: `kernel = { path = "../kernel" }`, `clap = { workspace = true }`;
  build-deps `vergen`/`vergen-gitcl`; dev-dep `time`.
- Module tree: `src/main.rs` (composition root), `src/lib.rs`, `build.rs`
  (vergen), `src/version/{core,inbound/cli,outbound/build_metadata}.rs`,
  `tests/version.rs`.
- **clap dispatch as it stands** — `src/version/inbound/cli.rs`: derive-based;
  `Cli` struct with `#[command(name = "luminosity", disable_version_flag = true)]`
  and a single `#[command(subcommand)] command: Command` field; **`Command` enum
  has exactly one variant, `Version`** (`:17-21`). **No `external_subcommand`
  variant yet** — this is where 0008 adds
  `#[command(external_subcommand)] External(Vec<OsString>)`. `dispatch(...) ->
  Result<(), kernel::Error>` (`:41-51`) is deliberately fallible ("the seam where
  a future command's failure will surface") though currently infallible.
- **Composition root** `main.rs:12-20`: `Cli::parse()`, build
  `VersionReporter::new(VergenBuildMetadata)`, match `dispatch`; the `Err` arm is
  `match error {}` (`:18`) — compiles **only** because `kernel::Error` is
  uninhabited. This breaks by design when a real error variant lands.
- **Hexagon core** `src/version/core.rs`: outbound/driven port
  `trait BuildMetadata` (four `&'static str` getters); inbound/driving port
  `trait ReportVersion`; application service `VersionReporter<M: BuildMetadata>`;
  and an **in-module unit test with an in-memory `FakeBuildMetadata`** — the
  pattern to copy for any new port fake.
- **Outbound adapter** `src/version/outbound/build_metadata.rs`:
  `VergenBuildMetadata` reads `env!("CARGO_PKG_VERSION")` +
  `option_env!("VERGEN_*")` with `.unwrap_or("unknown")` fallbacks.
- `build.rs` emits vergen build-timestamp, cargo target-triple, git SHA; does
  **not** call `fail_on_error()` (git-less builds degrade).

**Kernel crate** `cli/kernel/`: no dependencies. `src/lib.rs` holds
`pub enum Error {}` — **uninhabited** ("until a command can actually fail"),
with `Display` matching `*self {}` under `#[expect(clippy::uninhabited_references)]`
(self-cleans when a variant lands) and a compile-time `assert_std_error::<Error>()`
test. **This is the type 0008 populates** with fetch/IO/resolution/verification
variants.

### 2. Supply-chain / architecture config (`cli/`)

- **`cli/deny.toml` — the native-tls/openssl ban is LIVE** (`:52-61`):
  `[bans] deny = [native-tls, openssl, openssl-sys]`, exercised by the
  regression at `tests/integration/deny/test_deny_bans.py:71-89`. The graph is
  evaluated **as the release ships it (default-features = false, rustls), NOT
  `--all-features`** (`:15-20`) — so reqwest's optional `native-tls` feature
  stays disabled and the ban is not tripped **provided** reqwest is declared
  `default-features = false` with rustls features. Getting that wrong is the
  primary trap: default-feature reqwest pulls native-tls → openssl-sys → a
  `deny:check` failure.
- Licences (`:28-45`) are **pre-seeded** (MIT/Apache-2.0/BSD/ISC/Zlib/Unicode)
  specifically so 0007/0008 aren't blocked. `multiple-versions = "warn"` — the
  reqwest/tokio duplicate-version tail only warns. Sources: crates.io only
  (a git-sourced dep would fail).
- Architectural cross-crate ban-lists (`skip`/`skip-tree`, `:62-66`) are
  **empty/inert** until the workspace splits.
- **`cli/pup.ron`**: one rule, `version_core_imports_only_permitted`, scoping
  `luminosity::version::core` to `std/core/alloc`, `kernel`, `crate::version::core`.
  It constrains **only** that module — new subdomain code is unconstrained by pup
  unless placed under `version::core`.
- `cli/clippy.toml`: `msrv = "1.90.0"` (hand-synced mirror of `mise.toml:8`'s
  rust pin; coherence asserted by `tests/unit/tasks/test_mise_wiring.py`
  `TestToolchainCoherence`). New deps must be MSRV ≤ 1.90.
- `cli/rustfmt.toml`: `max_width = 80` (hand-duplicated from `.editorconfig`, no
  automated sync check).

### 3. Distribution / build / release tasks (`tasks/`)

**Version coherence** `tasks/version.py`: single-writer `write()` (`:71-80`)
re-renders all three anchors from one version string and atomic-writes each:
`.claude-plugin/plugin.json` (authoritative source), `cli/launcher/Cargo.toml`
(`package.version`), and `cli/launcher/bin/checksums.json` (top-level `version`
key only). Coherence is **enforced by construction — there is no `version:check`
audit task**. Caveat: `_render_checksums_version` reads `checksums.json`, which
**does not exist on disk**, so `version:write`/`version:bump` currently raise
`FileNotFoundError` until the manifest is seeded. `write()` never touches the
`"binaries"` map.

**Build** `tasks/build.py` (single file, task `build:launcher`):
- Iterates `host_targets(platform.system())` — **host-native only (two
  triples)**, via plain `cargo build --release --bin luminosity --target {triple}`
  (`:80`). **cargo-zigbuild is NOT used** (though `ziglang>=0.16.0` +
  `cargo-zigbuild>=0.22.3` are provisioned as uv build-group deps in
  `pyproject.toml:16-17`, referenced nowhere).
- `_verify_output` (`:50-65`) enforces static linkage on musl (`file`/`ldd`) and
  single-arch on darwin (`lipo -archs`).
- Binaries stay at `target/{triple}/release/luminosity`; **nothing copies them
  to `cli/launcher/bin/luminosity-{platform}`** (the name the upload path
  consumes). No checksum/archive/signing generation.

**Four-triple definition** `tasks/shared/targets.py`: `TARGETS` maps
`aarch64-apple-darwin→darwin-arm64`, `x86_64-apple-darwin→darwin-x64`,
`aarch64-unknown-linux-musl→linux-arm64`, `x86_64-unknown-linux-musl→linux-x64`;
`host_targets(system)` partitions by OS marker.

**Publish** `tasks/github.py`: `create_release` (`gh release create --draft
--generate-notes`, `--prerelease` for pre-versions), `upload_release_asset`,
`download_and_verify`, and `upload_and_verify` (`:135-177`) which reads
`checksums["binaries"]` as `{platform: "sha256:..."}`, builds `binary_path` +
`debug_archive_path` for **all four** targets, **errors if any artefact is
missing**, uploads binary + `.debug.tar.gz` per platform, re-downloads and
SHA-verifies, then `gh release edit --draft=false`. Manifest shape (test
fixture): `{"version", "binaries": {platform: "sha256:<hex>"}}` — **no
`signatures`/minisign field, no `description` field**.

**Orchestration** `tasks/release.py`: `prerelease_prepare`/`release_prepare`
only bump version + marketplace/changelog — **they do NOT build or checksum**,
despite `mise.toml:285/294` descriptions claiming they do. `_publish` does
commit→tag→push→create_release→upload_and_verify. `deps.py` adds rustup targets
for all four triples but **no zig/cargo-zigbuild/minisign provisioning**.

### 4. CI (`.github/workflows/main.yml`)

- Guard-rail jobs: `test-unit`, `test-integration` (both ubuntu+macos),
  `check-scripts`, `check-build-system`, `check-cli` (runs `mise run cli:check`
  — the workspace-wide roll-up; note the job/task keep the `cli` name, correctly,
  as 0014 renamed only the launcher-specific `build-cli`→`build-launcher`),
  `check-supply-chain` (`deny:check`), `check-architecture` (`pup:check` +
  `test:integration:pup`).
- **`build-launcher`** (`:138-182`): a **two-leg matrix** (ubuntu + macos), each
  running `mise run build:launcher`. Four-triple coverage is by **host
  partitioning, not single-host cross-compile** — ubuntu builds the two musl
  triples, macos the two darwin. aarch64-musl cross-linking is wired via
  apt-installed GNU cross-linkers + `CARGO_TARGET_..._LINKER` env, **not
  cargo-zigbuild**.
- **Release topology exists**: `prerelease` → `approve-release`
  (`environment: release` manual gate) → `release`, with a concurrency lock and
  three `actions/attest-build-provenance@v2` steps
  (`subject-path: "cli/launcher/bin/luminosity-*"`). This is **SLSA
  build-provenance (GitHub Attestations), NOT minisign** — the exact scheme 0008
  parks in favour of minisign.
- **Critical gap**: the `prerelease`/`release` jobs run only checkout → mise
  install → prepare (version bump) → attest → finalise (publish). **No step
  builds binaries, computes checksums, or creates archives** — yet the attest
  `subject-path` and `upload_and_verify` require them. The release jobs are
  aspirational scaffolding. Only secret referenced is `GITHUB_TOKEN`; **no
  minisign secret exists**.
- Required-check registration runbook: `CONTRIBUTING.md:7-62` (a matrix job = one
  required check per leg; a job is selectable only after it has run once;
  `tests/unit/tasks/test_workflows.py` proves jobs exist/gate but cannot prove
  registration).

### 5. Bootstrap / plugin runtime surface — greenfield

- `.claude-plugin/plugin.json` (11 lines): `"version": "0.1.0-pre.0"`,
  `"skills": []` (empty), **no `hooks`/`scripts`/`commands`/`bin` reference**.
- `scripts/` contains **only** `lint-bashisms.sh` — no config/VCS/frontmatter
  library, **no fetch/download/bootstrap script**. The "large bash library",
  hooks, and SKILL.md files described in `CLAUDE.md` are **target architecture
  that does not exist on disk yet**.
- `hooks/` and `skills/` directories **do not exist**. `${CLAUDE_PLUGIN_ROOT}`,
  the `!` preprocessor, `external_subcommand`, and `CommandExt::exec` appear
  **only in `meta/` docs and `CLAUDE.md`**.
- **Bash 3.2 floor** (enforced by `lint-bashisms.sh` over all tracked `*.sh`): a
  new `bootstrap.sh` is auto-scanned and must avoid associative arrays, namerefs,
  `mapfile`, `${x,,}`/`${x^^}`, `&>>`, `|&`, negative subscripts. The linter
  itself models the safe idioms (`set -uo pipefail`, `BASH_SOURCE` root
  resolution, `case` matching).
- **Runtime cache/bin dir is an open question** (0008 lines 203-204). The
  existing `cli/launcher/bin/` (`BIN_DIR`) is the **release-artefact staging
  area, not a user-machine cache**, and does not exist on disk. The runtime cache
  is uv-style, keyed by name+version+checksum, owned by the Rust launcher.
- **Reusable publish-side conventions** the bootstrap/launcher must mirror:
  platform-alias map + `luminosity-{platform}` asset naming
  (`tasks/shared/{targets,paths}.py`); `sha256:`-prefixed `checksums.json` shape;
  streaming `compute_sha256` (`tasks/shared/hashing.py`); the
  download→verify→cleanup contract (Python/`gh` in `github.py` — but the runtime
  path must fetch over **plain HTTPS via reqwest+rustls, not `gh`**).

### 6. Canonical design source — spike 0002 (`done`)

The still-current source behind ADR-0002/0010. **No prototypes were built** — the
evidence is analysis of the accelerator's real code plus web research, so 0008
carries first-time validation risk for the clap derive and exec path.

Firm recommendations 0008 should honour:
- **Launcher (§3)**: fetch→verify→cache→exec in Rust; thin bash bootstrap
  "simplified from the accelerator's `launch-server.sh`" fetches the launcher
  itself. **reqwest + rustls workspace-wide** (`default-features = false`,
  `rustls-tls`), **blocking in launcher / async in subdomains** — accepts pulling
  `tokio` into the launcher (judged acceptable on musl-static). sha2 checksum
  verified on fetch **and re-verified before every exec**. **No self-update**
  (`self_update`/`self-replace` explicitly dropped). The accelerator's launcher
  is a bash daemon and **does not port**; only its distribution half does.
- **Cross-compile & distribution (§4)**: **cargo-zigbuild** for all four triples
  from one host (`cross` not needed — pure Rust + rustls). Port the accelerator's
  **`tasks/build.py` + `tasks/github.py`** (invoke + `gh`, re-download-and-verify,
  version coherence across plugin.json/Cargo.toml/manifest) — chosen over
  `dist`/cargo-dist. Integrity = sha256 + TLS + manifest **plus minisign**: sign
  each artefact, **embed the public key in the launcher**, verify the detached
  `.minisig` in-process via **`minisign-verify` 0.2.5** (pure-Rust, zero-dep,
  sync) — **no `gh` dependency on the user machine**. Signing side uses
  `minisign`/`rsign2`. SLSA/Sigstore parked (heavy `aws-lc-rs`, musl-awkward,
  pre-1.0; mise's in-process attempt was archived May 2026).
- **Dispatch (§2)**: clap 4.x `#[command(external_subcommand)] External(Vec<OsString>)`
  (OsString preserves non-UTF-8 args); the derive attribute alone should enable
  it (confirm on pinned clap 4.6.1 — the one to-confirm consequence). `version`
  + `config` built-in. **Unix `exec` only** (Windows out of scope).
  Discoverability = clap help + a synthesised section from the manifest's
  **`description`** field (scan cache dir + manifest, no executing untrusted
  binaries); per-command `--help` delegated by re-exec.
- **Release-manifest schema** the launcher reads: per-sub-binary **name,
  version, sha256 checksum, minisign signature, and `description`** — one file
  for resolution, discoverable help, and manifest-hash change detection. The
  existing `checksums.json` is checksum-only and is **not** this manifest.

## Code References

- `cli/launcher/src/version/inbound/cli.rs:17-21` — the single-variant `Command`
  enum; insertion point for `External(Vec<OsString>)`.
- `cli/launcher/src/version/inbound/cli.rs:41-51` — the fallible `dispatch` seam.
- `cli/launcher/src/main.rs:12-20` — composition root; the `match error {}` arm
  (`:18`) that breaks when `kernel::Error` gains a variant.
- `cli/launcher/src/version/core.rs` — the hexagon + in-memory fake pattern.
- `cli/kernel/src/lib.rs` — the uninhabited `Error` enum to populate.
- `cli/Cargo.toml:5-12` — `[workspace.dependencies]`; where reqwest/rustls/tokio
  pins go, consumed via `{ workspace = true }`.
- `cli/deny.toml:52-61` — the live native-tls/openssl ban; `:15-20` — no
  `--all-features` evaluation.
- `tasks/version.py:71-80` — the three-anchor coherence writer.
- `tasks/build.py:68-88` — host-native-only `build:launcher` (plain cargo).
- `tasks/shared/targets.py:3-8` — the four triple→alias map.
- `tasks/github.py:135-177` — `upload_and_verify`, consuming artefacts nothing
  produces.
- `tasks/release.py:32-57` — prepare tasks that don't build/checksum.
- `.github/workflows/main.yml:138-182` — two-leg `build-launcher` matrix;
  `:241-362` — release topology + SLSA attestation.
- `.claude-plugin/plugin.json` — empty skills, no binary reference.
- `scripts/lint-bashisms.sh` — bash 3.2 floor a new bootstrap must satisfy.

## Architecture Insights

- **Seams-first scaffolding.** The scaffold, deny-config, and task skeleton were
  built to receive 0008: the fallible `dispatch`, uninhabited `Error`, pre-seeded
  licences, `{ workspace = true }` dependency convention, the four-triple map,
  and the full `gh` publish flow all exist ahead of the code that uses them.
- **Two integrity models in tension — resolve deliberately.** CI already ships
  **SLSA attestation**; 0008 mandates **minisign** and parks SLSA. 0008 must
  decide whether SLSA attestation stays alongside minisign or is removed, and add
  the minisign signing step + secret + `.minisig` assets + `signatures`/`description`
  manifest fields.
- **The `checksums.json` → release-manifest evolution.** The current
  checksum-only file blocks even `version:write` today (it must be seeded) and
  lacks the `signatures`/`description` fields the launcher needs. Extending it
  (or introducing a distinct manifest) plus its version-coherence check is core
  0008 work.
- **Cross-compile is the pivot.** Host-partitioned two-triple builds must become
  single-host four-triple cargo-zigbuild builds; the tool is already provisioned
  but unused, and `deps.py` needs a zig/cargo-zigbuild (and minisign)
  provisioning task, pinned per repo convention.
- **The rustls trap is guarded but not automatic.** The live ban catches a
  default-feature reqwest, but only because deny evaluates the shipped feature
  set — reqwest must be declared `default-features = false` + rustls.
- **Bootstrap is genuinely greenfield.** The bash runtime surface CLAUDE.md
  describes is aspirational; 0008 writes the bootstrap and runtime cache path new,
  reusing only publish-side naming/checksum conventions.

## Historical Context

- `meta/work/0002-...md` — the **done** architecture spike; §3/§4 are the
  concrete source (see §6 above). No prototypes built.
- `meta/decisions/ADR-0002-...md` — distribution model (static musl,
  cargo-zigbuild, invoke+gh over cargo-dist, sha256+minisign, rustls forced by
  musl-static).
- `meta/decisions/ADR-0010-...md` — git-style composition, clap
  external-subcommand dispatch, Unix exec, resolve-once-and-cache, reqwest+rustls,
  no self-update, manifest-driven help.
- `meta/decisions/ADR-0009-...md` — hexagon + inward-dependency rule (cargo-pup
  sole enforcer while single-crate).
- `meta/work/0007-...md` / `meta/research/codebase/2026-06-28-0007-...md` /
  `meta/plans/2026-06-29-0007-...md` — the scaffold this builds on.
- `meta/work/0014-...md` / `2026-07-02-0014-...md` — the (landed) relocation to
  `cli/launcher/` + `cli/kernel/`; 0008's terminology targets this layout.
- `meta/work/0006-...md` / `2026-06-27-0006-...md` — the Rust toolchain guard
  rails (mise pins, cargo-pup nightly lane) under the launcher build.
- `meta/work/0012-...md` — cross-crate enforcement that activates the inert
  deny ban-lists as the workspace grows (relevant when 0008 adds crates).
- `meta/work/0004-...md`, `0005-...md` — the ADR-authoring stories.

## Related Research

- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md`
- `meta/research/codebase/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`

## Open Questions

- **Runtime managed cache/bin directory path** (deferred by ADR-0002/0010 and
  0008 itself): XDG data dir vs plugin `bin/`. Distinct from the
  release-staging `cli/launcher/bin/`.
- **SLSA-vs-minisign coexistence**: does the existing `attest-build-provenance`
  wiring stay alongside minisign, or is it removed? 0008's criteria are
  minisign-only.
- **Release manifest: extend `checksums.json` or introduce a new file?** Either
  way it needs `signatures` + `description` and must join version coherence.
- **clap 4.6.1 external-subcommand derive** — confirm the derive alone enables
  external dispatch without a manual builder call (the spike's one to-confirm
  consequence), observable via the unknown-subcommand → `External` arm.
- **minisign key provisioning ownership** — 0008 notes this may need carving into
  its own `blocked_by` prerequisite if a separate ops/security owner controls
  release-environment secrets.
- **cargo-zigbuild + minisign provisioning + pinning** — needs a `deps.py` task
  and mise/repo-convention pins (mirroring the cargo-pup nightly lane approach).
- **Test-fixture strategy for dispatch/resolution with no real sub-binary** —
  resolved below in the follow-up (§ Test-fixture strategy). The remaining live
  sub-decisions are the dev-dep-vs-TLS-ban interaction and the lint/coverage
  scoping of the fixture crate.

## Follow-up Research [2026-07-03T10:07:14+00:00] — Test-fixture strategy

**Question raised:** is it a problem that no `luminosity-<sub>` sub-binary exists
yet, and if fixtures are used to test the launcher, should they be a **dedicated
workspace fixture crate** or **pre-built binaries committed to the repo**?

**It is not a problem — it is the designed baseline.** The git-style launcher
dispatches to sub-binaries that do not exist at build time and arrive on demand;
it must work correctly with **zero** sub-binaries present, and proving that is
part of 0008's scope. 0008's acceptance criteria are already written around
*observable behaviours* a throwaway stub satisfies (exit `42`; killed by
`SIGTERM` → `$?`=143; a sentinel `--help` string; a *synthetic* manifest listing
`foo`/`Bar tool`; fetch failures "induced by pointing the URL at an unreachable
host / a Release lacking the asset"). None of that needs a product subcommand —
the phrasing is the tell that fixtures are the intended vehicle. `version` (and
later `config`, in 0009) are built-in, so the launcher is useful with no external
sub-binaries at all; at 0008's completion the only real subcommand is `version`
and external dispatch is proven entirely against stubs. Proving the launcher
against fixtures now **de-risks** the later subdomain stories.

### The ACs test at three layers (mechanism differs per layer)

1. **Exec + signal/exit propagation** — pure `CommandExt::exec`; needs no Rust
   fixture. `/bin/sh -c 'exit 42'` and `sh -c 'kill -TERM $$'` exercise the real
   path honestly and for free (both targets are Unix).
2. **`--help` delegation** — needs a *controllable* executable emitting a
   sentinel marker.
3. **Fetch → verify → cache → exec resolution** — the layer that pulls on the
   fixture question. It sub-splits: verify/cache assertions need only stable
   **bytes** (any file with a known sha256 + a `.minisig`), while cases that
   *proceed to exec* need a genuinely runnable static binary.

### Decision: a dedicated fixture crate (preferred)

Provide layer 2/3's executable as a **single, arg-driven fixture crate** (one
crate exposing behaviours by argument — `exit 42`, `block-on-sigterm`,
`print-help-sentinel` — not a crate per behaviour), `publish = false`, located
from tests via `env!("CARGO_BIN_EXE_<name>")`.

Rationale, weighed against committed pre-built binaries:
- **It is the idiom the repo already uses** — `cli/launcher/tests/version.rs`
  spawns `CARGO_BIN_EXE_luminosity` today; extending that to fixture bins is
  consistent. Deterministic, rebuilt on source change, cargo guarantees the bin
  exists before the test runs, **no binary blobs in git**.
- **Cross-triple correctness is free** — each CI leg builds its own host-triple
  fixture with the same toolchain (darwin fixture on the macos leg, musl on the
  ubuntu leg). A committed blob cannot be exec-tested off its own triple, so it
  imposes a per-triple maintenance tax anyway.
- **Committed binaries lose on provenance and drift** — opaque executables in
  git (faintly absurd in a story about *verified* binaries), regenerate-and-
  re-sign by hand on every toolchain/security bump. Their one real edge —
  byte-stable digests for the mismatch assertions — evaporates because the bytes
  can be generated and signed deterministically in a test setup step.

### What serves the bytes (orthogonal, still needed)

Layer 3 must be **hermetic** — the normal suite must not hit real GitHub
Releases (flaky, network-coupled, no offline fallback). Serve the fixture bytes
from a **local mock HTTP server**; induce the failure cases (404 release, absent
asset, connection refused) by pointing the launcher's URL at it. Sign with a
**test minisign keypair generated in the fixture**, plus a **second, non-release
key** for the AC proving verification is key-bound rather than TLS-bound. Keep
exactly **one** CI-gated smoke test fetching a real signed asset from a real test
release, to honour the true end-to-end AC without coupling the whole suite to the
network.

### Non-obvious traps / live sub-decisions

- **Dev-dep vs the live TLS ban (the main trap).** `cargo-deny` scans *all*
  dependency kinds by default, so a mock-server or minisign dev-dependency that
  pulls `native-tls` would trip `cli/deny.toml`'s ban (`:52-61`) even though it
  never ships. Either choose rustls-only / TLS-free test deps or set
  `exclude-dev` deliberately — a real decision, not an oversight.
- **Lint/coverage scoping of the fixture crate.** Cleanest is to *not* opt the
  fixture into `[workspace.lints]` (it is test scaffolding, and a stub calling
  `process::exit` trips `clippy::exit` under the restriction lints) and to
  exclude it from `cargo llvm-cov nextest` coverage — but that bumps against
  CLAUDE.md's "tests held to the same standard" stance. Needs an explicit call.
- **Keep workspace surface minimal** — one arg-driven crate under (e.g.)
  `cli/testfixtures/`, not stray `[[bin]]`s in `launcher` (which would clutter
  `cargo build` and sit awkwardly beside the shipped `luminosity` bin), and not a
  crate per behaviour (each new member also implies a `<crate>:check` component
  per 0007's convention).
- **TDD framing** — treat the fixture crate as test infrastructure (like a test
  helper), not a red-green subject: scaffold it, then write the failing
  dispatch/resolution tests against it.
