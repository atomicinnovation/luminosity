---
type: work-item
id: "0001"
title: "Baseline Architecture and Engineering Guard Rails"
date: "2026-06-20T23:16:20+00:00"
author: Toby Clemson
producer: create-work-item
status: ready
kind: epic
priority: high
tags: [architecture, tooling, rust, foundations, adr]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0001: Baseline Architecture and Engineering Guard Rails

**Kind**: Epic
**Status**: Ready
**Priority**: High
**Author**: Toby Clemson

## Summary

Establish the baseline architecture and engineering guard rails for the
Luminosity plugin before feature work begins, so that every subsequent feature
is built on agreed foundations with automated quality enforcement, rather than
accreting decisions and tooling ad hoc.

This epic establishes the architectural direction (skills own probabilistic
work — reasoning, generation, summarisation, judgement — while all
deterministic, standard procedural logic is delegated to a modular, hexagonal
Rust CLI distributed as zero-setup static binaries), records the decisions
behind it as Architecture Decision Records (ADRs), stands up a comprehensive
Rust toolchain (format, lint, test, coverage, supply-chain) as guard rails,
resolves two key unknowns via spikes, and proves the whole approach end-to-end
with a first vertical slice: a `version` subcommand and a `configure` skill
backed by the CLI.

## Context

Luminosity is a Claude Code plugin. Today the shipped product is a set of
skills, agents, hooks, templates, and scripts, with three language toolchains
(Python invoke tasks, a bash library, and a nascent Rust component). Before
accelerating into features, we want to fix the architecture and guard rails so
the plugin can grow without compounding inconsistency.

The intended architecture:

- **Clear division of labour between skills and the CLI.** Skills do what large
  language models (LLMs) do well — reasoning, generation, summarisation,
  judgement. Any
  non-probabilistic, standard procedural logic is delegated to a Rust CLI. A
  skill decides and orchestrates; the CLI executes the deterministic work.
- **Zero user setup.** The plugin manages downloading static, dependency-free
  binaries so the end user installs nothing. This is a solved problem in the
  accelerator plugin (`../accelerator`) and its approach will be ported.
- **A git-style modular CLI.** The plugin is expected to grow large, so the CLI
  is composed of smaller binaries fetched on demand that present as a single
  `luminosity` command (as `git` dispatches to `git-foo`). Research points to
  clap external-subcommand dispatch plus a rustup/uv-style launcher.
- **A thin CLI over a hexagonal core.** The CLI is a thin driving adapter over a
  ports-and-adapters core, so a future backend and/or frontend can reuse the
  same domain with different adapters.
- **Adopt proven accelerator patterns.** Multi-level userspace configuration
  (team and personal, with skill extension points), templating, filesystem as
  message bus and knowledge corpus, and strict context management are adapted
  from the accelerator plugin rather than reinvented.

Several decisions already exist implicitly in the codebase (the three-toolchain
split, the bash 3.2 floor, the `mise` + invoke task runner, skills-as-product,
filesystem-mediated phase communication) and deserve to be recorded as ADRs
alongside the new ones.

The author is not deeply familiar with structuring a modularised Rust CLI or
splitting crates correctly across CLI / domain / persistence, nor with skill
evaluation approaches — hence two spikes are included.

## Requirements

High-level themes. Each theme will be decomposed into the child work items
listed below.

**1. Record the baseline architecture as ADRs.** Each ADR follows the project's
ADR template — frontmatter (`type: adr`; quoted `id` `"ADR-NNNN"`; `title`;
`date`; `author`; `status` from `proposed | accepted | rejected | superseded |
deprecated`; `decision_makers`; `tags`; `schema_version`) plus body sections
Context · Decision Drivers · Considered Options · Decision (active voice) ·
Consequences (Positive / Negative / Neutral) · References — and is immutable once
`accepted`. The implementer chooses how to produce ADRs matching this shape. The
closed set of decisions to record — eleven in total, numbered 1–11: eight
recordable immediately (1–8) and three spike-dependent (9–11) — by title:

