---
type: pr-description
id: "25"
title: "[0017] Add per-skill context injection"
date: "2026-07-18T13:07:56+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "0017"
parent: "work-item:0017"
relates_to: ["work-item:0016", "work-item:0018"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/25"
pr_number: 25
tags: [configuration, context-injection, rust-cli, skills, evals]
revision: "53426a9a33f57006923bfb4c0a4a2ffde499dcb3"
repository: "luminosity"
last_updated: "2026-07-18T13:07:56+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---
# [0017] Add per-skill context injection

## Summary

Teaches the Rust CLI to read **two-level per-skill context** — `.luminosity/skills/<skill>/context.md` (shared, committed) and `context.local.md` (personal, git-ignored) — combine them team-then-personal, and render them as a `## Skill-Specific Context` block directly beneath the `## Project Context` block story 0016 already emits. A user drops context in a file and it steers that one skill's prompt, without repeating it each invocation. Both blocks are produced by a single command, `luminosity context --skill=<name> --fail-safe`, which is what makes the ordering and absent-global behaviours structurally true rather than a convention two SKILL.md lines could drift out of.

## Changes

**Domain generalisation (`cli/config/`, `cli/config-adapters/`).** Story 0016's project-only context assembler is generalised into a single two-level-document domain keyed on a `ContextSource` (`Project` or `Skill(SkillName)`), rather than mirrored per document kind. The ports become `(source, level)`-keyed, `ProjectContext` becomes the document-neutral `AssembledContext`, and `Level` drops its hard-coded `config.md` for a precedence-independent qualifier so the whole `(source, level) → filename` rule lives in the adapter. This turns the successor story (0018, per-skill *instructions*) into "add a variant, a path arm, and a renderer" rather than a third parallel machine.

**CLI surface (`cli/launcher/`).** `luminosity context --skill=<name>` renders the project block then the skill block. The order is a property of a pure `join_blocks(project, skill)` signature, not a push-order a later edit could swap. The two sources degrade **independently** under `--fail-safe`: an unreadable skill file leaves the healthy project block standing under a notice that names the skill file, never the misleading project one. `--explain` reports the discovered root once, then a root-relative line per level for each source.

**Skill wiring (`skills/config/configure/SKILL.md`).** The injection line is `context --skill=configure --fail-safe` (equals form, deliberately). The registry-walking contract test now derives the expected `--skill` argument from each SKILL.md's own frontmatter `name:` and pins it to the Rust `SkillName` allow-list and the skill's directory name. The personal file gets the git-ignore pair `config.local.md` already has.

**Eval coverage (`tests/evals/`, `tests/unit/evals/`).** The existing `context` eval capability grows five fixtures and dataset rows; the scorer re-executes the exact argv the skill injects. The golden-pinning chain is extended and its two gaps closed: a CI render test now runs the compiled binary against every fixture and byte-compares stdout (so a mis-pathed fixture fails in free CI, not only in a billed run), and the committed live log is pinned to the behavioural dataset. A committed live eval log provides the durable proof that injection reaches the model.

**Decision record (`meta/decisions/ADR-0012`).** Records the two deliberate divergences from the Accelerator — a two-level personal `context.local.md`, and frontmatter stripping — plus the scope of the containment and mapping-strip rules across every `.luminosity` document.

## Security and trust boundary

Per-skill context is **untrusted committed content** spliced near the top of a skill prompt — a cross-user / supply-chain prompt-injection channel, carried forward from 0016's trust model (it is treated as data, not a capability). Three things enforce that boundary:

- **The skill's binding constraints sit *below* the injection point**, so a hostile body cannot shadow them by forging `##` headings. The contract test pins this placement structurally.
- **`SkillName` validates with an allow-list** (ASCII alphanumeric, `-`, `_`), which rejects `/`, `\`, `..`, Unicode lookalikes, and NUL by construction — closing the name side of path traversal.
- **Symlink containment on every read and write.** A symlinked file or directory component whose canonical target escapes `.luminosity/` is refused, never followed — and, crucially, a symlinked `config.md` can no longer be read through *or clobbered* by a write, so one file has one safety contract whatever port reaches it.

The single load-bearing safety property: an invalid `--skill` name or a malformed context file under `--fail-safe` must exit **0** and keep the project block. The `!` preprocessor discards the *entire prompt* on any non-zero exit, so skill-name validation happens inside `run()` — never in a clap `value_parser`, whose rejection would exit before the fail-safe boundary is reached.

## Context

- Work item: `meta/work/0017-per-skill-context-injection.md`
- Plan: `meta/plans/2026-07-13-0017-per-skill-context-injection.md`
- Validation: `meta/validations/2026-07-13-0017-per-skill-context-injection-validation.md`
- Decision: `meta/decisions/ADR-0012-two-level-per-skill-context-with-frontmatter-stripped.md`
- Builds directly on story 0016 (plugin-global context injection); sets up story 0018 (per-skill instructions).

## Testing

- [x] Full local CI mirror green end-to-end: `mise run` (format, lint, types across all three toolchains; `deny:check` / `pup:check`; the whole test suite with coverage; the host-native release build).
- [x] Rust domain + adapter unit tests: level combination, blank-line trimming, mapping-only frontmatter strip, skill-name validation, path construction, symlink refusal (file, directory component, sibling-prefix, symlinked root), and error propagation.
- [x] Rust black-box suite against the compiled binary: every level and ordering permutation, the empty-output policy, and the independent fail-safe boundary at each source.
- [x] Python skill-wiring tests: the injection line exists, in the right place, with a representable name, in every registered skill (registry-walk with a vacuity guard); personal file git-ignored, team file tracked.
- [x] Python eval-logic tests: goldens pinned to the Rust literals; compiled binary's stdout byte-matches the goldens for every fixture; committed live log covers the current dataset.
- [x] Live billed eval (`mise run eval:skills:configure`): both behavioural arms at pass^k 1.000 (6/6). The `context_global_and_skill` transcript is the headline evidence — the agent applies **Lantern** (project body only) and **Tier** (skill body only), proving both blocks reached the model in order through the real preprocessor.
- [x] Edge cases exercised against the real binary: invalid `--skill` under `--fail-safe` exits 0; symlink escape refused; thematic-break body injected whole; both-absent emits nothing; `--explain --fail-safe` degrades to a diagnostic line rather than exiting non-zero.

## Notes for Reviewers

**This PR includes its own validation and remediation.** The last four commits are the fixes from validating the plan, each driven from a failing test first:

1. **Symlink containment was extended to the config read/write path.** Validation found the guard was context-only, which meant `config set --level team` over a symlinked `config.md` would have renamed over the symlink, clobbering its target. Now refused.
2. **`--explain` was brought inside the fail-safe boundary.** It was the one error path in `run` that could still exit non-zero (only reachable via an unreadable working directory, and never on the injected path — but a policy hole nonetheless).
3. **The behavioural eval fixtures were corrected** — their prompts read a `core.example` key the fixtures did not define. A new CI test now fails free on prompt/fixture drift.
4. **Docs** (ADR-0012, the configure surface) record the broadened scope.

Two things worth a reviewer's eye:

- **A deliberate, documented behaviour change to project context.** Routing `config.md`'s body through the mapping-only strip means a `config.md` whose frontmatter is valid YAML but *not* a mapping (a sequence) is now injected whole, fences included, where 0016 injected only the body. This is intended — one strip rule for every injected body beats one safe rule and one silently-truncating one — and such a file is already broken *as config*. It is recorded in ADR-0012; the plan's Migration Notes wrongly called project-context behaviour untouched.
- **The committed live-eval logs predate the fixture correction.** They remain representative (the injected blocks are byte-identical, and the CI render test pins them against the real binary), so a re-run is optional rather than required — but it would remove the one caveat on the evidence.

**Naming tension left for follow-up:** the crate is still `config` and errors still surface as `ConfigError`, though the domain has generalised beyond configuration to all two-level `.luminosity` documents. Renaming is deferred to story 0018 to decide.
