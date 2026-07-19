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
last_updated: "2026-07-19T18:08:48+00:00"
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
`.luminosity/skills/<skill-name>/instructions.md` (team — shared, committed) and
`.luminosity/skills/<skill-name>/instructions.local.md` (personal — local,
git-ignored) combined and appended at the end of that skill's prompt, so I can
add binding instructions that extend the skill's own instructions (and, by
landing last, take precedence over those instructions) without editing the
plugin — with a personal level I keep out of version control.

## Context

Third of the three context-injection themes of epic 0011. The accelerator
implements this via `config-read-skill-instructions.sh <skill-name>`, which reads
`<config-dir>/skills/<skill-name>/instructions.md`, wraps it under an
`## Additional Instructions` header ("Follow these instructions in addition to
all instructions above."), and injects it at the **end** of the skill body. The
context-early / instructions-last ordering is load-bearing — the header text
itself references "all instructions above". In Luminosity, `<config-dir>`
resolves to `.luminosity` (ADR-0003); the skill `!`-preprocessor injects the
output of the per-skill instructions reader (the Rust CLI component) at the end
of the skill body. "Override" here is emergent from the ordering — appended-last
instructions take precedence over the skill's own by position, not by any
separate precedence mechanism. The wrapper prose interpolates the skill name
(see Technical Notes for the exact block).

Luminosity **deliberately diverges from the accelerator in two ways** (see
Technical Notes), exactly as story 0017 did for per-skill context: per-skill
instructions are **two-level** (team + personal), mirroring the multi-level
config model of ADR-0003 that stories 0016 and 0017 already apply; and the
files' YAML frontmatter is **stripped** before injection, consistent with every
other file the Luminosity CLI reads. Within the combined block the personal
level lands after the team level, so the instructions-last precedence property
extends to the two levels — personal instructions take precedence over team
instructions by position.

## Requirements

- The Rust CLI reads both levels of per-skill instructions for the invoked
  skill: `.luminosity/skills/<skill-name>/instructions.md` (team — shared,
  committed) and `.luminosity/skills/<skill-name>/instructions.local.md`
  (personal — local, git-ignored).
- The Rust CLI combines the two levels team-then-personal, joined by a single
  blank line, dropping an absent or empty level — the same combination rule
  stories 0016 and 0017 apply. Both levels land under a **single**
  `## Additional Instructions` header.
- The Rust CLI strips YAML frontmatter from each file, injecting only the body
  beneath it — consistent with `config.md` / `config.local.md` and
  `context.md` / `context.local.md`, and a deliberate divergence from the
  accelerator (which injects the whole file).
- The Rust CLI wraps the combined content under the exact
  `## Additional Instructions` header and wrapper prose reproduced in Technical
  Notes — the prose interpolates the skill name (header and prose are
  load-bearing).
- The skill `!`-preprocessor injects the CLI output at the END of the skill body
  (after the skill's own instructions and after any context blocks — the
  plugin-global `## Project Context` and per-skill `## Skill-Specific Context`
  blocks from stories 0016/0017). "End of the skill body" and "end of the prompt"
  denote the same insertion point.
- Wire the injection into **every skill** registered in
  `.claude-plugin/plugin.json` (this story's initial delivery scope covers all
  skills, not a subset).
- The Rust CLI emits nothing when both levels are absent or their combined
  trimmed content is empty.
- The personal `instructions.local.md` is git-ignored by default, as
  `config.local.md` and `context.local.md` already are.
- Expand the `configure` skill to surface this capability, naming **both** the
  team and personal paths (per epic 0011's cross-cutting requirement).
- Extend the eval suite to cover the injection behaviour, including the
  team-and-personal combination (per epic 0011's cross-cutting requirement,
  building on story 0010).

## Acceptance Criteria

- [ ] Given an `instructions.md` for skill X with non-empty content, when skill X
      is invoked, then a `## Additional Instructions` block with that content
      appears at the end of the skill body, after the skill's own instructions.
- [ ] Given only a team `instructions.md` for skill X, when skill X is invoked,
      then the `## Additional Instructions` block carries the team body.
- [ ] Given only a personal `instructions.local.md` for skill X, when skill X is
      invoked, then the `## Additional Instructions` block carries the personal
      body.
- [ ] Given both an `instructions.md` and an `instructions.local.md` for skill X,
      when skill X is invoked, then a **single** `## Additional Instructions`
      block carries both bodies joined team-then-personal by one blank line.
- [ ] Given a non-empty `instructions.md` and a present-but-empty (or
      whitespace-only) `instructions.local.md` for skill X — and the symmetric
      case (empty team, non-empty personal) — when skill X is invoked, then a
      single `## Additional Instructions` block carries only the non-empty level's
      body: the empty level is dropped with no stray, trailing, or doubled blank
      line in the combined content (the load-bearing drop-empty join path).
- [ ] Given a per-skill instructions file carrying YAML frontmatter, when the
      block is emitted, then only the body beneath the frontmatter appears — the
      frontmatter itself is never injected.
- [ ] Given no `instructions.md` and no `instructions.local.md` for skill X (or
      both empty), when skill X is invoked, then no `## Additional Instructions`
      block is emitted.
- [ ] Given a per-skill instructions file with surrounding blank lines, when the
      block is emitted, then it has no leading or trailing blank lines.
- [ ] Given at least one context file and at least one instructions file exist
      for skill X, the `## Additional Instructions` block appears after the
      context blocks — the plugin-global `## Project Context` (story 0016) and the
      per-skill `## Skill-Specific Context` (story 0017) — with ordering verified
      as context early, instructions last. This criterion verifies relative block
      position only; the byte-exact whitespace between blocks is owned by the
      shared injection mechanism (0016) and is not asserted here.
- [ ] The emitted block matches the exact `## Additional Instructions` block
      reproduced in Technical Notes, byte-for-byte — that block is the single
      source of truth for the expected bytes (header line, blank line,
      skill-name-interpolated prose, blank line, then the trimmed, combined
      content; the header and prose are load-bearing). The three prose lines are
      emitted with **fixed hard line breaks at the positions shown**, independent
      of the substituted skill name's length (a longer or shorter skill name
      shifts no break), so the expected byte string for a given skill name and
      content is fully determined.
- [ ] Given the set of skills enumerated in `.claude-plugin/plugin.json`, when
      each skill with a fixture instructions file is invoked, then every one
      emits the `## Additional Instructions` block — a test iterates the registry
      and asserts each entry, rather than checking a single skill.
- [ ] Given the set of skills enumerated in `.claude-plugin/plugin.json`, every
      such skill's `SKILL.md` contains the injection invocation line (the
      `!`-preprocessor call to the per-skill instructions reader) — a test
      iterates the registry and asserts the invocation is wired into each entry
      regardless of whether that skill carries a fixture, so a registered skill
      omitted from the wiring fails even when it has no fixture.
