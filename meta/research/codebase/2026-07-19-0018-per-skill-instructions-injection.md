---
type: codebase-research
id: "2026-07-19-0018-per-skill-instructions-injection"
title: "Research: Per-Skill Instructions Injection (story 0018)"
date: "2026-07-19T22:25:43+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0018"
parent: "work-item:0018"
relates_to: ["codebase-research:2026-07-13-0017-per-skill-context-injection", "codebase-research:2026-07-11-0016-plugin-global-context-injection"]
topic: "Per-Skill Instructions Injection"
tags: [research, codebase, configuration, context-injection, rust-cli, evals]
revision: "f022cd0cd6fa803351a61398ed752e32eed4cf9d"
repository: "luminosity"
last_updated: "2026-07-20T00:00:00+00:00"
last_updated_by: "Toby Clemson"
last_updated_note: "Recorded the Fragment rename, phase-0 sequencing, and Option A path-selection decisions"
schema_version: 1
---

# Research: Per-Skill Instructions Injection (story 0018)

**Date**: 2026-07-19T22:25:43+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: f022cd0cd6fa803351a61398ed752e32eed4cf9d
**Branch**: HEAD (detached; jj-colocated)
**Repository**: luminosity

## Research Question

How should story 0018 (per-skill instructions injection) be implemented, given
the codebase as it stands? The story appends a combined, two-level
(`instructions.md` team + `instructions.local.md` personal), frontmatter-stripped
per-skill instructions block under a `## Additional Instructions` header at the
**end** of every skill's prompt. Stories 0016 (plugin-global `## Project Context`)
and 0017 (per-skill `## Skill-Specific Context`) are already implemented and are
the direct template. What exactly is reusable, what must be new, and where does
every touchpoint live?

## Summary

**0018 is a near-exact structural clone of 0017**, differing in three ways: (1)
the on-disk base filename is `instructions` instead of `context`; (2) the emitted
block header/prose is `## Additional Instructions` (three hard-wrapped prose
lines, skill name on line 2); and (3) the block is injected at the **end** of the
SKILL.md body via a **separate** `!`-preprocessor line, rather than composed into
the same `context` invocation that emits the early context blocks.

The entire two-level assembly core in the `cli/config` crate is reusable
**as-is**: `combine` / `trim_blank_lines` (trim each level, drop empties, join
team-then-personal with one blank line), `ContextAssembler`, `Assembly` /
`AssembledContext` / `LevelContribution`, the `ReadContextBody` / `AssembleContext`
ports, and the `SkillName` value object. The `config-adapters` crate's
frontmatter-strip primitive (`read_context_body`, mapping-only strip) and its path
composition are reusable, with `context_path` being the one function that
hard-codes the `context` base name and therefore must be extended.

The **cleanest design** — flagged by two analyser agents and consistent with the
current source-agnostic core — is to generalise the on-disk document base name
rather than duplicate the machinery. Two viable shapes exist (see Architecture
Insights): a new document-kind discriminator threaded through `ContextSource` /
`context_path`, or a parallel path method plus a new inbound render adapter. Either
way, the byte-exact block renderer is new (mirroring `render_skill`), and a new
end-of-body `!`-preprocessor invocation must be wired into every registered
`SKILL.md` and enforced by the existing Python registry-iteration test.

Testing spans two tiers already established by 0016/0017: the **Rust byte-exact
tier** (`cli/config/src/context.rs`, `cli/config-adapters/src/store.rs`,
`cli/launcher/src/context_command/inbound/cli.rs`, `cli/launcher/tests/context.rs`)
and the **Python eval + wiring tier** (`tests/evals/skills/configure/`,
`tests/unit/skills/test_context_injection.py`). Both must gain instructions
analogues, plus a third `.gitignore` ignore+negation pair for
`instructions.local.md`.

## Detailed Findings

### 1. The reusable assembly core (`cli/config/`)

The domain core is serde-free and **source-agnostic** — it assembles any
`ContextSource`, so instructions get the two-level combination logic for free.