*Recordable immediately (decided; no spike dependency):*

1. Skills-vs-CLI division of labour (probabilistic work in skills; deterministic
   procedural logic in the CLI).
2. Zero-setup static-binary distribution (ported from accelerator).
3. Multi-level userspace configuration model.
4. Three-toolchain split (Python / shell / Rust).
5. Bash 3.2 floor.
6. `mise` + invoke task runner.
7. Skills-as-product.
8. Filesystem-as-message-bus and knowledge corpus. *(The specific directory is
   an Open Question below; this ADR records the pattern and is finalised once
   the directory is settled.)*

*Dependent on a spike (recorded after it concludes):*

9. Thin CLI over a hexagonal ports-and-adapters core. *(architecture spike)*
10. Git-style modular CLI of on-demand static binaries. *(architecture spike)*
11. Skill evaluation framework selection. *(eval spike)*

The acceptance criterion for theme 1 counts one accepted ADR per numbered title
above.

**2. Establish a comprehensive Rust toolchain (format, lint, test, coverage,
supply-chain) as guard rails**, wired into `mise run` tasks and enforced in the
existing CI:

- Formatting: rustfmt (`cargo fmt --check`).
- Linting: clippy with pedantic + nursery + cherry-picked restriction lints,
  `-D warnings`.
- Testing: cargo-nextest (plus proptest / insta where they earn their place).
- Coverage: cargo-llvm-cov.
- Supply-chain: cargo-deny (advisories, licenses, bans, sources).

**3. Resolve two unknowns via spikes**:

- Modular Rust CLI architecture and hexagonal workspace layout — crate split
  (`core` / `adapters` / `cli`), git-style external-subcommand dispatch, and the
  on-demand static-binary launcher.
- Skill evaluation framework — assess Anthropic's official `skill-creator`
  Eval/Benchmark workflow against external harnesses (promptfoo, DeepEval) and
  recommend an approach.

**4. Land the first vertical slice (the definition of done)**:

- A `luminosity version` subcommand that prints the CLI version, built
  test-first over the hexagonal skeleton.
- A multi-level configuration system (team and personal precedence) exposed as a
  CLI command and driven by a thin `configure` skill.
- On-demand static-binary distribution working for the four target platforms,
  ported from the accelerator approach.
- The chosen eval framework applied to the `configure` skill as its first
  evaluation target.

**Target platforms** for static binaries (target triple → distribution alias):

- `aarch64-apple-darwin` → `darwin-arm64`
- `x86_64-apple-darwin` → `darwin-x64`
- `aarch64-unknown-linux-musl` → `linux-arm64`
- `x86_64-unknown-linux-musl` → `linux-x64`

**Child work items** (to be created under this epic). The parenthetical notes
record the ordering each child implies — see Dependencies for the consolidated
sequencing:

- Spike: Modular Rust CLI architecture & hexagonal workspace layout *(precedes
  the scaffold, distribution, and spike-dependent ADR stories)*