- [ ] Given the `configure` skill is invoked, then its rendered surface lists an
      action for managing per-skill instructions that names **both** the
      `.luminosity/skills/<skill-name>/instructions.md` and
      `.luminosity/skills/<skill-name>/instructions.local.md` paths as the
      sources, and the skill body includes that action.
- [ ] The personal `instructions.local.md` is git-ignored by default, while the
      team `instructions.md` stays tracked.
- [ ] The eval suite exercises each injection scenario: instructions present
      (block emitted at the end), absent/empty (no block), team-and-personal
      combination (including the mixed empty-level case), and
      context-then-instructions ordering when at least one context file and at
      least one instructions file exist — each asserting the presence/absence and
      position of the `## Additional Instructions` block (building on the eval
      framework from story 0010).

## Open Questions

- None outstanding. The accelerator's `config_assert_no_legacy_layout`
  precondition does not apply: Luminosity is an as-yet-unreleased plugin with no
  prior released on-disk layout, so there is no legacy layout to assert against
  (see Technical Notes). It is deliberately out of scope for this story.

## Dependencies

- Blocked by: 0009 (multi-level config model — done); 0016 (plugin-global
  context — done) and 0017 (per-skill context — done) — the
  context-early/instructions-last ordering criterion can only be verified once
  those context blocks exist, and 0016 owns the shared injection/wiring
  mechanism, so both land before 0018. 0017 is additionally the direct template
  for the two-level model and frontmatter-stripping adopted here. All three
  blockers are done, so this story is unblocked.