- **Combination rule** — `combine` at
  [`cli/config/src/context.rs:153-164`](cli/config/src/context.rs). Trims each
  level with `trim_blank_lines`, drops empty/whitespace-only levels via
  `.filter(|part| !part.is_empty())`, joins survivors with `"\n\n"` in fixed
  `[team, personal]` order, returns `None` when nothing survives. This *is* the
  story's required rule verbatim.
- **Trim rule** — `trim_blank_lines` at
  [`cli/config/src/context.rs:166-180`](cli/config/src/context.rs). Strips
  leading/trailing whitespace-only lines and the trailing line terminator while
  preserving interior blank lines, indentation, and CRLF interiors.
- **Domain types** — `AssembledContext { body }`, `Assembly { context:
  Option<AssembledContext>, levels: [LevelContribution; 2] }`, `LevelBody`,
  `SourceLocation` at
  [`cli/config/src/context.rs:18-57`](cli/config/src/context.rs). `context ==
  None` is the "emit nothing" signal.
- **Ports** — driven `ReadContextBody` and driving `AssembleContext` at
  [`cli/config/src/context.rs:60-104`](cli/config/src/context.rs); service
  `ContextAssembler<R>` at
  [`cli/config/src/context.rs:107-141`](cli/config/src/context.rs) (reads team
  then personal, combines, records per-level contributions).
- **Value objects** — `SkillName` (allow-list validated: non-empty, ASCII
  alphanumeric / `-` / `_`; rejects `.`, `..`, separators, NUL) and
  `ContextSource` (`Project | Skill(SkillName)`) at
  [`cli/config/src/source.rs:17-59`](cli/config/src/source.rs). `Level`
  (`Team`/`Personal`) with `qualifier()` returning `""` / `".local"` at
  [`cli/config/src/level.rs:17-22`](cli/config/src/level.rs).

The `#[cfg(test)] mod tests` at
[`cli/config/src/context.rs:182-520`](cli/config/src/context.rs) already covers
every combination case the story lists (both absent, both empty, whitespace-only,
team-only, personal-only, team-then-personal join, surrounding-blank trim,
interior-blank preservation, CRLF, no-trailing-terminator) using a `FakeReader` —
a direct template for instructions unit tests.

### 2. Path composition + frontmatter strip (`cli/config-adapters/`)

- **The one function that hard-codes `context`** — `context_path` at
  [`cli/config-adapters/src/store.rs:67-76`](cli/config-adapters/src/store.rs):

  ```rust
  fn context_path(&self, source: &ContextSource, level: Level) -> PathBuf {
      match source {
          ContextSource::Project => self.config_path(level),
          ContextSource::Skill(name) => self
              .config_dir()
              .join("skills")
              .join(name.as_str())
              .join(format!("context{}.md", level.qualifier())),
      }
  }
  ```

  For 0018 the skill arm must yield `instructions{qualifier}.md`, i.e.
  `.luminosity/skills/<skill>/instructions.md` and `instructions.local.md`. This
  is the sole path-level change.
- **Frontmatter strip primitive** — `read_context_body` at
  [`cli/config-adapters/src/store.rs:89-106`](cli/config-adapters/src/store.rs):
  strips a leading `---` fence **only when it parses as a YAML mapping**;
  non-mapping fences (prose thematic breaks, sequences) round-trip byte-for-byte;
  an *unterminated* fence fails loud (`ConfigError::MalformedFrontmatter`). Shared
  with the config reader. Reusable verbatim for instructions.
- Supporting: `frontmatter::split` at
  [`cli/config-adapters/src/frontmatter.rs:21-55`](cli/config-adapters/src/frontmatter.rs)
  (first-two-fence splitter, CRLF-aware); `document::parse_frontmatter` at
  [`cli/config-adapters/src/document.rs:53-60`](cli/config-adapters/src/document.rs);
  containment guard `refuse_escaping_path` at
  [`cli/config-adapters/src/store.rs:115-130`](cli/config-adapters/src/store.rs);
  root discovery `discover_root` at
  [`cli/config-adapters/src/store.rs:250-259`](cli/config-adapters/src/store.rs).
