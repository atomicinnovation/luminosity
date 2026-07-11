---
type: codebase-research
id: "2026-07-11-0016-plugin-global-context-injection"
title: "Research: Plugin-Global Additional Context Injection (story 0016)"
date: "2026-07-11T17:58:14+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0016"
parent: "work-item:0016"
relates_to: ["codebase-research:2026-07-05-0009-multi-level-configuration-system", "codebase-research:2026-07-08-0010-inspect-integration-findings"]
topic: "Plugin-Global Additional Context Injection"
tags: [research, codebase, configuration, context-injection, rust-cli, hexagonal, skills, evals]
revision: "4eec1223408e4705bf1cf528619fde31a1e2dfec"
repository: "luminosity"
last_updated: "2026-07-11T17:58:14+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Plugin-Global Additional Context Injection (story 0016)

**Date**: 2026-07-11T17:58:14+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: 4eec1223408e4705bf1cf528619fde31a1e2dfec
**Branch**: working copy (change not on a pushed bookmark)
**Repository**: luminosity

## Research Question

What does the codebase currently provide, and what must be built, to implement
story 0016 — "Plugin-Global Additional Context Injection"? The story requires a
Rust CLI that reads the Markdown *bodies* of `.luminosity/config.md` (team) and
`.luminosity/config.local.md` (personal), concatenates and trims them, wraps
them under an exact `## Project Context` header, emits nothing when both are
empty, and is injected near the top of **every** skill prompt via the
`!`-preprocessor — plus a `configure`-skill surface and eval coverage.

## Summary

The building blocks are largely present, and the story maps cleanly onto three
existing, well-established patterns. The implementation is best understood as
four coordinated changes:

1. **A new CLI reader.** The frontmatter/body split primitive that story 0016
   needs **already exists and is fully tested** — `frontmatter::split` in
   `cli/config-adapters/src/frontmatter.rs` returns exactly the body below the
   closing `---`, with every edge case the ACs enumerate (no-opening-fence →
   all-body; exactly-two-fences; body-internal `---` preserved; CRLF;
   missing-final-newline) already handled. But it is **crate-private,
   untrimmed, and discarded on the read path** — so the work is *exposing and
   composing* it, not writing a parser. The natural shape is a new subcommand
   (a `context`/`config context` hexagon) that reads both levels' bodies,
   concatenates team-then-personal, trims, and renders the load-bearing block.

2. **Wiring the `!`-preprocessor into skills.** This is where reality diverges
   sharply from the story's framing. **Only one skill exists today**
   (`skills/config/configure/SKILL.md`), `.claude-plugin/plugin.json` registers
   exactly one skill directory (`./skills/config/`), and **no SKILL.md uses the
   `!`-preprocessor at all yet** — it is documented in ADRs/plans but never
   exercised. There is also **no shared-partial mechanism**; each SKILL.md is
   standalone. So "wire into every skill" currently means "wire into the one
   skill, and establish the mechanism + placement anchor that 0017/0018 and all
   future skills inherit."

3. **The `configure` surface.** The `configure` skill is static prose with two
   actions (`get`, `set`); it must gain an action describing how to manage the
   plugin-global project context (naming the team/personal config-file bodies
   as the source).

4. **Eval coverage.** The Inspect-based eval framework (story 0010) grades by
   **re-executing the real `luminosity` binary** as the source of truth. The
   four required scenarios (team-only / personal-only / both / both-empty) fit
   this pattern, but need **new body-bearing fixtures** (every existing fixture
   is frontmatter-only) and a **new scorer that grades the reader's stdout
   directly** — because context injection is passive (rendered at skill load),
   there is no agent-issued `config get` command for the current scorer to
   observe.

A cross-cutting note: the ADR numbers the story cites (**ADR-0017** config
extension points, **ADR-0003** `.luminosity` layout) **do not match this repo's
ADRs** — those numbers are from the sibling *accelerator* repo. The local
equivalents are ADR-0003 (multi-level config model), ADR-0007 (skills as the
product / the `!`-preprocessor), ADR-0009 (thin CLI over hexagonal core), and
ADR-0011 (Inspect harness). This should be corrected in the story's Technical
Notes before planning.

