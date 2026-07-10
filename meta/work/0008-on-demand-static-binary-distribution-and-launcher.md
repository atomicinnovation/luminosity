---
type: work-item
id: "0008"
title: "On-Demand Static-Binary Distribution & Launcher"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: done
kind: story
priority: high
parent: "work-item:0001"
blocked_by: ["work-item:0007", "work-item:0002"]
relates_to: ["work-item:0014"]
tags: [story, rust, distribution, launcher, cross-compile, dispatch]
last_updated: "2026-07-03T00:12:58+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0008: On-Demand Static-Binary Distribution & Launcher

**Kind**: Story
**Status**: In Progress
**Priority**: High
**Author**: Toby Clemson

## Summary

Build zero-setup, fully static `luminosity` binaries for the four target
platforms and the git-style launcher that fetches the correct per-platform
binary on demand, verifies it (sha256 + minisign), caches it, and execs it — plus
the clap external-subcommand dispatch that lets the single `luminosity` command
grow as on-demand sub-binaries. The end user installs no toolchain, runtime, or
package manager — nothing beyond the plugin itself.

## Context

Zero user setup is a core architectural goal (ADR-0002): the plugin (via a thin
bash bootstrap, then the Rust launcher) downloads static, dependency-free
binaries and the user installs no toolchain, runtime, or package manager. The git-style modular CLI (ADR-0010) presents as a single
`luminosity` command that dispatches to sub-binaries fetched on demand. This story
implements the distribution and launcher, building on the hexagonal workspace
scaffold (0007) and the `cli/` workspace relocation (0014).

Two accepted ADRs settle the choices this story realises. **ADR-0002** fixes the
distribution model: fully static binaries (musl on Linux), cross-compiled with
`cargo-zigbuild`, released by a hand-rolled Python invoke + `gh` pipeline (chosen
over `dist`/cargo-dist), with integrity resting on sha256 **plus minisign**
verified in-process — not GitHub Attestations or TLS alone. **ADR-0010** fixes
the composition (one independently-shipped binary per subdomain), the dispatch
(clap `external_subcommand`, Unix `exec`, `version`/`config` built-in,
manifest-driven discoverable help), and the launcher resolution (fetch → verify →
cache → exec in the `luminosity` launcher binary (the `launcher` crate at
`cli/launcher/`, per 0014) behind a thin bash bootstrap). The external-subcommand
dispatch and the confirmation of clap's derive behaviour were relocated here from
the scaffold story (0007), which owns only the in-process `version` subcommand.

Terminology used throughout: **the launcher binary** (equivalently the `launcher`
crate at `cli/launcher/`) is the shipped `luminosity` entry point; **launcher
resolution** is its fetch → verify → cache → exec pipeline; **the bash bootstrap**
is the thin shell slice that fetches the launcher binary itself on first use.
`cli` denotes the whole workspace — ADR-0010 predates the 0014 relocation and
still names this crate `cli`, but post-0014 the crate is `launcher` and `cli` is
the workspace.

This story is kept as a single unit rather than split into separate distribution
and launcher stories: ADR-0002 and ADR-0010 frame the launcher and its
distribution as one launcher/distribution effort, and the launcher's fetch →
verify → exec path is only meaningfully exercised against the real signed,
per-platform assets the pipeline produces — so the two halves are validated
together, not in isolation.

## Requirements

**Target platforms** (target triple → distribution alias):

- `aarch64-apple-darwin` → `darwin-arm64`
- `x86_64-apple-darwin` → `darwin-x64`
- `aarch64-unknown-linux-musl` → `linux-arm64`
- `x86_64-unknown-linux-musl` → `linux-x64`

- **Cross-compile** fully static binaries for all four platforms from one host
  via `cargo-zigbuild` (musl gives fully static Linux binaries; macOS targets
  cross-built likewise). No dynamic libc dependency on the musl targets.
- **Integrity & signing** (ADR-0002) — each artifact carries a sha256 checksum
  and a **minisign signature**. The checksum is verified on fetch **and
  re-verified before every exec**; the minisign signature is verified
  **in-process**, so trust rests on "signed by our key", not merely "served over
  TLS". In-process Sigstore/SLSA-provenance verification is deliberately parked
  until that ecosystem stabilises.
