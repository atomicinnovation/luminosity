---
type: pr-description
id: "6"
title: "Plan-skill comment guidance and CLI-switches note"
date: "2026-07-02T00:14:11+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
pr_url: "https://github.com/atomicinnovation/luminosity/pull/6"
pr_number: 6
tags: [dx, tooling, notes, documentation]
revision: "960928c79dc61a464cc96c91eef405f268aac09a"
repository: "luminosity"
last_updated: "2026-07-02T00:14:11+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Plan-skill comment guidance and CLI-switches note

## Summary

Two small, self-contained follow-ups that emerged from the 0007 review: a
comment-discipline addition to the plan skills' project instructions, and a note
capturing a possible CLI-switch ergonomics improvement for the task toggles.

## Changes

- **`.accelerator/skills/create-plan` + `review-plan` instructions**: add
  guidance to avoid comments that merely restate code, keep comment tolerance
  very low, and drop ADR / work-item / AC references from comments (they go
  stale). review-plan gets the matching edit-time guidance.
- **`meta/notes/2026-07-01-support-cli-switches-alongside-env-toggles.md`**: a
  note on additionally supporting `--no-coverage`-style switches as a front-end
  that lowers onto the existing `coverage_enabled()` / `pup_mode()` env-var
  reads, keeping env vars as the propagation mechanism through mise roll-ups.

## Context

Both fell out of the 0007 implementation review — the comment-guidance from
tightening the plans' comment discipline, and the note from the discussion of
why the task toggles are env-var-based today.

## Testing

- [x] Documentation/config only — no code, build, or test changes; nothing to
      run.

## Notes for Reviewers

- Top of the stack (based on #5). Two independent small changes grouped into one
  PR per the agreed stack layout; neither affects runtime behaviour.