- Adapter tests to mirror live at
  [`cli/config-adapters/src/store.rs:278-973`](cli/config-adapters/src/store.rs)
  (frontmatter-strip, empty-fence, thematic-break preservation, CRLF, malformed,
  symlink containment, and the path-mapping assertion
  `the_skill_context_path_nests_under_skills` at `store.rs:888-898`).

### 3. Byte-exact block rendering (`cli/launcher/src/context_command/inbound/cli.rs`)

This inbound adapter **owns the byte contract** — it is the primary file 0018
mirrors for the new block.

- Skill prose with name interpolation — `skill_prose` at
  [`cli/launcher/src/context_command/inbound/cli.rs:80-86`](cli/launcher/src/context_command/inbound/cli.rs)
  (two hard-wrapped lines, `{skill}` on line 1).
- Renderers `render_project` / `render_skill` at
  [`cli/launcher/src/context_command/inbound/cli.rs:88-97`](cli/launcher/src/context_command/inbound/cli.rs):
  `format!("## Skill-Specific Context\n\n{prose}\n\n{}", context.body)` — header,
  blank line, prose, blank line, trimmed body, ending at the last body byte (the
  single trailing newline is added by `println!` at `cli.rs:150`).
- **0018's new renderer** produces header `## Additional Instructions` and the
  story's **three-line** prose (skill name on line 2), byte contract at
  [`meta/work/0018-per-skill-instructions-injection.md:207-226`](meta/work/0018-per-skill-instructions-injection.md).
  The prose's hard line breaks are fixed regardless of skill-name length — the
  literal `format!` string encodes them, exactly as `skill_prose` does today. Its
  byte-exact test mirrors `renders_the_byte_exact_skill_block` at
  [`cli/launcher/src/context_command/inbound/cli.rs:419-432`](cli/launcher/src/context_command/inbound/cli.rs).
- Empty-output policy: `block` at `cli.rs:237-250` maps over
  `assembly.context.as_ref()` (None → no block); `join_blocks` at `cli.rs:116-128`
  returns `None` when all sections are None; `run` at `cli.rs:139-159` only
  `println!`s inside `if let Some(output)`. Instructions inherit this for free by
  reusing `Assembly`.
- Fail-safe (`OnFailure::Degrade` vs `Fail`) and `--explain` machinery at
  `cli.rs:37-56, 166-337` — reuse the same pattern so a broken config can't blank
  the whole prompt.

### 4. Subcommand dispatch — the four coordinated sites

There is one `context` subcommand today. Whether 0018 adds a flag to it or a new
subcommand, these sites move together:

- Clap `Command` enum, `Context { skill, explain, fail_safe }` variant at
  [`cli/launcher/src/launch/inbound/cli.rs:15-45`](cli/launcher/src/launch/inbound/cli.rs).
  Note `skill: Option<String>` is deliberately **unvalidated** by clap so
  validation happens inside the fail-safe boundary.
- Dispatch match at
  [`cli/launcher/src/launch/mod.rs:40-55`](cli/launcher/src/launch/mod.rs) (maps
  `fail_safe` → `OnFailure`).
- Builtin-name list at
  [`cli/launcher/src/main.rs:146`](cli/launcher/src/main.rs):
  `Some("version" | "config" | "context" | "help")` — a new subcommand name must
  be added here or the external-subcommand fallthrough will catch it.
- The exhaustive-match test in `cli.rs` (`~:114-117`).

Wiring in `main.rs`: `ContextAssembler::new(LazyContextBody)` at
[`cli/launcher/src/main.rs:163`](cli/launcher/src/main.rs);
`discover_store` at `main.rs:108-114`.

### 5. SKILL.md wiring and the end-of-body placement

