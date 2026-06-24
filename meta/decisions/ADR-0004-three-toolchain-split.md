---
type: adr
id: "ADR-0004"
title: "Three-Toolchain Split (Python / Shell / Rust)"
date: "2026-06-24T16:46:21+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0004"
relates_to: ["adr:ADR-0001", "adr:ADR-0002"]
tags: [architecture, toolchain, rust, python, shell, foundations]
last_updated: "2026-06-24T16:46:21+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0004: Three-Toolchain Split (Python / Shell / Rust)

**Date**: 2026-06-24
**Status**: Accepted
**Author**: Toby Clemson

## Context

Luminosity is a Claude Code plugin. The repository's initial layout was based on
the Accelerator plugin, which used **shell as its runtime substrate** (config
reading, VCS detection, frontmatter parsing, migrations, hooks) with **Python**
for build tooling. ADR-0001 deliberately moves away from that substrate:
deterministic procedural logic belongs in a compiled CLI, not in a body of bash.

Stated forward-looking, three language toolchains have distinct, deliberately
unequal roles:

- **Rust** carries the bulk of the domain — the deterministic product core. The
  CLI is the home for the procedural logic skills delegate to, and the logic
  behind the plugin's hooks belongs here too. Distributed as zero-setup static
  binaries (ADR-0002).
- **Python** is the support language: build, release, and automation tooling
  (invoke tasks under `tasks/`, run through `mise`, type-checked with pyrefly and
  linted with ruff), *and* the general-purpose test language for the non-Rust
  surfaces — testing shell wrappers and writing guardrail tests for components
  that aren't Rust, such as the CI pipeline.
- **Shell (bash)** is confined to **thin wrappers only**, used where the plugin or
  host environment strictly requires a shell entry point and where the wrapper
  does little more than resolve and delegate to the CLI.

Each toolchain carries its own formatters, linters, checks, and pinned versions.
This ADR records the standing decision to keep three toolchains with these roles
— Rust-dominant, Python-supporting, shell-minimal — rather than consolidating
onto fewer or reverting to a shell substrate.

## Decision Drivers

- Put the bulk of the domain in one compiled, statically typed, testable,
  distributable language (Rust), per ADR-0001 and ADR-0002.
- Keep a fast-iterating, mature support language for build, release, and
  automation — and, critically, a test language *separate from the product core*
  for exercising the non-Rust surfaces (shell wrappers, CI guardrails).
- Minimise shell to thin wrappers only, avoiding the untestable shell substrate
  ADR-0001 exists to leave behind.
- Use each language for what it is genuinely best at, and accept the cost of an
  extra toolchain only where it earns its place.

## Considered Options

1. **Three toolchains with Rust-dominant roles** — Rust for the bulk of the
   domain (CLI and hook logic), Python as the support language (build, release,
   automation, and testing of non-Rust surfaces), shell as thin wrappers only
   where strictly needed.
2. **Single language** — drive everything from Rust (including build/release
   automation and the tests for non-Rust surfaces), or the Accelerator-style
   shell-substrate-plus-Python with no compiled core.
3. **Two toolchains** — Rust plus Python with shell forbidden outright, or Rust
   plus shell with Python's support role dropped.

## Decision

We will keep **three toolchains in deliberately unequal roles**: **Rust** for the
bulk of the domain (the deterministic CLI core and the logic behind hooks),
**Python** as the support language (build, release, automation, and the test
language for non-Rust surfaces), and **shell** as thin wrappers only, where
strictly required.

We chose option 1 because each language earns a distinct, bounded role:

- **Rust owns the domain.** ADR-0001 establishes that deterministic procedural
  logic belongs in a compiled, testable, distributable core, and ADR-0002 ships
  it as static binaries. Hooks are part of this: the hook logic is implemented in
  the CLI, fronted by a thin shell shim only if the hook entry point demands a
  shell command.
- **Python is the support language, not a second product language.** The invoke
  task tree is mature and fast to iterate for build, release, and automation, and
  rewriting it in Rust would slow that work for little gain. Just as important,
  Python is the test language for everything that *isn't* Rust — it exercises the
  shell wrappers and carries guardrail tests for non-Rust components such as the
  CI pipeline. A test harness separate from the product compiler keeps those
  surfaces testable without coupling them to the Rust build.
- **Shell is minimised, not foundational.** Skills' `!` preprocessor can invoke
  the CLI directly, and hook logic lives in the CLI, so shell is not needed as a
  runtime substrate. It remains only as thin wrappers where the environment
  strictly requires a shell entry point.

Option 2 was rejected at both poles: driving build/release/automation and
non-Rust tests from Rust is heavyweight and couples the test harness to the
product compiler, while the Accelerator-style shell substrate is precisely the
untestable, fragile model ADR-0001 exists to leave behind. Option 3 was rejected
because dropping Python forfeits the fast-iterating support and the separate test
language the non-Rust surfaces need, while forbidding shell outright forces
awkward workarounds at the few integration points that genuinely require a shell
entry point — better to keep shell and bound it tightly than to ban it.

This ADR records only the **split and the role each toolchain plays**. The
toolchain-specific decisions that hang off it — the bash 3.2 floor and the `mise`
+ invoke task runner — are recorded as their own ADRs (the 5th and 6th ADRs in
epic 0001's decision set, forthcoming).

## Consequences

### Positive

- The domain lives in one compiled, unit-testable, reusable, distributable
  language; reliability, reuse, and zero-setup distribution follow ADR-0001 and
  ADR-0002.
- Python gives fast-iterating build/release/automation and a proper test language
  for the non-Rust surfaces (shell wrappers, CI guardrails) without dragging a
  compile step into that work.
- Shell stays minimal — thin wrappers only — so the fragile-shell failure mode is
  contained by design rather than sitting at the foundation.

### Negative

- Three toolchains mean three sets of formatters, linters, checks, pinned tool
  versions, and CI lanes to maintain.
- Contributors must work across — or context-switch between — three languages.
- Each boundary (skill↔CLI, wrapper↔CLI, hook-shim↔CLI) is an integration surface
  to design, test, and keep stable.
- Shared conventions must be duplicated by hand across toolchains — notably the
  80-column line width, copied into each tool's config because none reads
  `.editorconfig` uniformly.

### Neutral

- Node is also provisioned (e.g. for `actionlint` and markdown/CI tooling) but is
  auxiliary dev infrastructure, not a product toolchain.
- The bash 3.2 floor (the 5th ADR in this set) still governs the thin shell
  wrappers and the Python-driven shell tests, and the `mise` + invoke task runner
  (the 6th ADR) provisions and version-pins all three toolchains; both are
  recorded separately and hang off this split.
- The split is about *roles*: shell's footprint is intended to stay small by
  design, not to shrink over time from a large existing base.

## References

- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — Epic;
  decision 4 of the baseline architecture-decision set.
- `meta/work/0004-record-existing-implicit-architecture-decisions-as-adrs.md` —
  Owning story (decision 4 of 1–8).
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Establishes the
  Rust deterministic core that carries the domain.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — How the
  Rust core ships.
- Forthcoming: bash 3.2 floor (the 5th ADR in epic 0001's decision set) and
  `mise` + invoke task runner (the 6th) — toolchain-specific ADRs that hang off
  this split.
