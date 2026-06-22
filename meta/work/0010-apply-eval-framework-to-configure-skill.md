---
type: work-item
id: "0010"
title: "Apply the Eval Framework to the configure Skill"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: high
parent: "work-item:0001"
tags: [story, evaluation, skills, configure]
last_updated: "2026-06-22T20:03:08+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0010: Apply the Eval Framework to the configure Skill

**Kind**: Story
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Apply the chosen skill-evaluation framework to the `configure` skill as its first
evaluation target, run during development, with the benchmark result committed to
the repository, so the eval approach is proven end-to-end without incurring
per-PR token cost in CI.

## Context

The eval-framework spike recommends an approach; this story applies it (A4). The
`configure` skill is the first target because it is the proof-of-architecture for
the skills-vs-CLI division. Skill evals consume significant tokens per trial, so
they are run on demand during development rather than on every CI run; the
recorded benchmark result is version-controlled as the quality signal.

## Requirements

- Stand up an eval suite for the `configure` skill using the framework chosen by
  the eval spike, following that spike's recommendation for how a pass-rate /
  benchmark result is produced.
- Run the eval during development via a repeatable command (e.g. a `mise` task),
  not in CI — explicitly to avoid per-PR token cost.
- Commit the benchmark result (pass-rate / metrics artifact) to the repository
  under version control, so changes to the signal are visible in diffs/history.
- Apply the epic's provisional floor (≥ 3 tasks, ≥ 80% pass-rate) unless the eval
  spike raised it; use the spike's recorded final thresholds where set.

## Acceptance Criteria

- [ ] The eval suite for the `configure` skill contains at least the agreed
      minimum number of tasks (≥ 3 provisional, or the eval spike's final count)
      and is runnable on demand via a documented command.
- [ ] When the eval is run during development, it produces a benchmark result
      that is committed to the repository.
- [ ] The committed `configure` pass-rate meets or exceeds the agreed baseline
      (≥ 80% provisional, or the eval spike's final baseline).
- [ ] The eval uses the framework selected by the eval spike (decision 11), and
      no eval is wired to run on every CI build.

## Open Questions

- Is there a cadence/trigger for refreshing the committed benchmark (e.g. on
  `configure` skill changes), or is it left to developer discretion? To be
  settled with the eval spike's workflow recommendation.

## Dependencies

- Blocked by: the eval-framework spike (0003, chooses the framework, thresholds,
  and dev-time workflow); the configuration story (0009, provides the `configure`
  skill).
- Blocks: none; part of the epic's definition of done.
- Parent: epic 0001.

## Assumptions

- The eval-framework recommendation is applied within this epic (A4), not just
  decided.
- Running evals in CI is deliberately avoided due to token cost; the
  version-controlled benchmark result is the durable record instead.

## Technical Notes

- Methodology follows the eval spike: multiple trials per task for variance,
  outcome-based grading, baseline comparison.
- The committed benchmark artifact (e.g. skill-creator's `benchmark.json` /
  `benchmark.md`, or the chosen framework's equivalent) is the checked-in signal;
  re-running the eval regenerates it.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (one eval suite applied to
  one skill).
- Execution model set to dev-time + committed results (per the author), NOT CI
  gating, to control token cost — this revises the epic's "runs in CI" criterion
  and the eval spike's CI-gate framing.
- Task sourcing left to the eval spike's workflow; default leans toward realistic
  `configure` scenarios (get/set, precedence, missing/malformed key) starting at
  the provisional floor and expanding later.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