- Only **one** skill is registered today — `plugin.json` lists `"./skills/config/"`
  ([`.claude-plugin/plugin.json:10-12`](.claude-plugin/plugin.json)), resolving to
  [`skills/config/configure/SKILL.md`](skills/config/configure/SKILL.md).
- The existing context injection is a **single line under the H1** at
  [`skills/config/configure/SKILL.md:16`](skills/config/configure/SKILL.md):
  `` !`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill=configure --fail-safe` ``.
  That one invocation emits *both* the `## Project Context` and
  `## Skill-Specific Context` blocks in project-then-skill order (composed
  in-process by `join_blocks`), and they land **above** the skill's own prose.
- **0018 needs a new, separate `!`-preprocessor line at the very end of the body**
  (after the skill's own instructions, after the context blocks). The existing
  top-of-body line cannot produce an end-of-body block, so the "context early /
  instructions last" ordering is realised by *two* invocation lines in SKILL.md,
  not by a single Rust join. The tool grant at
  [`skills/config/configure/SKILL.md:11`](skills/config/configure/SKILL.md)
  (`Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)`) already covers a
  `context`-prefixed command; a new subcommand name would need its own grant.
- The three load-bearing parts of the invocation (`--skill=<name>` equals-form,
  `--fail-safe`, `${CLAUDE_PLUGIN_ROOT}`) are documented and enforced — see
  [`tests/unit/skills/test_context_injection.py:28-43`](tests/unit/skills/test_context_injection.py).

### 6. The Python registry-iteration wiring test

[`tests/unit/skills/test_context_injection.py`](tests/unit/skills/test_context_injection.py)
reads `.claude-plugin/plugin.json`'s `skills` array (`_registered_skill_dirs`
`:58-60`), `rglob`s `SKILL.md` under each (`_discover_skill_files` `:63-70`), and
parametrizes `TestEverySkillIsWired` (`:106-158`) over every skill:
- `test_carries_the_exact_injection_line` (`:110-112`) against `INJECTION_TEMPLATE`
  (`:40-43`).
- `test_line_sits_under_the_h1_before_any_subsection` (`:126-152`) — positional.
- `test_allowed_tools_grants_the_context_command` (`:154-158`).
- `TestConfigureSurface` (`:161-188`) asserts the `configure` SKILL.md names both
  `context.md` and `context.local.md` — the template for 0018's configure-surface
  AC.
- `TestGitignore` (`:191-212`) shells out to `git check-ignore` to pin the
  ignore+negation pairs.

For 0018 this suite gains: a second per-skill injection-line assertion (the
instructions line, independent of fixtures — story AC at
[`meta/work/0018-...md:145-150`](meta/work/0018-per-skill-instructions-injection.md)),
an **inverse** positional test (instructions line at end-of-body, after any
subsection), a configure-surface assertion for both instructions paths, and a
third `TestGitignore` pair.

### 7. `.gitignore` ignore + eval-fixture-negation pairs

[`.gitignore:12-25`](.gitignore) carries two pairs today; 0018 adds a third:

```
**/.luminosity/skills/**/context.local.md
!tests/evals/skills/configure/fixtures/**/context.local.md
```
→ mirror as:
```
**/.luminosity/skills/**/instructions.local.md
!tests/evals/skills/configure/fixtures/**/instructions.local.md
```
The broad ignore keeps personal files out of VCS; the negation lets the eval
fixtures commit a personal file to exercise the team-then-personal path. Team
`instructions.md` stays tracked (no rule). Story Technical Notes flag this at
[`meta/work/0018-...md:242-244`](meta/work/0018-per-skill-instructions-injection.md).

### 8. The eval tier (story 0010, Inspect AI, Python)

- **Two eval sub-tiers**: the free CI unit tier `tests/unit/evals/**` (run via
  `mise run test:unit:evals` → `uv run pytest tests/unit/evals`) tests the eval
  *logic*; the billed live tier `tests/evals/skills/configure/` (run via
  `mise run eval:skills:configure`, gated by `LUMINOSITY_EVAL_LIVE`) spawns
  `claude -p` and grades whether a block reached the model.
