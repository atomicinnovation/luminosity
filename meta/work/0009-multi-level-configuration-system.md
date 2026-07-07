---
type: work-item
id: "0009"
title: "Multi-Level Configuration System — CLI Command + Thin configure Skill"
date: "2026-06-22T20:03:08+00:00"
author: Toby Clemson
producer: extract-work-items
status: ready
kind: story
priority: high
parent: "work-item:0001"
blocked_by: ["work-item:0007", "work-item:0006"]
blocks: ["work-item:0010", "work-item:0011"]
relates_to: ["work-item:0012", "adr:ADR-0003", "adr:ADR-0009", "adr:ADR-0010"]
tags: [story, configuration, cli, skills, architecture-enforcement]
last_updated: "2026-07-05T15:05:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0009: Multi-Level Configuration System — CLI Command + Thin configure Skill

**Kind**: Story
**Status**: Ready
**Priority**: High
**Author**: Toby Clemson

## Summary

Implement a multi-level configuration system (team and personal precedence)
exposed as a CLI command and driven by a thin `configure` skill, proving the
skills-vs-CLI division of labour end-to-end: the skill orchestrates while the
CLI executes the deterministic configuration logic. In doing so it also stands
up the workspace's first cross-crate hexagon (the `config` / `config-adapters`
split) and first activates the cross-crate dependency-direction enforcement (the
cargo-deny ban-list), so the story carries an architectural-proof dimension
alongside the feature.

## Context

The `configure` skill is the first concrete instance of the skills-vs-CLI
division — a skill driving deterministic configuration logic that lives in the
CLI — so it doubles as the proof-of-architecture for the whole approach. It also
becomes the first eval target — the first skill whose behaviour the
eval-application story (0010) exercises and grades. Configuration scope is
deliberately minimal: enough to prove the multi-level model end-to-end, not a
complete schema for as-yet-unbuilt features. The multi-level model is adapted
from the accelerator plugin's
(https://github.com/atomicinnovation/accelerator — the sibling plugin this repo
ports proven patterns from, typically checked out locally at `../accelerator`)
project-level configuration approach.

## Requirements

- Implement configuration resolution across two levels, mirroring the
  accelerator's scheme: a team level at `.luminosity/config.md` (committed) and a
  personal level at `.luminosity/config.local.md` (project-local, gitignored),
  both carrying YAML frontmatter. Personal precedence wins on conflict.
- The CLI is the reader: it parses the YAML frontmatter natively (no shell YAML
  parsing — this is exactly the deterministic work the CLI owns). The resolution
  logic lives in the hexagonal core and is exposed through a CLI command (e.g.
  `luminosity config get` / `set`). A dotted key denotes a **nested path** in
  the frontmatter: `core.example` maps to `example` nested under `core:`, so the
  CLI walks the nested structure rather than treating the dotted string as a
  single flat key.
- Expose level-aware read and write. `config set <key> <value> [--level
  team|personal]` defaults to the **personal** level (the gitignored
  `.luminosity/config.local.md`), so an accidental `set` never lands in shared
  committed state; `--level team` targets the committed `.luminosity/config.md`.
  `config get <key> [--level team|personal]` defaults to full-stack resolution
  (personal over team) and, when given `--level`, reads that single level without
  resolving across levels.
- Define explicit failure behaviour for the read/write commands so callers (and
  the skill) can distinguish "unset" from "empty": a `get` for a key absent from
  every resolved level exits non-zero rather than succeeding silently, and an
  unrecognised `--level` value on either `get` or `set` exits non-zero with an
  error naming the invalid level and touches no config file. On success, `get`
  prints the resolved value followed by a single trailing newline and exits 0,
  and `set` exits 0 — this fixed output contract keeps the string-equality checks
  in the acceptance criteria unambiguous.
- Realise the config hexagon as the `config` / `config-adapters` crate split
  (ADR-0010): the `config` core holds resolution (domain + application + ports)
  and depends on no serde / toml / filesystem crate; those concerns live in
  `config-adapters`, wired at each sub-binary's composition root. This is the
  workspace's first
  *cross-crate* hexagon — one whose core and adapters live in separate crates, as
  distinct from the existing `version` / `launch` subdomains, which are intra-crate
  modules within the launcher enforced by cargo-pup. So the inward dependency
  direction is enforced *across a crate boundary* here for the first time — by the
  Cargo graph and a cargo-deny `[[bans.deny]]` + `wrappers` entry (the
  direction-enforcing mechanism the toolchain story 0006 prepared `deny.toml` for;
  the file's inert `skip` / `skip-tree` lists are duplicate-version suppression,
  not this).