- Spike: Skill evaluation framework selection *(precedes "Apply the eval
  framework")*
- Story: Record existing/implicit architecture decisions as ADRs *(theme 1
  decisions 1–8; recordable immediately)*
- Story: Record spike-dependent architecture decisions as ADRs *(theme 1
  decisions 9–11; 9–10 after the architecture spike, 11 after the eval spike)*
- Story: Establish Rust toolchain guard rails in `mise` + CI *(paired with the
  scaffold story)*
- Story: Scaffold the hexagonal Rust workspace with a `version` subcommand
  *(after the architecture spike; precedes distribution, configuration, and
  eval-application)*
- Story: On-demand static-binary distribution & launcher (port accelerator's
  approach) *(after the scaffold story)*
- Story: Multi-level configuration system — CLI command + thin `configure` skill
  *(after the scaffold story)*
- Story: Apply the eval framework to the `configure` skill *(after the eval spike
  and the configuration story)*

**Out of scope**:

- Any actual product feature or real domain logic beyond the `version` slice and
  configuration.
- A working backend or frontend — the core is shaped to allow them; neither is
  built.
- Re-litigating the existing Python and shell toolchains — they are recorded as
  ADRs but not changed.

## Acceptance Criteria

- [ ] An accepted ADR exists for each of the eleven numbered decision titles in
      theme 1, each following the ADR template with non-empty Context, Considered
      Options, and Consequences sections and status `accepted`. (Deeper quality
      is the remit of an ADR review, not this criterion.)
- [ ] Both spikes are completed, each producing a written recommendation with a
      decision at a stated path under the knowledge directory, and the resulting
      ADR(s) cite that document.
- [ ] Given the Rust toolchain tasks, when `mise run check` is run, then it
      includes the Rust component (format-check, clippy `-D warnings`, tests,
      coverage, `cargo deny check`) and exits 0.
- [ ] Given a Rust change that fails format-check or clippy, when CI runs on a
      pull request, then the workflow fails and the PR is non-mergeable (the
      read-only Rust checks run on the existing `.github` workflows).
- [ ] Given a built CLI, when `luminosity version` is run, then it prints the
      CLI version; the behaviour is covered by a test written test-first.
- [ ] Given key `core.example` set to `team-value` in the team config and
      `personal-value` in the personal config, when the value is read via the
      backing CLI command (e.g. `luminosity config get core.example`), then it
      returns `personal-value`; setting and inspecting the same key via the
      `configure` skill yields the same result.
- [ ] Static binaries build for all four target platforms and the launcher
      fetches the correct per-platform binary on demand (approach ported from
      accelerator).
- [ ] The eval suite for the `configure` skill contains at least three tasks
      (provisional floor), is run during development, and the resulting
      `configure` pass-rate of at least 80% (provisional floor) is committed to
      the repository as a version-controlled benchmark result. The eval spike may
      raise these thresholds and records the final minimum task count and
      baseline at a stated path, against which this criterion is then evaluated.
      Evals are deliberately not wired to run on every CI build, to control token
      cost.
- [ ] `mise run` (the bare default task) exits 0 end-to-end with the Rust
      component included.

## Open Questions

- Which directory serves as the filesystem message bus / knowledge corpus for
  this plugin (the accelerator uses `meta/`; this plugin's choice is undecided)?
  Settled within the existing/implicit ADR story (child 0004) as part of
  recording decision 8.
- Which eval framework is adopted — `skill-creator` vs an external harness — is
  the explicit output of the eval spike.

## Dependencies

- Blocked by: none externally.
- Blocks: all subsequent feature work in this repository (this epic establishes
  the foundations features will be built on).
- Depends on the accelerator plugin (`../accelerator`) as a build-time /
  authoring source: its ADR skills author theme 1's ADRs, and its solved
  binary-distribution, config-model, and templating approaches are ported here.
  It is not a runtime dependency, but the ADR-authoring and distribution stories
  cannot proceed as planned if it is unavailable or its approach has changed.

**Intra-epic ordering** (between the child work items above):

- The architecture spike precedes the scaffold story, the distribution story,
  and the spike-dependent ADR story (theme 1 decisions 9–10).
- The scaffold story precedes the distribution, configuration, and
  eval-application stories (each lives in or builds on the hexagonal workspace).
- The toolchain story is paired with the scaffold story: it has nothing to lint
  or test until the first Rust code exists, and the scaffold should not merge
  ahead of the guard rails meant to enforce its quality. Both must land before
  the two `mise run` green-build acceptance criteria can pass.
- The eval spike precedes the eval-application story; the configuration story
  also precedes it (the `configure` skill is its target).
- The existing/implicit ADR story (theme 1 decisions 1–8) has no spike
  dependency and can proceed immediately.

## Assumptions

- **A1**: Zero-setup binary distribution is in scope and is ported from the
  accelerator plugin's solved approach, rather than designed from scratch.
- **A2**: Configuration is scoped to just enough to prove the multi-level model
  end-to-end (a value resolved across team and personal precedence via the
  `configure` skill and its CLI command), not a complete configuration schema
  for as-yet-unbuilt features.
- **A3**: The specific Rust tool choices (clippy pedantic + nursery, nextest,
  cargo-llvm-cov, cargo-deny, and the distribution tooling) are each
  architectural decisions and are ratified as ADRs rather than adopted silently.
- **A4**: The eval-framework spike's recommendation is not only decided but
  applied — the first eval target is the `configure` skill, demonstrating the
  harness within this epic.

## Technical Notes

- **Git-style dispatch**: clap `allow_external_subcommands` captures unknown
  `luminosity foo` invocations; a launcher (rustup/uv-style) resolves and execs
  `luminosity-foo`, fetching it if absent. Prefer a managed bin dir over `$PATH`
  and use rustls (not OpenSSL) so the launcher itself stays statically linkable.
- **Hexagonal workspace**: start lean — `core` (domain + ports as traits +
  application), `adapters` (port implementations), `cli` (composition root /
  driving adapter). Crate-splitting (not module-splitting) is what lets a future
  backend/frontend reuse `core` with the compiler enforcing the dependency
  direction.
- **Static binaries**: musl targets for Linux give fully static binaries;
  `cargo-zigbuild` or `cross` for cross-compilation; `dist` for signed,
  checksummed, per-platform release artifacts; `self_update` for the
  fetch/verify/cache loop. Confirm which of these the accelerator already uses
  before re-selecting.
- **Skill evals**: Anthropic's `skill-creator` plugin provides Eval/Benchmark
  modes with a with-skill vs baseline comparison, `evals/evals.json` task
  format, assertion-based grading, and variance analysis (pass-rate, tokens,
  time as mean ± stddev). This is the leading candidate for the eval spike.

## Drafting Notes

- The accelerator plugin (`../accelerator`) is treated as a reference to adapt
  and a source of solved approaches (config model, templating, filesystem bus,
  context management, binary distribution, ADR skills) — not as a runtime
  dependency.
- jj-colocated VCS (version control system) was deliberately *excluded* from the
  ADR set: it is an individual preference, and the repo remains usable with plain
  git. No VCS decision is recorded.
- The `configure` skill is read as the first concrete instance of the
  skills-vs-CLI division of labour — a skill driving deterministic configuration
  logic that lives in the CLI — so it doubles as the proof-of-architecture for
  the whole approach; hence it is both the eval target and the driver of the
  configuration slice.
- The skill-evaluation thread (the eval-framework spike plus applying it to
  `configure`) is independently deliverable, but is deliberately kept inside this
  epic rather than split into a sibling: applying the eval harness to `configure`
  is what demonstrates the skills-vs-CLI division working end-to-end, so it
  shares this epic's proof-of-architecture goal rather than being a separable
  concern. The epic is therefore a single planning unit spanning all five
  threads.
- "Guard rails" is interpreted as primarily the Rust toolchain (per the author),
  with the existing Python/shell toolchains recorded but unchanged.

## References

- Related: accelerator plugin at `../accelerator` (config, templating,
  filesystem-bus, context-management, binary-distribution, and ADR skills to be
  adapted).
- Research: Anthropic `skill-creator` Eval/Benchmark workflow
  (https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md);
  "Demystifying evals for AI agents"
  (https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
- Research: clap external subcommands & multicall; rustup proxy/shim model; uv
  tool caching; `dist` (axodotdev) and `self_update` for distribution;
  cargo-nextest, cargo-llvm-cov, cargo-deny for the toolchain.
