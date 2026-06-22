---
type: work-item
id: "0004"
title: "Record Existing/Implicit Architecture Decisions as ADRs"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
tags: [story, adr, architecture, documentation]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0004: Record Existing/Implicit Architecture Decisions as ADRs

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Record the eight immediately-recordable baseline architecture decisions
(theme 1 decisions 1–8) as accepted ADRs, so the foundations the plugin already
rests on are explicit and reviewable before feature work begins.

## Context

Several architectural decisions already exist — some decided, some implicit in
the codebase — and the epic (0001) calls for capturing them as ADRs. These eight
have no dependency on the architecture spike and can be recorded immediately.

## Requirements

Record one accepted ADR per decision, for theme 1 decisions 1–8:

1. Skills-vs-CLI division of labour (probabilistic work in skills; deterministic
   procedural logic in the CLI).
2. Zero-setup static-binary distribution (ported from accelerator).
3. Multi-level userspace configuration model.
4. Three-toolchain split (Python / shell / Rust).
5. Bash 3.2 floor.
6. `mise` + invoke task runner.
7. Skills-as-product.
8. Filesystem-as-message-bus and knowledge corpus.

Each ADR follows the project's ADR template (frontmatter + Context · Decision
Drivers · Considered Options · Decision · Consequences · References; status from
proposed | accepted | rejected | superseded | deprecated; immutable once
accepted). Each ADR is authored as `proposed` and accepted by the author
directly — a separate review (e.g. a review-adr workflow) is optional, not
required for this story.

This story also settles the message-bus / knowledge-corpus directory (the epic's
first Open Question) so that decision 8's ADR records the chosen directory
concretely and is accepted here — not left pending.

## Acceptance Criteria

- [ ] An accepted ADR exists for each of decisions 1–8, each following the ADR
      template with non-empty Context, Considered Options, and Consequences
      sections; each transitions proposed → accepted by author acceptance.
- [ ] Each ADR's Decision is stated in active voice and its Consequences cover
      Positive, Negative, and Neutral.
- [ ] The message-bus / knowledge-corpus directory is decided within this story,
      and decision 8's ADR records that directory concretely with status
      `accepted` (no pending placeholder, no deferred superseding ADR).

## Open Questions

- None outstanding for this story — the message-bus / knowledge-corpus directory
  is decided here as part of recording decision 8 (resolving the epic's first
  Open Question).

## Dependencies

- Blocked by: none (no spike dependency).
- Blocks: none directly, though it records foundations later work relies on.
- Parent: epic 0001.

## Assumptions

- The existing Python/shell toolchains are recorded but not changed (epic Out of
  Scope).

## Technical Notes

- Existing implicit decisions live in the current codebase (three-toolchain
  split, bash 3.2 floor, `mise` + invoke, skills-as-product, filesystem-mediated
  phase communication).
- The ADR template, status vocabulary, and immutability rule are described in
  Requirements so the implementer can satisfy them with any tooling they choose.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (eight ADRs).
- Split from the spike-dependent ADRs (decisions 9–11) so the immediately-
  recordable decisions are not gated behind the spikes.
- Describes the ADR template/structure rather than naming a specific authoring
  tool (per the author) — the implementer chooses how to produce ADRs matching
  this shape.
- Acceptance gate set to author acceptance (review optional) per the author.
- Directory decision pulled into this story's scope (per the author) so decision
  8's ADR is fully accepted, rather than recording the pattern and deferring the
  directory — this resolves the epic's first Open Question.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
