---
type: work-item
id: "0011"
title: "Configuration Parity and Enhancements with Accelerator"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: epic
priority: medium
relates_to: ["work-item:0009", "work-item:0010", "work-item:0001"]
tags: [epic, configuration, parity, future]
last_updated: "2026-07-11T12:37:10+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0011: Configuration Parity and Enhancements with Accelerator

**Kind**: Epic
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As the Luminosity plugin, I want my configuration system to match the
accelerator's fuller feature set — and in two areas to go beyond it — so that
skills can be configured and extended as richly (and more safely) than in the
accelerator. This builds on the two-level team/personal value resolution proved
in the foundations work (story 0009), adding plugin-global and per-skill
context/instructions, template management, and a composed, validated
configuration schema. Three themes are strict parity with the accelerator; two
(schema-enforced validation and a config-file comment strategy) are deliberate
enhancements past what the accelerator does today — hence "parity **and
enhancements**".

Delivering these themes is not just CLI plumbing: each includes **expanding the
`configure` skill** to surface the capability, and **extending the eval suite**
(building on story 0010) to cover the expanded skill. Both fall under this epic.

## Context

The foundations story (0009, now **done**) delivered the minimal multi-level
configuration model: a value resolved across team and personal precedence,
exposed as a `luminosity config` CLI command driven by a thin `configure` skill.
The accelerator additionally supports several configuration capabilities that
Luminosity will want now that the foundation has landed. These were deliberately
scoped out of the foundations slice (per its assumption A2 — prove the
multi-level model, not a full schema) and are captured here so they are not
lost.

Two important accuracy notes surfaced while validating this epic against the
live accelerator checkout (`../accelerator`, 2026-07-10):

- The accelerator's configuration system is **bash-backed in production** (skills
  invoke `scripts/config-*.sh` via the `!`-preprocessor). Its Rust `cli/config` +
  `cli/config-adapters` crates are a **not-yet-integrated** parallel port
  (get/set/resolve only — no `config` binary, no template management, no context
  injection). They are the closest reference design for Luminosity's Rust port
  but are themselves pre-integration.
- Two of the five themes exceed the accelerator's actual behaviour: the
  accelerator's validation is **warn-and-ignore** (unknown keys are logged and
  dropped, never rejected) and it **explicitly bans YAML comments** in config
  files. So schema-enforced validation and a comment strategy are enhancements,
  not parity.

The overarching architectural approach mirrors 0009: every capability is
**surfaced through the `configure` skill (and content skills) but implemented
under the hood in the Luminosity Rust CLI** as much as possible — the skill is a
thin surface, the CLI is the engine.

## Requirements

Five high-level themes, now decomposed into child work items (0016–0021). All
five are confirmed in scope. Each is surfaced through skills and implemented in
the Rust CLI wherever practical.

- **Plugin-global additional context** (parity — child **0016**) — free-form context in the
  config file bodies (team and personal), i.e. the Markdown body below the
  frontmatter of `.luminosity/config.md` and `.luminosity/config.local.md`,
  injected into skill prompts. Accelerator reference: `config-read-context.sh`
  reads both bodies (team then personal), wraps them under a fixed
  `## Project Context` header, and the skill splices that into its prompt near
  the top of the skill body. Parity means matching both the wrapper prose and
  the placement.
- **Per-skill context** (parity — child **0017**) — additional per-skill context at
  `<config-dir>/skills/<skill-name>/context.md` (path confirmed against the
  accelerator). Injected under a `## Skill-Specific Context` header,
  immediately after the plugin-global context near the top of the skill body.
- **Per-skill instructions** (parity — child **0018**) — additional per-skill instructions at
  `<config-dir>/skills/<skill-name>/instructions.md` (path confirmed). Injected
  under an `## Additional Instructions` header **at the end** of the skill body
  ("in addition to all instructions above"). The context-early / instructions-
  last ordering is load-bearing and must be reproduced.
- **Template management** (parity — child **0019**) — the five operations **list, show, eject,
  diff, reset** over configurable templates, with the accelerator's **three-tier
  resolution**: `templates.<key>` config value (explicit path) → user override at
  `<paths.templates>/<key>.md` → plugin default. In the accelerator these are
  `configure`-skill H3 sub-actions backed by `config-*-template.sh` scripts. For
  Luminosity, the same capabilities are exposed through the expanded `configure`
  skill (parity of surface), but implemented under the hood via the Rust CLI
  (e.g. `luminosity config template <op>`) rather than shell scripts.