- Ensure `.luminosity/config.local.md` is gitignored so personal config is never
  committed (mirroring how the accelerator's `init` handles `.local.md`).
- Provide a thin `configure` skill that orchestrates by invoking the CLI command;
  the skill carries no configuration logic of its own.
- Build test-first, with the precedence logic covered by core tests.

## Acceptance Criteria

- [ ] Given `core.example` = `team-value` in `.luminosity/config.md` and
      `personal-value` in `.luminosity/config.local.md` — the key nested as
      `core:` / `example:` in each file's frontmatter — when read via
      `luminosity config get core.example` (no `--level` → full-stack
      resolution), then it prints `personal-value` and exits 0.
- [ ] Given only `.luminosity/config.md` sets `core.example` (personal file
      absent or key not present in it), when read via `luminosity config get
      core.example`, then it returns the team value — proving fall-through, not
      just override.
- [ ] Given both levels set `core.example`, when read via `luminosity config get
      core.example --level team`, then it returns the team value (a level-scoped
      read bypasses resolution); `--level personal` returns the personal value.
- [ ] Given `luminosity config set core.example personal-value` with no `--level`,
      then the value is written to the personal file `.luminosity/config.local.md`
      (set defaults to the personal level); `--level team` writes it to
      `.luminosity/config.md` instead.
- [ ] Given `luminosity config set core.example personal-value --level personal`,
      when the key is subsequently read via `luminosity config get core.example`,
      then full-stack resolution returns `personal-value` (set/get round-trip).
- [ ] Given `core.example` is set in neither level (both files absent, or
      present without the key), when read via `luminosity config get
      core.example`, then the command exits non-zero and prints nothing to
      stdout — the not-found path is explicit, not a silent empty-string success.
- [ ] Given `core.example` is present but set to an empty value in
      `.luminosity/config.md`, when read via `luminosity config get
      core.example`, then it exits 0 and prints an empty string — distinct from
      the exit-non-zero not-found path above, proving the empty-vs-unset
      distinction the requirements call for.
- [ ] Given an unrecognised level, `luminosity config get core.example --level
      bogus` (and likewise `luminosity config set core.example v --level bogus`)
      exits non-zero with an error naming the invalid level, and no config file
      is created or modified.
- [ ] Setting `core.example` via the `configure` skill and then reading it via the
      skill returns the same value as reading it directly with `luminosity config
      get`. The skill emits the CLI's stdout verbatim, so the check is
      mechanical: skill output equals `luminosity config get core.example` stdout
      for the same key (the skill drives the CLI and adds no behaviour of its
      own). Capturing skill output needs an eval harness not built in this story
      (deferred to 0010), so the in-scope mechanical proof is the grep-verifiable
      thin-skill criterion below; full behavioural equivalence is validated by the
      eval-application story (0010).
- [ ] The repository `.gitignore` ignores `.luminosity/config.local.md` and does
      not ignore `.luminosity/config.md`; `git check-ignore` confirms the personal
      file is ignored and the team file is tracked.
- [ ] The two-level precedence resolution is implemented in the `config` core
      crate (not in `config-adapters` or the launcher), and that crate's own unit
      tests cover the personal-over-team override, the team-only fall-through, and
      level-scoped reads.
- [ ] `cargo tree -p config` shows no serde, toml, or filesystem crate in the
      `config` core crate's dependency closure — those appear only under
      `config-adapters`. Adding serde, toml, or a filesystem crate to `config`'s
      manifest causes `cargo deny check` to fail against a cross-crate
      `[[bans.deny]]` entry added to `cli/deny.toml` by this story, one that pins
      each infrastructure crate to a `wrappers = ["config-adapters"]` allow-list so
      it may be reached only *through* `config-adapters` and never directly from
      `config` — mirroring the live `native-tls` / `openssl` `[[bans.deny]]`
      entries already in that file. (The `skip` / `skip-tree` lists scaffolded in
      `deny.toml` are cargo-deny's duplicate-version suppression for the
      `multiple-versions` check, **not** a dependency-direction mechanism, and are
      not what enforces this; see
      `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md`.)
      That `cargo deny check` failure is the authoritative check; a build failure,
      where it also occurs, is a secondary signal.
- [ ] Every config read or write in the `configure` `SKILL.md` body is a call to
      `luminosity config get` / `set`; the skill body contains no YAML parsing,
      precedence resolution, config-path construction, or any other command that
      reads `.luminosity/config*.md` directly (grep-verifiable over the skill
      body).

## Open Questions

- `set` default level: **resolved to personal** during the 2026-07-05 plan review.
  `set` with no `--level` writes the gitignored personal file, so an accidental
  `set` never lands in shared committed state; `--level team` is required to write
  the committed file (matching `git config`'s local-scope default). This reverses
  the earlier team-default author's call.
- The configuration key namespace/schema beyond the single proof value is fixed
  as out of scope by assumption A2 (see Assumptions); nothing else about this
  slice remains unresolved.

## Dependencies

- Blocked by: the scaffold story (0007, the config command lives in the
  workspace).
- Relies on: the toolchain story (0006) for the cargo-deny ban-list that enforces
  the `config` core's clean dependency closure — this is the first crate split
  where that ban-list does real work. (Both this enabling prerequisite and the
  hard blocker 0007 are recorded in frontmatter `blocked_by`, the only
  directional-upstream field; the blocker-vs-relies-on nuance lives here in prose.)
- Blocks: the eval-application story (0010, the `configure` skill is its eval
  target); the configuration-parity epic (0011, builds on this base model).
- Relates to: the per-subdomain enforcement follow-on (0012, which extends the
  cross-crate enforcement this story first makes live).
- Reference input: the sibling accelerator plugin
  (https://github.com/atomicinnovation/accelerator, typically checked out locally
  at `../accelerator`), from which the config model, layout, precedence, and
  gitignore handling are ported — a design/reference coupling, not a build- or
  run-time blocker, so the repo must be reachable to check fidelity to its
  approach.
- Parent: epic 0001.

## Assumptions

- Assumption A2 (from work item 0001): "some degree of configuration" means
  enough to prove the multi-level model end-to-end, not a complete configuration
  schema. The configuration key namespace/schema beyond the single proof value
  is therefore out of scope for this story.
- The multi-level configuration model is recorded as an ADR (decision 3),
  now ADR-0003.

## Technical Notes

- This story is the canonical demonstration of the skills-vs-CLI division
  (decision 1); keep the skill thin and the logic in the CLI/core.
- Format/location mirrors the accelerator's consolidated layout
  (`.luminosity/config.md` + `.luminosity/config.local.md` under a dedicated
  plugin directory, YAML frontmatter), but the reader is the Rust CLI parsing
  YAML natively — not the accelerator's bash-3.2 line-by-line parser. The
  directory location and the model are fixed by ADR-0003.
- Precedence is personal-over-team (last-writer-wins, personal last), matching the
  accelerator's two-tier model.
- Per ADR-0010 the config domain is the `config` crate and its outbound readers
  (serde/toml/fs) are the `config-adapters` crate; "core" in this story means the
  `config` crate. Keeping infrastructure out of `config`'s closure is enforced by
  a cargo-deny `[[bans.deny]]` + `wrappers` entry (toolchain story 0006 prepared
  `deny.toml`; this story adds the entry), and this is the first place that
  cross-crate enforcement is exercised.
- `config` is a *shared crate* split (per ADR-0010: the launcher depends on it for
  the built-in `config` command, and each sub-binary wires its own
  `config-adapters` at its composition root), which is why the hexagon is split
  across crate boundaries rather than realised as intra-crate modules. The existing
  `version` / `launch` subdomains are launcher-local and live as modules within the
  launcher crate, with their inward direction enforced by cargo-pup; `config` is
  the first subdomain promoted to its own crate pair, so the Cargo graph +
  cargo-deny (not cargo-pup) carry the enforcement here.

## Drafting Notes

- Kind set to `story`: a concrete, bounded deliverable (config resolution + CLI
  command + thin skill).
- Scope deliberately minimal per A2 — one resolvable value across two levels, not
  a full schema.
- Config format/location set to mirror the accelerator's consolidated
  `.luminosity/config*.md` directory (.md + YAML frontmatter) for familiarity,
  with the CLI as the native reader; personal level is project-local and
  gitignored, per the author. The directory location was settled by ADR-0003
  (originally drafted as `.claude/luminosity*.md`, then consolidated).
- Fuller accelerator config features (plugin-global body context, per-skill
  `context.md` / `instructions.md`, template-management subcommands) are
  explicitly out of scope here per A2, and captured as a separate future work
  item (0011, "Configuration Feature Parity with Accelerator") rather than
  expanding this proof slice.

- Added 2026-06-27 (from codebase research
  `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`): the
  `config` / `config-adapters` split is the workspace's first multi-crate hexagon,
  so the inward-dependency cargo-deny ban-list enforcement (designed in ADR-0009,
  mechanism in 0006) first becomes live and verifiable here — captured as an
  explicit requirement and acceptance criterion. Later per-subdomain enforcement
  is tracked in work item 0012.

- Added 2026-07-04 (enrichment against the current workspace state): `config set`
  defaults to the **team** level (the committed, shared file) with `--level
  personal` opting into the local override; `config get` defaults to full-stack
  resolution with `--level` for single-level reads. The team-as-default-for-`set`
  was the author's call — flagged so a reviewer can reconsider whether personal is
  the safer default. Also refined during this pass: the "first multi-crate hexagon"
  claim is sharpened to "first *cross-crate* hexagon" now that the workspace
  already carries three members (`launcher`, `kernel`, `verify`) and the launcher
  runs live intra-crate `version` / `launch` subdomains enforced by cargo-pup — the
  config split itself has not started. Toolchain story 0006 is now `done`, so the
  cargo-deny ban-list this story activates already exists (inert `skip` /
  `skip-tree` in `cli/deny.toml`, whose comment names this split). Acceptance
  criteria were rewritten for mechanical verifiability (level behaviour, `git
  check-ignore`, `cargo tree` closure, skill-body inspection) in place of the
  process-only "written test-first" phrasing. `relates_to` gained `adr:ADR-0009`
  (relied on throughout the body) and `work-item:0012` (which already links back
  here).

- Added 2026-07-05 (correction from codebase research
  `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md`):
  the enforcement mechanism was mis-named throughout the earlier drafts. cargo-deny
  `skip` / `skip-tree` only suppress duplicate-version warnings for the
  `multiple-versions` check — they cannot ban a crate from a dependency closure, so
  populating them would not fail the build when serde/toml/fs enters `config`'s
  closure. The 2026-07-04 note above (and the stale "Cross-crate architectural
  ban-lists" comment on the `skip` / `skip-tree` lists in `cli/deny.toml:65-69`)
  are wrong on this point. The mechanism that enforces dependency *direction* is
  `[[bans.deny]]` with a `wrappers` allow-list — exactly what the live `native-tls`
  / `openssl` ban at `cli/deny.toml:60-64` already uses; scoping is required
  because the launcher legitimately depends on serde. The requirement, acceptance
  criterion, and technical note above were corrected accordingly. Related finding:
  the "single-crate bootstrap" framing is stale — the workspace already has three
  members (`launcher`, `kernel`, `verify`) and `cli/pup.ron` already carries two
  live intra-crate layering rules; only the deny `skip` / `skip-tree` lists remain
  inert. Implementation should also fix the misleading `deny.toml` comment when it
  adds the `[[bans.deny]]` entry.

- Updated 2026-07-05 (during the plan review of story 0009, see
  `meta/reviews/plans/2026-07-05-0009-multi-level-configuration-system-review-1.md`):
  two decisions were settled that update this work item. (1) **`set` default level
  reversed to personal** (the gitignored file) from the earlier team default —
  the safer least-surprise default, so an accidental `set` never mutates shared
  committed state; the requirement and acceptance criterion above were updated.
  (2) **Store rooting resolves the project root** by walking upward from the
  current directory to the nearest ancestor holding `.luminosity/` (else the repo
  root, else the current directory), so `get`/`set` work from any subdirectory and
  `set` never scatters a stray nested `.luminosity/` — a plan-level detail, no AC
  change. The plan additionally adopts a typed, order-preserving config value model
  (via `serde-saphyr`) and defers the configuration schema, cross-crate schema
  composition, and comment preservation to work item 0011.

## References

- Source: `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md`
- Related: `meta/work/0011-configuration-feature-parity-with-accelerator.md`
- Toolchain: `meta/work/0006-establish-rust-toolchain-guard-rails-in-mise-and-ci.md`
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
- Reference: accelerator plugin — https://github.com/atomicinnovation/accelerator
  (the multi-level config model, layout, precedence, and gitignore handling are
  ported from it; typically checked out locally at `../accelerator`)
