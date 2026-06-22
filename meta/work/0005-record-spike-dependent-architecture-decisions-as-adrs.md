---
type: work-item
id: "0005"
title: "Record Spike-Dependent Architecture Decisions as ADRs"
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

# 0005: Record Spike-Dependent Architecture Decisions as ADRs

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Record the three spike-dependent baseline architecture decisions (theme 1
decisions 9–11) as accepted ADRs once their feeding spikes conclude, so the
architecture and eval-framework choices are captured as explicit, reviewable
decisions.

## Context

Three baseline decisions cannot be recorded until a spike resolves them:
decisions 9 and 10 depend on the modular-CLI / hexagonal architecture spike, and
decision 11 (the eval framework) depends on the skill-evaluation spike. The epic
(0001) calls for capturing them as ADRs once the spikes deliver their
recommendations.

## Requirements

Record one accepted ADR per decision, for theme 1 decisions 9–11:

9.  Thin CLI over a hexagonal ports-and-adapters core. *(from the architecture
    spike)*
10. Git-style modular CLI of on-demand static binaries. *(from the architecture
    spike)*
11. Skill evaluation framework selection. *(from the eval spike)*

Each ADR follows the project's ADR template (frontmatter + Context · Decision
Drivers · Considered Options · Decision · Consequences · References; status from
proposed | accepted | rejected | superseded | deprecated; immutable once
accepted). Each ADR is authored as `proposed` and accepted by the author
directly — a separate review is optional, not required. Each ADR cites the
recommendation recorded in its feeding spike's work item.

## Acceptance Criteria

- [ ] An accepted ADR exists for each of decisions 9–11, each following the ADR
      template with non-empty Context, Considered Options, and Consequences
      sections; each transitions proposed → accepted by author acceptance.
- [ ] Each ADR's Decision is stated in active voice and its Consequences cover
      Positive, Negative, and Neutral.
- [ ] The ADRs for decisions 9 and 10 cite the architecture spike's
      Recommendation (0002); the ADR for decision 11 cites the eval spike's
      Recommendation (0003).

## Open Questions

- None outstanding for this story — the decisions are fixed by the two spikes'
  recommendations.

## Dependencies

- Blocked by: the modular-CLI / hexagonal architecture spike (0002, decisions
  9–10); the skill-evaluation spike (0003, decision 11).
- Blocks: none directly, though the recorded decisions guide the scaffold,
  distribution, and eval-application stories.
- Parent: epic 0001.

## Assumptions

- The eval framework warrants its own ADR (decision 11), per the epic's expanded
  theme 1 (eleven decisions).

## Technical Notes

- The ADR template, status vocabulary, and immutability rule are described in
  Requirements so the implementer can satisfy them with any tooling they choose.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (three ADRs).
- Split from the immediately-recordable ADRs (decisions 1–8) so these are not
  blocked until the spikes conclude.
- Decision 11 added per the author's choice to record the eval framework as its
  own ADR; this story therefore covers 9–11, not just 9–10.
- Kept as one story (blocked by both spikes) per the author rather than splitting
  by feeding spike — it closes once both spikes conclude.
- ADR-template description and author-acceptance convention carried over from the
  existing/implicit ADR story for consistency.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