- **Release orchestration** (ADR-0002) — a hand-rolled pipeline (Python invoke
  tasks + `gh`), not `dist`/cargo-dist, that builds, checksums, signs, and
  publishes the per-platform artifacts (binary + checksum + signature) as GitHub
  Release assets, with re-download-and-re-verify. The pipeline enforces **version
  coherence** across `plugin.json`, the launcher crate's `Cargo.toml`
  (`cli/launcher/Cargo.toml`, the version-bearing manifest), and the release
  manifest. The **release manifest** is the single artifact listing every
  platform's asset, checksum, signature, and a `description` field; it is the one
  file the launcher later reads for resolution, discoverable help, and
  manifest-hash change detection — every later mention of "the manifest" refers
  to it.
- **Launcher resolution** (ADR-0010) — implemented inside the `luminosity`
  launcher binary (the `launcher` crate at `cli/launcher/`, per 0014), not in
  bash: a uv-style **resolve-once-and-cache** pipeline that scans a managed
  cache/bin directory first (keyed by name + version + checksum), fetches the
  asset matching the host target triple from GitHub Releases on miss, verifies it
  (sha256 + minisign), caches it, then execs it. Dispatch is **Unix `exec`**
  (`CommandExt::exec`, process-replacing, so exit codes and signals propagate);
  Windows is out of scope (all four targets are Unix). The HTTP/TLS stack is
  **`reqwest` + rustls** (`default-features = false`), pinned once in the
  workspace manifest (`cli/Cargo.toml` `[workspace.dependencies]`, alongside the
  existing clap/vergen pins) and opted into by the `launcher` crate and any
  future subdomain crates — `kernel` stays dependency-light and out of it. This
  keeps the launcher statically linkable and independent of the host cert store;
  no OpenSSL / native-tls. There is **no launcher self-update** — a new plugin
  version drives a new launcher via the bootstrap, and sub-binaries re-fetch on
  manifest-hash change.
- **Bootstrap** (ADR-0010) — a thin bash bootstrap fetches the `luminosity`
  binary itself on first use; thereafter the Rust launcher owns fetch, verify,
  cache, and exec entirely.
- **Dispatch & external subcommands** (ADR-0010; relocated from 0007) — `luminosity`
  uses clap 4.x derive `#[command(external_subcommand)] External(Vec<OsString>)`:
  the first element is the subcommand name, the rest are forwarded verbatim, and
  `Vec<OsString>` (not `String`) preserves non-UTF-8 arguments. `version` and
  `config` are **built-in** subcommands compiled into `luminosity`; external
  dispatch is purely the growth mechanism for on-demand subdomains. Confirm
  clap's derive enables external dispatch without a manual builder call on the
  pinned clap version (ADR-0010 records this as a to-be-confirmed consequence;
  relocated here from 0007) — verified observably by the dispatch acceptance
  criterion, whose unknown-subcommand case must reach the `External(Vec<OsString>)`
  arm.
- **Discoverable surface** (ADR-0010) — because clap cannot enumerate external
  subcommands, render clap's built-in help plus a synthesised "external
  subcommands" section built from the release manifest's `description` field (no
  executing untrusted binaries to introspect them). Per-command `--help` is
  **delegated** by re-exec'ing the child with `--help`.

## Acceptance Criteria

- [ ] Static binaries **build** for all four target triples via cross-compile
      from a single host, each published as a GitHub Release asset with a sha256
      checksum **and** a minisign signature. Each is **verifiably static** by a
      defined check: on the musl targets `file <binary>` reports "statically
      linked" and `ldd` reports "not a dynamic executable"; on the darwin targets
      `otool -L` lists only system libraries. All four triples are
      build-verified; the runtime criteria below are execution-verified on the
      host triple, with the remaining triples build-only (explicitly noted, not
      silently assumed covered).
- [ ] Given a platform, when the launcher needs an absent sub-binary, then it
      fetches the asset matching the host target triple from GitHub Releases,
      verifies its sha256 **and** minisign signature **in-process** (against our
      release public key, not TLS transport alone), caches it in the managed
      bin dir keyed by name + version + checksum, and execs it.
- [ ] Given a sub-binary already cached, when invoked again, then the launcher
      reuses the cache without re-fetching (resolve-once-and-cache).
- [ ] Given a checksum or signature mismatch (checked on fetch and re-verified
      before exec), when the launcher verifies a binary, then it refuses to exec
      and reports the failure. This includes an asset with a **valid sha256 whose
      minisign signature was made by a non-release key**: the launcher refuses
      it, proving verification is in-process and key-bound rather than
      TLS-dependent.