- The context eval asserts **behaviour, not bytes**: `grade_behaviour` at
  [`tests/evals/skills/configure/context_scorer.py:19-31`](tests/evals/skills/configure/context_scorer.py)
  checks that *every* sentinel term appears (case-insensitively) in the assistant
  transcript. Byte-level rendering is explicitly deferred to the Rust tier
  (`context_eval.py:33-37`), so the dataset carries no golden rows.
- Task definition — `configure_context_with_skill` at
  [`tests/evals/skills/configure/context_eval.py:31-46`](tests/evals/skills/configure/context_eval.py);
  live solver `run_configure_agent` at
  [`tests/evals/skills/configure/solvers.py:139-159`](tests/evals/skills/configure/solvers.py)
  (seeds a fixture's `.luminosity` into a `.git`-rooted temp dir, spawns
  `claude -p ... --plugin-dir`).
- Fixtures under `tests/evals/skills/configure/fixtures/<name>/.luminosity/...`;
  the two-level witness is
  `context_skill_both_levels/.luminosity/skills/configure/{context.md,
  context.local.md}`.
- Dataset hygiene tests at
  [`tests/unit/evals/skills/configure/test_context_dataset.py`](tests/unit/evals/skills/configure/test_context_dataset.py)
  assert declared source files exist and sentinels actually appear in fixture
  bodies (mirroring the frontmatter strip).

For 0018: add `instructions_eval.py`, `instructions_scorer.py`,
`instructions_dataset.json`, `instructions_*` fixtures (including a both-levels
and a mixed-empty-level fixture), plus `tests/unit/evals/**` analogues. The
`test:unit:evals` leaf auto-discovers new unit files; the billed arm is wired
into the `configure` task if a live arm is wanted.

## Code References

- `cli/config/src/context.rs:153-180` — `combine` + `trim_blank_lines`: the exact
  two-level combination rule (reusable as-is).
- `cli/config/src/context.rs:18-141` — domain types, ports, `ContextAssembler`
  service (source-agnostic; reusable).
- `cli/config/src/source.rs:17-59` — `SkillName` validation + `ContextSource`
  enum.
- `cli/config-adapters/src/store.rs:67-76` — `context_path`: **the one function
  hard-coding the `context` base name**; extend for `instructions`.
- `cli/config-adapters/src/store.rs:89-106` — `read_context_body`: mapping-only
  frontmatter strip (reusable).
- `cli/launcher/src/context_command/inbound/cli.rs:80-159` — byte-exact block
  rendering, name interpolation, join/ordering, empty-output policy (mirror for
  the `## Additional Instructions` renderer).
- `cli/launcher/src/launch/inbound/cli.rs:15-45` — clap `Command` tree.
- `cli/launcher/src/launch/mod.rs:40-55` — dispatch match.
- `cli/launcher/src/main.rs:146,163` — builtin-name list + assembler wiring.
- `cli/launcher/tests/context.rs:15-21,267-563` — black-box binary byte-contract
  tests (mirror for instructions).
- `skills/config/configure/SKILL.md:11,16` — tool grant + context injection line
  (add an end-of-body instructions line + grant).
- `.claude-plugin/plugin.json:10-12` — skill registry (the universal-wiring
  enumeration source).
- `tests/unit/skills/test_context_injection.py:40-212` — registry-iteration
  wiring test, configure-surface test, `.gitignore` pair test.
- `.gitignore:12-25` — ignore + eval-fixture-negation pairs (add the third).
- `tests/evals/skills/configure/context_eval.py`,
  `context_scorer.py`, `context_dataset.json`, `solvers.py`, `fixtures/` — eval
  tier to mirror.

## Architecture Insights

