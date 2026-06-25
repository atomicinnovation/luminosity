---
type: adr
id: "ADR-0010"
title: "Git-Style Modular CLI of On-Demand Static Binaries"
date: "2026-06-26T00:29:29+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0005"
relates_to: ["adr:ADR-0001", "adr:ADR-0002", "adr:ADR-0009"]
tags: [architecture, cli, modular, git-style, dispatch, launcher, workspace, rust]
last_updated: "2026-06-26T00:29:29+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0010: Git-Style Modular CLI of On-Demand Static Binaries

**Date**: 2026-06-26
**Status**: Accepted
**Author**: Toby Clemson

## Context

Luminosity runs its deterministic work in a compiled Rust CLI (ADR-0001),
distributed as zero-setup, fully static binaries the plugin fetches and verifies
on demand (ADR-0002), with its domain code structured as a hexagon (ADR-0009).
Two questions those decisions deliberately left open meet here: how the CLI is
*composed* from more than one binary, and how a single entry point *dispatches*
to and *resolves* them at runtime.

ADR-0009 records the hexagonal pattern and the inward-dependency rule but defers
"how the CLI is packaged and dispatched — the git-style, multi-binary, on-demand
modular split" to this decision. ADR-0002 records the distribution model
(cross-compile, release orchestration, sha256+minisign integrity) but defers "the
git-style modular composition" and "the launcher's dispatch/resolution internals"
here too. This ADR fills exactly that gap. A spike (work item 0002) resolved the
choices; its Recommendation §1 (crate split), §2 (dispatch), and §3 (launcher)
are the source. No Rust code exists yet; this governs the scaffold (0007) and the
launcher/distribution story (0008).

The forces:

- The product grows by adding subdomains (e.g. ads, video) with **divergent and
  potentially heavy dependency profiles**. A single binary carrying all of them
  would ship every subdomain's dependency tail to every user — the opposite of
  the lean, on-demand goal.
- Distribution is **per-platform and on-demand** (ADR-0002): the unit that is
  independently fetched and versioned must be the unit of composition.
- Users meet **one command** (`luminosity`), not a scatter of tools, so growth
  must be invisible at the entry point and the surface must stay discoverable.
- The launcher's fetch → verify → cache → exec logic is load-bearing and must be
  **testable**, not buried in shell on a bash 3.2 floor.
- The four target triples (ADR-0002) are **all Unix**, which removes the Windows
  process model from consideration.

## Decision Drivers

- One binary per independently-shippable subdomain, so a subdomain's dependencies
  never bleed into another or into every user's download.
- A single command-line entry point that grows by on-demand subcommands without
  changing its surface.
- Dispatch and launcher resolution implemented in testable Rust, not shell.
- A discoverable surface despite subcommands that are not present until fetched.
- Fit to the per-platform, individually-fetched distribution model (ADR-0002),
  not a model that releases a fixed binary set together.

## Considered Options

1. **Git-style multi-binary workspace, decomposed by bounded context** — a
   `luminosity` launcher dispatching to independently-shipped `luminosity-<sub>`
   sub-binaries, one Cargo crate per subdomain, fetched and exec'd on demand.
2. **Single fat multicall binary (busybox-style)** — one binary containing every
   subdomain, dispatching internally by `argv[0]`/first arg.
3. **rustup-style shim/proxy model** — per-tool shim binaries placed on `PATH`,
   each proxying to a managed toolchain.
4. **One shared `core` crate with sub-commands as inbound adapters** — a single
   package, subcommands distinguished only at the command layer.

## Decision

We will compose the CLI as a **git-style modular command: a single `luminosity`
launcher that dispatches to on-demand, independently-shipped static
sub-binaries**, with the workspace decomposed by bounded context.

**Composition — the binary axis.** The CLI is a Cargo workspace whose primary
decomposition axis is the **subdomain (bounded context)**, because the git-style
model ships independently-fetched sub-binaries and multiple binaries from one
package would force a single shared dependency set and version. Each
independently-shippable sub-binary is its own crate (`luminosity-<sub>`) and its
own composition root. Supporting crates:

- **`kernel`** — a deliberately dependency-light crate for genuinely
  cross-cutting concerns (error taxonomy, the config-access and dispatch/launcher
  contracts, logging); everything links it, so a dependency tail is resisted.
- **`config`** — a shared crate other subdomains may depend on, itself split into
  `config` (domain + application + ports) and `config-adapters` (outbound
  readers). Each sub-binary wires its own `config-adapters` at its composition
  root (Model 1); resolving config once in the launcher and injecting it (Model 2)
  is held in reserve.
- **`cli`** — the `luminosity` launcher binary; depends on `kernel` (and `config`,
  for the built-in `config` command), never on a subdomain.

The *hexagonal layering within* each subdomain, and the inward-dependency
enforcement across all of it, are governed by ADR-0009; this decision settles
only the binary axis — what is split into separately-shippable units and why.

**Dispatch.** `luminosity` uses clap 4.x derive
`#[command(external_subcommand)] External(Vec<OsString>)`: the first element is
the subcommand name, the rest are forwarded verbatim, and `Vec<OsString>`
(not `String`) preserves non-UTF-8 arguments.

