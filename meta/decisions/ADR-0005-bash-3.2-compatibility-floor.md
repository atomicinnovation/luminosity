---
type: adr
id: "ADR-0005"
title: "Bash 3.2 Compatibility Floor"
date: "2026-06-24T19:41:23+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0004"
relates_to: ["adr:ADR-0004", "adr:ADR-0002", "adr:ADR-0003", "adr:ADR-0001"]
tags: [architecture, toolchain, shell, bash, portability, foundations]
last_updated: "2026-06-24T19:41:23+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0005: Bash 3.2 Compatibility Floor

**Date**: 2026-06-24
**Status**: Accepted
**Author**: Toby Clemson

## Context

ADR-0004 confines shell to thin wrappers and hook shims that resolve and
delegate to the CLI. Unlike the dev toolchains, this shell runs in the **host
environment** — the user's machine and the Claude Code host — not under `mise`.
`mise` provisions dev tooling; it does not choose the shell the plugin's entry
points run under at a user's site. The plugin gets whatever shell the host
provides.

On macOS that shell is **bash 3.2.57** — the last GPLv2 bash, frozen in 2007 and
still shipped as `/bin/bash` (and `/bin/sh`) on every Mac roughly two decades
later. A large share of users and contributors are on macOS. bash-4+ constructs
(associative arrays, `${var,,}`/`${var^^}` case modification, `mapfile`/
`readarray`, namerefs, `&>>`) therefore fail or silently misbehave on a stock
Mac, and requiring users to install a newer bash before the plugin's shell entry
points work would contradict the zero-setup distribution ethos of ADR-0002.

No off-the-shelf static tool verifies a *version* floor. ShellCheck distinguishes
shell **dialect** (`sh`/`bash`/`dash`/`ksh`/`busybox`) but not bash **version** —
declared as `bash`, it accepts bash-4 features as valid; its version-targeting
request (issue #2850) has been open since 2023 with no implementation. shfmt,
bashate, and checkbashisms do not check bash-version conformance either. A floor
can therefore be enforced only by a hand-rolled denylist or by executing scripts
under a real bash 3.2.

## Decision Drivers

- Shell entry points must run on a stock macOS (bash 3.2.57) with zero setup,
  consistent with ADR-0002 — no newer shell as a prerequisite.
- The host shell is not ours to provision; we must target the oldest shell a
  supported host ships rather than the one we would prefer.
- Enforcement should be faithful and low-maintenance — not resting solely on a
  brittle, hand-maintained checker.
- Shell is already minimised to thin wrappers (ADR-0004), so the cost of
  forgoing newer bash conveniences is bounded.

## Considered Options

1. **Bash 3.2 floor** — write to bash 3.2.57 and ban bash-4+ constructs. Enforce
   by running the shell test suite under a real bash 3.2 as the authoritative
   gate, with a minimal static denylist as a backstop.
2. **Target modern bash (4/5)** — require users and contributors to install a
   newer bash (e.g. via Homebrew) and document it as a prerequisite.
3. **Strict POSIX `sh`** — write to the POSIX shell command language only,
   runnable by any `/bin/sh` (dash/busybox included), enforced by stock
   ShellCheck in `sh` mode.
4. **No floor** — rely on convention and review.

## Decision

We will hold a **bash 3.2 compatibility floor** for all shell code: scripts and
wrappers target bash 3.2.57, and bash-4+ constructs are disallowed.

We chose option 1 over the alternatives:

- **Modern bash (option 2)** contradicts ADR-0002 head-on. The host shell is not
  ours to provision, so targeting bash 4/5 would force macOS users to install and
  path-resolve a newer bash before the plugin's shell entry points worked — a
  prerequisite the zero-setup model exists to avoid.
- **Strict POSIX (option 3)** is genuinely attractive: it is maximally portable
  and enforceable by stock ShellCheck, which would retire the bespoke checker
  entirely. We rejected it because its portability serves a target we do not
  have — every supported host (macOS, Linux, WSL) ships bash — while its cost
  lands on the very constructs that make shell safer: POSIX has no arrays, no
  `local`, no `[[ ]]`, no `pipefail`, and no process substitution. Our own
  `lint-bashisms.sh` already relies on arrays, process substitution, and
  `pipefail`; a POSIX rewrite would reintroduce the piped-`while` subshell
  footgun and global-only function variables. Bash 3.2 keeps these safety tools
  and costs only bash-4 niceties we do not need.
- **No floor (option 4)** would let shell break silently on the most common
  contributor platform.

Because no static tool targets a bash version, the faithful check is execution
under bash 3.2.57 itself — available for free on macOS CI runners, which ship
exactly that interpreter. Now that Python is the test language for non-Rust
surfaces (ADR-0004), the shell suite **will be** run under bash 3.2.57 (and
differentially against modern bash) as the **authoritative** conformance gate,
demoting the static denylist to a **backstop** for branches the suite does not
exercise. Until that execution gate lands, the static denylist
(`lint-bashisms.sh`) remains the **sole operative** enforcement; once the gate is
in place the denylist need not be exhaustive.

## Consequences

### Positive

- Shell entry points run on a stock Mac with zero setup, consistent with
  ADR-0002 — no "install a newer bash" prerequisite.
- Targeting the oldest supported bash maximises host portability by construction.
- Retains the safety constructs (arrays, `local`, `[[ ]]`, `pipefail`, process
  substitution) that strict POSIX would forfeit.
- A real-interpreter gate will give faithful conformance rather than heuristics,
  and will let the brittle denylist relax into a non-exhaustive backstop.

### Negative

- Forgoes ergonomic bash-4 features (associative arrays, case-modification
  expansions, `mapfile`/`readarray`, namerefs); some logic is more verbose. This
  was felt in Accelerator's bash config parser (per ADR-0003), where the floor
  forced design compromises — though Luminosity's own parser is now Rust-native
  and no longer bound by it.
- Behavioural conformance testing is coverage-bound: a banned construct in an
  unexercised branch is caught only by the static backstop, which is incomplete
  by nature.
- No off-the-shelf tool enforces the floor, so we own the enforcement machinery.
- Running a real bash 3.2 off macOS requires provisioning a source-built 3.2.57
  (CI or Docker) — an added cost if the gate must also run on Linux or locally.
- Shell has no autofixer; floor violations are fixed by hand.

### Neutral

- macOS CI runners ship bash 3.2.57 — the exact target — so the authoritative
  gate will be essentially free there once wired in.
- ShellCheck and shfmt versions are pinned via `mise` (the 6th ADR in this set);
  shfmt reads `.editorconfig` with no explicit dialect set.
- The floor was established ahead of the shell library it governs; today the only
  `.sh` file is the linter itself.
- ShellCheck's version-targeting request (#2850) is open upstream; were it to
  ship, it could supplement or replace the static backstop.

## References

- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — Epic;
  decision 5 of the baseline architecture-decision set.
- `meta/work/0004-record-existing-implicit-architecture-decisions-as-adrs.md` —
  Owning story (decision 5 of 1–8).
- `meta/decisions/ADR-0004-three-toolchain-split.md` — Confines shell to the thin
  wrappers this floor governs.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — The
  zero-prerequisite ethos driving the floor.
- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — Config
  parser constrained by the floor (downstream consequence).
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — Cites the floor
  as a constraint on shell robustness.
- `scripts/lint-bashisms.sh` — The current static backstop (denylist).
- ShellCheck issue #2850 — open upstream request for bash-version targeting.