- [ ] Given the host-triple asset **cannot be fetched** — induced under test by
      pointing the asset/manifest URL at an unreachable host (network error), at
      a Release lacking the host-triple asset (no asset), or at a missing Release
      (unavailable) — when the launcher resolves, then it exits non-zero with a
      diagnostic naming the missing target and does **not** exec a stale or wrong
      binary.
- [ ] Given `luminosity <external-sub> <args>`, when dispatched, then clap routes
      it via `External(Vec<OsString>)` (an unknown subcommand provably reaches
      that arm on the pinned clap version), the launcher resolves and execs the
      sub-binary, and exit codes and signals propagate: a sub-binary exiting `42`
      makes `luminosity <sub>` exit `42`, and a sub-binary killed by `SIGTERM`
      makes the caller observe the same termination signal (shell `$?` = 143,
      i.e. 128 + signum), since `exec` replaces the launcher process; `version`
      and `config` remain built-in.
- [ ] Given a release manifest listing sub-binary `foo` with
      `description: "Bar tool"`, when `luminosity --help` runs, then the output
      lists the built-in commands plus a synthesised external-subcommands section
      whose content is drawn from the manifest — it contains a line matching
      `foo` and `Bar tool` — and `luminosity foo --help` is delegated to the
      child, emitting the child's own help (verified by a sentinel string only
      the child emits).
- [ ] The launcher binary is statically linkable and free of OpenSSL/native-tls
      by a defined check: `cargo tree -e features` for the `launcher` crate shows
      no `openssl-sys`/`native-tls` (`reqwest` + rustls, `default-features =
      false`, pinned in `cli/Cargo.toml` `[workspace.dependencies]`), and the
      built musl binary passes the static check above. The launcher performs no
      self-update.
- [ ] Version coherence across `plugin.json`, the launcher crate's `Cargo.toml`
      (`cli/launcher/Cargo.toml`), and the release manifest is enforced by the
      release pipeline with a defined check: given the three declare mismatching
      versions, when the pipeline runs, then it exits non-zero and names the
      mismatching files; given all three agree, it proceeds.
- [ ] The release-signing minisign secret key is present as a
      release-environment/CI secret, and the public key the launcher verifies
      against is the one that signs releases: an artifact signed by the
      provisioned key verifies and execs, while one signed by any other key is
      refused (per the mismatch criterion above). Key rotation and `.minisig`
      publishing are documented as a standing operational responsibility.

## Open Questions

- The exact managed cache/bin directory path is deferred here by ADR-0002 and
  ADR-0010; it is settled during implementation.

## Dependencies

- Blocked by: the scaffold story (0007 — binaries are built from the hexagonal
  workspace, and external dispatch builds on its clap inbound boundary); the
  architecture spike (0002, decides the launcher pipeline and distribution
  tooling).
- Operational prerequisite (blocking): **minisign key provisioning** — a
  minisign keypair must be generated and its secret key provisioned as a
  release-environment/CI secret before any artifact can be signed. ADR-0002
  assigns key storage, rotation policy, and `.minisig` publishing to this story;
  the signing and signature-verification acceptance criteria cannot pass until
  the key exists. This is a prerequisite the story must discharge, not merely a
  standing operational note. If a separate ops/security owner controls
  release-environment secrets, carve key provisioning into its own `blocked_by`
  prerequisite work item so the ownership boundary is explicit.
- External systems: **GitHub Releases** is the artifact host for both the
  publish side (the invoke + `gh` pipeline uploads assets) and the fetch side
  (the launcher downloads the host-triple asset); the asset-naming scheme and
  release-manifest URL contract are shared between publisher and launcher and
  must agree. The **`gh` CLI** is the publishing mechanism. Runtime success is
  coupled to GitHub Releases availability and network access: first use requires
  a network fetch and there is no offline/air-gapped fallback (ADR-0002 caveat).
- CI / branch protection: any new CI job this story introduces (e.g. the
  four-triple build/verify matrix) must be registered as a GitHub
  branch-protection **required check** per the `CONTRIBUTING.md` runbook — a
  manual repo-settings action with no local signal, mirroring the coupling 0014
  records for renamed jobs. An unregistered job silently fails to gate merges.
- Build-environment prerequisite: **cargo-zigbuild** (and the underlying `zig`
  toolchain) must be provisioned — and, per repo convention, pinned — in the
  build/release environment for the four-target cross-compile criterion.
