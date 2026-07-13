---
type: work-item
id: "0019"
title: "Template Management Subcommands"
date: "2026-07-11T11:19:14+00:00"
author: Toby Clemson
producer: extract-work-items
status: draft
kind: story
priority: medium
parent: "work-item:0011"
tags: [configuration, templates, cli]
last_updated: "2026-07-11T11:19:14+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0019: Template Management Subcommands

**Kind**: Story
**Status**: Draft
**Priority**: Medium
**Author**: Toby Clemson

## Summary

As a Luminosity user, I want to list, show, eject, diff, and reset the plugin's
configurable document templates, so I can inspect the defaults and manage my own
overrides without hand-editing hidden files.

## Context

Fourth theme of epic 0011. In the accelerator these five operations are
`configure`-skill H3 sub-actions backed by `config-*-template.sh` scripts, over a
three-tier resolution. For Luminosity the same capabilities are surfaced through
the expanded `configure` skill (parity of surface) but implemented under the hood
in the Rust CLI (e.g. `luminosity config template <op>`) — "do both".

## Requirements

- **list** — a table of every template key with its resolution source and path.
- **show `<key>`** — print the resolved template content plus its source.
- **eject `<key>` | `--all` `[--force] [--dry-run]`** — copy the plugin default
  into the user templates directory; a target that already exists is an error
  unless `--force`.
- **diff `<key>`** — a unified diff of the plugin default vs the user override.
- **reset `<key>` `[--confirm]`** — delete the user override (dry-run without
  `--confirm`).
- **Three-tier resolution**: `templates.<key>` config value (explicit path) →
  `<paths.templates>/<key>.md` user override → plugin default at
  `<plugin_root>/templates/<key>.md`. Source labels: "config path" /
  "user override" / "plugin default".
- Surfaced via the `configure` skill; engine in the Rust CLI.

## Acceptance Criteria

- [ ] Given a template key with no override, when `show <key>` runs, then it
      resolves the plugin default and labels the source "plugin default".
- [ ] Given a key with no existing override, when `eject <key>` runs, then a user
      template file is created from the default; re-running without `--force`
      reports the target exists and exits non-zero.
- [ ] Given a user override exists, when `diff <key>` runs, then it shows the
      unified diff of default vs override; when `reset <key> --confirm` runs, the
      override is removed.
- [ ] When `list` runs, then every template key is enumerated with its
      resolution source and path.
- [ ] The `configure` skill surfaces all five operations, and the eval suite
      covers them (per epic 0011's cross-cutting requirement).

## Open Questions

- Which template keys does Luminosity define? (The accelerator ships 13.) The
  key set is determined by Luminosity's own template catalogue.

## Dependencies

- Blocked by: 0009 (multi-level config model — done).
- Parent: 0011.

## Assumptions

- Luminosity mirrors the accelerator's three-tier resolution and source labels;
  the CLI is the engine even though the surface is the `configure` skill.

## Technical Notes

- Accelerator reference:
  `scripts/config-{list,show,eject,diff,reset,read}-template.sh` and
  `config_resolve_template` in `config-common.sh`.
- ADR-0021 (template-management subcommands), ADR-0003 (`.luminosity/` layout).

## Drafting Notes

- Extracted from epic 0011's fourth theme. Proposed kind `story`, priority
  `medium` (inherited from the epic).
- The five operation names and the three-tier resolution are source-faithful to
  the accelerator; the Luminosity CLI surfacing (`luminosity config template
  <op>`) is illustrative and settled at planning.

- Extracted from source documents without interactive enrichment.
  Acceptance criteria, dependencies, and kind may need refinement before
  promoting from `draft` to `ready`.

## References

- Source: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
