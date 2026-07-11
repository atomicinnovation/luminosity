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
last_updated: "2026-07-11T13:03:03+00:00"
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
`.luminosity/skills/<skill-name>/context.md` injected into that skill's prompt,
so I can tailor a specific skill's behaviour without touching global config.

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

## Requirements

- The Rust CLI reads `.luminosity/skills/<skill-name>/context.md` for the
  invoked skill.
- The Rust CLI wraps the content under the exact `## Skill-Specific Context`
  header and wrapper prose reproduced in Technical Notes — the prose interpolates
  the skill name (header and prose are load-bearing).
- The skill `!`-preprocessor injects the CLI output at a fixed near-top
  injection point in the skill body: immediately after the plugin-global
  `## Project Context` block when present; when absent, the
  `## Skill-Specific Context` block is the first injected block at that same
  point.
- Wire the injection into **every skill** registered in
  `.claude-plugin/plugin.json` (first-slice scope is all skills, not a subset).
- The Rust CLI emits nothing when the file is absent or its trimmed content is
  empty.
- Expand the `configure` skill to surface this capability (per epic 0011's
  cross-cutting requirement).
- Extend the eval suite to cover the injection behaviour (per epic 0011's
  cross-cutting requirement, building on story 0010).

## Acceptance Criteria

- [ ] Given a `context.md` for skill X with non-empty content and a
      `## Project Context` block present, when skill X is invoked, then its
      prompt contains a `## Skill-Specific Context` block with that content,
      positioned immediately after the `## Project Context` block.
- [ ] Given a `context.md` for skill X with non-empty content and no
      `## Project Context` block, when skill X is invoked, then the
      `## Skill-Specific Context` block appears at the fixed near-top injection
      point as the first injected block there — the same structural point it
      would occupy immediately after a `## Project Context` block, which is
      simply absent.
- [ ] Given no `context.md` for skill X (or empty), when skill X is invoked,
      then no `## Skill-Specific Context` block is emitted.
- [ ] Given a `context.md` with surrounding blank lines, when the block is
      emitted, then it has no leading or trailing blank lines.
- [ ] Given both plugin-global context and per-skill context exist, the ordering
      is global-then-skill.
- [ ] The emitted header line and wrapper prose match the exact
      `## Skill-Specific Context` block reproduced in Technical Notes,
      byte-for-byte (including the skill-name-interpolated lead sentence); the
      header and prose are load-bearing.
- [ ] Given the set of skills enumerated in `.claude-plugin/plugin.json`, when
      each skill with a fixture `context.md` is invoked, then every one emits the
      `## Skill-Specific Context` block — a test iterates the registry and
      asserts each entry, rather than checking a single skill.
- [ ] Given the `configure` skill is invoked, then its rendered surface lists an
      action for managing per-skill context that names the
      `.luminosity/skills/<skill-name>/context.md` path as the source, and the
      skill body includes that action.
- [ ] The eval suite exercises each injection scenario: `context.md` present
      (block emitted after any `## Project Context`), absent/empty (no block),
      and global-then-skill ordering — each asserting the presence/absence and
      position of the `## Skill-Specific Context` block (building on the eval
      framework from story 0010).

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
  should match the accelerator exactly.

## Technical Notes

- Accelerator reference: `scripts/config-read-skill-context.sh`; live example
  layout under `.accelerator/skills/<skill>/`.
- **Exact wrapper block (load-bearing, from `config-read-skill-context.sh`)** —
  the prose interpolates the invoked skill's name:

  ```
  ## Skill-Specific Context

  The following context is specific to the <skill-name> skill. Apply this
  context in addition to any project-wide context above.

  <trimmed context.md content>
  ```
- `<config-dir>` resolves to `.luminosity` in Luminosity (ADR-0003).
- ADR-0020 (per-skill customisation directory), ADR-0003 (`.luminosity/` layout).

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

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