## Detailed Findings

### 1. The Rust workspace and the subcommand pattern

The Cargo workspace is rooted at `cli/` with five members
(`cli/Cargo.toml:5`): `launcher` (the binary + several subcommand hexagons),
`kernel` (shared boundary error), `config` + `config-adapters` (a subcommand
whose domain/adapters were extracted into their own crates), and `verify`.

Each built-in subcommand is a **self-contained hexagon**: a dependency-free
domain `core` (value objects + port traits), an `inbound/` driving adapter
(clap → core, and output rendering), and an `outbound/` driven adapter. There
are **two structural variants** to choose between for the new reader:

- **`version` style** — the whole hexagon lives inside the launcher crate under
  `src/version/{core,inbound,outbound}`; pure, no I/O beyond build-baked env
  vars. Reference: `cli/launcher/src/version/core.rs` (port `BuildMetadata`,
  value object `VersionReport`, service `VersionReporter<M>`), inbound
  `cli/launcher/src/version/inbound/cli.rs` (`render()` + `report()` writing
  stdout via `println!`), outbound
  `cli/launcher/src/version/outbound/build_metadata.rs`.
- **`config` style** — the core + ports live in a standalone crate
  (`cli/config/`), driven adapters in `cli/config-adapters/`, and only the thin
  clap-mapping inbound adapter stays in the launcher
  (`cli/launcher/src/config_command/`). This is the pattern when the subcommand
  does real filesystem I/O.

Because the context reader **reuses config-file discovery and reading**, it
should build on the `config` crate rather than start a new pure hexagon.

**Command registration & dispatch** (clap v4.6 derive, `cli/Cargo.toml:9`):

- Command tree: `Cli` / `enum Command` in
  `cli/launcher/src/launch/inbound/cli.rs:8-28` — add a `Context` variant here
  (bare, or `Context { action }` if nesting under `config`).
- `main()` (`cli/launcher/src/main.rs:143-165`) is the composition root:
  constructs concrete adapters (`main.rs:132-141`) and calls
  `dispatch(...)`. **`is_root_help` (`main.rs:109-120`) hard-codes the built-in
  subcommand names `"version" | "config" | "help"`** — a new top-level name
  must be added there so `context --help` is delegated to clap.
- Dispatch: `cli/launcher/src/launch/mod.rs:25-43` matches on `cli.command`,
  taking one `&impl <Port>` per collaborator; add a `Command::Context => ...`
  arm and thread the new port in from `run()`.

**Conventions to follow** (from the analysis of the whole workspace):

- Shared boundary error `kernel::Error` (single `Failed(String)` variant,
  `cli/kernel/src/lib.rs:9-13`); each subdomain keeps a rich error enum and
  maps in **only at the dispatch boundary** via `impl From<E> for kernel::Error`
  (pattern at `cli/config/src/error.rs:99-103`).
- **Generics-based DI, not `dyn`** — services are generic over their ports
  (`VersionReporter<M>`, `ConfigService<R, W>`); `dispatch` takes `&impl Trait`;
  `const fn new` where possible.
- **No output-port abstraction** — a pure `render(...) -> String` plus a single
  `println!` in the thin entry function; stdout proven by black-box integration
  tests, not a mockable port.
- **cargo-pup inward layering** (`cli/pup.ron`) has one `RestrictImports` block
  per core module — a new core module needs its own block (copy the
  `version_core_imports_only_permitted` block at `pup.ron:6-20`). ADR-0009.
- Register the new top-level module in `cli/launcher/src/lib.rs`.

### 2. The frontmatter/body split already exists (and is the crux)

`cli/config-adapters/src/frontmatter.rs` already produces exactly the body
story 0016 wants:

```rust
pub struct Split { pub frontmatter: String, pub body: String }
pub fn split(content: &str) -> Result<Split, String>   // frontmatter.rs:7-21
```

Behaviour, all tested (`frontmatter.rs`, plus round-trips in `store.rs`):

