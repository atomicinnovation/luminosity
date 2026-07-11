---
type: work-item
id: "0016"
title: "Plugin-Global Additional Context Injection"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: medium
parent: "work-item:0011"
blocks: ["work-item:0017", "work-item:0018"]
relates_to: ["work-item:0010"]
tags: [configuration, context-injection]
last_updated: "2026-07-11T17:58:14+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0016: Plugin-Global Additional Context Injection

**Kind**: Story
**Status**: Ready
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity user, I want free-form project context I write in the bodies of
`.luminosity/config.md` (team) and `.luminosity/config.local.md` (personal) to be
injected into skill prompts, so that skills act on project-specific context
without me repeating it each invocation.

## Context

First of the three context-injection themes of epic 0011. The accelerator
implements this via `config-read-context.sh`, which reads the Markdown body
below the frontmatter of both config files (team then personal), concatenates
them, wraps them under a fixed `## Project Context` header, and the skill splices
that stdout into its prompt near the top of the skill body via the
`!`-preprocessor. In Luminosity the *management* surface — where a user edits
the config-file bodies — is the `configure` skill, but the *injection target* is
every skill's prompt; the reader itself is implemented in the Rust CLI.

## Requirements

- The Rust CLI reads the Markdown body (content below the closing frontmatter
  `---`) of the team and personal config files, in team-then-personal order.
- The Rust CLI concatenates the two bodies separated by a blank line and trims
  leading/trailing blank lines.
- The Rust CLI wraps the combined body under the exact `## Project Context`
  header and wrapper prose reproduced in Technical Notes (header and prose are
  load-bearing).
- The skill `!`-preprocessor injects the CLI output near the top of the skill
  body, before skill-specific instructions.
- Wire the injection into **every skill** registered in
  `.claude-plugin/plugin.json` (first-slice scope is all skills, not a subset).
- The Rust CLI emits nothing when both bodies are empty/absent.
- Expand the `configure` skill to surface this capability (per epic 0011's
  cross-cutting requirement).
- Extend the eval suite to cover the injection behaviour (per epic 0011's
  cross-cutting requirement, building on story 0010).

## Acceptance Criteria

- [ ] Given a team config with a non-empty body and no personal config, when a
      wired skill is invoked, then the prompt contains the `## Project Context`
      block with the team body.
- [ ] Given a personal config with a non-empty body and no team config, when a
      wired skill is invoked, then the prompt contains the `## Project Context`
      block with the personal body.
- [ ] Given both team and personal config bodies are non-empty, when a wired
      skill is invoked, then both bodies appear under one `## Project Context`
      block, team first, separated by a blank line.
- [ ] Given config bodies with surrounding blank lines, when the block is
      emitted, then it has no leading or trailing blank lines.
- [ ] Given both config bodies are empty or absent, when a wired skill is
      invoked, then no `## Project Context` block is emitted.
- [ ] Given a wired skill whose body contains skill-specific instructions, when
      the skill is invoked with a non-empty config body, then the
      `## Project Context` block appears *before* those skill-specific
      instructions (the near-top placement is load-bearing).
- [ ] The emitted header line and wrapper prose match the exact
      `## Project Context` block reproduced in Technical Notes, byte-for-byte
      (the header and prose are load-bearing).
- [ ] Frontmatter/body split uses the first two `---` fences only; a file whose
      first line is not `---` is treated as all-body.
- [ ] Given the set of skills enumerated in `.claude-plugin/plugin.json`, when
      each is invoked with a non-empty config body, then every one emits the
      `## Project Context` block — a test iterates the registry and asserts each
      entry, rather than checking a single skill.
- [ ] Given the `configure` skill is invoked, then its rendered surface lists an
      action for managing the plugin-global project context that names the team
      and personal config-file bodies as the source, and the skill body includes
      that action.
- [ ] The eval suite exercises each injection scenario: team-only body,
      personal-only body, both bodies present (team-first ordering), and
      both-empty-emits-nothing — each asserting the presence/absence and content
      of the `## Project Context` block (building on the eval framework from
      story 0010).

## Open Questions

- None outstanding.

## Dependencies

- Blocked by: 0009 (multi-level config model — done).
- Relates to: 0010 (eval framework) — the eval-coverage acceptance criterion
  builds on the framework story 0010 establishes; that framework must be in
  place before the eval-coverage criterion can be satisfied.
- Parent: 0011.
- Blocks: 0017 (per-skill context) and 0018 (per-skill instructions) — this
  story establishes the shared injection/wiring mechanism and the
  `## Project Context` placement anchor that both siblings extend, so it lands
  first. All three remain separate stories (decided); the shared mechanism does
  not warrant merging.