- Relates to: 0010 (eval framework — done) — the eval-coverage acceptance
  criterion builds on the framework story 0010 establishes; that framework must
  be in place before the eval-coverage criterion can be satisfied, and it is
  done.
- Parent: 0011.
- All three (0016/0017/0018) remain separate stories (decided); the shared
  injection mechanism does not warrant merging.

## Assumptions

- The wrapper header text and end-of-body placement should match the accelerator
  exactly; the ordering relative to context blocks is part of the contract. The
  **level model** (two-level) and the **frontmatter handling** (stripped)
  deliberately do not match the accelerator — they mirror story 0017's
  divergences for per-skill context.

## Technical Notes

- Accelerator reference: `scripts/config-read-skill-instructions.sh`, wired at
  the end of each `SKILL.md`.
- **Exact wrapper block (load-bearing, from `config-read-skill-instructions.sh`)**
  — the prose interpolates the invoked skill's name; the emitted block is the
  header, a blank line, the three-line prose, a blank line, then the trimmed,
  combined team-then-personal instructions content:

  ```
  ## Additional Instructions

  The following additional instructions have been provided for the
  <skill-name> skill. Follow these instructions in addition to all
  instructions above.

  <trimmed, combined team-then-personal content>
  ```
  The three prose lines carry **fixed hard line breaks at the positions shown**
  — they are part of the byte contract, not width-reflowed. Substituting a
  `<skill-name>` of any length leaves those break positions unchanged (the name
  is interpolated into the second line without rewrapping the paragraph), so the
  expected bytes for a given skill name and content are fully determined. The
  block **ends** with the final line of the trimmed content followed by a single
  newline — no trailing blank line (the content is trimmed) and no terminator
  beyond that newline — completing the byte contract for the block itself. The
  byte-exact whitespace that separates this block from any preceding context
  blocks in the assembled prompt is a concern of the shared injection mechanism
  (0016), not of this block's contract.
- **Two-level per-skill instructions (divergence from the accelerator).** The
  accelerator has a single `skills/<skill>/instructions.md` with no personal
  level. Luminosity adds `skills/<skill>/instructions.local.md`, so per-skill
  instructions follow the same team/personal model ADR-0003 defines and stories
  0016/0017 already apply. The combination rule is the one 0016/0017 implement —
  trim each level, drop the empty ones, join the survivors team-then-personal
  with one blank line — so an empty combined result means no block at all. The
  two levels share one `## Additional Instructions` header. Personal-after-team
  ordering means the personal level lands last and therefore takes precedence,
  consistent with the instructions-last precedence property.
- **Frontmatter is stripped (divergence from the accelerator).** The
  accelerator's per-skill readers inject the whole file; Luminosity strips YAML
  frontmatter and injects only the body, consistent with `config.md` /
  `context.md` and with the single file-reading primitive the Rust CLI already
  owns.
- `.gitignore` already carries the ignore+eval-fixture-negation pair for
  `config.local.md` and `context.local.md`; the per-skill personal instructions
  file needs the equivalent pair.
