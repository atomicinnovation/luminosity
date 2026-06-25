---
type: adr
id: "ADR-0009"
title: "Thin CLI over a Hexagonal Ports-and-Adapters Core"
date: "2026-06-25T14:57:12+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0005"
relates_to: ["adr:ADR-0001", "adr:ADR-0002", "adr:ADR-0004"]
tags: [architecture, hexagonal, ports-and-adapters, dependency-inversion, rust, cli]
last_updated: "2026-06-25T14:57:12+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0009: Thin CLI over a Hexagonal Ports-and-Adapters Core

**Date**: 2026-06-25
**Status**: Accepted
**Author**: Toby Clemson

## Context

Luminosity runs its deterministic work in a compiled Rust CLI (ADR-0001), with
Rust as the product/domain language (ADR-0004). That code is not glue: it carries
real domain logic for content production, and it must stay testable and
changeable as the infrastructure around it — configuration formats, the
filesystem, network fetches, external media tooling, the command-line surface
itself — evolves independently of the rules at the centre.

ADR-0001 established *that* the CLI exists and deferred its internal architecture
to "decision 9". A spike (work item 0002) confirmed the pattern. This ADR records
that pattern — how domain code is structured and how infrastructure attaches to
it. How the CLI is *packaged and dispatched* (the git-style, multi-binary,
on-demand modular split) is a distinct concern, recorded as decision 10. No Rust
code exists yet; this decision governs the scaffold (work item 0007).

The forces:

- Domain logic must be isolated from I/O and infrastructure so it can be
  unit-tested without them and so adapters can change without touching the rules.
- Many infrastructure concerns (config, filesystem, network, CLI parsing,
  external tools) attach to the same domain; the structure must admit many
  adapters without coupling them to one another or to the core.
- That isolation must be a load-bearing, enforced rule — not an intention that
  erodes under delivery pressure.

## Decision Drivers

- A domain core that is unit-testable in isolation from infrastructure.
- Dependencies that point inward toward the domain, enforced mechanically rather
  than by convention.
- Thin, replaceable adapters at every boundary — the CLI is just one of them.
- Ports expressed in the domain's own language, so the core never speaks
  serde/toml/fs/http.
- A single, uniform structure every subdomain follows.

## Considered Options

1. **Hexagonal (ports and adapters)** — a domain/application core whose
   boundaries are ports (traits); all I/O and infrastructure live in adapters
   outside the core, depending inward.
2. **Classic layered / n-tier** — presentation → service → data-access, where the
   domain sits above and depends on a persistence/infrastructure layer.
3. **Transaction script** — commands call infrastructure directly, business logic
   interleaved with I/O, no isolated domain.

## Decision

We will structure the CLI's domain code as a **hexagonal, ports-and-adapters
architecture**: a thin CLI (and thin adapters generally) over a rich domain core.

Each unit of domain code is a hexagon with three concerns:

- **A domain + application core** that holds the business logic and depends on no
  infrastructure. It defines its boundaries as **ports — traits** — covering both
  **inbound/driving** ports (the operations the core offers its callers) and
  **outbound/driven** ports (the capabilities the core requires: config access,
  filesystem, network, external tools), expressed in the domain's own terms.
- **Inbound adapters** that drive the core through its inbound ports. The **CLI is
  the primary inbound adapter** — argument parsing and presentation only,
  delegating immediately into the core. It is deliberately thin: no business
  logic lives in the command layer.
- **Outbound adapters** that implement the outbound ports against concrete
  technology (serde/toml config readers, the filesystem, HTTP over rustls,
  wrappers around external media binaries). Adapters depend on the core; the core
  depends on neither inbound nor outbound adapters.

Concrete adapters are bound to ports at a **composition root**, so the core is
constructed against traits and never against concrete infrastructure — which is
also what lets it be tested with in-memory fakes.