- **Composed configuration schema, validation, and comment strategy**
  (enhancement — children **0020** (schema + validation) and **0021** (comment
  strategy)) — promote the configuration from a dynamic key/value tree to a
  schema of keys known ahead of time, so values can be validated (unknown-key
  and type errors caught) and config interactions can rely on typed values. The
  accelerator has a precedent to build on — a recognised-key **catalogue of 55
  keys across 6 groups**, drift-tested between bash (`config-defaults.sh`) and
  Rust (`cli/config/src/catalogue.rs`) — but its validation is warn-and-ignore
  (only a few enum keys such as `work.integration` hard-fail), so **schema-
  enforced validation is an enhancement past the accelerator**. The schema must
  be **composable across crates**: each subcommand crate contributes its own
  fragment (a namespaced, serde-(de)serialisable sub-struct), and the aggregate
  schema is assembled only at the launcher composition root — the generic
  `config` core (which resolves precedence dynamically) never depends on any
  subcommand's schema, so the ADR-0009/0010 inward dependency direction is
  preserved. On top of the schema, decide and implement a **comment strategy**
  for the committed team file. This too is an enhancement: the accelerator
  **explicitly does not support comments** (its parser bans them, and a typed
  reserialise strips them), so Luminosity is choosing greenfield. Because no Rust
  YAML library preserves comments across a dynamic-key parse→edit→serialise
  round-trip (see Technical Notes), the leading candidate is generating comments
  *from* the schema (each key's doc description rendered above/beside its value on
  write, e.g. via `serde-saphyr`'s `Commented` wrapper), making config files a
  documented, tool-owned rendering rather than trying to preserve hand-authored
  comments. This theme consumes and builds on the typed, order-preserving `Node`
  foundation that story 0009 established.

**Cross-cutting (in scope for every theme):** each theme's delivery includes
(a) expanding the `configure` skill so the capability is exposed through its
user surface (consistent with the "thin skill surface, Rust CLI engine" pattern
from 0009), and (b) extending the eval framework — the same one story 0010
applied to the `configure` skill — to cover the new configure-skill behaviour.
The skill extensions and their eval coverage are part of this epic, not a
separate follow-up.

## Acceptance Criteria

- [ ] When this epic is refined, each of the **five** themes yields at least one
      child work item with its own specific, testable acceptance criteria.
- [ ] Given the three context-injection themes are implemented, when a skill is
      invoked with plugin-global, per-skill context, and per-skill instructions
      present, then the injected prompt reproduces the accelerator's wrapper
      headers (`## Project Context`, `## Skill-Specific Context`,
      `## Additional Instructions`) and their placement (context and per-skill
      context near the top, instructions at the end), reading from
      `.luminosity/config.md` / `config.local.md` bodies and
      `.luminosity/skills/<skill-name>/{context,instructions}.md`.
- [ ] Given template management is implemented, the `configure` skill supports
      list, show, eject, diff, and reset over the three-tier resolution
      (`templates.<key>` → user override → plugin default), with the underlying
      work performed by the Rust CLI.
- [ ] The validation posture (strict-reject vs warn-and-ignore) and the comment
      strategy (generate-from-schema vs preserve-user-authored) are each
      explicitly **decided and recorded** (both exceed accelerator behaviour, so
      a choice must be made, not inherited), and the chosen validation behaviour
      is exercised by tests.
- [ ] The `configure` skill is expanded to surface every delivered capability
      (plugin-global/per-skill context and instructions management, template
      list/show/eject/diff/reset, and schema-aware get/set/validate), and each
      surface is exercised by tests.
- [ ] The eval suite is extended to cover the expanded `configure` skill for
      each delivered capability, building on the eval framework established in
      story 0010.
- [ ] Configuration behaviour remains consistent with the two-level
      team-over-personal precedence model established in story 0009 across all
      additions.

## Open Questions

- Comment strategy for the committed team file: **generate comments from the
  schema** (tool-owned, deterministic files; users cannot hand-annotate) vs
  **preserve user-authored comments** (only inline comments on known fields are
  recoverable via `serde-saphyr`'s `Commented`, and freestanding comment blocks
  separated by blank lines are lost — so preservation is inherently partial).
  The accelerator offers no precedent here (it bans comments entirely), so this
  is a greenfield Luminosity choice. Leaning towards generate-from-schema;
  settled at decomposition.
- Whether the composed schema is enforced strictly (unknown keys rejected) or
  leniently (unknown keys passed through) — interacts with forward/backward
  compatibility across plugin versions. Reference point: the accelerator is
  **lenient** (unknown keys warn to stderr and are ignored), with hard-fails
  reserved for a few enum keys (e.g. `work.integration` must be one of
  jira/linear/trello/github-issues). Luminosity may choose to be stricter.

## Dependencies

- Blocked by: nothing outstanding. The foundations multi-level configuration
  story (0009) established the base config model this builds on and is now
  **done**, so this epic is unblocked and ready to refine.
- Blocks: none currently.
- Relates to: 0009 (foundations config model); 0010 (eval framework applied to
  the `configure` skill — **this epic extends that eval coverage to the new
  capabilities**); 0001 (baseline architecture epic under which the config work
  sits).

## Assumptions

- All **five** feature themes are confirmed wanted for Luminosity (per the
  author); the exact adaptations from the accelerator's implementation are
  determined at decomposition.
- Two of the five themes — schema-enforced validation and a config-file comment
  strategy — deliberately **exceed** the accelerator's current behaviour (which
  is warn-and-ignore for validation and bans comments), so "parity" is a loose
  umbrella label for the epic, not a literal claim for every theme.