- **No legacy-layout precondition (divergence from the accelerator).** The
  accelerator's readers call `config_assert_no_legacy_layout` first to guard
  against a pre-migration on-disk config layout inherited from its released
  history. Luminosity is an as-yet-unreleased plugin with no prior released
  layout, so there is no legacy layout to assert against — the precondition does
  not carry over and is deliberately out of scope for this story. The reader is
  not required to call any legacy-layout assertion.
- `<config-dir>` resolves to `.luminosity` in Luminosity (ADR-0003).
- **ADR references.** ADR-0020 (per-skill customisation directory) is an ADR of
  the **accelerator** repository, not of Luminosity — Luminosity's own ADR series
  currently ends at ADR-0011. The governing *Luminosity* ADRs are ADR-0003 (the
  `.luminosity/` layout and the multi-level config model), ADR-0001 (skills-vs-CLI
  division of labour), and ADR-0009 (the hexagonal core).

## Drafting Notes

- Extracted as a standalone story from epic 0011's third theme; kept separate
  from 0016 and 0017 per the author (the shared injection mechanism does not
  warrant merging).
- Proposed kind `story`, priority `medium` (inherited from the epic).
- Enriched 2026-07-11: resolved the first-slice wiring question to **all skills**;
  tightened acceptance criteria (blank-line trimming, exact-header-match,
  all-skills wiring; split the configure-surface and eval-coverage criteria).
- Reviewed 2026-07-11 (review 1, REVISE — see
  `meta/reviews/work/0018-per-skill-instructions-injection-review-1.md`).
  Amendments: reconciled the "override" wording with the additive mechanism;
  fixed the "skill body" vs "prompt" placement-term drift; embedded the exact
  `## Additional Instructions` wrapper block; made the configure-surface and
  eval-coverage ACs observable; named `.claude-plugin/plugin.json` as the
  universal-wiring enumeration source; recorded 0010, 0016/0017, and the
  `config_assert_no_legacy_layout` precondition as dependencies.
- Enriched 2026-07-19: adopted the **two-level model** (`instructions.local.md`
  personal level alongside the team `instructions.md`) and **frontmatter
  stripping**, bringing per-skill instructions to full parity with story 0017's
  per-skill context. This directly acts on the flag raised in 0017's own drafting
  notes ("Story 0018 should very likely follow suit with an `instructions.local.md`").
  Both divergences were confirmed by the author. Drove Summary/Context rewrites,
  new Requirements (both-level read, combination rule, frontmatter stripping,
  git-ignore), five new acceptance criteria (per-level, combination, frontmatter,
  git-ignore), and Technical Notes recording both divergences and the
  personal-after-team precedence property.
- Reviewed 2026-07-19 (review 2, REVISE — see
  `meta/reviews/work/0018-per-skill-instructions-injection-review-2.md`).
  Amendments: retired the `config_assert_no_legacy_layout` Open Question as
  not-applicable (Luminosity is an unreleased plugin with no legacy layout) and
  removed the conditional prerequisite from Dependencies; annotated the 0016/0017
  blockers as done (all three blockers now cleared); pinned the wrapper prose to
  fixed hard line breaks so the byte-for-byte AC is fully determined; added an
  acceptance criterion asserting the injection invocation line is present in every
  registered `SKILL.md` (independent of fixtures), closing the universal-wiring
  gap; and applied clarity polish (spelled out the Summary precedence referents,
  named the per-skill instructions reader consistently, glossed "initial delivery
  scope").
- Re-reviewed 2026-07-19 (review 2, pass 2, COMMENT — all pass-1 findings
  resolved). Follow-up amendments closing the newly-surfaced items: added an
  acceptance criterion for the mixed empty-level (drop-empty join) case; named
  the `## Project Context` / `## Skill-Specific Context` blocks in the ordering
  criterion and Requirements and scoped that criterion to relative position;
  pinned the block terminator (single trailing newline, no trailing blank line)
  in Technical Notes; and annotated the 0010 eval-framework relation as done.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
- Related: 0017 (per-skill context — the direct template for the two-level model
  and frontmatter stripping adopted here)
