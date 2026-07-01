---
type: note
id: "2026-07-01-support-cli-switches-alongside-env-toggles"
title: "Additionally support CLI switches alongside the env-var task toggles"
date: "2026-07-01T22:59:15+00:00"
author: "Toby Clemson"
producer: create-note
status: captured
topic: "CLI switches for task toggles (coverage, pup mode)"
tags: [mise, invoke, ergonomics, tasks, dx]
revision: "3cf55941e2f5d92ac4032ab62836c4aa8b795534"
repository: "luminosity"
last_updated: "2026-07-01T22:59:15+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Additionally support CLI switches alongside the env-var task toggles

Today the cross-cutting task toggles are env-var only: `LUMINOSITY_COVERAGE=off`
(gates `coverage_enabled()`) and `LUMINOSITY_PUP_MODE=warn` (gates `pup_mode()`),
both in `tasks/shared/rust.py` and read at call time.

Env vars were chosen because they propagate through mise's `depends` roll-ups
(mise does **not** forward task flags down the dependency chain) and need zero
plumbing across the mise → invoke → cargo layers. The cost is discoverability:
a switch would show up in help and can't be exported-and-forgotten, whereas an
env var is invisible until you know it exists.

**Idea:** additionally support switches (e.g. `--no-coverage`) as a *front-end*
that maps onto the same `coverage_enabled()` / `pup_mode()` call-time reads —
keeping the env var as the propagation mechanism through roll-ups, not replacing
it. Sketch:

- Give the leaf invoke tasks an optional param (e.g. `run(context, coverage=None)`)
  where an explicit switch wins over the env var, and the env var remains the
  default.
- A switch on an aggregate (`test`, `test:unit`, the bare `mise run` default)
  can't reach the leaves via `depends`, so the ergonomic path is likely a thin
  wrapper that sets the env var from the switch before delegating — i.e. the
  switch is sugar that lowers to the env var. That keeps a single source of
  truth (the call-time read) and avoids re-plumbing every roll-up.

Worth doing only if the discoverability/DX win justifies the added surface;
otherwise the env vars stay sufficient. Relates to `tasks/shared/rust.py` and
the toolchain wiring from work item 0006.
