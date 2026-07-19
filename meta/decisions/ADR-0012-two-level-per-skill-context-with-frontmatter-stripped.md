---
type: adr
id: "ADR-0012"
title: "Two-Level Per-Skill Context With Frontmatter Stripped"
date: "2026-07-14T09:12:00+00:00"
author: Toby Clemson
producer: implement-plan
status: accepted
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
**Status**: Accepted
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
  a committed team file and a git-ignored personal file layered over it — and
  story 0016 applied exactly that rule to the plugin-global context bodies. (The
  two levels compose differently by document part: configuration *keys* override
  last-writer-wins, personal last, while free-form *bodies* concatenate,
  team first. It is the body rule that per-skill context inherits.) A
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
2. **Strip unconditionally** — reuse the existing lexical splitter as-is: treat
   whatever sits between the first two `---` fences as frontmatter. Free, and
   safe for the CLI-owned `config.md` it was built for. But a per-skill context
   file is free-form user prose, where a leading thematic break is legitimate
   Markdown: a file opening `---\nSection A\n---\nSection B` would silently lose
   "Section A". Silent loss of a user's prose is the worst failure available
   here.
3. **Strip a YAML frontmatter mapping, inject the body** — consistent with
   `config.md` and with the CLI's single file-reading primitive, and it closes
   option 2's silent-loss hole by testing what the fence actually contains.
   Needs a rule for what counts as frontmatter in a free-form prose file.

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
injected whole. Only an *unterminated* leading fence fails loud: it errors on the
read, and so — under `--fail-safe` — degrades to a *Skill-Specific Context
Unavailable* block rather than a silently truncated one. Loud degradation is the
point; without the mapping qualification a prose file opening
`---\nSection A\n---\nSection B` would silently lose "Section A".

Both are deliberate divergences from the Accelerator, taken because ADR-0003
adopted the Accelerator's *model*, not its bash-era implementation details, and
because the CLI-native reader ADR-0003 chose is what makes both affordable — the
reading and assembly being deterministic work the CLI owns under ADR-0001, not
prose a skill improvises.

**Scope of the two rules**: both govern *every* two-level `.luminosity` document,
not per-skill context alone.

- The **mapping-only strip** governs any document *body* the CLI splices into a
  prompt — `config.md`'s as well as a skill's. So a `config.md` whose frontmatter
  is valid YAML but not a mapping (a sequence, say) is now injected whole, fences
  included, where story 0016 injected only the text below the fences. That is a
  behaviour change to project context, and it is the intended one: the alternative
  is one silent-truncation rule for `config.md` and a safe one for skills, which
  is exactly the two-subtly-different-readers outcome this decision set out to
  avoid. A `config.md` in that shape is already malformed *as config* — no key can
  resolve out of a sequence — so the loud, whole-file injection is the more
  honest signal.
- **Containment** (refusing a symlinked file or directory component whose target
  escapes `.luminosity/`) governs every read *and every write*, not just the
  context read. Guarding only the context path would have left one file with two
  safety contracts: `luminosity context` refusing a symlinked `config.md` that
  `luminosity config get` would happily read through — and that `config set` would
  clobber by renaming over.

## Consequences

### Positive

- Every `.luminosity` document now follows one level model, so there is one rule
  for a user to learn and one for the CLI to implement.
- A developer can hold a private per-skill note without committing it, the same
  way they can for configuration values and project context.
- The per-skill reader reuses the existing frontmatter splitter, so the adapter
  has one file-reading primitive rather than two subtly different ones. The
  splitter itself stays purely lexical; the mapping test is a thin layer above it
  in the store, so the reuse costs the splitter no new special cases.
- The domain generalised to a `ContextSource` rather than a second parallel
  assembler, so story 0018 adds a variant, a path arm, and a renderer — not a
  third machine.

### Negative

- Diverges from the Accelerator, so the two plugins' per-skill context files are
  not interchangeable and the Accelerator's documentation does not describe
  Luminosity's behaviour.
- The mapping-only strip is a rule a user can be surprised by: a context file
  opening with an unterminated `---` errors on the read, so under `--fail-safe`
  it degrades the block rather than being injected whole. That is the loud
  failure the decision chose, but it is still a failure the author did not expect
  to provoke. The `configure` skill's surface names this hazard, and `--explain`
  diagnoses it.
- Two files per skill instead of one — marginally more to explain, and a
  `.gitignore` pair to maintain.
- Extending the mapping-only strip to `config.md`'s body changes project-context
  behaviour for a file story 0016 handled differently (see Scope, above). The
  blast radius is small — it takes a `config.md` whose frontmatter is valid YAML
  but not a mapping, which is already broken as config — but it is a change, not
  a pure addition, and the story's plan wrongly recorded project-context behaviour
  as untouched.

### Neutral

- Per-skill context remains untrusted committed content spliced into a prompt, on
  the same trust boundary story 0016 established for project context: it is data,
  not a capability, and the skill's own binding constraints are re-asserted below
  the injection point. Path-side hardening (a skill-name allow-list, and refusal
  of a symlink whose target escapes `.luminosity/`, on every read and write) is an
  implementation consequence, not a separate decision.
- The crate is still named `config` and its errors still surface as
  `ConfigError`, though the domain has generalised beyond configuration to all
  two-level `.luminosity` documents. Renaming is left for story 0018 to decide.
- Story 0018 (per-skill *instructions*) should very likely follow suit with an
  `instructions.local.md`, for symmetry with the two-level model established
  here. That is flagged on the story for its author, not decided by this ADR —
  the `ContextSource` generalisation makes either answer cheap.

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