- Each capability is surfaced through the `configure` (and content) skills but
  implemented under the hood in the Rust CLI wherever practical, consistent with
  the pattern 0009 established. Expanding the `configure` skill and extending its
  evals are in scope of this epic, not deferred elsewhere.

## Technical Notes

- Accelerator references: ADR-0016 (userspace configuration model), ADR-0017
  (configuration extension points), ADR-0020 (per-skill customisation
  directory), ADR-0021 (template-management subcommands), ADR-0047 (multi-level
  model).
- The config-directory layout is settled by ADR-0003: `.luminosity/config.md`
  (team, committed) + `.luminosity/config.local.md` (personal, gitignored),
  under the consolidated `.luminosity/` root. (Supersedes the earlier tentative
  `.claude/luminosity.md` framing.)
- **Accelerator implementation state:** the live config system is bash
  (`scripts/config-*.sh`, invoked via the `!`-preprocessor in each `SKILL.md`).
  The Rust `cli/config` + `cli/config-adapters` crates are a not-yet-integrated
  port covering get/set/resolve only — there is no `config` binary, no template
  management in Rust, and no context injection in Rust. Treat the accelerator's
  Rust core as a reference design, not a finished target.
- **Schema precedent:** the accelerator's recognised-key catalogue is 55 keys
  across 6 groups (`PATH_KEYS`, `TEMPLATE_KEYS`, `WORK_KEYS`, `REVIEW_KEYS`,
  `AGENT_KEYS`, `VISUALISER_KEYS`) plus doc-types, drift-tested between
  `scripts/config-defaults.sh` and `cli/config/src/catalogue.rs`. It is a
  defaults registry + drift test, not a rejecting schema — the enhancement here
  is turning it into a validated schema.
- **Context-injection is load-bearing:** the wrapper headers (`## Project
  Context`, `## Skill-Specific Context`, `## Additional Instructions`) and the
  placement (context/per-skill-context near the top, instructions at the end)
  are part of the contract, not incidental — the instructions header text even
  references "all instructions above". Frontmatter/body split uses the first two
  `---` fences only.
- **Template resolution** is a three-tier fallback: `templates.<key>` config
  value (explicit path) → `<paths.templates>/<key>.md` user override → plugin
  default at `<plugin_root>/templates/<key>.md`. Source labels in the accelerator
  are "config path" / "user override" / "plugin default".
- A composed schema is consistent with ADR-0003, which explicitly anticipates
  "richer schemas as the configuration catalogue grows" — the schema theme is
  the ADR's own anticipated direction, not a reversal of it. When built, the
  schema-composition design (cross-crate fragment aggregation at the composition
  root, generic core untouched) should be recorded as its own additive ADR.
- Foundation from story 0009: the `config` core models a **typed, order-
  preserving `Node`** (scalar strings, booleans, integers, floats, null, and
  sequences, with mapping key insertion order retained), parsed and serialised
  by `serde-saphyr` (pure-Rust, MIT/Apache) in `config-adapters`. Resolution
  (precedence, fall-through, level-scoped reads, empty-vs-unset) stays dynamic in
  the core; typed values and ordering are retained through the round-trip. This
  epic layers the schema and validation at the edge (composition root) on top of
  that dynamic typed core, so it can be added without re-architecting 0009's core
  or its cross-crate boundary.
