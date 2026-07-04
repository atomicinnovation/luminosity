---
type: work-item
id: "0011"
title: "Configuration Feature Parity with Accelerator"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: epic
priority: medium
relates_to: ["work-item:0009"]
tags: [epic, configuration, parity, future]
last_updated: "2026-07-05T15:05:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0011: Configuration Feature Parity with Accelerator

**Kind**: Epic
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

Bring Luminosity's configuration system to parity with the accelerator's fuller
feature set — beyond the two-level team/personal value resolution proved in the
foundations epic — so skills can be configured and extended as richly as in the
accelerator.

## Context

The foundations epic (0001) proves only the minimal multi-level configuration
model (a value resolved across team and personal precedence via the `configure`
skill and CLI). The accelerator additionally supports several configuration
capabilities that Luminosity will likely want once foundations land. These are
captured here so they are not lost, deliberately scoped out of 0001 per its
assumption A2 (configuration limited to proving the multi-level model).

## Requirements

High-level themes (to be decomposed when this epic is refined). All five are
confirmed in scope:

- **Plugin-global additional context** — free-form context in the config file
  bodies (team and personal), e.g. `.accelerator/config.md` /
  `config.local.md` body equivalents, injected into skill prompts.
- **Per-skill context** — additional per-skill context at
  `<config-dir>/skills/<skill-name>/context.md`.
- **Per-skill instructions** — additional per-skill instructions at
  `<config-dir>/skills/<skill-name>/instructions.md`.
- **Template management subcommands** — CLI subcommands to list, show, eject,
  diff, and reset templates (mirroring the accelerator's template-management
  commands).
- **Composed configuration schema, validation, and comment strategy** — promote
  the configuration from a dynamic key/value tree to a schema of keys known
  ahead of time, so values can be validated (unknown-key and type errors caught)
  and config interactions can rely on typed values. The schema must be
  **composable across crates**: each subcommand crate contributes its own
  fragment (a namespaced, serde-(de)serialisable sub-struct), and the aggregate
  schema is assembled only at the launcher composition root — the generic
  `config` core (which resolves precedence dynamically) never depends on any
  subcommand's schema, so the ADR-0009/0010 inward dependency direction is
  preserved. On top of the schema, decide and implement a **comment strategy**
  for the committed team file, since no Rust YAML library preserves comments
  across a dynamic-key parse→edit→serialise round-trip (see Technical Notes):
  the leading candidate is generating comments *from* the schema (each key's
  doc description rendered above/beside its value on write, e.g. via
  `serde-saphyr`'s `Commented` wrapper), making config files a documented,
  tool-owned rendering rather than trying to preserve hand-authored comments.
  This theme consumes and builds on the typed, order-preserving `Node`
  foundation that story 0009 establishes.

## Acceptance Criteria

- [ ] Each feature theme above is decomposed into child work items with its own
      testable acceptance criteria when this epic is refined.
- [ ] Configuration behaviour remains consistent with the two-level precedence
      model established in the foundations epic.

## Open Questions

- The precise child decomposition (one child per feature vs grouped) is settled
  when this epic is refined; all five feature themes are confirmed in scope.
- Comment strategy for the committed team file: **generate comments from the
  schema** (tool-owned, deterministic files; users cannot hand-annotate) vs
  **preserve user-authored comments** (only inline comments on known fields are
  recoverable via `serde-saphyr`'s `Commented`, and freestanding comment blocks
  separated by blank lines are lost — so preservation is inherently partial).
  Leaning towards generate-from-schema; settled at decomposition.
- Whether the composed schema is enforced strictly (unknown keys rejected) or
  leniently (unknown keys passed through) — interacts with forward/backward
  compatibility across plugin versions.

## Dependencies

- Blocked by: the foundations multi-level configuration story (0009, establishes
  the base config model this builds on).
- Blocks: none currently.
- Relates to: the foundations configuration story (0009).

## Assumptions

- All four feature themes are confirmed wanted for Luminosity (per the author);
  the exact adaptations from the accelerator's implementation are determined at
  decomposition.

## Technical Notes

- Accelerator references: ADR-0017 (configuration extension points), ADR-0020
  (per-skill customisation directory), ADR-0021 (template-management
  subcommands), ADR-0016 (userspace configuration model).
- The config-directory layout is settled by ADR-0003: `.luminosity/config.md`
  (team, committed) + `.luminosity/config.local.md` (personal, gitignored),
  under the consolidated `.luminosity/` root. (Supersedes the earlier tentative
  `.claude/luminosity.md` framing.)
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
  generate-comments-from-schema strategy viable.

## Drafting Notes

- Created during extraction of epic 0001 when the author noted these accelerator
  features were absent from the foundations configuration story.
- Kind set to `epic`: four distinct deliverable themes, kept as one epic per the
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
  strategy were held here to keep 0009 within its Assumption A2 scope ("prove the
  multi-level model, not a full schema"). The scope boundary is A2's, not
  ADR-0003's — ADR-0003 is schema-friendly. See the 0009 plan and its review
  (`meta/reviews/plans/2026-07-05-0009-multi-level-configuration-system-review-1.md`).

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0009-multi-level-configuration-system.md`