- Iterates with `split_inclusive('\n')` so newlines are preserved verbatim
  (`frontmatter.rs:22`).
- **First line not a `---` fence → empty frontmatter, entire content is the
  body** (`frontmatter.rs:24-29`) — satisfies the AC "a file whose first line is
  not `---` is treated as all-body."
- **Exactly two fences** delimit frontmatter; once closed, a `---` in the body
  is preserved literally (`frontmatter.rs:34-42`, test `:77-83`) — satisfies
  "uses the first two `---` fences only."
- Fence detection strips optional `\n` then `\r`, so `---`, `---\n`, `---\r\n`,
  and a final unterminated `---` all match; the line must equal `---` exactly
  (`frontmatter.rs:49-55`).
- **Body is returned untrimmed, byte-for-byte** — no normalisation anywhere
  (this is why 0016's "trim leading/trailing blank lines" is new behaviour to
  add on top).
- Unterminated frontmatter (opening `---`, no closing) → `Err` →
  `ConfigError::MalformedFrontmatter` on read (`store.rs:85-90`).

**Two obstacles to reuse:**

1. **Visibility** — `frontmatter` is `mod frontmatter;` (private,
   `cli/config-adapters/src/lib.rs:9`), and only `FileConfigStore` is
   re-exported (`lib.rs:12`). The split is unreachable outside the crate.
2. **The read path discards the body** — `document::parse`
   (`cli/config-adapters/src/document.rs:30-33`) keeps only
   `split.frontmatter`. Today the body is retained **only on the write path**,
   via `preserved_body` (`document.rs:41-56`), purely to round-trip it
   untouched during `config set`. There is **no read path and no domain type**
   that surfaces the body to a caller.

So the CLI reader needs either a new public function in `config-adapters` or a
new **driven port method** (e.g. `ReadConfigBody`, mirroring `ReadConfigLevel`
in `cli/config/src/service.rs:20`) implemented on `FileConfigStore` by reusing
`frontmatter::split`. The hexagon currently has no `Node`-level or port-level
notion of a document body — introducing one is the main domain addition.

### 3. Config-file location, selection, and precedence (reusable)

`FileConfigStore` (`cli/config-adapters/src/store.rs`) already owns everything
the reader needs for *locating and reading* the files:

- Discovery: `FileConfigStore::discover(start_dir)` walks ancestors, rooting at
  the nearest `.luminosity/` dir **or** `.git` marker (dir or file, covering
  worktrees), else `start_dir` (`store.rs:33-37,112-121`).
- Config dir: `<root>/.luminosity` (`store.rs:39-41`).
- Level → filename: `Level::Team => "config.md"`,
  `Level::Personal => "config.local.md"` (`store.rs:43-48`).
- Read: `fs::read_to_string`, `NotFound → Ok(None)` (absent file is not an
  error, `store.rs:75-93`) — directly supports "emits nothing when both bodies
  are empty/absent."
- **Precedence lives in the core, not the store** — `ConfigService::get` reads
  personal then team, personal wins (`cli/config/src/service.rs:83-99`). For
  0016 the composition is different: **both bodies are concatenated
  team-then-personal**, not a personal-overrides-team resolution — so this is a
  new domain operation, not a reuse of `ConfigService::get`.

### 4. The `!`-preprocessor and skill wiring — mostly greenfield

This is the highest-uncertainty area and the biggest divergence from the
story's framing:

- **`.claude-plugin/plugin.json`** registers skills **by directory**, and there
  is exactly one entry: `"skills": [ "./skills/config/" ]`. Plugin version
  `0.3.0-pre.1`.
- **Only one SKILL.md exists**: `skills/config/configure/SKILL.md`. The
  `skills/` tree contains nothing else. The `hooks/`, `agents/`, and
  `templates/` directories described in CLAUDE.md **do not exist yet** in the
  working tree.
