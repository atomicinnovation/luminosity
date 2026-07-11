---
type: work-item
id: "0020"
title: "Composed, Validated Configuration Schema"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: medium
parent: "work-item:0011"
blocks: ["work-item:0021"]
tags: [configuration, schema, validation, architecture]
last_updated: "2026-07-11T11:19:14+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0020: Composed, Validated Configuration Schema

**Kind**: Story
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity maintainer, I want a composed, typed configuration schema
assembled from per-crate fragments at the launcher composition root, so config
values can be validated (unknown-key and type errors caught) while the generic
`config` core stays free of any dependency on subcommand schemas.

## Context

Fifth theme of epic 0011, and an enhancement past the accelerator (whose
validation is warn-and-ignore, not schema-enforced). The accelerator does offer a
precedent: a recognised-key catalogue of 55 keys across 6 groups, drift-tested
between bash (`config-defaults.sh`) and Rust (`cli/config/src/catalogue.rs`) — a
defaults registry, not a rejecting schema. This story turns that idea into a
validated, cross-crate-composable schema on top of story 0009's typed,
order-preserving `Node` and `serde-saphyr` adapters.

## Requirements

- Each subcommand crate contributes its own namespaced, serde-(de)serialisable
  schema fragment (a sub-struct).
- The aggregate schema is assembled ONLY at the launcher composition root; the
  generic `config` core never depends on any subcommand's schema fragment,
  preserving the ADR-0009/0010 inward dependency direction.
- Config values are validated against the schema: unknown-key and type errors
  are caught.
- The validation posture — strict-reject vs warn-and-ignore — is decided and
  enforced (the accelerator is lenient with a few enum hard-fails).
- Built on 0009's dynamic typed core; the schema/validation layer sits at the
  edge (composition root), not inside the generic core.

## Acceptance Criteria

- [ ] Given a config containing an unknown key, when config is loaded and
      validated, then the chosen posture is applied deterministically (rejected
      with an error, or warned-and-ignored) and the behaviour is exercised by
      tests.
- [ ] Given a config value of the wrong type for a known key, when validated,
      then a type error is surfaced.
- [ ] The generic `config` core compiles and links without depending on any
      subcommand crate's schema fragment (enforced by an architecture check,
      e.g. cargo-pup).
- [ ] The composed schema aggregates fragments from at least two crates at the
      launcher composition root.
- [ ] The `configure` skill surfaces schema-aware get/set/validate, and the eval
      suite covers it (per epic 0011's cross-cutting requirement).

## Open Questions

- Strict-reject vs warn-and-ignore posture (see epic 0011) — interacts with
  forward/backward compatibility across plugin versions.
- Is this story large enough to warrant promotion to a nested `epic`?

## Dependencies

- Blocked by: 0009 (typed `Node` + `serde-saphyr` adapters — done).
- Blocks: 0021 (config-file comment strategy depends on this schema).
- Parent: 0011.

## Assumptions

- The schema layer can be added at the composition root without re-architecting
  0009's generic core or its cross-crate boundary (per epic 0011's Technical
  Notes).

## Technical Notes

- Accelerator catalogue precedent: 55 keys across 6 groups
  (`cli/config/src/catalogue.rs`, drift-tested against
  `scripts/config-defaults.sh`).
- The schema-composition design (cross-crate fragment aggregation at the
  composition root, generic core untouched) should be recorded as its own
  additive ADR (per epic 0011). Consistent with ADR-0003 ("richer schemas as the
  configuration catalogue grows") and ADR-0009/0010 (inward dependency).

## Drafting Notes

- Extracted from epic 0011's fifth theme, split from the comment-strategy work
  (0021) which depends on this schema.
- Proposed kind `story` but flagged for possible re-size to `epic` — cross-crate
  schema composition plus validation may be several stories.

- Extracted from source documents without interactive enrichment.
  Acceptance criteria, dependencies, and kind may need refinement before
  promoting from `draft` to `ready`.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
