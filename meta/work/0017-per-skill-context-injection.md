---
type: work-item
id: "0017"
title: "Per-Skill Context Injection"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: medium
parent: "work-item:0011"
blocks: ["work-item:0018"]
relates_to: ["work-item:0010"]
tags: [configuration, context-injection]
last_updated: "2026-07-13T21:18:06+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0017: Per-Skill Context Injection

**Kind**: Story
**Status**: Ready
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity user, I want per-skill context I write at
`.luminosity/skills/<skill-name>/context.md` (team) and
`.luminosity/skills/<skill-name>/context.local.md` (personal) injected into that
skill's prompt, so I can tailor a specific skill's behaviour without touching
global config.

## Context

Second of the three context-injection themes of epic 0011. The accelerator
implements this via `config-read-skill-context.sh <skill-name>`, which reads
`<config-dir>/skills/<skill-name>/context.md`, wraps its content under a
`## Skill-Specific Context` header, and the skill injects that near the top of
its body — immediately after the plugin-global project context. In Luminosity,
`<config-dir>` resolves to `.luminosity` (ADR-0003); the skill `!`-preprocessor
injects the reader's output and the reader itself is implemented in the Rust CLI.
The wrapper prose interpolates the invoked skill's name (see Technical Notes for
the exact block).

Luminosity **deliberately diverges from the accelerator in two ways** (see
Technical Notes): per-skill context is **two-level** (team + personal), mirroring
the multi-level config model of ADR-0003 that story 0016 already applies to the
plugin-global context; and the files' YAML frontmatter is **stripped** before
injection, consistent with every other file the Luminosity CLI reads.

## Requirements

- The Rust CLI reads both levels of per-skill context for the invoked skill:
  `.luminosity/skills/<skill-name>/context.md` (team — shared, committed) and
  `.luminosity/skills/<skill-name>/context.local.md` (personal — local,
  git-ignored).
- The Rust CLI combines the two levels team-then-personal, joined by a single
  blank line, dropping an absent or empty level — the same combination rule
  story 0016 applies to the plugin-global bodies. Both levels land under a
  **single** `## Skill-Specific Context` header.
- The Rust CLI strips YAML frontmatter from each file, injecting only the body
  beneath it — consistent with `config.md` / `config.local.md`, and a deliberate
  divergence from the accelerator (which injects the whole file).
- The Rust CLI wraps the combined content under the exact
  `## Skill-Specific Context` header and wrapper prose reproduced in Technical
  Notes — the prose interpolates the skill name (header and prose are
  load-bearing).
- The skill `!`-preprocessor injects the CLI output at a fixed near-top
  injection point in the skill body: immediately after the plugin-global
  `## Project Context` block when present; when absent, the
  `## Skill-Specific Context` block is the first injected block at that same
  point.
- Wire the injection into **every skill** registered in
  `.claude-plugin/plugin.json` (first-slice scope is all skills, not a subset).
- The Rust CLI emits nothing when both levels are absent or their combined
  trimmed content is empty.
- The personal level is git-ignored by default, as `config.local.md` already is.
- Expand the `configure` skill to surface this capability (per epic 0011's
  cross-cutting requirement).
- Extend the eval suite to cover the injection behaviour (per epic 0011's
  cross-cutting requirement, building on story 0010).

## Acceptance Criteria

- [x] Given a per-skill context file for skill X with non-empty content and a
      `## Project Context` block present, when skill X is invoked, then its
      prompt contains a `## Skill-Specific Context` block with that content,
      positioned immediately after the `## Project Context` block.
- [x] Given a per-skill context file for skill X with non-empty content and no
      `## Project Context` block, when skill X is invoked, then the
      `## Skill-Specific Context` block appears at the fixed near-top injection
      point as the first injected block there — the same structural point it
      would occupy immediately after a `## Project Context` block, which is
      simply absent.
- [x] Given only a team `context.md` for skill X, when skill X is invoked, then
      the `## Skill-Specific Context` block carries the team body.
- [x] Given only a personal `context.local.md` for skill X, when skill X is
      invoked, then the `## Skill-Specific Context` block carries the personal
      body.
- [x] Given both a `context.md` and a `context.local.md` for skill X, when skill
      X is invoked, then a **single** `## Skill-Specific Context` block carries
      both bodies joined team-then-personal by one blank line.
- [x] Given a per-skill context file carrying YAML frontmatter, when the block is
      emitted, then only the body beneath the frontmatter appears — the
      frontmatter itself is never injected.
- [x] Given neither a `context.md` nor a `context.local.md` for skill X (or both
      empty), when skill X is invoked, then no `## Skill-Specific Context` block
      is emitted.
- [x] Given a per-skill context file with surrounding blank lines, when the block
      is emitted, then it has no leading or trailing blank lines.
- [x] Given both plugin-global context and per-skill context exist, the ordering
      is global-then-skill.
- [x] The emitted header line and wrapper prose match the exact
      `## Skill-Specific Context` block reproduced in Technical Notes,
      byte-for-byte (including the skill-name-interpolated lead sentence); the
      header and prose are load-bearing.
- [x] Given the set of skills enumerated in `.claude-plugin/plugin.json`, when
      each skill with a fixture per-skill context file is invoked, then every one
      emits the `## Skill-Specific Context` block — a test iterates the registry
      and asserts each entry, rather than checking a single skill.
- [x] Given the `configure` skill is invoked, then its rendered surface lists an
      action for managing per-skill context that names **both** the
      `.luminosity/skills/<skill-name>/context.md` and
      `.luminosity/skills/<skill-name>/context.local.md` paths as the sources,
      and the skill body includes that action.
- [x] The personal `context.local.md` is git-ignored by default, while the team
      `context.md` stays tracked.