- **No SKILL.md uses the `!`-preprocessor.** A repo-wide search for the
  ``!` `` backtick-command syntax found zero matches in `skills/`; it appears
  only in `meta/` design docs. The `configure` skill documents CLI usage via
  ordinary fenced bash blocks (`SKILL.md:36-38, 47-49`), not live injection.
- **No shared-partial / common-header mechanism exists.** Each SKILL.md is
  standalone. Since 0016 must inject the same block into *every* skill and
  0017/0018 build on this anchor, whether to introduce a shared snippet
  mechanism (vs. hand-copying a `!`-preprocessor line into each SKILL.md) is a
  genuine design decision this story effectively opens.
- **Invocation contract**: skills call the CLI by path through a bash bootstrap
  wrapper — `${CLAUDE_PLUGIN_ROOT}/bin/luminosity <args>` (the wrapper at
  `bin/luminosity` verifies + caches + `exec`s the real launcher). The
  canonical future `!`-preprocessor form,
  `` !`${CLAUDE_PLUGIN_ROOT}/bin/luminosity <args>` ``, is written down in the
  0008/0009 plans but not yet used. `allowed-tools` must scope the new command,
  as `configure/SKILL.md:10` does for `config *`.

Design rationale for the mechanism: ADR-0007 (skills as the product) and
ADR-0001 (skills-vs-CLI division of labour — reading lives in the CLI, the
skill only consumes the injected context).

### 5. The `configure` skill surface

`skills/config/configure/SKILL.md` is entirely static prose + fenced examples.
Its sections: intro (CLI owns config files; skill never reads/writes them), the
two-level model (team shared/committed; personal local/git-ignored/overrides),
`## Reading a value` (`get`), `## Writing a value` (`set`), and `## Guidance`.
The two concrete actions are **`get`** and **`set`**, each optionally scoped by
`--level team|personal`. Story 0016's AC requires adding an action that names
the team/personal config-file **bodies** as the source of the plugin-global
project context.

### 6. The eval framework (story 0010) and how to extend it

Built on **Inspect AI** (ADR-0011). Per-skill Inspect `Task`s live under
`tests/evals/skills/<skill>/`. The design bypasses Inspect's model provider
(`MODEL = "mockllm/model"`): a custom **solver** shells out to real `claude -p`
against a staged plugin copy, and a custom **scorer** grades by **re-executing
the real `luminosity` binary** against the seeded workdir — output is the source
of truth, not the agent's self-report.

- Eval case = one JSON object in `dataset.json` with `input` (prompt), `target`,
  and `metadata` (grading contract + `fixture` name). 9 cases today, all
  config get/set.
- Solver `_seed` (`tests/evals/skills/configure/solvers.py:83-89`) makes a
  `.git` dir and copies every file from `fixtures/<name>/.luminosity/` into the
  workdir — **so new body-bearing fixtures need no solver change.**
- Scorer `_grade`/`_exec`
  (`tests/evals/skills/configure/scorer.py:156-211`) re-runs the CLI and
  asserts byte-exact stdout / stderr-marker / exit code.
- **Every existing fixture is frontmatter-only** — none has a body below the
  closing `---`, which is exactly the surface 0016 exercises.
- **Staging copies only `skills/config/`**
  (`tasks/shared/eval/staging.py:18`) — if injection is wired into skills
  outside that tree, staging must be extended.
- CI runs the **eval-logic unit tests** under
  `tests/unit/evals/skills/configure/` (`test:unit:evals`), not the live eval
  (gated behind `LUMINOSITY_EVAL_LIVE`, pass^k floor 0.8).

**The genuine extension**: context injection is *passive* — the block is
rendered at skill load, the agent issues no `config get`. So the current
scorer's `config_command_ran` attribution check does not apply. The new scorer
must re-invoke the **reader** subcommand directly and assert on its stdout:
presence (exact header + prose + body byte-for-byte), absence (empty for
both-empty), team-first ordering with a blank-line separator, and no
leading/trailing blank lines. Add body-bearing fixtures (`context_team_only`,
`context_personal_only`, `context_both`, `context_empty`), dataset cases (bump
the hard-coded count at `test_dataset.py:79`), a new scorer/arms, and mirroring
unit tests under `tests/unit/evals/`.

## Code References