- Comment preservation is a known gap deferred from 0009: as of 2026-07, no Rust
  YAML crate offers ruamel-style comment-preserving round-trip for a dynamic-key
  tree — `serde-saphyr`'s `Commented` covers only inline comments on known typed
  fields (freestanding blocks are lost), and surgical patchers
  (`yamlpath`/`yamlpatch`) preserve formatting but are string-level, caveated
  (no `Replace` on sequences, weak at creating absent nested blocks), and
  incompatible with a typed reserialise. The schema theme is what makes the
  generate-comments-from-schema strategy viable. The accelerator itself sidesteps
  this by banning comments outright, so Luminosity has no inherited solution.

## Drafting Notes

- Created during extraction of epic 0001 when the author noted these accelerator
  features were absent from the foundations configuration story.
- Kind set to `epic`: five distinct deliverable themes, kept as one epic per the
  author. May be re-sized or split during refinement.
- Deliberately NOT a child of epic 0001 (per the author) — it is future work
  beyond the foundations proof slice; linked via `relates_to` instead of
  `parent`.
- Added 2026-07-05 (during planning of story 0009): the **composed configuration
  schema, validation, and comment strategy** theme was added as the fifth
  in-scope theme, and the typed-`Node`/`serde-saphyr` foundation was recorded.
  This came out of the 0009 plan review: type fidelity (bool/number/null/
  sequence) and key-order retention are delivered by 0009's typed `Node`, but a
  schema, cross-crate schema composition, validation, and a comment-preservation
  strategy were held here to keep 0009 within its Assumption A2 scope. The scope
  boundary is A2's, not ADR-0003's — ADR-0003 is schema-friendly. See the 0009
  plan and its review
  (`meta/reviews/plans/2026-07-05-0009-multi-level-configuration-system-review-1.md`).
- Enriched 2026-07-10 by validating every theme against the live accelerator
  checkout (`../accelerator`). Corrections made: (a) the stale "four themes"
  count in Assumptions and Drafting Notes was fixed to five; (b) template
  management was reframed — the accelerator surfaces it as `configure`-skill
  sub-actions backed by shell scripts, not CLI binaries, so Luminosity's plan is
  now stated as "skill surface + Rust CLI engine, do both"; (c) schema-enforced
  validation and a comment strategy were flagged as enhancements **past**
  accelerator behaviour (which is warn-and-ignore and bans comments), and the
  title was reframed to "Parity **and Enhancements**"; (d) the accelerator's
  55-key/6-group catalogue was recorded as the schema precedent; (e) 0009 is now
  done, so the blocker is cleared. The author confirmed keeping all five themes,
  reframing as parity + enhancements, and the "both" template-surface approach.
- Clarified 2026-07-11 (per the author): expanding the `configure` skill to
  surface these capabilities, and extending the evals to cover that expanded
  skill, are **explicitly in scope of this epic** — not deferred to a separate
  work item. Reflected as a cross-cutting requirement and two acceptance
  criteria.
- Decomposed 2026-07-11 into six child work items (thin drafts, extracted without
  enrichment): 0016 (plugin-global context), 0017 (per-skill context), 0018
  (per-skill instructions), 0019 (template management), 0020 (composed schema +
  validation), 0021 (comment strategy). The fifth theme was split into 0020 and
  0021, with 0021 blocked by 0020. Requirements bullets now reference the child
  IDs. Children carry `parent: work-item:0011`.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0009-multi-level-configuration-system.md`,
  `meta/work/0010-apply-eval-framework-to-configure-skill.md`,
  `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Accelerator (`../accelerator`) validation sources:
  `skills/config/configure/SKILL.md`; `scripts/config-read-context.sh`,
  `config-read-skill-context.sh`, `config-read-skill-instructions.sh`,
  `config-{list,show,eject,diff,reset,read}-template.sh`, `config-common.sh`,
  `config-defaults.sh`; `cli/config/src/{catalogue,service,key,node,level}.rs`,
  `cli/config-adapters/src/{frontmatter,document}.rs`; ADR-0016, ADR-0017,
  ADR-0020, ADR-0021, ADR-0047.