## Assumptions

- The wrapper header text and near-top placement should match the accelerator
  exactly (the header text is load-bearing for downstream skill prose).

## Technical Notes

- **Accelerator reference (external `atomicinnovation/accelerator` repo — these
  paths are NOT in this tree).** The behaviour this story reimplements in Rust
  lives in the accelerator's bash library:
  - `scripts/config-read-context.sh` — the reader itself (assembles the
    `## Project Context` block).
    URL: <https://github.com/atomicinnovation/accelerator/blob/main/scripts/config-read-context.sh>
    Local (installed plugin cache):
    `~/.claude/plugins/cache/atomic-innovation-prerelease/accelerator/<version>/scripts/config-read-context.sh`
  - `config_extract_body` / `config_trim_body` in `scripts/config-common.sh` —
    the body-extract and body-trim helpers it builds on.
    URL: <https://github.com/atomicinnovation/accelerator/blob/main/scripts/config-common.sh>
    Local:
    `~/.claude/plugins/cache/atomic-innovation-prerelease/accelerator/<version>/scripts/config-common.sh`
  - (`<version>` is the installed accelerator plugin version, e.g.
    `1.24.0-pre.11`.)
- **Local (luminosity) Rust body-split equivalent to build on** —
  `cli/config-adapters/src/frontmatter.rs` (the `split` primitive) +
  `document.rs`. These paths exist only in this repo; the accelerator's own Rust
  migration has not yet extracted a `config-adapters` crate.
- **Exact wrapper block (load-bearing, from `config-read-context.sh`)** — the
  emitted block is the header, a blank line, the fixed two-line prose, a blank
  line, then the trimmed combined body:

  ```
  ## Project Context

  The following project-specific context has been provided. Take this into
  account when making decisions, selecting approaches, and generating output.

  <combined team-then-personal body>
  ```
- **ADR-0017 — accelerator ADR** (external repo), "Configuration Extension
  Points for Templates, Agents, and Custom Lenses".
  URL: <https://github.com/atomicinnovation/accelerator/blob/main/meta/decisions/ADR-0017-configuration-extension-points.md>
  Local:
  `~/.claude/plugins/cache/atomic-innovation-prerelease/accelerator/<version>/meta/decisions/ADR-0017-configuration-extension-points.md`
- **ADR-0003 — this repo's ADR**, "Multi-Level Userspace Configuration Model"
  (the `.luminosity/` config-file layout / team-vs-personal levels this story
  reads from): `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md`.

## Drafting Notes

- Extracted as a standalone story from epic 0011's first theme; kept separate
  from 0017/0018 per the author (the shared injection mechanism does not warrant
  merging).
- Proposed kind `story` (specific single deliverable) and priority `medium`
  (inherited from the epic).
- Enriched 2026-07-11: resolved the first-slice wiring question to **all skills**
  (recorded as a requirement and a universal-wiring acceptance criterion);
  tightened acceptance criteria (added personal-only, blank-line trimming,
  exact-header-match, and all-skills-wiring cases; split the configure-surface
  and eval-coverage criterion in two).
- Reviewed 2026-07-11 (review 1, REVISE — see
  `meta/reviews/work/0016-plugin-global-context-injection-review-1.md`).
  Amendments: disambiguated the Context management-surface vs injection-target
  wording; embedded the exact `## Project Context` wrapper block in Technical
  Notes and pointed the exact-match AC at it; added a placement-verification AC
  (block before skill-specific instructions); made the configure-surface and
  eval-coverage ACs observable (concrete `configure` action; enumerated eval
  scenarios); named `.claude-plugin/plugin.json` as the universal-wiring
  enumeration source; added Requirements bullets for the configure-surface and
  eval extension; recorded 0010 as an eval-framework dependency and reframed
  0017/0018 from symmetric `relates_to` to `Blocks` (0016 owns the shared
  mechanism/anchor).

- Corrected 2026-07-11 (post codebase research,
  `meta/research/codebase/2026-07-11-0016-plugin-global-context-injection.md`):
  disambiguated accelerator vs. local references in Technical Notes. The
  `config-read-context.sh` / `config-common.sh` scripts and ADR-0017 are
  **accelerator** artifacts (external `atomicinnovation/accelerator` repo), now
  cited by URL then installed-plugin-cache path; the `cli/config-adapters/**`
  Rust paths are **luminosity-local**; ADR-0003 is this repo's config-model ADR
  (its prior "`.luminosity/` layout" gloss corrected to the actual title).

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
