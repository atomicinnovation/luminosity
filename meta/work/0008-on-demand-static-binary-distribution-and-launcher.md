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
tags: [story, rust, distribution, launcher, cross-compile]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0008: On-Demand Static-Binary Distribution & Launcher

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Build static, dependency-free `luminosity` binaries for the four target
platforms and a launcher that fetches the correct per-platform binary on demand,
so the end user installs nothing and the git-style modular CLI can grow as
on-demand sub-binaries.

## Context

Zero user setup is a core architectural goal (the plugin downloads static
binaries; the user installs nothing). The git-style modular CLI presents as a
single `luminosity` command that dispatches to sub-binaries fetched on demand.
This story implements the distribution and launcher per the architecture spike's
recommendation, building on the hexagonal workspace skeleton. The accelerator's
solved approach is confirmed and reused where it fits, rather than reinvented.

## Requirements

**Target platforms** (target triple → distribution alias):

- `aarch64-apple-darwin` → `darwin-arm64`
- `x86_64-apple-darwin` → `darwin-x64`
- `aarch64-unknown-linux-musl` → `linux-arm64`
- `x86_64-unknown-linux-musl` → `linux-x64`

- Produce fully static binaries for all four platforms (musl gives fully static
  Linux binaries). Cross-compilation via `cargo-zigbuild` (with `cross` as a
  fallback for awkward native deps); per-platform release artifacts via `dist`
  (formerly cargo-dist).
- Publish per-platform artifacts and their checksums as GitHub Release assets
  (dist's default), optionally backed by GitHub Attestations for provenance.
- Implement the launcher (rustup/uv-style): resolve a sub-binary, fetch it from
  GitHub Releases if absent, verify it against the published checksum, cache it
  in a managed bin dir, then exec it (exec on Unix — all four target platforms
  are Unix). The launcher itself must stay statically linkable — rustls (not
  OpenSSL), built with `default-features = false`.
- No separate signing infrastructure in this slice: integrity rests on checksums
  plus optional GitHub Attestations, not minisign/zipsign signatures.
- Confirm which of these tools the accelerator already uses before re-selecting,
  per the architecture spike's recommendation.

## Acceptance Criteria

- [ ] Static binaries build for all four target platforms, each published as a
      GitHub Release asset with a checksum, and verifiably static (no dynamic
      libc dependency on the musl targets).
- [ ] Given a platform, when the launcher needs an absent sub-binary, then it
      fetches the asset matching the host target triple from GitHub Releases,
      verifies its checksum against the published value, caches it in the managed
      bin dir, and execs it.
- [ ] Given a sub-binary already cached, when invoked again, then the launcher
      reuses the cache without re-fetching.
- [ ] Given a checksum mismatch, when the launcher verifies a fetched binary,
      then it refuses to exec and reports the failure.
- [ ] The launcher binary is statically linkable (rustls, no OpenSSL).

## Open Questions

- Whether GitHub Attestations are enabled in this slice or deferred is an
  implementation choice; checksum verification is required either way.

## Dependencies

- Blocked by: the scaffold story (0007, binaries are built from the workspace);
  the architecture spike (0002, decides the launcher pipeline and distribution
  tooling).
- Blocks: none directly; enables the modular CLI to grow as on-demand
  sub-binaries.
- Parent: epic 0001.

## Assumptions

- Zero-setup binary distribution is ported from the accelerator's solved approach
  rather than designed from scratch (A1), adapted where Luminosity differs.

## Technical Notes

- `cargo-zigbuild` is the current default for musl-static / macOS cross builds;
  `dist` v0.32+ provides checksums (sha256+), cargo-auditable, SBOM, and GitHub
  Attestations, publishing to GitHub Releases. Compose download/verify/cache
  directly for a multi-sub-binary launcher.
- rustls + webpki-roots keeps the launcher independent of the host cert store;
  audit the dep tree so nothing re-enables `default-tls`.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (build pipeline +
  launcher).
- Tooling reflects mid-2026 research (cargo-zigbuild, dist, rustls launcher);
  final selection follows the architecture spike's recommendation and a check of
  what the accelerator already uses.
- Integrity scope set to checksums + optional GitHub Attestations (no signing
  keys) and fetch source set to GitHub Releases, per the author.
- Windows handling dropped: none of the four target platforms are Windows, so the
  launcher's exec path is Unix-only.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Research: cargo-zigbuild; dist (formerly cargo-dist); self_update / self-replace;
  rustls vs native-tls; rustup proxy/shim model; uv tool caching.