- `cli/config-adapters/src/frontmatter.rs:7-55` — the body-split primitive to
  expose/reuse (`Split`, `split`, `is_fence`); handles all AC edge cases,
  returns body untrimmed.
- `cli/config-adapters/src/document.rs:30-33` — read path that currently
  **discards** the body; `:41-56` — `preserved_body` (write-path body reuse).
- `cli/config-adapters/src/lib.rs:9,12` — `frontmatter` is private; only
  `FileConfigStore` is exported.
- `cli/config-adapters/src/store.rs:33-48,75-93` — discovery, team/personal
  filename selection, absent-file → `Ok(None)`.
- `cli/config/src/service.rs:20-99` — driven ports `ReadConfigLevel` /
  `WriteConfigLevel`, driving port `ConfigAccess`, and personal-over-team
  precedence (not the concatenation 0016 needs).
- `cli/launcher/src/version/{core.rs,inbound/cli.rs,outbound/build_metadata.rs}`
  — the pure hexagon reference (ports, value object, `render()`, single
  `println!`).
- `cli/launcher/src/config_command/inbound/cli.rs` — thin clap-mapping inbound
  adapter for an I/O subcommand.
- `cli/launcher/src/launch/inbound/cli.rs:8-28` — the `Cli` / `Command` tree to
  extend.
- `cli/launcher/src/launch/mod.rs:25-43` — `dispatch`; add a `Command::Context`
  arm.
- `cli/launcher/src/main.rs:109-120,132-141` — `is_root_help` name list to
  update; composition root wiring.
- `cli/pup.ron:6-20` — per-core-module import-restriction block to copy.
- `cli/kernel/src/lib.rs:9-13` — boundary error to map into at dispatch.
- `.claude-plugin/plugin.json` — single registered skill (`./skills/config/`).
- `skills/config/configure/SKILL.md:10,36-49` — `allowed-tools` scope + the
  static get/set actions to extend.
- `bin/luminosity:16,108,146` — the bootstrap wrapper skills invoke by path.
- `tests/evals/skills/configure/{solvers.py:83-89,scorer.py:156-211,dataset.json}`
  — seeding, CLI-re-execution grading, eval cases.
- `tests/evals/skills/configure/fixtures/*/.luminosity/` — frontmatter-only
  fixtures (no bodies yet).
- `tasks/shared/eval/staging.py:18` — copies only `skills/config/`.
- `tests/unit/evals/skills/configure/{test_scorer.py,test_dataset.py}` — the
  CI-run eval-logic tests to mirror.

## Architecture Insights

- **The parser is already written.** The single most valuable discovery is that
  `frontmatter::split` already implements every body-extraction edge case the
  ACs enumerate. The work is *exposing* it (visibility + a read path + a domain
  representation) and *composing* it (concat + trim + wrap), not re-deriving
  frontmatter parsing. TDD here starts against a new port/service, reusing the
  proven split beneath.
- **Two distinct config operations.** Existing config *resolution* is
  personal-overrides-team (a winner). 0016 is *concatenation*
  team-then-personal (a merge). These are different domain operations sharing
  only file location/reading — so 0016 adds a domain service, not a variant of
  `ConfigService::get`.
- **Rendering vs. domain.** Per the established pattern, the trim + concat +
  emptiness decision is domain logic (unit-tested against fakes), while the
  exact `## Project Context` header + wrapper prose belongs in a pure inbound
  `render()` returning `String` (empty string → print nothing). This keeps the
  load-bearing byte-exact block one `render()` function, black-box-tested.
