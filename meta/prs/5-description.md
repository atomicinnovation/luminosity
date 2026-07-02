---
type: pr-description
id: "5"
title: "Add work item 0013: bump the pinned Rust stable toolchain"
date: "2026-07-02T00:12:52+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "0013"
relates_to: ["work-item:0007"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/5"
pr_number: 5
tags: [work-item, rust, toolchain, planning]
revision: "3c4b7860f65274a16c9e85a0aae4de263ccbb722"
repository: "luminosity"
last_updated: "2026-07-02T00:12:52+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Add work item 0013: bump the pinned Rust stable toolchain

## Summary

Captures the follow-up work item 0013: bump the pinned Rust stable toolchain
past 1.90 and remove the dependency-pinning workarounds the 1.90 ceiling forced
during 0007 (the exact `vergen = "=9.0.6"` pin and the transitive
`cargo-platform 0.3.2` pin). Documentation only — a single work-item file.

## Changes

- New `meta/work/0013-bump-pinned-rust-stable-toolchain.md` (task, low priority):
  scope, acceptance criteria, and open questions (bump cadence and the exact
  target version).

## Context

Surfaced while implementing 0007: `vergen` 10.x requires Rust 1.95, so the 9.x
line and an exact pin were needed to stay within the 1.90 MSRV. For a
static-binary project (no downstream MSRV contract) the low pin buys little,
so the bump is worth doing deliberately. Relates to work item 0007; sits under
epic 0001.

## Testing

- [x] Documentation only — no code, build, or test changes; nothing to run.

## Notes for Reviewers

- Small, self-contained work-item addition. Stacked on #4; the actual toolchain
  bump is deferred to this work item's own future implementation.