- Relates to: work item 0014 (the `cli/` relocation; 0008's launcher and build
  pipeline target the relocated `cli/launcher/` layout and its terminology).
  0014 preferably lands **before** 0008, so 0008's new subdomain crates are born
  under `cli/` rather than created at the old root and relocated later (the soft
  ordering 0014 itself records).
- Blocks: none directly; enables the modular CLI to grow as on-demand
  sub-binaries.
- Parent: epic 0001.

## Assumptions

- The distribution pipeline is adapted from the accelerator's solved approach,
  which ADR-0002 found ports cleanly; the accelerator's launcher (a bash daemon)
  is deliberately **not** carried over, because it does not model a git-style
  sub-binary CLI — the launcher here is built fresh in Rust per ADR-0010.

## Technical Notes

- `cargo-zigbuild` is the cross-compile path for musl-static Linux and macOS
  binaries from a single host.
- `reqwest` + rustls (with webpki-roots) keeps the launcher independent of the
  host cert store; audit the dependency tree so nothing re-enables `default-tls`.
  reqwest pulls `tokio` into the launcher for sync+async uniformity from one HTTP
  stack — accepted per ADR-0010 as the price of one TLS stack workspace-wide. It
  is declared once in `cli/Cargo.toml` `[workspace.dependencies]` and consumed by
  the `launcher` crate via `workspace = true`.
- minisign key management (generation, protection, rotation) is a standing
  operational responsibility (ADR-0002); a leaked key forges releases.
- musl static builds carry known caveats (DNS resolution behaviour, some native
  dependencies) that dynamic builds avoid.

## Drafting Notes

- **ADR-0002 alignment (correction)**: replaced `dist`/cargo-dist with the
  hand-rolled invoke + `gh` pipeline ADR-0002 chose, and replaced GitHub
  Attestations / "checksums only, no signing" with sha256 **plus minisign**
  verified in-process (re-verified before every exec). Added the version-coherence
  obligation. The prior draft contradicted the accepted ADR on both points.
- **ADR-0010 alignment (fill-in)**: added clap `external_subcommand` dispatch,
  Unix `exec`, `version`/`config` built-in, manifest-driven discoverable help and
  per-command `--help` delegation, uv-style resolve-once-and-cache keyed by
  name + version + checksum, `reqwest` + rustls workspace-wide, the thin bash
  bootstrap, and "no launcher self-update".
- **External dispatch relocated from 0007 (decision)**: per the scaffold story's
  enrichment, this story now owns git-style external-subcommand dispatch and the
  confirmation of clap's `External(Vec<OsString>)` derive behaviour. 0007 keeps
  only the in-process `version` subcommand.
- **Cache/bin path (open)**: ADR-0002 and ADR-0010 both defer the exact managed
  directory path to this story; flagged as an open question to settle in
  implementation.
- **Story size (resolved)**: the combined scope is large, but the story is
  deliberately kept whole — ADR-0002 and ADR-0010 frame launcher and
  distribution as one effort, and the launcher's fetch → verify → exec path is
  only meaningfully testable against the real signed assets the pipeline emits.
  The indivisibility rationale now lives in Context; the earlier "possible
  split" hedge was removed from Open Questions (review 1). The build/sign
  criteria and the launcher-resolution criteria may still be sequenced as
  internally-tracked sub-deliverables within the single story so progress stays
  visible without splitting the validated end-to-end unit.
- Kind set to `story`: a concrete, bounded deliverable (build pipeline + launcher
  + dispatch).
- Windows handling dropped: none of the four target platforms are Windows, so the
  launcher's exec path is Unix-only.
- **0014 alignment (this pass)**: reconciled the launcher-crate terminology to
  the post-relocation layout — the `luminosity` launcher binary is the `launcher`
  crate at `cli/launcher/`, and `cli` now names the whole workspace, not the
  crate. Clarified that `reqwest` + rustls is pinned once in `cli/Cargo.toml`
  `[workspace.dependencies]` and consumed by `launcher` (kernel stays
  dependency-light), and named `cli/launcher/Cargo.toml` as the version-bearing
  manifest in the coherence requirement. Reconciled frontmatter `blocked_by`
  (0007, 0002) with the body's Blocked-by line, and added 0014 to `relates_to`.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Spike: `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- Scaffold: `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md`
- Relocation: `meta/work/0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- Research: cargo-zigbuild; minisign; reqwest + rustls (vs native-tls); rustup
  proxy/shim model; uv tool caching.
