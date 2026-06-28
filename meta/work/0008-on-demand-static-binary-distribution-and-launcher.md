---
type: work-item
id: "0008"
title: "On-Demand Static-Binary Distribution & Launcher"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
relates_to: ["work-item:0002"]
tags: [story, rust, distribution, launcher, cross-compile, dispatch]
last_updated: "2026-06-28T16:16:24+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0008: On-Demand Static-Binary Distribution & Launcher

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Build zero-setup, fully static `luminosity` binaries for the four target
platforms and the git-style launcher that fetches the correct per-platform
binary on demand, verifies it (sha256 + minisign), caches it, and execs it — plus
the clap external-subcommand dispatch that lets the single `luminosity` command
grow as on-demand sub-binaries. The end user installs nothing.

## Context

Zero user setup is a core architectural goal (ADR-0002): the plugin downloads
static, dependency-free binaries and the user installs no toolchain, runtime, or
package manager. The git-style modular CLI (ADR-0010) presents as a single
`luminosity` command that dispatches to sub-binaries fetched on demand. This story
implements the distribution and launcher, building on the hexagonal workspace
scaffold (0007).

Two accepted ADRs settle the choices this story realises. **ADR-0002** fixes the
distribution model: fully static binaries (musl on Linux), cross-compiled with
`cargo-zigbuild`, released by a hand-rolled Python invoke + `gh` pipeline (chosen
over `dist`/cargo-dist), with integrity resting on sha256 **plus minisign**
verified in-process — not GitHub Attestations or TLS alone. **ADR-0010** fixes
the composition (one independently-shipped binary per subdomain), the dispatch
(clap `external_subcommand`, Unix `exec`, `version`/`config` built-in,
manifest-driven discoverable help), and the launcher resolution (fetch → verify →
cache → exec in the Rust `cli` binary, behind a thin bash bootstrap). The
external-subcommand dispatch and the confirmation of clap's derive behaviour were
relocated here from the scaffold story (0007), which owns only the in-process
`version` subcommand.

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
  coherence** across `plugin.json`, the CLI's `Cargo.toml`, and the release
  manifest.
- **Launcher resolution** (ADR-0010) — implemented inside the Rust `cli` binary,
  not in bash: a uv-style **resolve-once-and-cache** pipeline that scans a managed
  cache/bin directory first (keyed by name + version + checksum), fetches the
  asset matching the host target triple from GitHub Releases on miss, verifies it
  (sha256 + minisign), caches it, then execs it. Dispatch is **Unix `exec`**
  (`CommandExt::exec`, process-replacing, so exit codes and signals propagate);
  Windows is out of scope (all four targets are Unix). The HTTP/TLS stack is
  **`reqwest` + rustls** workspace-wide (`default-features = false`), keeping the
  launcher statically linkable and independent of the host cert store; no OpenSSL
  / native-tls. There is **no launcher self-update** — a new plugin version drives
  a new launcher via the bootstrap, and sub-binaries re-fetch on manifest-hash
  change.
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
  pinned clap version (the confirmation ADR-0009/ADR-0010 attribute to the
  scaffold, relocated here from 0007).
- **Discoverable surface** (ADR-0010) — because clap cannot enumerate external
  subcommands, render clap's built-in help plus a synthesised "external
  subcommands" section built from the release manifest's `description` field (no
  executing untrusted binaries to introspect them). Per-command `--help` is
  **delegated** by re-exec'ing the child with `--help`.

## Acceptance Criteria

- [ ] Static binaries build for all four target platforms, each published as a
      GitHub Release asset with a sha256 checksum **and** a minisign signature,
      and verifiably static (no dynamic libc dependency on the musl targets).
- [ ] Given a platform, when the launcher needs an absent sub-binary, then it
      fetches the asset matching the host target triple from GitHub Releases,
      verifies its sha256 **and** minisign signature, caches it in the managed
      bin dir keyed by name + version + checksum, and execs it.
- [ ] Given a sub-binary already cached, when invoked again, then the launcher
      reuses the cache without re-fetching (resolve-once-and-cache).
- [ ] Given a checksum or signature mismatch (checked on fetch and re-verified
      before exec), when the launcher verifies a binary, then it refuses to exec
      and reports the failure.
- [ ] Given `luminosity <external-sub> <args>`, when dispatched, then clap routes
      it via `External(Vec<OsString>)`, the launcher resolves and execs the
      sub-binary, and exit codes and signals propagate (Unix `exec`); `version`
      and `config` remain built-in.
- [ ] Given `luminosity --help`, when run, then the output lists the built-in
      commands plus a synthesised external-subcommands section drawn from the
      manifest's `description` field, and `luminosity <sub> --help` is delegated
      to the child.
- [ ] The launcher binary is statically linkable (`reqwest` + rustls,
      `default-features = false`, no OpenSSL) and performs no self-update.
- [ ] Version coherence holds across `plugin.json`, the CLI's `Cargo.toml`, and
      the release manifest, enforced by the release pipeline.

## Open Questions

- The exact managed cache/bin directory path is deferred here by ADR-0002 and
  ADR-0010; it is settled during implementation.
- This story now spans the build pipeline, signing, the launcher resolution
  pipeline, external dispatch, and the bash bootstrap — a large surface. Whether
  to split it (e.g. distribution/signing vs launcher/dispatch) is worth a
  planning review; it is kept as one story here to match the ADRs' single
  launcher/distribution framing.

## Dependencies

- Blocked by: the scaffold story (0007 — binaries are built from the hexagonal
  workspace, and external dispatch builds on its clap inbound boundary); the
  architecture spike (0002, decides the launcher pipeline and distribution
  tooling).
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
  stack — accepted per ADR-0010 as the price of one TLS stack workspace-wide.
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
- **Story size (flagged)**: noted in Open Questions that the combined scope is
  large; kept as one story to match the ADRs' single launcher/distribution
  framing, but flagged for a possible split at planning.
- Kind set to `story`: a concrete, bounded deliverable (build pipeline + launcher
  + dispatch).
- Windows handling dropped: none of the four target platforms are Windows, so the
  launcher's exec path is Unix-only.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Spike: `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
- Scaffold: `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md`
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
- Research: cargo-zigbuild; minisign; reqwest + rustls (vs native-tls); rustup
  proxy/shim model; uv tool caching.