The **inward dependency direction is the load-bearing rule**, enforced
mechanically rather than trusted to discipline. Two mechanisms apply at
different granularities:

- **Crate boundaries** enforce direction *between* crates: where layers and
  contexts are separate crates, the Cargo dependency graph makes a violation fail
  to compile, and `cargo-deny` ban-lists keep infrastructure crates out of the
  core's dependency closure.
- **`cargo-pup`** enforces direction *inside* a crate, at module granularity, on
  a pinned-nightly lane (the product build and all other checks stay on stable).

Because each subdomain begins as a single crate with its layers as modules,
crate boundaries are initially inert and `cargo-pup` is the sole enforcer of the
inward rule until a subdomain is split into separate crates.

Within a subdomain the hexagon's concerns begin as modules of a single crate;
their concrete layout is settled by the scaffold (work item 0007). How far
the codebase is then split into separate crates and independently-shipped
binaries is a packaging-and-dispatch concern governed by **decision 10**, not by
this decision: the pattern and the dependency rule hold regardless of packaging
granularity.

We chose option 1 because it isolates the domain behind ports so it can be tested
and evolved independently of every I/O concern, and admits many adapters without
coupling them. Option 2 was rejected: in a layered model the domain still depends
on the layer beneath it, so persistence and infrastructure choices leak upward
into the rules — the dependency inversion we want is exactly what
ports-and-adapters gives and layering does not. Option 3 was rejected:
interleaving logic with I/O leaves nothing testable in isolation and will not
survive the domain's expected growth.

## Consequences

### Positive

- The domain core is unit-testable in isolation, with adapters faked at the
  ports.
- Infrastructure (config formats, filesystem, network, media tools) can change
  behind its port without touching the core.
- Dependency direction is enforced by the compiler and CI, not by convention.
- A uniform shape across subdomains lowers the cost of moving between them.
- The CLI surface stays thin and replaceable — another inbound adapter (a
  library or service entry) could drive the same core unchanged.

### Negative

- Ports-and-adapters adds indirection (traits plus wiring) that is overhead for
  trivial commands carrying no real domain logic.
- The `cargo-pup` enforcement needs a pinned-nightly lane (it hooks `rustc`
  internals) — extra toolchain surface and real fragility — and in the
  single-crate starting state it is the *only* mechanism enforcing the inward
  rule, with no cruder floor behind it. If the nightly lane breaks or is
  downgraded to advisory, the rule is unguarded until it is restored or the
  subdomain is split into crates (mitigation: pin and bump the nightly
  deliberately; treat lane breakage as a fix-now signal).
- The dependency rule is a standing contract every adapter and subdomain must
  respect, policed by several mechanisms rather than one.

### Neutral

- Ports are defined as traits in the core; both driving and driven ports live
  with the domain/application, not with the adapters.
- The hexagon starts as a single crate with layers as modules; crate- and
  binary-level decomposition is deferred to decision 10.
- The feeding spike also proposed a zero-dependency CI grep tripwire as a floor
  beneath `cargo-pup`; this decision deliberately omits it, treating `cargo-pup`
  as sufficient and accepting that the single-crate phase has no cruder backstop.
- No code exists yet; the pattern is realised by the scaffold (work item 0007),
  where clap's derive behaviour at the inbound boundary will be confirmed.

## References

- `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
  — Feeding spike; Recommendation §1 is the source of this decision.
- `meta/work/0005-record-spike-dependent-architecture-decisions-as-adrs.md` —
  Owning story (decision 9 of the baseline set).
- `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md` —
  Scaffold that realises this pattern and settles the concrete module layout.
- `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md` —
  Packaging and dispatch (decision 10); not yet recorded as an ADR.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Establishes the
  CLI exists; defers its internal architecture to this decision.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` —
  Distribution; defers git-style dispatch/composition to decision 10.
- `meta/decisions/ADR-0004-three-toolchain-split.md` — Rust as the product/domain
  language.
