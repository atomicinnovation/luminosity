---
type: adr
id: "ADR-0002"
title: "Zero-Setup Static-Binary Distribution"
date: "2026-06-24T15:42:45+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0004"
relates_to: ["adr:ADR-0001"]
tags: [architecture, distribution, static-binaries, zero-setup, rust, foundations]
last_updated: "2026-06-24T15:42:45+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0002: Zero-Setup Static-Binary Distribution

**Date**: 2026-06-24
**Status**: Accepted
**Author**: Toby Clemson

## Context

Luminosity delegates all deterministic procedural logic to a compiled CLI
(ADR-0001). That CLI is an artifact that must reach the end user's machine.
Luminosity is a Claude Code plugin installed from a marketplace by people who are
not necessarily Rust developers and who should not have to provision a toolchain,
a runtime, or a package manager to use it. The supported platforms are macOS and
Linux on both arm64 and x64 — four target triples, all Unix.

A compiled CLI introduces a distribution problem: a binary must exist for the
user's platform, must run there without a local build toolchain or a matching
system library, must arrive without manual installation steps, and must be
verifiable before it is trusted to run. On Linux in particular, linking against
the host's glibc and system libraries is fragile across the range of
distributions a user might run.

The modular-CLI architecture spike (work item 0002) investigated how to build,
sign, and deliver these binaries, evaluating current options on merit rather than
adopting any prior approach by default. Its §3 (on-demand launcher) and §4
(cross-compile & distribution) settled the concrete choices this ADR records. The
Accelerator plugin (https://github.com/atomicinnovation/accelerator) was one
input the spike analysed directly: its *distribution* pipeline was found to port
cleanly, while its *launcher* (a bash daemon) does not model a git-style
sub-binary CLI and was deliberately not carried over.

## Decision Drivers

- **Zero user setup** — the end user installs nothing beyond the plugin itself;
  no toolchain, runtime, package manager, or `PATH` configuration.
- **Runs on diverse hosts** — the binary must execute without a local build
  toolchain and without depending on a specific host libc or system libraries.
- **Integrity** — a fetched binary must be verifiable, and verifiably built by
  us, before it is executed.
- **Per-platform delivery without bloat** — each user receives only the binary
  for their platform, not a bundle of all four.
- **Reuse existing repo infrastructure** — the Python invoke task system already
  in the repo, rather than new release tooling, where it serves the model well.
- **A prior pipeline exerts pull** — the Accelerator's distribution pipeline is
  a ready porting source, creating gravity toward wholesale adoption; tooling
  must instead be chosen on its fit for an individually-fetched, per-platform
  binary model, not inherited by default.

## Considered Options

1. **Fully static binaries the plugin fetches and verifies on demand** — built
   for the four targets (musl on Linux for full static linking), cross-compiled,
   published as checksummed and signed release assets, fetched and verified by the
   plugin at runtime; the user installs nothing.
2. **User-installed CLI** — the user obtains the binary themselves via
   `cargo install`, a package manager (Homebrew, etc.), or a manual download plus
   `PATH` setup.
3. **Vendor prebuilt binaries inside the plugin package** — ship all four
   platform binaries as part of the plugin distribution, so no runtime download
   occurs.
4. **Dynamically-linked binaries** — distribute on demand as in option 1 but link
   against the host libc and system libraries (and, for TLS, native-tls/OpenSSL)
   rather than building fully static binaries.

## Decision

We will distribute the CLI as **zero-setup, fully static, dependency-free
binaries that the plugin fetches, verifies, and executes on demand**, so the end
user installs nothing. Linux targets are built against **musl** for full static
linking; macOS and Linux on both arm64 and x64 are the four supported targets.

Per the spike's §3–§4, the concrete model — detail owned by the distribution
story (work item 0008) — is:

- **Cross-compilation** with `cargo-zigbuild`, producing fully static musl Linux
  binaries and macOS binaries from one host.
- **Release orchestration** as a hand-rolled pipeline (Python invoke tasks +
  `gh`) with re-download-and-re-verify and **version coherence** across
  `plugin.json`, the CLI's `Cargo.toml`, and the release manifest — chosen over
  `dist`/cargo-dist, which is oriented at a fixed set of workspace binaries
  released together and fights the individually-fetched, per-platform model, and
  which would add tooling the repo's existing invoke infrastructure makes
  unnecessary.
- **Integrity** layered as sha256 (verified on fetch and re-verified before every
  exec) plus TLS in transit, **plus minisign** signing verified in-process — so
  trust rests on "signed by our key", not merely "served over TLS". In-process
  Sigstore/SLSA-provenance verification was parked until that ecosystem
  stabilises.
- **rustls throughout, not OpenSSL/native-tls** — a static-linking
  prerequisite, not a launcher-architecture choice: native-tls breaks
  musl-static linking, so rustls is what makes the fully static binary
  achievable at all. (The launcher's dispatch/resolution internals remain
  decision 10's; only the TLS stack that static linking forces is settled
  here.)

We chose option 1 because it is the only option that delivers zero user setup
*and* runs reliably across diverse hosts. Option 2 was rejected: requiring the
user to install a toolchain, package, or `PATH` entry defeats the frictionless
plugin install and excludes non-developers. Option 3 was rejected: bundling all
four platforms bloats every install and rigidly couples the binary's release
cadence to the plugin's, while still requiring static binaries to run portably.
Option 4 was rejected: dynamic linking reintroduces a dependency on the host's
libc and system libraries — fragile across Linux distributions — and native-tls
in particular breaks musl-static linking, defeating the "runs anywhere with no
setup" guarantee that static linking provides.

This ADR records the **distribution model** — that the CLI reaches users as
zero-setup static binaries the plugin builds, signs, and delivers. The **git-style
modular composition** of the CLI from on-demand sub-binaries and the launcher's
dispatch/resolution internals are a separate, spike-dependent decision (decision
10 in epic 0001's set); the full launcher and distribution implementation is
owned by work item 0008.

## Consequences

### Positive

- The end user installs nothing; the CLI works out of the box on all four target
  platforms.
- Fully static musl binaries are immune to host libc/runtime drift, so they run
  across heterogeneous Linux distributions without per-host adaptation.
- Reusing the repo's existing invoke infrastructure for release orchestration
  avoids adopting and maintaining a separate release tool.
- minisign signing plus sha256 gives integrity that authenticates the build, not
  just the transport, and verifies in-process with no `gh` dependency on the
  user's machine.
- On-demand, per-platform fetching keeps the plugin package small — each user
  pulls only their platform's binary.

### Negative

- Introduces a build and distribution pipeline (cross-compilation for four
  targets, hand-rolled release orchestration, checksum and signature generation
  and verification) that must be built and maintained in-house rather than
  delegated to an off-the-shelf tool.
- First use of a binary requires network access to fetch it; offline or
  air-gapped environments need a fallback this model does not itself provide.
- Adds a version-coherence obligation across `plugin.json`, the CLI's
  `Cargo.toml`, and the release manifest.
- Introduces minisign key management (generation, protection, rotation) as an
  operational responsibility; a leaked key forges releases.
- musl static builds carry known caveats (some native dependencies, DNS
  resolution behaviour) that dynamic builds avoid.

### Neutral

- Binaries are hosted as GitHub Release assets and cached in a plugin-managed bin
  directory; the exact cache path is deferred to work item 0008.
- In-process Sigstore/SLSA-provenance verification is deferred, to be revisited if
  that ecosystem reaches a stable, musl-friendly 1.0 — at which point it would
  strengthen, not replace, the integrity story.
- The four supported targets are `darwin-arm64`, `darwin-x64`, `linux-arm64`, and
  `linux-x64` (the Linux targets via musl).
- The git-style modular CLI structure and the launcher's dispatch internals are
  governed by a separate decision (decision 10 / work item 0008).

## References

- `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
  — Architecture spike; §3 (on-demand launcher) and §4 (cross-compile &
  distribution) settle the choices recorded here, evaluating alternatives on
  merit.
- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — Epic;
  states the "Zero user setup" goal and the four target platforms.
- `meta/work/0004-record-existing-implicit-architecture-decisions-as-adrs.md` —
  Owning story (decision 2 of 1–8).
- `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md` —
  Implementation story owning the full launcher and distribution pipeline.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Related; the CLI
  whose distribution this ADR records.