- **Rename the shared kernel to the `Fragment` vocabulary (decided).** The
  `cli/config` kernel is reused verbatim for instructions, so its `*Context*`
  names would understate what they model once a second, semantically distinct
  consumer (instructions is a directive to *follow*, context is information to
  *consider*) flows through them. Context and instructions are different domain
  concepts sharing one *mechanism*; the mechanism is named for the neutral thing
  it produces — a **prompt fragment** (a two-level-combined, frontmatter-stripped
  piece of userspace-authored content bound for a skill's prompt). The
  `context`/`instructions` vocabulary stays at the *edges* (launcher renderers,
  `## …` headers and prose, the `context.md` / `instructions.md` base names, the
  subcommands, and the new `instructions_command` module) — that is where the
  distinction is real. `Fragment` was chosen over the alternative `Injection`
  (the project's ubiquitous word for the feature) to keep `cli/config` — the
  infra-free domain crate — named for the *material* rather than the delivery
  *act*, and to compose with the crate's existing neutral names (`LevelBody`,
  `Assembly`, `SourceLocation`). Kernel rename map (launcher `context_command`
  and its renderers stay context-named):
  - `AssembledContext { body }` → `Fragment { body }` (or `AssembledFragment`;
    a micro-choice for implementation — `Fragment` is preferred as the bare
    assembled type)
  - `ContextSource` → `FragmentSource`; `ContextAssembler<R>` →
    `FragmentAssembler`
  - `AssembleContext` (port) → `AssembleFragment`; `ReadContextBody` (port) →
    `ReadFragmentBody`
  - `read_context_body` → `read_fragment_body`; `context_path` →
    `fragment_path`
  - module `cli/config/src/context.rs` → `fragment.rs`; the `Assembly.context`
    field → `Assembly.fragment`
  - Establish "prompt fragment" once in the module doc rather than baking
    `Prompt` into every symbol.
  The rename is a pure mechanical refactor (no behaviour change; tests stay
  green). Sequencing relative to 0018 is still open (see Open Questions).
- **The core is source-agnostic; only the on-disk name and the emitted header
  differ.** 0018 is not new machinery — it is a second document kind flowing
  through the same assembly. The design decision is *how* to select the
  `instructions` base name:
  - **Option A — generalise `ContextSource` / `context_path`.** Thread a document
    kind (context vs instructions) so `context_path` picks the base name. Smallest
    domain surface, keeps one assembly path, but touches the `ContextSource` enum
    and its call sites.
  - **Option B — parallel path method + new inbound adapter.** Add an
    `instructions_path` alongside `context_path` and a sibling
    `instructions_command` inbound module. More duplication but keeps `context`
    untouched; clearer separation if instructions later diverge.
  Given the strict-DDD house style and the fact that the block header/prose and
  end-of-body placement genuinely differ, a **new inbound render path** is
  warranted regardless; the open choice is whether the *path selection* is a new
  enum arm/kind (A) or a parallel method (B). Recommend confirming this in the
  plan.
- **Placement is a SKILL.md concern, not a Rust concern.** Unlike context (one
  invocation composes both blocks via `join_blocks`), the "context early /
  instructions last" ordering is produced by two separate `!`-preprocessor lines
  in the SKILL.md — one under the H1, one at the end. The Rust tier can only
  assert the instructions block's own bytes; the *relative* ordering is asserted
  by the Python positional test and/or the behavioural eval. This matches the
  story's AC scoping (relative position only; between-block whitespace owned by
  0016's shared mechanism).
- **Two test tiers with a deliberate division of labour.** Byte-exactness lives in
  Rust; "did it reach the model" lives in the Python eval. The eval dataset
  deliberately carries no golden bytes to avoid duplicating the Rust contract.
- **Four coordinated dispatch sites** (enum, dispatch match, builtin-name list,
  match-test) move together for any new subcommand — a known gotcha to note in the
  plan.
- **Fail-safe is load-bearing.** The `!` preprocessor discards the whole prompt on
  any non-zero exit, so `--fail-safe` (degrade to a stdout notice, exit 0) must be
  on the instructions invocation too.

## Historical Context

- `meta/decisions/ADR-0012-two-level-per-skill-context-with-frontmatter-stripped.md`
  — the governing decision for the two-level + frontmatter-strip model that 0018
  extends from context to instructions.
- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — the
  team/personal level model and `.luminosity/` layout.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md` —
  the hexagonal structure the CLI follows.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — what runs in a
  SKILL.md vs the Rust CLI.
- `meta/plans/2026-07-13-0017-per-skill-context-injection.md` — the **primary
  implementation template** for 0018.
- `meta/plans/2026-07-11-0016-plugin-global-context-injection.md` — the plan that
  established the shared injection mechanism.
- `meta/research/codebase/2026-07-13-0017-per-skill-context-injection.md` and
  `.../2026-07-11-0016-plugin-global-context-injection.md` — prior locator/analyser
  research directly reusable.
- `meta/plans/2026-07-07-0010-apply-eval-framework-to-configure-skill.md` and
  `meta/research/codebase/2026-07-08-0010-inspect-integration-findings.md` — the
  eval-framework template.
- `meta/validations/2026-07-13-0017-per-skill-context-injection-validation.md` —
  the validation template.

## Related Research

- `meta/research/codebase/2026-07-13-0017-per-skill-context-injection.md` — the
  immediate predecessor's research (nearest template).
- `meta/research/codebase/2026-07-11-0016-plugin-global-context-injection.md` —
  the shared-mechanism story's research.
- `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md` —
  the config-reading foundation.
- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md` —
  the CLI's hexagonal scaffold.

## Open Questions

- **Kernel-rename sequencing (decided).** The `Fragment` rename (see
  Architecture Insights) lands as **phase 0 of the 0018 plan** — a pure
  mechanical, behaviour-neutral refactor (tests stay green) that precedes all of
  0018's new instructions behaviour, so the later phases build the instructions
  consumer on the already-neutral kernel.
- **Path-selection shape (decided — Option A, arm-bearing form).** The document
  kind is folded into `FragmentSource` as explicit, kind-bearing arms rather than
  threaded as an orthogonal `(source, kind)` pair, keeping the kernel
  kind-agnostic and making illegal states unrepresentable (there is no
  project-global instructions):

  ```rust
  enum FragmentSource {
      ProjectContext,               // config.md
      SkillContext(SkillName),      // skills/<s>/context.md
      SkillInstructions(SkillName), // skills/<s>/instructions.md
  }
  ```

  `fragment_path` matches each arm to its base name; there stays one port, one
  `FragmentAssembler`, and one path function. `combine` / `trim_blank_lines` never
  branch on kind. The launcher's context command requests
  `ProjectContext` / `SkillContext`; the new instructions command requests
  `SkillInstructions`; each command owns its own header/prose. Sequencing: phase 0
  is a pure rename that keeps the two `Project | Skill` arms (no kind qualifier
  while only context exists); the kind-bearing arms (`Skill` → `SkillContext`,
  plus the new `SkillInstructions` arm) are introduced in the instructions phase,
  which re-touches the `Skill` call sites once more — each step small and
  test-covered. Option B (a parallel `instructions_path` + sibling read method)
  was rejected as it duplicates the path/read plumbing and tempts a second
  assembly path.
- **New subcommand vs a flag on `context`.** A sibling `instructions` subcommand
  (its own name in the builtin list + tool grant) reads cleanly and keeps the
  end-of-body invocation self-describing; a `--instructions` flag on `context`
  reuses the existing grant but overloads one command with two headers/placements.
  Recommend a sibling subcommand for clarity; confirm in the plan.
- **`ConfigError` wording.** `Display` messages say "config file" even for skill
  context files (`error.rs:87-93`). Instructions inherit this quirk; whether to
  generalise the wording is a minor cleanup decision, out of this story's stated
  scope.
- **Live eval arm.** Whether to add a billed live instructions arm to the
  `configure` eval task or rely on the free unit tier + Rust byte tests. The story
  requires eval coverage; the exact billed/free split follows 0017's precedent.
