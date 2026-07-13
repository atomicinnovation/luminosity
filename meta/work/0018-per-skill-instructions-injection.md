---
type: work-item
id: "0018"
title: "Per-Skill Instructions Injection"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: medium
parent: "work-item:0011"
relates_to: ["work-item:0010"]
tags: [configuration, context-injection]
last_updated: "2026-07-11T13:03:03+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0018: Per-Skill Instructions Injection

**Kind**: Story
**Status**: Ready
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity user, I want per-skill instructions I write at
`.luminosity/skills/<skill-name>/instructions.md` appended at the end of that
skill's prompt, so I can add binding instructions that extend the skill's own
(and, by landing last, can take precedence over them) without editing the
plugin.

## Context

Third of the three context-injection themes of epic 0011. The accelerator
implements this via `config-read-skill-instructions.sh <skill-name>`, which reads
`<config-dir>/skills/<skill-name>/instructions.md`, wraps it under an
`## Additional Instructions` header ("Follow these instructions in addition to
all instructions above."), and injects it at the **end** of the skill body. The
context-early / instructions-last ordering is load-bearing — the header text
itself references "all instructions above". In Luminosity, `<config-dir>`
resolves to `.luminosity` (ADR-0003); the skill `!`-preprocessor injects the
reader's output at the end of the skill body and the reader is implemented in
the Rust CLI. "Override" here is emergent from the ordering — appended-last
instructions take precedence over the skill's own by position, not by any
separate precedence mechanism. The wrapper prose interpolates the skill name
(see Technical Notes for the exact block).

## Requirements

- The Rust CLI reads `.luminosity/skills/<skill-name>/instructions.md` for the
  invoked skill.
- The Rust CLI wraps the content under the exact `## Additional Instructions`
  header and wrapper prose reproduced in Technical Notes — the prose interpolates
  the skill name (header and prose are load-bearing).
- The skill `!`-preprocessor injects the CLI output at the END of the skill body
  (after the skill's own instructions and after any context blocks). "End of the
  skill body" and "end of the prompt" denote the same insertion point.
- Wire the injection into **every skill** registered in
  `.claude-plugin/plugin.json` (first-slice scope is all skills, not a subset).
- The Rust CLI emits nothing when the file is absent or its trimmed content is
  empty.
- Expand the `configure` skill to surface this capability (per epic 0011's
  cross-cutting requirement).
- Extend the eval suite to cover the injection behaviour (per epic 0011's
  cross-cutting requirement, building on story 0010).

## Acceptance Criteria

- [ ] Given an `instructions.md` for skill X with non-empty content, when skill X
      is invoked, then a `## Additional Instructions` block with that content
      appears at the end of the skill body, after the skill's own instructions.
- [ ] Given no `instructions.md` for skill X (or empty), when skill X is invoked,
      then no `## Additional Instructions` block is emitted.
- [ ] Given an `instructions.md` with surrounding blank lines, when the block is
      emitted, then it has no leading or trailing blank lines.
- [ ] Given context and instructions files both exist, the instructions block
      appears after the context blocks (ordering verified: context early,
      instructions last).
- [ ] The emitted block matches the exact `## Additional Instructions` block
      reproduced in Technical Notes, byte-for-byte — that block is the single
      source of truth for the expected bytes (header line, blank line,
      skill-name-interpolated prose, blank line, then the trimmed content; the
      header and prose are load-bearing).
- [ ] Given the set of skills enumerated in `.claude-plugin/plugin.json`, when
      each skill with a fixture `instructions.md` is invoked, then every one
      emits the `## Additional Instructions` block — a test iterates the registry
      and asserts each entry, rather than checking a single skill.
- [ ] Given the `configure` skill is invoked, then its rendered surface lists an
      action for managing per-skill instructions that names the
      `.luminosity/skills/<skill-name>/instructions.md` path as the source, and
      the skill body includes that action.
- [ ] The eval suite exercises each injection scenario: `instructions.md` present
      (block emitted at the end), absent/empty (no block), and
      context-then-instructions ordering when both files exist — each asserting
      the presence/absence and position of the `## Additional Instructions` block
      (building on the eval framework from story 0010).

## Open Questions

- Does Luminosity already provide a `config_assert_no_legacy_layout` equivalent
  (e.g. delivered by 0009's config surface), or must this story provide it? If it
  must be provided, it becomes an upstream prerequisite for the reader (see
  Dependencies and Technical Notes). Resolve before implementation.

## Dependencies

- Blocked by: 0009 (multi-level config model — done); 0016 (plugin-global
  context) and 0017 (per-skill context) — the context-early/instructions-last
  ordering criterion can only be verified once those context blocks exist, and
  0016 owns the shared injection/wiring mechanism, so both land before 0018.
- Relates to: 0010 (eval framework) — the eval-coverage acceptance criterion
  builds on the framework story 0010 establishes; that framework must be in
  place before the eval-coverage criterion can be satisfied.
- Prerequisite to confirm: a `config_assert_no_legacy_layout` equivalent must run
  before the reader (see Open Questions and Technical Notes) — an upstream
  blocker only if it is not already delivered by 0009's config surface.
- Parent: 0011.
- All three (0016/0017/0018) remain separate stories (decided); the shared
  injection mechanism does not warrant merging.

## Assumptions

- The wrapper header text and end-of-body placement should match the accelerator
  exactly; the ordering relative to context blocks is part of the contract.

## Technical Notes

- Accelerator reference: `scripts/config-read-skill-instructions.sh`, wired at
  the end of each `SKILL.md`.
- **Exact wrapper block (load-bearing, from `config-read-skill-instructions.sh`)**
  — the prose interpolates the invoked skill's name; the emitted block is the
  header, a blank line, the three-line prose, a blank line, then the trimmed
  instructions content:

  ```
  ## Additional Instructions

  The following additional instructions have been provided for the
  <skill-name> skill. Follow these instructions in addition to all
  instructions above.

  <trimmed instructions.md content>
  ```
- **Legacy-layout precondition:** the accelerator's readers call
  `config_assert_no_legacy_layout` first. Confirm whether the Luminosity
  equivalent already exists (e.g. delivered by 0009's config surface) or must be
  provided; if the latter, it is an upstream prerequisite for the reader.
- `<config-dir>` resolves to `.luminosity` in Luminosity (ADR-0003).
- ADR-0020 (per-skill customisation directory), ADR-0003 (`.luminosity/` layout).

## Drafting Notes

- Extracted as a standalone story from epic 0011's third theme; kept separate
  from 0016 and 0017 per the author (the shared injection mechanism does not
  warrant merging).
- Proposed kind `story`, priority `medium` (inherited from the epic).
- Enriched 2026-07-11: resolved the first-slice wiring question to **all skills**
  (recorded as a requirement and a universal-wiring acceptance criterion);
  tightened acceptance criteria (added blank-line trimming and exact-header-match
  cases, plus all-skills wiring; split the configure-surface and eval-coverage
  criterion in two).
- Reviewed 2026-07-11 (review 1, REVISE — see
  `meta/reviews/work/0018-per-skill-instructions-injection-review-1.md`).
  Amendments: reconciled the Summary "override" wording with the additive
  mechanism (override is emergent from instructions-last ordering, stated in
  Context); fixed the "skill body" vs "prompt" placement-term drift (declared
  equivalent); embedded the exact `## Additional Instructions` wrapper block
  (including the skill-name-interpolated prose) in Technical Notes and had the
  exact-match AC assert the full block skeleton; made the configure-surface and
  eval-coverage ACs observable (concrete `configure` action; enumerated eval
  scenarios); named `.claude-plugin/plugin.json` as the universal-wiring
  enumeration source; added Requirements bullets for the configure-surface and
  eval extension (previously only in the AC); recorded 0010 as an eval-framework
  dependency, 0016/0017 as ordering blockers, and the `config_assert_no_legacy_layout`
  precondition as an upstream prerequisite to confirm.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