- `version` and `config` are **built-in** subcommands compiled into `luminosity`;
  external dispatch is purely the *growth* mechanism for on-demand subdomains.
- Dispatch is **Unix `exec` only** (`CommandExt::exec`, process-replacing, so exit
  codes and signals propagate). Windows is out of scope — the four targets are all
  Unix.
- Because clap cannot list external subcommands, the surface is made discoverable
  by rendering clap's built-in help plus a synthesised "external subcommands"
  section built from the release manifest's `description` field (the manifest the
  launcher already needs — one extra field, no executing untrusted binaries to
  introspect them). Per-command `--help` is **delegated** by re-exec'ing the child
  with `--help` (cargo's convention).

**Launcher resolution.** The fetch → verify → cache → exec pipeline for
sub-binaries lives **inside the Rust `cli` binary**, not in bash. A **thin bash
bootstrap** fetches the `luminosity` binary itself on first use; thereafter the
Rust launcher owns everything. Resolution is **uv-style resolve-once-and-cache**:
a managed cache dir is scanned first, keyed by name+version+checksum, with
fetch-on-miss. The HTTP/TLS stack is **`reqwest` + rustls workspace-wide**
(`default-features = false`), chosen over `ureq` for sync+async uniformity from
one dependency. There is **no launcher self-update**: a new plugin version drives
a new launcher via the bootstrap, and sub-binaries re-fetch on manifest-hash
change. (The integrity layers this pipeline applies — sha256 and minisign — and
the cross-compile/release machinery are ADR-0002's; this decision settles only
*where* resolution runs and *how* dispatch finds its target.)

We chose option 1 because only an independently-shipped binary per subdomain
keeps each subdomain's dependency tail out of every other binary and matches the
per-platform, on-demand distribution model, while a single launcher keeps the
user-facing surface to one command. Option 2 (fat multicall binary) was rejected:
it grows monolithically and ships every subdomain's dependencies to everyone — the
opposite of on-demand. Option 3 (rustup shims) was rejected: its per-tool-on-PATH
benefit does not apply to a single-entry-point CLI and it adds shim management for
no gain. Option 4 (one shared `core`) was rejected: a subdomain's heavy
dependencies (e.g. video codecs) would land in the shared closure and bleed into
every binary, defeating the lean goal.

## Consequences

### Positive

- Each subdomain ships independently; a subdomain's heavy dependencies never enter
  another binary or every user's download.
- The user meets a single `luminosity` command that grows by on-demand subcommands
  without any change to its surface.
- Dispatch and launcher resolution are implemented in testable Rust rather than
  shell, keeping load-bearing logic out of the bash 3.2 floor.
- Unix-only `exec` gives natural signal and exit-code propagation with no
  spawn-and-wait shim.
- The manifest-driven listing keeps the surface discoverable even though external
  subcommands are absent until fetched, without executing untrusted binaries.

### Negative

- A workspace of per-subdomain binaries plus a launcher is more moving parts than
  a single binary — more crates, composition roots, and a release manifest to keep
  coherent.
- First use of any subdomain requires a network fetch; the on-demand model has a
  cold-start cost a bundled binary would not.
- Synthesising help and listings outside clap's generator is bespoke work that
  must track the manifest format.
- A bash bootstrap remains on the critical path for first launch, retaining a thin
  slice of shell despite moving the rest into Rust.
- The reqwest/rustls choice pulls `tokio` into the launcher for sync+async
  uniformity — a heavier dependency tree than a sync-only client (`ureq`) would
  carry, accepted as the price of one HTTP stack workspace-wide.

### Neutral

- `version` and `config` are built-in; all other subdomains arrive via external
  dispatch — the split between compiled-in and fetched commands is a deliberate,
  standing distinction.
- The config composition root starts as Model 1 (each sub-binary wires its own
  `config-adapters`); moving to Model 2 (launcher resolves once and injects) is a
  reserved option, triggered only if resolution becomes expensive or a single
  per-invocation source of truth is wanted.
- clap's derive enabling external dispatch without a manual builder call is to be
  confirmed on the pinned clap version when the scaffold (0007) is built; low risk.
- The exact managed cache/bin directory path is owned by the distribution story
  (0008), not fixed here.
- The hexagonal layering within each subdomain and the inward-dependency
  enforcement are ADR-0009's; the integrity, signing, and cross-compile machinery
  are ADR-0002's. This decision composes with both and re-decides neither.

## References

- `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
  — Feeding spike; Recommendation §1 (crate split), §2 (dispatch), and §3
  (launcher) are the source of this decision.
- `meta/work/0005-record-spike-dependent-architecture-decisions-as-adrs.md` —
  Owning story (decision 10 of the baseline set).
- `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md` —
  Scaffold that realises the workspace and confirms clap's external-dispatch
  behaviour.
- `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md` —
  Implementation story owning the launcher pipeline and cache-path detail.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Establishes the
  CLI exists.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` —
  Distribution model; defers git-style composition and launcher dispatch internals
  here.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md` —
  Hexagonal pattern and dependency enforcement; defers packaging and dispatch here.
