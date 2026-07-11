---
type: work-item
id: "0021"
title: "Config-File Comment Strategy"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: medium
parent: "work-item:0011"
tags: [configuration, comments, schema]
last_updated: "2026-07-11T11:19:14+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0021: Config-File Comment Strategy

**Kind**: Story
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity user, I want the committed team config file to carry helpful
comments documenting each key, so the file is self-documenting — implemented as
tool-generated comments derived from the schema rather than fragile hand-authored
ones.

## Context

Second half of epic 0011's fifth theme, and an enhancement past the accelerator
(which bans YAML comments outright). No Rust YAML crate preserves comments across
a dynamic-key parse→edit→serialise round-trip, so the leading candidate is to
generate comments *from* the schema on write. This story depends on the composed
schema (0020), which is what makes generate-from-schema viable.

## Requirements

- Decide between **generate-comments-from-schema** (tool-owned, deterministic
  files; users cannot hand-annotate) and **preserve-user-authored** (partial —
  only inline comments on known fields are recoverable via `serde-saphyr`'s
  `Commented`; freestanding blocks are lost).
- Record the decision (e.g. as an additive ADR or on the schema story).
- Implement the chosen strategy for the committed team file
  (`.luminosity/config.md`).
- If generate-from-schema: render each key's doc description above/beside its
  value on write (e.g. via `serde-saphyr`'s `Commented` wrapper).

## Acceptance Criteria

- [ ] The comment strategy is explicitly decided and recorded.
- [ ] Given the chosen strategy, when the team config file is written by the
      tool, then comments are present (generated) or preserved per the decision.
- [ ] A read→write round-trip of the team config file is deterministic and
      lossless for values and key ordering (building on 0009's order-preserving
      `Node`).
- [ ] The `configure` skill surfaces this behaviour, and the eval suite covers
      it (per epic 0011's cross-cutting requirement).

## Open Questions

- Generate vs preserve — leaning generate-from-schema per epic 0011, but the
  decision is not yet final. If it needs prototyping, this could be run as a
  `spike` first.

## Dependencies

- Blocked by: 0020 (composed, validated configuration schema — the schema is what
  makes generate-from-schema viable) and 0009 (order-preserving `Node` — done).
- Parent: 0011.

## Assumptions

- The team config file becomes a documented, tool-owned rendering rather than a
  hand-annotated file (if generate-from-schema is chosen).

## Technical Notes

- `serde-saphyr`'s `Commented` covers only inline comments on known typed fields;
  freestanding comment blocks separated by blank lines are lost. String-level
  patchers (`yamlpath`/`yamlpatch`) preserve formatting but are caveated (no
  `Replace` on sequences, weak at creating absent nested blocks) and incompatible
  with a typed reserialise.
- The accelerator bans comments entirely, so Luminosity has no inherited
  solution — this is greenfield.

## Drafting Notes

- Extracted from epic 0011's fifth theme, split from the schema story (0020)
  which it depends on.
- Proposed kind `story`; could be a `spike` if the generate-vs-preserve decision
  needs prototyping before commitment.

- Extracted from source documents without interactive enrichment.
  Acceptance criteria, dependencies, and kind may need refinement before
  promoting from `draft` to `ready`.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