- [x] The eval suite exercises each injection scenario: per-skill context present
      (block emitted after any `## Project Context`), absent/empty (no block),
      team-and-personal combination, and global-then-skill ordering — each
      asserting the presence/absence and position of the
      `## Skill-Specific Context` block (building on the eval framework from
      story 0010).

## Open Questions

- None outstanding.

## Dependencies

- Blocked by: 0009 (multi-level config model — done); 0016 (plugin-global
  context) — 0016 establishes the shared injection/wiring mechanism and the
  `## Project Context` anchor that the global-then-skill ordering criterion
  verifies against, so 0016 lands first (or co-delivers).
- Relates to: 0010 (eval framework) — the eval-coverage acceptance criterion
  builds on the framework story 0010 establishes; that framework must be in
  place before the eval-coverage criterion can be satisfied.
- Parent: 0011.
- Blocks: 0018 (per-skill instructions) — 0018's ordering criterion verifies its
  block lands after this per-skill context block. All three remain separate
  stories (decided); the shared mechanism does not warrant merging.

## Assumptions

- The wrapper header text and placement (after global context, near the top)
  should match the accelerator exactly. The **level model** and the
  **frontmatter handling** deliberately do not — see Technical Notes.

## Technical Notes

- Accelerator reference: `scripts/config-read-skill-context.sh`; live example
  layout under `.accelerator/skills/<skill>/`.
- **Exact wrapper block (load-bearing, from `config-read-skill-context.sh`)** —
  the prose interpolates the invoked skill's name; the content is the combined
  team-then-personal body:

  ```
  ## Skill-Specific Context

  The following context is specific to the <skill-name> skill. Apply this
  context in addition to any project-wide context above.

  <trimmed, combined team-then-personal content>
  ```
- **Two-level per-skill context (divergence from the accelerator).** The
  accelerator has a single `skills/<skill>/context.md` with no personal level.
  Luminosity adds `skills/<skill>/context.local.md`, so per-skill context follows
  the same team/personal model ADR-0003 defines and story 0016 applies to the
  plugin-global bodies. The combination rule is the one 0016 already
  implements — trim each level, drop the empty ones, join the survivors
  team-then-personal with one blank line — so an empty combined result means no
  block at all. The two levels share one `## Skill-Specific Context` header, just
  as the two config bodies share one `## Project Context` header.
- **Frontmatter is stripped (divergence from the accelerator).** The
  accelerator's per-skill readers inject the whole file; Luminosity strips YAML
  frontmatter and injects only the body, consistent with `config.md` /
  `config.local.md` and with the single file-reading primitive the Rust CLI
  already owns.
- `.gitignore` already carries `**/.luminosity/config.local.md` (with a negation
  for the eval fixtures); the per-skill personal file needs the equivalent pair.
- `<config-dir>` resolves to `.luminosity` in Luminosity (ADR-0003).
- **ADR references.** "ADR-0020 (per-skill customisation directory)" is an ADR of
  the **accelerator** repository, not of Luminosity — Luminosity's own ADR series
  currently ends at ADR-0011 and has no ADR-0020. The governing *Luminosity* ADRs
  are ADR-0003 (the `.luminosity/` layout and the multi-level config model),
  ADR-0001 (skills-vs-CLI division of labour), and ADR-0009 (the hexagonal core).

## Drafting Notes

- Extracted as a standalone story from epic 0011's second theme; kept separate
  from 0016 and 0018 per the author (the shared injection mechanism does not
  warrant merging).
- Proposed kind `story`, priority `medium` (inherited from the epic).
- Enriched 2026-07-11: resolved the first-slice wiring question to **all skills**
  (recorded as a requirement and a universal-wiring acceptance criterion);
  tightened acceptance criteria (added blank-line trimming and exact-header-match
  cases, plus all-skills wiring; split the configure-surface and eval-coverage
  criterion in two).
- Reviewed 2026-07-11 (review 1, REVISE — see
  `meta/reviews/work/0017-per-skill-context-injection-review-1.md`).
  Amendments: embedded the exact `## Skill-Specific Context` wrapper block
  (including the skill-name-interpolated lead sentence) in Technical Notes and
  pointed the exact-match AC at it; defined the placement when no
  `## Project Context` block exists (new AC + requirement); made the
  configure-surface and eval-coverage ACs observable (concrete `configure`
  action; enumerated eval scenarios); named `.claude-plugin/plugin.json` as the
  universal-wiring enumeration source; attributed the read/wrap steps to the Rust
  CLI; noted `<config-dir>` = `.luminosity`; added Requirements bullets for the
  configure-surface and eval extension; recorded 0010 as an eval-framework
  dependency and 0016 as an ordering blocker (0016 → 0017 → 0018).
- Amended 2026-07-13 during planning (see
  `meta/plans/2026-07-13-0017-per-skill-context-injection.md`). Three decisions
  taken by the author:
  1. **Per-skill context becomes two-level** — a personal `context.local.md`
     joins the team `context.md`, combined team-then-personal under a single
     header, mirroring the rule 0016 applies to the plugin-global bodies. Drove
     new Requirements, five new acceptance criteria (per-level, combination,
     frontmatter, git-ignore), and a Technical Note recording the divergence from
     the accelerator's single-file model. **Story 0018 (per-skill instructions)
     should very likely follow suit** with an `instructions.local.md` — flagged
     there for the author, not decided here.
  2. **Frontmatter is stripped** from the per-skill context files, consistent
     with `config.md` and with the CLI's single file-reading primitive, diverging
     from the accelerator's whole-file injection.
  3. **The ADR-0020 citation names the accelerator's ADR**, not a Luminosity one
     (Luminosity's series ends at ADR-0011). Made explicit in Technical Notes
     rather than corrected — the reference was never wrong, only ambiguous about
     which repository it names.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
