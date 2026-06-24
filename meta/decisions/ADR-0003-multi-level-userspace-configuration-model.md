---
type: adr
id: "ADR-0003"
title: "Multi-Level Userspace Configuration Model"
date: "2026-06-24T16:17:54+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0004"
relates_to: ["adr:ADR-0001", "adr:ADR-0002"]
tags: [architecture, configuration, cli, skills, foundations]
last_updated: "2026-06-24T16:17:54+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0003: Multi-Level Userspace Configuration Model

**Date**: 2026-06-24
**Status**: Accepted
**Author**: Toby Clemson

## Context

Claude Code provides no built-in mechanism for plugin configuration — no
settings schema in `plugin.json`, no plugin section in user/project
`settings.json`, and no structured channel from a project to a plugin.
Anthropic's `plugin-dev` toolkit documents only a convention: a
`.claude/<plugin-name>.local.md` file with YAML frontmatter that each plugin
must read itself. Luminosity therefore has to define and implement its own
configuration model.

The plugin needs to support both team-shared conventions (templates, path
conventions, agent assignments) and personal developer overrides (preferred
agents, local paths). Team settings belong in version control; personal
settings must never be committed.

The Accelerator plugin (`../accelerator`) already solved this problem and the
model is proven in production. Its configuration grew across several accepted
decisions: a two-tier team/personal file model (ADR-0016), extension points for
templates and agents (ADR-0017), a per-skill customisation directory (ADR-0020),
and template-management subcommands (ADR-0021). Accelerator also consolidated
its configuration and plugin-owned files out of `.claude/accelerator*.md` and
into a dedicated `.accelerator/` directory; Luminosity adopts that consolidated
layout from the start. Luminosity intends to reach parity with that feature set
(work item 0011), so the foundational model recorded here must accommodate those
surfaces rather than preclude them.

Accelerator read its configuration with a bash, line-by-line/awk frontmatter
parser, constrained by the macOS bash 3.2 floor. That constraint forced two
design compromises that exist *only* because of the parser, not because the
domain wanted them: a two-level `section.key` nesting cap, and a ban on any
external YAML dependency. Luminosity is different: ADR-0001 establishes a
compiled CLI that owns deterministic procedural logic, and parsing configuration
is exactly that kind of work. A native YAML reader in the CLI removes the bash
constraints entirely, while ADR-0002's zero-setup static-binary distribution
means the reader ships with no runtime dependency to install.

## Decision Drivers

- Clean separation of team-shared vs personal configuration, with natural VCS
  integration (team committed, personal gitignored).
- Deterministic configuration resolution — values must reach skills exactly as
  written, not via the model's interpretation of natural language.
- Reliability and testability — resolution logic should be unit-testable in the
  CLI core, not encoded in fragile shell parsing.
- No runtime dependencies — must work within the zero-setup static binary
  (ADR-0002); no `yq`, Python, or external YAML parser required.
- A simple, discoverable mental model — one namespace, predictable precedence,
  known file locations.
- Alignment with Anthropic's documented `.local.md` plugin convention.
- Headroom to grow to full Accelerator feature parity (extension points,
  per-skill customisation, template management) without re-architecting.
- Consistency with the skills-vs-CLI division (ADR-0001): config parsing is
  deterministic work the CLI owns, not skill-prose work.

## Considered Options

This ADR bundles four coupled choices. Options are grouped by axis; the Decision
picks one from each.

### Config file scheme

1. **Single file** — one config file for everything. Simpler, but no
   team/personal separation.
