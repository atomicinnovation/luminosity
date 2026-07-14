---
type: adr
id: "ADR-0012"
title: "Two-Level Per-Skill Context With Frontmatter Stripped"
date: "2026-07-14T09:12:00+00:00"
author: Toby Clemson
producer: implement-plan
status: proposed
decision_makers: [Toby Clemson]
parent: "work-item:0017"
relates_to: ["adr:ADR-0003", "adr:ADR-0001", "adr:ADR-0009"]
tags: [architecture, configuration, context-injection, skills]
last_updated: "2026-07-14T09:12:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0012: Two-Level Per-Skill Context With Frontmatter Stripped

**Date**: 2026-07-14
**Status**: Proposed
**Author**: Toby Clemson

## Context

ADR-0003 adopted the Accelerator's configuration model and committed to its
extension surfaces — among them the per-skill customisation directory (the
Accelerator's ADR-0020, not a Luminosity ADR) — while explicitly deferring their
internals: *"Their detailed internal designs will be recorded as their own
decisions when built."* Story 0017 builds the first of those surfaces, per-skill
**context** injection, so the deferred decision falls due now.

ADR-0003's own layout sketch shows a single-file per-skill `context.md`, which is
what the Accelerator has: one `skills/<skill>/context.md`, injected whole,
frontmatter and all. Building that surface in Luminosity surfaced two places
where copying the Accelerator would contradict decisions Luminosity has already
taken:

- **The level model.** ADR-0003's headline is that configuration is *two-level* —
  a committed team file and a git-ignored personal file that overrides it — and
  story 0016 applied exactly that rule to the plugin-global context bodies. A
  single-file per-skill context would make per-skill context the one channel in
  `.luminosity/` with no personal level, so a developer could not hold a private
  working note for one skill without committing it.
- **Frontmatter.** The Accelerator's per-skill readers inject the whole file. The
  Luminosity CLI already owns one file-reading primitive that splits YAML
  frontmatter from body, and every other `.luminosity` document it reads is read
  that way. Injecting a per-skill file whole would mean two subtly different
  read paths in one adapter, and would splice a YAML block into a prompt as if it
  were prose.

## Decision Drivers

- Consistency with ADR-0003's two-level team/personal model, which every other
  `.luminosity` document already follows.
- One file-reading primitive in the adapter, not one per document kind
  (ADR-0009's hexagonal core keeps the rules in one place).
- Per-skill context is untrusted committed content spliced into a prompt; the
  fewer bespoke read paths it travels, the smaller the surface to reason about.
- Headroom for story 0018 (per-skill *instructions*) to be a variant of the same
  machine rather than a third parallel one.

## Considered Options

### Level model

1. **Single-file `context.md`** — the Accelerator's literal shape. Simplest, and
   ADR-0003's sketch shows it. But it makes per-skill context the only channel
   with no personal level, and offers no private-note affordance.
2. **Two-level `context.md` + `context.local.md`** — mirrors the team/personal
   model ADR-0003 defines and story 0016 already applies to the plugin-global
   bodies. Combined team-then-personal under a single header, so an empty
   combined result means no block at all.

### Frontmatter handling

1. **Inject the whole file** — the Accelerator's behaviour. No stripping rule to
   define, but splices a YAML block into a prompt and needs a second read path.
2. **Strip a YAML frontmatter mapping, inject the body** — consistent with
   `config.md` and with the CLI's single file-reading primitive. Needs a rule for
   what counts as frontmatter in a free-form prose file.

## Decision

**Level model**: per-skill context is **two-level**.
`.luminosity/skills/<skill-name>/context.md` is the shared, committed team body;
`.luminosity/skills/<skill-name>/context.local.md` is the local, git-ignored
personal body. They combine team-then-personal, joined by a single blank line,
dropping an absent or empty level — the same combination rule the plugin-global
bodies use — under a single `## Skill-Specific Context` header. `<skill-name>` is
the name the skill is *invoked* by (its frontmatter `name:`), not its category
directory.

**Frontmatter handling**: YAML frontmatter is **stripped**; only the body beneath
it is injected. Because a per-skill context file is free-form user prose rather
than a CLI-owned document, the strip is **mapping-only**: a terminated `---`
fence is treated as frontmatter and stripped only when its content is empty or
parses as a YAML *mapping*. A terminated fence whose content is a non-mapping
scalar — a prose thematic break, or malformed YAML — is body, and the file is
injected whole. Only an *unterminated* leading fence fails loud. Without that
qualification a prose file opening `---\nSection A\n---\nSection B` would
silently lose "Section A".

Both are deliberate divergences from the Accelerator, taken because ADR-0003
adopted the Accelerator's *model*, not its bash-era implementation details, and
because the CLI-native reader ADR-0003 chose is what makes both affordable.

**Story 0018** (per-skill instructions) should very likely follow suit with an
`instructions.local.md`, for symmetry with the two-level model this establishes —
flagged there for the author, not decided here.

## Consequences

### Positive

- Every `.luminosity` document now follows one level model, so there is one rule
  for a user to learn and one for the CLI to implement.
- A developer can hold a private per-skill note without committing it, the same
  way they can for configuration values and project context.
- The per-skill reader reuses the existing frontmatter splitter, so the adapter
  has one file-reading primitive rather than two subtly different ones.
- The domain generalised to a `ContextSource` rather than a second parallel
  assembler, so story 0018 adds a variant, a path arm, and a renderer — not a
  third machine.

### Negative

- Diverges from the Accelerator, so the two plugins' per-skill context files are
  not interchangeable and the Accelerator's documentation does not describe
  Luminosity's behaviour.
- The mapping-only strip is a rule a user can be surprised by: a context file
  opening with an unterminated `---` degrades the block rather than being
  injected whole. The `configure` skill's surface names this hazard, and
  `--explain` diagnoses it.
- Two files per skill instead of one — marginally more to explain, and a
  `.gitignore` pair to maintain.

### Neutral

- Per-skill context remains untrusted committed content spliced into a prompt, on
  the same trust boundary story 0016 established for project context: it is data,
  not a capability, and the skill's own binding constraints are re-asserted below
  the injection point. Path-side hardening (a skill-name allow-list, and refusal
  of a symlink whose target escapes `.luminosity/`) is an implementation
  consequence, not a separate decision.
- The crate is still named `config` and its errors still surface as
  `ConfigError`, though the domain has generalised beyond configuration to all
  two-level `.luminosity` documents. Renaming is left for story 0018 to decide.

## References

- `meta/work/0017-per-skill-context-injection.md` — the story this decision
  serves.
- `meta/plans/2026-07-13-0017-per-skill-context-injection.md` — the plan that
  raised both divergences.
- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — the
  predecessor: adopts the model and defers this decision.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
  — why the read rules live in the adapter and the assembly rule in the core.
- `meta/work/0016-plugin-global-context-injection.md` — the sibling story whose
  two-level combination rule this reuses.
- `meta/work/0018-per-skill-instructions-injection.md` — the successor, which
  should very likely gain an `instructions.local.md` for symmetry.
- Accelerator ADR-0020 (per-skill customisation directory) — the single-file,
  whole-file model this diverges from.
