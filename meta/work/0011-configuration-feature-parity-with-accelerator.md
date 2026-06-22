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
last_updated: "2026-06-22T20:03:08+00:00"
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

High-level themes (to be decomposed when this epic is refined). All four are
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

## Acceptance Criteria

- [ ] Each feature theme above is decomposed into child work items with its own
      testable acceptance criteria when this epic is refined.
- [ ] Configuration behaviour remains consistent with the two-level precedence
      model established in the foundations epic.

## Open Questions

- The precise child decomposition (one child per feature vs grouped) is settled
  when this epic is refined; all four feature themes are confirmed in scope.

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
- The exact config-directory layout for Luminosity follows whatever the
  foundations config story established (`.claude/luminosity.md` family).

## Drafting Notes

- Created during extraction of epic 0001 when the author noted these accelerator
  features were absent from the foundations configuration story.
- Kind set to `epic`: four distinct deliverable themes, kept as one epic per the
  author. May be re-sized or split during refinement.
- Deliberately NOT a child of epic 0001 (per the author) — it is future work
  beyond the foundations proof slice; linked via `relates_to` instead of
  `parent`.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0009-multi-level-configuration-system.md`