- **"Every skill" is aspirational today.** With one skill and no shared-partial
  mechanism, 0016's real deliverable is the *mechanism and placement anchor*
  (0017/0018 explicitly build on it). The registry-iterating AC ("a test
  iterates plugin.json and asserts each entry") will iterate a one-element set —
  worth deciding whether to introduce a shared injection snippet now so the
  anchor genuinely scales, rather than hand-copying into each future SKILL.md.
- **Passive injection breaks the eval's attribution half.** The scorer's
  two-conjunct model (did-the-agent-run-the-command + is-the-outcome-right)
  collapses to one conjunct here: there is no agent command to attribute. The
  new scorer grades the *reader* output directly. This is a real, if small,
  extension of the story-0010 framework, not a copy.
- **Manual-sync hazards to respect.** A new core module needs a matching
  `pup.ron` block; a new top-level subcommand name must be added to
  `is_root_help`; extending skills beyond `skills/config/` requires touching
  `staging.py`. None are automatically enforced.

## Historical Context

- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — the
  `.luminosity/` team/personal config model 0016 reads from (the story's cited
  "ADR-0003 `.luminosity` layout" maps here).
- `meta/decisions/ADR-0007-skills-as-the-product.md` — SKILL.md + the
  `!`-preprocessor injection mechanism 0016 targets.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — reading lives
  in the CLI; the skill only consumes injected context (the boundary 0016 sits
  across).
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
  — the hexagonal/inward-direction architecture the reader must follow.
- `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md` — the
  eval harness the coverage AC builds on.
- `meta/decisions/ADR-0004-three-toolchain-split.md` — Python is the test
  language for non-Rust surfaces (where the eval-logic tests live).
- `meta/work/0011-configuration-feature-parity-with-accelerator.md` (draft) —
  the parent epic; `0009` (done) — the config model foundation; `0010` (done) —
  the eval framework; `0017`/`0018` (ready) — the siblings 0016 unblocks.
- `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md`
  and `.../2026-07-08-0010-inspect-integration-findings.md` — prior research on
  the config system and the Inspect integration.
- `meta/reviews/work/0016-plugin-global-context-injection-review-1.md` — the
  review that shaped the current story (REVISE, amendments folded in).
- **Discrepancy to correct:** the story's Technical Notes cite accelerator ADR
  numbers (ADR-0017 config extension points; a different ADR-0003) and
  accelerator shell scripts (`config-read-context.sh`, `config-common.sh`) that
  **do not exist in this repo**. Local ADRs stop at 0011. The exact
  `## Project Context` wrapper block quoted in the story remains the
  authoritative load-bearing spec regardless.

## Related Research

- `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md`
- `meta/research/codebase/2026-07-07-0010-apply-eval-framework-to-configure-skill.md`
- `meta/research/codebase/2026-07-08-0010-inspect-integration-findings.md`
- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md`

## Open Questions

1. **Subcommand shape/name.** A new top-level `luminosity context` vs. a
   `luminosity config context` subcommand? The reader reuses config-file
   discovery, which argues for nesting under `config`; a separate top-level verb
   argues for a clean injection contract for skills. (Affects the `Command`
   enum, `is_root_help`, dispatch, and `allowed-tools` scoping.)
2. **Crate placement of the body-read.** Add a public `split`/body function to
   `config-adapters`, or a new driven port (`ReadConfigBody`) on the `config`
   core implemented by `FileConfigStore`? The port route keeps the hexagon
   honest and testable with fakes but is more scaffolding.
3. **Where the wrapper prose lives.** Confirm the header + fixed two-line prose
   belong in a pure inbound `render()` (recommended) vs. the domain — this
   decides where the byte-exact AC is tested.
4. **Shared injection snippet vs. per-skill copy.** With one skill today and
   0017/0018 building on this anchor, should 0016 introduce a shared
   `!`-preprocessor snippet/partial so "every skill" scales, or hand-place the
   line in each SKILL.md? No such mechanism exists yet.
5. **Does "every skill" mean literally the one registered skill for now?** The
   registry-iterating AC will assert a one-element set. Confirm that satisfying
   it for `configure` (plus establishing the anchor) is the intended first
   slice.
6. **Eval scope of passive injection.** Should the eval assert only that the
   reader CLI emits the correct block (robust, deterministic), or also that the
   agent's *behaviour* visibly reflects the injected context (closer to the
   real value, but noisier)? The existing framework strongly favours the
   former (re-execute the CLI as source of truth).
7. **Trimming precedents.** No body trimming exists anywhere today; confirm the
   exact normalisation (strip leading/trailing blank lines of the *combined*
   body; single blank line as the team/personal separator) and where it lives
   (domain service).