2. **Two-tier files in `.claude/`** — `.claude/luminosity.md` +
   `.claude/luminosity.local.md` (Anthropic's literal `.local.md` convention;
   Accelerator's original layout). Scatters plugin-owned files across the shared
   `.claude/` directory.
3. **Two-tier files in a dedicated `.luminosity/` directory** —
   `.luminosity/config.md` (team, committed) + `.luminosity/config.local.md`
   (personal, gitignored), each with YAML frontmatter and last-writer-wins
   precedence with personal last, housed alongside the other files the plugin
   owns (templates, per-skill customisation, state). Keeps Anthropic's
   `.local.md` spirit while consolidating everything plugin-owned under one root.
   Matches Accelerator's consolidated `.accelerator/` layout.
4. **Environment variables** — shell-native, no parsing. Poor discoverability,
   no VCS integration, no room for free-form project context.

### Configuration reader

1. **Bash/awk frontmatter parser** — Accelerator's status quo. Fragile, bound by
   the bash 3.2 floor, and precisely the untestable deterministic-in-prose
   pattern ADR-0001 moves away from.
2. **External YAML tool (`yq` / Python)** — robust parsing, but requires a
   runtime dependency, breaking the zero-setup distribution story (ADR-0002).
3. **CLI-native YAML parsing in the hexagonal core** — the compiled CLI parses
   the frontmatter natively and exposes resolution through a command (e.g.
   `luminosity config get`). Deterministic, dependency-free, and unit-testable.

### Frontmatter expressiveness

1. **Two-level `section.key` cap** — Accelerator's constraint, imposed solely to
   keep bash parsing reliable. Unnecessary once a real parser reads the file.
2. **Arbitrary YAML structure** — lists, nesting, and richer schemas, parsed
   natively by the CLI. No artificial depth limit.

### Scope and extension model

1. **Global-only structured settings** — uniform keys across all skills, nothing
   more. Tempting for its simplicity — one flat namespace, no per-skill or
   extension machinery to build or document — but it cannot express the
   per-skill context, template, and agent extensions Luminosity wants parity
   with.
2. **Global structured settings plus the Accelerator extension model** — global
   two-tier value resolution, a free-form context channel from the file bodies,
   plus the per-skill customisation directory, template/agent extension points,
   and template-management subcommands (ADR-0017/0020/0021), adopted as the
   target model and implemented in stages.

## Decision

We will adopt the Accelerator's proven multi-level userspace configuration
model, choosing one option per axis:

**Config file scheme**: A dedicated `.luminosity/` directory is the consolidated
root for everything the plugin owns. Within it, `config.md` holds team-shared,
committed configuration and `config.local.md` holds personal overrides,
gitignored. Precedence is last-writer-wins per key, personal last: a value in
`config.local.md` overrides the same key in `config.md`. The markdown bodies of
both files are concatenated (team first, personal second) as a free-form
project-context channel. Other plugin-owned files — templates, per-skill
customisation directories, and local state — live under the same `.luminosity/`
root rather than being scattered across `.claude/`.

**Configuration reader**: The compiled CLI is the native reader. It parses the
YAML frontmatter itself, resolves precedence in the hexagonal core, and exposes
the result through a command (e.g. `luminosity config get` / `set`). This is the
deterministic work the CLI owns under ADR-0001. Skills inject values at load
time via the `!` preprocessor invoking the CLI; a SessionStart hook injects a
configuration summary into session context. Natural-language interpretation is
not used to carry config values.

**Frontmatter expressiveness**: Arbitrary YAML structure. Because the CLI parses
natively, we drop Accelerator's two-level `section.key` cap — frontmatter may use
lists, nesting, and richer schemas as the configuration catalogue grows.

**Scope and extension model**: We adopt the full Accelerator model as the target,
implemented in stages. The foundational two-tier value resolution is proved
end-to-end by the `configure` skill and CLI (work item 0009). The extension
surfaces — per-skill `context.md`/`instructions.md` directories (ADR-0020),
template/agent extension points (ADR-0017), and template-management subcommands
(ADR-0021) — are part of the model Luminosity commits to and are brought to
parity under work item 0011. Their detailed internal designs will be recorded as
their own decisions when built; this ADR commits to the model's shape, not to
re-deciding each extension's internals.

We chose two-tier files with a CLI-native reader because it is the only
combination that keeps configuration deterministic, dependency-free, and
unit-testable while preserving Accelerator's proven team/personal ergonomics.
The bash/awk reader was rejected as the very fragility ADR-0001 exists to
eliminate; an external YAML tool was rejected for breaking zero-setup
distribution; the two-level nesting cap was rejected as an artefact of a
constraint Luminosity no longer has.

## Consequences

### Positive

- Clean team/personal separation with natural VCS integration: `init`-style
  setup gitignores `.luminosity/config.local.md`; the team file is a normal
  committed file.
- All plugin-owned files live under a single discoverable `.luminosity/` root,
  keeping the project's `.claude/` directory uncluttered.
- Deterministic configuration injection — values reach skills via CLI stdout
  exactly as configured, not via model interpretation.
- Resolution logic is unit-testable in the CLI core, free of token cost, model
  variance, and the fragility of shell-based YAML parsing.
- No runtime dependency — the reader ships inside the zero-setup static binary
  (ADR-0002); no `yq` or Python to install.
- Arbitrary frontmatter structure — lists, nesting, and richer schemas — with no
  artificial depth cap.
- Aligns with the skills-vs-CLI division (ADR-0001) and Anthropic's documented
  `.local.md` convention.
- Leaves headroom for full feature parity (extension points, per-skill
  customisation, template management) without re-architecting the base model.

### Negative

- Configuration resolution now depends on the CLI being present and
  version-coherent with the plugin — config is coupled to the binary
  build/distribution pipeline.
- The full target model is large; reaching Accelerator parity is substantial
  future work (work item 0011).
- Config changes take effect only on the next skill invocation: the preprocessor
  runs at skill load time, not mid-conversation (inherited from the injection
  mechanism).
- Last-writer-wins offers no sentinel to *unset* a team value from personal
  config — a developer wanting "use the built-in default" must set a concrete
  value (inherited from Accelerator's model).

### Neutral

- Injection is via the `!` preprocessor plus a SessionStart summary hook,
  governed by ADR-0001 rather than re-decided here.
- The two tiers are both project-scoped (team committed, personal project-local);
  a machine-global (`$HOME`) configuration level is not introduced and can be
  added later if a concrete need arises.
- This ADR refined work item 0009's originally tentative
  `.claude/luminosity.md` / `.claude/luminosity.local.md` paths to the
  consolidated `.luminosity/` directory (`config.md` / `config.local.md`),
  matching Accelerator's `.accelerator/` consolidation; 0009's acceptance
  criteria have been updated to the new paths accordingly.
- Extension-surface internals (per-skill directories, templates, agents) will be
  recorded as their own decisions as they are implemented.

## References

- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — Epic;
  decision 3 of the baseline architecture-decision set.
- `meta/work/0004-record-existing-implicit-architecture-decisions-as-adrs.md` —
  Owning story (decision 3 of 1–8).
- `meta/work/0009-multi-level-configuration-system.md` — Proof slice: two-tier
  resolution via the `configure` skill + CLI.
- `meta/work/0011-configuration-feature-parity-with-accelerator.md` — Epic
  bringing the extension surfaces to parity.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — The CLI owns
  this deterministic parsing work.
- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — Why no
  runtime YAML dependency is acceptable.
- Accelerator ADR-0016 (userspace configuration model), ADR-0017 (extension
  points), ADR-0020 (per-skill customisation directory), ADR-0021
  (template-management subcommands) — the proven model this adopts and adapts.
