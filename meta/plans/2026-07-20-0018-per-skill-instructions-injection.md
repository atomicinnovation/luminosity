---
type: plan
id: "2026-07-20-0018-per-skill-instructions-injection"
title: "Per-Skill Instructions Injection Implementation Plan"
date: "2026-07-19T23:29:16+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0018"
parent: "work-item:0018"
derived_from: ["codebase-research:2026-07-19-0018-per-skill-instructions-injection"]
tags: [configuration, instructions-injection, rust-cli, skills, evals]
revision: "bfd8df6e8202836fce1fb09206df1672d64cffc3"
repository: "luminosity"
last_updated: "2026-07-20T08:09:21+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Per-Skill Instructions Injection Implementation Plan

## Overview

Teach the Rust CLI to read two-level per-skill *instructions* —
`.luminosity/skills/<skill>/instructions.md` (team) and
`.luminosity/skills/<skill>/instructions.local.md` (personal) — combine them
team-then-personal, strip their frontmatter, and render them as a
`## Additional Instructions` block at the **end** of a skill's prompt, after the
skill's own instructions and after the `## Project Context` / `## Skill-Specific
Context` blocks stories 0016/0017 already emit above.

Story 0017 already built the two-level, frontmatter-stripped, source-agnostic
assembly kernel and proved it against a second document kind. 0018 is a **third
document kind flowing through the same kernel**, with three differences:

1. the on-disk base name is `instructions`, not `context`;
2. the emitted block header/prose is `## Additional Instructions` (three
   hard-wrapped prose lines, skill name on line 2); and
3. the block is injected at the **end** of the SKILL.md body via a **separate**
   `!`-preprocessor line and a **sibling `instructions` subcommand**, so
   "context early / instructions last" is realised by two invocation lines in
   the SKILL.md, not by one Rust join.

The plan opens with a **behaviour-neutral kernel rename** (Phase 0) that renames
the `config` crate's context-assembly vocabulary to the neutral **`Fragment`**
vocabulary the research settled on, so the later phases build the instructions
consumer on an already-neutral kernel rather than threading a third consumer
through symbols still named for the first.

## Current State Analysis

Story 0017 left the machine 0018 needs almost entirely in place. The remaining
work is one document kind on an existing kernel, one new render path, and one new
SKILL.md line — not a new subsystem.

**What already exists and is reused as-is:**

- **The two-level combination rule.** `combine` /
  `trim_blank_lines` ([`cli/config/src/context.rs:153-180`](cli/config/src/context.rs))
  trim each level, drop the empty ones, join survivors team-then-personal with
  one blank line; empty → `None` → nothing printed. This *is* the story's
  required rule, including the mixed-empty (drop-empty join) case.
- **The source-agnostic assembler.** `ContextAssembler` and the
  `AssembleContext` / `ReadContextBody` ports
  ([`cli/config/src/context.rs:60-141`](cli/config/src/context.rs)) assemble any
  `ContextSource`; a third source gets the combination logic for free.
- **The validated `SkillName` and `ContextSource` enum**
  ([`cli/config/src/source.rs:14-59`](cli/config/src/source.rs)) — allow-list
  validated (ASCII alphanumeric / `-` / `_`), rejecting `.`, `..`, separators,
  Unicode lookalikes, and NUL by construction.
- **The mapping-only frontmatter strip and symlink containment.**
  `read_context_body` and `refuse_escaping_path`
  ([`cli/config-adapters/src/store.rs:89-130`](cli/config-adapters/src/store.rs))
  are keyed on a `Path`, so an `instructions.md` at a new path inherits both the
  frontmatter-strip and the containment contract with no new code.
- **The byte-exact render / empty-output / independent-degrade / `--explain`
  machinery** in the launcher's inbound adapter
  ([`cli/launcher/src/context_command/inbound/cli.rs`](cli/launcher/src/context_command/inbound/cli.rs))
  — the template the new `## Additional Instructions` renderer mirrors.
- **The registry-walking contract test**
  ([`tests/unit/skills/test_context_injection.py`](tests/unit/skills/test_context_injection.py))
  walks `plugin.json`'s `skills` array and `rglob`s `SKILL.md` beneath each, with
  a vacuity guard. It auto-enrols any future skill; the instructions wiring test
  reuses the same discovery helpers.
- **The eval framework** (story 0010): `capabilities(skill)` globs
  `*_eval.py` ([`tasks/shared/eval/run.py:73-84`](tasks/shared/eval/run.py)), the
  behavioural scorer grades sentinel presence in the transcript, the dataset
  hygiene tests pin prose against a hand-maintained transcription
  (`test_dataset.py`'s `_DOMAIN_TEMPLATES`) rather than scraping the Rust source,
  and `solvers.py::_seed` already `copytree`s nested `.luminosity/skills/`
  fixtures (fixed in 0017). The byte-exact golden/render tier 0018 needs is **not**
  among the reused parts — it is net-new (built in Phase 4).

**What is missing or in the way:**

- **Every context-assembly symbol is named `*Context*`.** With a second,
  semantically distinct consumer (instructions is a directive to *follow*,
  context is information to *consider*) flowing through the kernel, the names
  understate what they model. Phase 0 renames them to the neutral `Fragment`
  vocabulary.
- **`context_path` hard-codes the `context` base name**
  ([`cli/config-adapters/src/store.rs:67-76`](cli/config-adapters/src/store.rs)).
  It is the sole path-level change: the skill-instructions arm must yield
  `instructions{qualifier}.md`.
- **There is no instructions subcommand, renderer, or SKILL.md line.** The
  end-of-body block is a new inbound render path plus a new
  `!`-preprocessor invocation.
- **`capabilities("configure") == ["context", "values"]` is pinned by three
  exact-list tripwires.** A new `instructions_eval.py` adds a third capability,
  so — unlike 0017, which deliberately kept those lists frozen — the tripwires
  must grow to `["context", "instructions", "values"]`.
- **`.gitignore` has two ignore+negation pairs.** The personal
  `instructions.local.md` needs the third.

### Key Discoveries

- **The kernel is already source-agnostic; 0018 adds a variant, not a machine.**
  `assemble`, `combine`, and `trim_blank_lines` never branch on which document
  they assemble. The document kind is selected entirely by the `ContextSource`
  variant the caller passes and the path arm the adapter maps it to.
- **The `!` preprocessor's all-or-nothing failure mode governs this story too.**
  A non-zero exit from an injected command discards the *entire prompt*, so the
  instructions invocation carries `--fail-safe`, the `--skill=<name>` equals
  form, and validates the skill name **inside** the fail-safe boundary (never a
  clap `value_parser`, which exits before the boundary). This is the same
  discipline 0017 established and the wiring test enforces.
- **Placement is a SKILL.md concern, not a Rust concern.** Context composes both
  its blocks in one Rust `join_blocks`; instructions land at the *end* of the
  body, which no top-of-body invocation can produce. So "context early /
  instructions last" is realised by **two** `!`-lines in the SKILL.md — the
  Rust tier asserts only the instructions block's own bytes; the *relative*
  ordering is asserted by the Python positional test and the behavioural eval.
  This matches the story's AC scoping (relative position only; between-block
  whitespace owned by 0016's shared mechanism).
- **A sibling subcommand keeps the end-of-body line self-describing** (author
  decision, confirmed during planning). `luminosity instructions --skill=<name>
  --fail-safe` reads cleanly, needs its own `instructions*` grant and a new entry
  in `main.rs`'s builtin-name list, and keeps `context` untouched — rather than a
  `--instructions` flag overloading `context` with two headers and two
  placements.
- **`ConfigError`'s `Display` says "config file" even for skill files**
  ([`cli/config/src/error.rs:87-93`](cli/config/src/error.rs)). Instructions
  inherit this quirk; generalising the wording is out of this story's scope
  (noted in What We're NOT Doing).

## Desired End State

A user writes `.luminosity/skills/configure/instructions.md` (shared) or
`.luminosity/skills/configure/instructions.local.md` (personal, git-ignored),
and that content appears at the **end** of the `configure` skill's prompt as a
`## Additional Instructions` block, after the skill's own prose and after any
context blocks. When both an instructions file and a context file exist, the
context blocks land near the top and the instructions block lands last.

Verified by: `luminosity instructions --skill=configure` printing the block;
`cli/launcher/tests/instructions.rs` black-box tests covering every level and
degrade permutation and the empty-output policy; the registry-walking contract
test asserting every registered skill carries the end-of-body instructions line
(independent of fixtures); a CI pytest that runs the compiled binary against each
fixture and byte-compares stdout against goldens; and a live eval run in which
the real `claude -p` agent, driven through the real skill, demonstrably receives
the instructions block after the context block.

## What We're NOT Doing

- **Not renaming the `config` crate or the `ConfigError` taxonomy.** Phase 0
  renames only the context-assembly *types and ports* within the crate to the
  `Fragment` vocabulary. The crate stays `config` and errors stay `ConfigError`,
  as 0017 explicitly left them. This deliberately widens the name/contents gap
  (the crate's dominant export is now fragment assembly), so it is booked as a
  concrete follow-up: a dedicated story to rename the crate and the error taxonomy
  together once the vocabulary has settled. Phase 0's `fragment.rs` `//!` doc
  signposts the residual split (the kernel is named for the fragment it produces;
  its errors still surface as `ConfigError`).
- **Not generalising `ConfigError`'s "config file" wording** for skill files.
  Out of the story's stated scope; the notice still names the exact path, which
  is what makes it diagnosable.
- **Not raising a new ADR.** ADR-0012 already governs the two-level +
  frontmatter-stripped per-skill model that 0018 extends from context to
  instructions; the `Fragment` rename is a mechanical generalisation of the
  already-decided source-agnostic core, not a new architectural direction. The
  vocabulary decision is recorded in the research and this plan. (If the author
  considers the kernel vocabulary itself ADR-worthy, a short successor ADR can be
  raised independently — it does not gate this story.)
- **Not project-global instructions.** There is no `## Additional Instructions`
  analogue at the project level. Instructions are always skill-scoped, which is
  why the kind-bearing enum makes `SkillInstructions` the only instructions arm —
  illegal states (project-global instructions) are unrepresentable.
- **Not changing any context behaviour.** The `context` subcommand, its two
  blocks, and their ordering are unchanged; the existing black-box and eval
  suites pin that and must stay green through every phase.
- **Not adding a personal-level scaffolder.** The user creates the nested
  directory and file by hand, as with context; `--explain` prints the exact
  paths read.
- **Not treating `instructions.md` as an untrusted-input boundary.** Like
  `context.md` and the SKILL.md body itself, an instructions file is a
  repo-committed, code-review-gated surface authored by the team or the user — not
  external attacker input. Its frontmatter-stripped body is spliced verbatim after
  the launcher's own header and prose with no fence, which is a deliberate choice:
  the eval requires instructions to read as natural directives, and fencing would
  fight that. The trust boundary is the commit review, not the renderer; the
  softened "in addition to" framing (Phase 3 §2) keeps a skill author's own
  guidance from being silently overridden by a userspace file.

## Implementation Approach

**Rename first, then add a variant.** The kernel is reused verbatim, so its
`*Context*` names are renamed once, up front, to the neutral **prompt fragment**
vocabulary — the material the mechanism produces, regardless of whether it is
consumed as context or as instructions. The `context` / `instructions`
distinction then lives only at the *edges* where it is real: the launcher
renderers, the `## …` headers and prose, the `context.md` / `instructions.md`
base names, and the two subcommands.

The path-selection shape is **Option A, arm-bearing** (research decision): the
document kind is folded into the source enum as explicit, kind-bearing arms
rather than threaded as an orthogonal `(source, kind)` pair, so the kernel stays
kind-agnostic and illegal states are unrepresentable:

```rust
enum FragmentSource {
    ProjectContext,
    SkillContext(SkillName),
    SkillInstructions(SkillName),
}
```

`fragment_path` matches each arm to its base name; there stays **one** port, one
`FragmentAssembler`, and one path function. `combine` / `trim_blank_lines` never
branch on kind. The launcher's context command requests
`ProjectContext` / `SkillContext`; the new instructions command requests
`SkillInstructions`; each command owns its own header and prose.

The sequencing keeps every step small and test-covered:

- **Phase 0** renames the kernel vocabulary while keeping the two existing
  `Project | Skill` arms (no kind qualifier yet — only context exists). Pure
  rename, zero behaviour change, all tests green.
- **Phase 1** introduces the kind-bearing arms (`Project` → `ProjectContext`,
  `Skill` → `SkillContext`, plus the new `SkillInstructions`) and the adapter
  path arm. This re-touches the `Skill` call sites once more, each change small.
- **Phases 2–5** add the render path, the SKILL.md wiring, and the eval
  coverage, mirroring 0017's Phases 2–5.

### Phase mergeability

Every phase is a complete, green, independently mergeable increment: each ends
with `mise run check` and (for the Rust phases) `mise run test:unit:cli` green,
and `mise run` (the full local CI mirror) green. Phases 0–1 change no
user-visible surface; Phase 2 ships a working `instructions` subcommand; Phase 3
wires it into the skill; Phase 4 adds CI-tier eval coverage (the new capability's
committed-log assertion is marked `xfail(strict=True)`, so Phase 4 merges fully
green and the assertion flips to enforcing the instant Phase 5's live log lands —
no phase leaves a required check red); Phase 5 commits the billed log; Phase 6 is
the final full-mirror gate.

---

## Phase 0: Fragment kernel rename

### Overview

A pure, behaviour-neutral rename of the `config` crate's context-assembly
vocabulary to the neutral `Fragment` vocabulary, plus the launcher and adapter
import sites. No arms change, no behaviour changes, and every existing test stays
green — the rename is complete only when the suite is green without any test
*logic* change (only symbol renames in test bodies).

### Changes Required

#### 1. The kernel module and its symbols

**File**: `cli/config/src/context.rs` → `cli/config/src/fragment.rs`
**Changes**: Rename the module file and its public vocabulary. Establish the term
"prompt fragment" once in the `//!` module doc (a two-level-combined,
frontmatter-stripped piece of userspace-authored content bound for a skill's
prompt) rather than baking `Prompt` into every symbol.

| Before | After |
|---|---|
| `AssembledContext { body }` | `Fragment { body }` |
| `ContextSource` | `FragmentSource` |
| `ContextAssembler<R>` | `FragmentAssembler<R>` |
| `AssembleContext` (port) | `AssembleFragment` |
| `ReadContextBody` (port) | `ReadFragmentBody` |
| `Assembly.context` (field) | `Assembly.fragment` |

`Assembly`, `LevelBody`, `LevelContribution`, and `SourceLocation` keep their
names (already neutral). The `FragmentSource` arms stay `Project | Skill` in this
phase — the kind qualifier arrives in Phase 1.

**File**: `cli/config/src/source.rs`
**Changes**: `ContextSource` → `FragmentSource`; update the module `//!` doc to
speak of "which document a fragment is assembled from". Arms unchanged.

**File**: `cli/config/src/lib.rs`
**Changes**: `pub mod context;` → `pub mod fragment;`; update the re-export list,
the crate `//!` doc's "context block" phrasing to "prompt fragment", and the
crate doc's `[`ContextSource`]` intra-doc link to `[`FragmentSource`]` so no
stale (rustdoc-broken) intra-doc reference survives the rename.

#### 2. The adapter import + primitive names

**File**: `cli/config-adapters/src/store.rs`
**Changes**: `read_context_body` → `read_fragment_body`; `context_path` →
`fragment_path`; update the `use config::{…}` import and the module `//!` doc
(which references `ContextSource`). Behaviour unchanged.

#### 3. The launcher import sites

**File**: `cli/launcher/src/context_command/inbound/cli.rs`,
`cli/launcher/src/launch/mod.rs`, `cli/launcher/src/main.rs`
**Changes**: Update the `use config::{…}` imports and type references
(`AssembleContext` → `AssembleFragment`, `AssembledContext` → `Fragment`,
`ContextSource` → `FragmentSource`, `ContextAssembler` → `FragmentAssembler`,
`ReadContextBody` → `ReadFragmentBody`, `LazyContextBody` → `LazyFragmentBody`,
`assembly.context` → `assembly.fragment`). **The `context_command` module,
its renderers (`render_project` / `render_skill`), and the `## Project Context`
/ `## Skill-Specific Context` headers and prose stay context-named** — the
distinction is real at that edge. So the edge reads intentionally rather than
half-renamed, this is a firm decision rather than a taste call: the
`context_command` *locals and parameters* stay uniformly `context`-named (the
`dispatch` parameter stays `context: &impl AssembleFragment`), and the module
`//!` doc gains one sentence naming the relationship — the kernel produces a
*fragment*; this edge wraps it as a *context* block — so a reader meeting
`assembly.fragment` inside a context renderer reads it as deliberate.

### Tests (rename only — no logic change)

Every `#[cfg(test)]` module in the renamed files updates symbol references only
(`ContextSource::Project` → `FragmentSource::Project`, `AssembledContext { body }`
→ `Fragment { body }`, `path_of` helper's `ContextSource` match, etc.). No
assertion changes; a diff that alters any test's expected value in this phase is
a mistake.

### Success Criteria

#### Automated Verification

- [x] Rust format and lint pass: `mise run cli:check`
- [x] Workspace unit tests and the black-box suite pass unchanged:
      `mise run test:unit:cli`
- [x] `mise run deny:check` passes (no serde/YAML crate entered the `config`
      core's closure through the rename)
- [x] The full local CI mirror is green: `mise run`

#### Manual Verification

- [x] The diff is a pure rename: no expected-value change in any test, no
      behaviour change, no new arm.
- [x] `cli/config/src/fragment.rs`'s `//!` doc establishes "prompt fragment" as
      the neutral term; the launcher's `context_command` renderers and `## …`
      headers remain context-named.

---

## Phase 1: The instructions domain kind

### Overview

Introduce the kind-bearing `FragmentSource` arms and the adapter's
`instructions` path arm, so the kernel can assemble a skill's instructions from
`.luminosity/skills/<name>/instructions.md` and `instructions.local.md`. No
user-visible surface changes; the CLI does not yet expose an `instructions`
command.

### Changes Required

#### 1. The kind-bearing source arms

**File**: `cli/config/src/source.rs`
**Changes**: Rename `Project` → `ProjectContext`, `Skill(SkillName)` →
`SkillContext(SkillName)`, and add `SkillInstructions(SkillName)`.

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FragmentSource {
    ProjectContext,
    SkillContext(SkillName),
    SkillInstructions(SkillName),
}
```

The module `//!` doc gains one sentence: instructions are always skill-scoped, so
there is no project-instructions arm — illegal states are unrepresentable. The
assembler and `combine` / `trim_blank_lines` are unchanged: they never branch on
the arm.

#### 2. The adapter path arm

**File**: `cli/config-adapters/src/store.rs`
**Changes**: `fragment_path` gains the instructions arm; the two existing arms
are renamed.

```rust
fn fragment_path(&self, source: &FragmentSource, level: Level) -> PathBuf {
    match source {
        FragmentSource::ProjectContext => self.config_path(level),
        FragmentSource::SkillContext(name) => self
            .skill_dir(name)
            .join(format!("context{}.md", level.qualifier())),
        FragmentSource::SkillInstructions(name) => self
            .skill_dir(name)
            .join(format!("instructions{}.md", level.qualifier())),
    }
}
```

Extract the shared `skill_dir(name) -> config_dir().join("skills").join(name)`
helper so the two skill arms compose the same nested directory (single source of
the `skills/<name>/` rule). The frontmatter strip (`read_fragment_body`) and the
symlink containment (`refuse_escaping_path`) are path-keyed and already applied
by `read_body` / `locate`, so the instructions arm inherits both with no new
code.

#### 3. Update the call sites

**Files**: `cli/launcher/src/context_command/inbound/cli.rs`,
`cli/launcher/src/launch/mod.rs`, `cli/launcher/src/main.rs`, and the kernel's
own `#[cfg(test)]` helpers.
**Changes**: `FragmentSource::Project` → `ProjectContext`, `FragmentSource::Skill`
→ `SkillContext` at every match/construction site. No behaviour change to the
context command.

The context command constructs only `ProjectContext` / `SkillContext`
([`cli.rs:209,232`](cli/launcher/src/context_command/inbound/cli.rs)), but its two
render matches (`block` at `cli.rs:240-247`) become non-exhaustive once
`FragmentSource` grows the third arm. **Prefer the structurally-exhaustive
resolution**: have the context command pick its renderer from a command-local
two-variant view (project vs skill), constructed where it already builds its
source, so its render match never sees `SkillInstructions` at all — the illegal
state is unrepresentable *at that edge*, which both honours the plan's own framing
and respects the workspace's panic-free convention (clippy warns on `panic` /
`todo` / `unimplemented`; `cli/` has zero panicking macros today). Fall back to an
explicit `FragmentSource::SkillInstructions(_) => unreachable!(…)` arm (never a
`_ =>` catch-all, its panic message stating the invariant) **only** if the
narrowing proves disproportionate — and in that case add `clippy::unreachable` to
the workspace opt-in lints with a justified single `#[allow]`, so the codebase's
first panicking macro is a deliberate, enforced exception rather than one that
slips past CI. No regression test is warranted either way; the exhaustive-match
test in `launch/inbound/cli.rs` already guards that command routing is total.

### Tests (write first)

**`cli/config/src/source.rs`** — the existing `SkillName` tests are unchanged;
add none for the enum (it is a plain data carrier).

**`cli/config/src/fragment.rs`** — the `FakeReader::path_of` helper's match adds
the `SkillInstructions` arm (`.luminosity/skills/<name>/instructions`); add:

- `assembles_a_skill_instructions_source_identically_to_a_skill_context_source`
  (parametrised proof the combination rule is kind-agnostic)
- `reports_the_instructions_paths_for_a_skill_instructions_source`

The combine / trim cases stay as direct tests of `combine` / `trim_blank_lines`
(they exercise the shared rule; they need not be duplicated per source).

**`cli/config-adapters/src/store.rs`** — mirror the skill-context adapter tests
for instructions, reusing the `seed_skill` / `skill_body` helpers against
`instructions.md`:

- `an_absent_skill_instructions_reads_as_none`
- `a_team_skill_instructions_reads_its_body`
- `a_personal_skill_instructions_reads_its_body`
- `a_skill_instructions_body_strips_its_frontmatter_mapping`
- `a_skill_instructions_without_frontmatter_returns_the_whole_content`
- `a_skill_instructions_opening_with_a_thematic_break_is_preserved`
- `a_malformed_skill_instructions_fails_loud_naming_the_path`
- `a_symlinked_skill_instructions_file_pointing_outside_is_refused`
- `the_skill_instructions_path_nests_under_skills` (asserting
  `.luminosity/skills/<name>/instructions.md` and `instructions.local.md`)
- `read_body_reports_the_instructions_path_it_read`

The symlinked-directory and sibling-prefix containment cases already cover the
`skills/<name>/` directory component for *both* skill arms (the directory is
shared), so they need not be duplicated per base name — one instructions
symlinked-*file* test plus the existing directory-component tests suffice.

### Success Criteria

#### Automated Verification

- [x] Rust format and lint pass: `mise run cli:check`
- [x] Workspace unit tests pass: `mise run test:unit:cli`
- [x] The new adapter tests pass in isolation:
      `cd cli && cargo nextest run -p config-adapters -E 'test(instructions)'`
- [x] `mise run deny:check` passes
- [x] The full local CI mirror is green: `mise run`

#### Manual Verification

- [x] `cli/config/` still has no filesystem or serde dependency — the
      instructions arm is a value-object variant; the path rule and strip live in
      `config-adapters`.
- [x] The context command's behaviour is unchanged (its black-box suite is green
      without edits beyond the arm rename).

---

## Phase 2: The `instructions` subcommand

### Overview

Expose `luminosity instructions --skill=<name>`, rendering the byte-exact
`## Additional Instructions` block, omitted when empty, degrading under
`--fail-safe`. Shippable on its own: `luminosity instructions --skill=configure`
works from a terminal before any skill injects it.

### Changes Required

#### 1. The new inbound render module

**Files**: `cli/launcher/src/instructions_command/mod.rs` (new),
`cli/launcher/src/instructions_command/inbound/mod.rs` (new),
`cli/launcher/src/instructions_command/inbound/cli.rs` (new); register
`pub mod instructions_command;` in `cli/launcher/src/lib.rs`.
**Changes**: A single-source render command that **reuses** — rather than
re-implements — the fail-safe boundary. This is the most correctness-sensitive
code in the feature (a non-zero exit discards the whole prompt), so it must have
**one** implementation, not two byte-identical copies that can drift. Factor the
shared machinery into a new neutral submodule `cli/launcher/src/command_support/`
(shared inbound scaffolding, **not** a subcommand — the `_command` suffix stays
reserved for `context_command` / `instructions_command`, and the name avoids
colliding with the `config` crate's `fragment` kernel). It holds the **whole**
fail-safe boundary: the `OnFailure` enum, the assemble-then-degrade wrapper and its
`Outcome`, `degraded_state`, the `--explain` line-grammar helpers, **and — the
load-bearing slice — the raw-`--skill`-name parse *inside* the boundary plus the
`Unresolved` / invalid-skill-name-line handling** (today `resolve_skill` +
`invalid_skill_line` in `context_command`). That path is precisely the one where a
non-zero exit is most dangerous (`--skill=../../etc --fail-safe` must exit 0), so it
must route through one implementation, not two. `context_command` is refactored to
consume this scaffold; `instructions_command` composes the same scaffold and owns
only what genuinely differs: its renderer, its `## Additional Instructions`
header/prose, and its single-source section composition (no join, no project
block). To keep each diff trivially reviewable, land the extraction +
`context_command` refactor as its own behaviour-neutral increment (context suite
green and unchanged) **before** adding the instructions consumer on top. Each new
module root (`mod.rs`, `inbound/mod.rs`) and `inbound/cli.rs` carries a `//!` doc,
matching the `context_command` tree.

The renderer reproduces the story's exact block. The three prose lines carry
**fixed hard line breaks** encoded by the `format!` literal, with the skill name
interpolated into line 2 via an inline `{skill}` capture — so a longer or shorter
name shifts no break, and the literal stays a single scrapable string for the
golden-pinning test:

```rust
fn instructions_prose(skill: &SkillName) -> String {
    format!(
        "\
The following additional instructions have been provided for the
{skill} skill. Follow these instructions in addition to all
instructions above."
    )
}

#[must_use]
pub fn render_instructions(skill: &SkillName, fragment: &Fragment) -> String {
    let prose = instructions_prose(skill);
    format!("## Additional Instructions\n\n{prose}\n\n{}", fragment.body)
}
```

For skill `configure` and combined body `team\n\npersonal`, the block is exactly:

```
## Additional Instructions

The following additional instructions have been provided for the
configure skill. Follow these instructions in addition to all
instructions above.

team

personal
```

ending at the last body byte (the single trailing newline is added by `println!`,
matching `context_command`).

The unavailable notice mirrors `render_skill_unavailable` — the error names the
file, so it needs no skill-name parameter; the header is a `const` to stay within
80 columns:

```rust
const INSTRUCTIONS_UNAVAILABLE_HEADER: &str =
    "## Additional Instructions Unavailable";

#[must_use]
pub fn render_instructions_unavailable(error: &ConfigError) -> String {
    format!(
        "{INSTRUCTIONS_UNAVAILABLE_HEADER}\n\n\
         {INSTRUCTIONS_UNAVAILABLE_PROSE}\n\n{error}"
    )
}
```

`run` resolves the one source through the same degrade discipline as
`context_command`: an absent `--skill` prints nothing (there is no instructions
without a skill); a present raw name is parsed **inside** the fail-safe boundary
(invalid → unavailable notice under `Degrade`, error under `Fail`); a parsed name
assembles to a `Fragment` (`None` → nothing printed) or degrades to the notice.

`--explain` degrades *with* the rest under `--fail-safe` (never a hole in the
boundary) and, for a valid or degraded name, prints the root line then the two
instructions-level lines in the established `<level> (<path>): <state>` grammar
(root-relative paths via `locate`). Two boundary cases differ from `context`,
which always has an ever-present `Project` source to `locate`:

- **Invalid `--skill`.** There is no `SkillInstructions` source to `locate`, so no
  root line can be produced; explain emits a **single name-only line** naming the
  rejected input, with no root line (pinned by
  `explain_reports_an_invalid_skill_name_as_a_single_name_only_line`).
- **Absent `--skill`.** There is neither a skill source nor a project fallback, so
  explain has zero reportable levels: it prints **nothing** and exits 0, matching
  the bare-render no-op (pinned by a new `explain_without_a_skill_prints_nothing`
  case in the black-box suite below).

#### 2. The command arguments

**File**: `cli/launcher/src/launch/inbound/cli.rs`
**Changes**: A new `Command::Instructions` variant, its `skill` deliberately an
`Option<String>` (not a clap `value_parser` over `SkillName`, whose rejection
would exit non-zero before `--fail-safe`).

```rust
/// Print this skill's `## Additional Instructions` block, assembled from
/// `.luminosity/skills/<name>/instructions.md` and `instructions.local.md`.
/// Prints nothing when no block survives.
Instructions {
    /// The skill whose instructions to assemble, named by its frontmatter
    /// `name`. Instructions are always skill-scoped; without it, nothing prints.
    #[arg(long)]
    skill: Option<String>,
    /// Also print a per-level discovery diagnostic to stderr.
    #[arg(long)]
    explain: bool,
    /// Never exit non-zero: render an unreadable file as a notice on stdout
    /// instead. For callers that splice this command's stdout into a prompt,
    /// where a non-zero exit would discard the whole prompt.
    #[arg(long)]
    fail_safe: bool,
},
```

The exhaustive-match test (`an_unknown_subcommand_routes_to_external_with_its_args`)
grows the `Command::Instructions { .. }` arm.

#### 3. Dispatch and composition root

**File**: `cli/launcher/src/launch/mod.rs`
**Changes**: An `Instructions { skill, explain, fail_safe }` dispatch arm that
builds `instructions_cli::Options` (mapping `fail_safe` → `OnFailure`) and calls
`instructions_cli::run(assembler, &options)`. **The same `AssembleFragment` port
serves both commands** — the source selects the document — so `dispatch` gains no
new port parameter; it passes the existing assembler to the new arm.

**File**: `cli/launcher/src/main.rs`
**Changes**: `is_root_help`'s hard-coded builtin-name list gains `"instructions"`:

```rust
Some("version" | "config" | "context" | "instructions" | "help")
```

so `luminosity instructions --help` renders clap's own subcommand help rather
than the augmented root help. The `FragmentAssembler::new(LazyFragmentBody)` from
Phase 0 is reused unchanged.

`OnFailure` now lives in the shared `command_support` scaffold (§1), so both
commands share the one enum — one degrade vocabulary, no re-export chain. Each
command keeps its own `Options` (they carry different flags and defaults), built in
its own `run` from the clap variant.

### Tests (write first)

**`cli/launcher/src/instructions_command/inbound/cli.rs`** (unit — byte-exact and
policy invariants below the process boundary):

- `renders_the_byte_exact_instructions_block` — the full block for `configure`
- `the_instructions_block_interpolates_the_skill_name` — a longer/shorter name
  shifts no line break
- `the_instructions_block_ends_at_the_last_body_byte`
- `the_instructions_unavailable_notice_names_the_skill_file`
- `an_invalid_skill_name_explains_under_a_skill_prefix`
- `an_invalid_skill_name_explains_as_a_name_only_line_with_no_root`
- `an_absent_skill_explain_reports_no_levels`
- `explain_degrades_with_the_rest_under_fail_safe`
- `explain_still_fails_loudly_without_fail_safe`

**`cli/launcher/tests/instructions.rs`** (black-box, against the compiled binary,
each test seeding a `.git`-marked temp workdir so discovery roots inside it):

- `a_team_skill_instructions_prints_the_block`
- `a_personal_skill_instructions_prints_the_block`
- `both_levels_join_team_first_with_one_blank_line`
- `a_present_but_empty_personal_level_is_dropped_with_no_doubled_blank`
  (the mixed-empty drop-empty join case)
- `a_present_but_empty_team_level_is_dropped_with_no_leading_blank` — its symmetric
  twin, exercising the other branch of the `[team, personal]` filter-then-join
  (kept a distinct named test, not folded into the personal-empty case)
- `an_absent_instructions_file_prints_nothing_and_exits_zero`
- `an_empty_instructions_file_prints_nothing`
- `a_frontmatter_mapping_is_not_injected`
- `a_thematic_break_body_is_injected_whole`
- `surrounding_blank_lines_leave_no_leading_or_trailing_blanks`
- `no_skill_flag_prints_nothing_and_exits_zero`
- `an_unknown_skill_name_prints_nothing` — silence, not an error
- **`an_invalid_skill_name_under_fail_safe_exits_zero_with_a_notice`** — the
  load-bearing one: `--skill=../../etc --fail-safe` exits 0 with the unavailable
  notice, never a non-zero exit that would discard the prompt
- `an_invalid_skill_name_without_fail_safe_exits_non_zero`
- `a_malformed_instructions_under_fail_safe_exits_zero_with_a_notice`
- `a_malformed_instructions_without_fail_safe_fails_loudly`
- `explain_reports_the_root_and_both_instructions_levels`
- `explain_surfaces_the_attempted_paths_when_a_valid_named_source_degrades`
- `explain_reports_an_invalid_skill_name_as_a_single_name_only_line` (no root line
  — there is no source to `locate`)
- `explain_without_a_skill_prints_nothing` — zero reportable levels, exit 0 (no
  project fallback, unlike `context`'s config-only explain)
- `help_describes_the_instructions_command`

### Success Criteria

#### Automated Verification

- [x] Rust format and lint pass: `mise run cli:check`
- [x] Workspace unit tests and the black-box suite pass: `mise run test:unit:cli`
- [x] The instructions black-box suite passes in isolation:
      `cd cli && cargo nextest run -p luminosity -E 'test(instructions)'`
- [x] The full local CI mirror is green: `mise run` (exercises `build:launcher`)

#### Manual Verification

- [x] In a scratch repo with `.luminosity/skills/configure/instructions.md`,
      `luminosity instructions --skill=configure` prints the block with the exact
      header/prose and no trailing blank line.
- [x] `luminosity instructions --skill=../../etc --fail-safe` exits **0** and
      prints the `## Additional Instructions Unavailable` notice — a bad name
      cannot discard a prompt.
- [x] `instructions_command/inbound/cli.rs` carries a `//!` module doc describing
      the single-source block and the fail-safe policy, and every public item has
      a `///` summary (no `missing_docs` lint to catch a miss).

---

## Phase 3: Skill wiring, contract test, and the configure surface

### Overview

Add the end-of-body `!`-preprocessor line and the `instructions*` grant to every
registered skill, prove the wiring with a registry-walking contract test,
document the capability on the configure surface, and git-ignore the personal
instructions file.

### Changes Required

#### 1. The injection line and grant

**File**: `skills/config/configure/SKILL.md`
**Changes**: Add, at the **very end** of the body (after the skill's own prose and
after the top-of-body context line), the end-of-body invocation:

```markdown
!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions --skill=configure --fail-safe`
```

and add the grant to `allowed-tools`:

```yaml
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions*)
```

The `--skill=<name>` equals form and `--fail-safe` are load-bearing for the same
reasons as the context line. The context injection line stays at the top of the
body; the two lines together realise "context early / instructions last".

#### 2. The configure surface

**File**: `skills/config/configure/SKILL.md`
**Changes**: A `## Managing skill-specific instructions` section after
`## Managing skill-specific context`, in the same user-action register. It opens
with a one-line framing distinguishing the two mechanisms — instructions are
**directives the skill should follow**, distinct from context, which is
information it should merely *consider* — so a reader can tell which to reach for.
It must contain, and the tests assert:

- both source paths, using the concrete skill name
  (`.luminosity/skills/configure/instructions.md` team/committed and
  `.luminosity/skills/configure/instructions.local.md` personal/git-ignored) — led
  with the exact path and the `--explain` diagnostic so the silent-on-typo path is
  the first thing a reader learns to check;
- that instructions are **appended after, and applied in addition to, the skill's
  own instructions and any context** — they land last in the prompt (personal
  after team within the block). The surface describes this positional lastness
  only; it makes **no** override/precedence promise, so it matches the injected
  prose ("Follow these instructions in addition to all instructions above") rather
  than contradicting it;
- the same naming rule and silence caveat as context (the `<skill-name>` is the
  invoked name; a wrong name emits nothing);
- the unterminated-`---` hazard already stated once for bodies (a single shared
  caveat covers instructions files too — reference it rather than restating);
- `${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions --skill=configure --explain`
  as the diagnostic, paired with a note that `context --explain` and
  `instructions --explain` are **separate** views — a reader debugging an empty or
  unexpected prompt runs both to see everything the skill receives.

#### 3. Git-ignore the personal level

**File**: `.gitignore`
**Changes**: Mirror the existing `context.local.md` pair — the ignore rule plus
the eval-fixture negation.

```gitignore
**/.luminosity/skills/**/instructions.local.md
!tests/evals/skills/configure/fixtures/**/instructions.local.md
```

#### 4. The contract test

**File**: `tests/unit/skills/test_instructions_injection.py` (new)
**Changes**: A sibling of `test_context_injection.py` that reuses the same
registry-walk discovery but asserts the *instructions* line, positioned at the
**end** of the body. Keeping it a separate file keeps each file's docstring and
positional logic coherent (context = top-of-body; instructions = end-of-body).

```python
INJECTION_TEMPLATE = (
    "!`${{CLAUDE_PLUGIN_ROOT}}/bin/luminosity instructions "
    "--skill={skill} --fail-safe`"
)
INSTRUCTIONS_GRANT = (
    "Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity instructions*)"
)
```

The registry walk, the vacuity guard, the frontmatter-name allow-list assertion,
and the name-matches-directory assertion are reused from the context suite's
shape.

### Tests (write first)

- `test_carries_the_exact_injection_line` — parametrized over the discovered
  skills, expecting the instructions line with the frontmatter `name:` — asserted
  for **every** registered skill regardless of whether it carries a fixture (the
  universal-wiring AC)
- `test_line_sits_at_the_end_after_the_context_line_and_all_subsections` — the
  instructions line index exceeds the context injection line index and the last
  `## ` heading index (end-of-body placement, the inverse of the context test).
  Give the "last `## ` heading index" an explicit sentinel default (e.g. the H1
  index) for a body with no `## ` subsections, mirroring the context test's
  `len(lines)` guard, so the assertion stays well-defined as future skills enrol
- `test_allowed_tools_grants_the_instructions_command`
- `TestConfigureSurface::test_carries_the_managing_skill_instructions_section`
- `TestConfigureSurface::test_names_both_skill_instructions_paths_as_the_source`
- `TestConfigureSurface::test_shows_the_explain_diagnostic_for_instructions`
- `TestGitignore::test_hides_a_personal_skill_instructions`
- `TestGitignore::test_tracks_a_team_skill_instructions`
- `TestGitignore::test_tracks_a_personal_skill_instructions_in_the_eval_fixtures`
- `TestGitignore::test_tracks_a_team_skill_instructions_in_the_eval_fixtures`

### Success Criteria

#### Automated Verification

- [x] Skill-wiring tests pass: `mise run test:unit:skills`
- [x] A single test runs green:
      `uv run pytest tests/unit/skills/test_instructions_injection.py -v`
- [x] `git check-ignore -v .luminosity/skills/x/instructions.local.md` reports
      the new rule, and does **not** match a fixture `instructions.local.md` nor
      any `instructions.md`
- [x] The full local CI mirror is green: `mise run`

#### Manual Verification

- [x] The rendered `configure` skill reads coherently: project context, then
      skill-specific context, then the skill's own prose, then the
      `## Additional Instructions` block at the end.
- [x] The new surface section frames editing as a user action, distinguishes
      instructions (directives to follow) from context (information to consider),
      and states that instructions land last and are applied *in addition to* the
      skill's own instructions — with no override/precedence promise, matching the
      injected prose.

---

## Phase 4: Eval coverage (CI tier)

### Overview

Add a new `instructions` eval capability — fixtures, dataset rows, scorer argv,
the golden-pinning chain, and a CI render test that runs the compiled binary — 
plus the coordinated growth of the three exact-list capability tripwires. This is
the **inverse** of 0017's Phase 4: because instructions is a *new* command, a new
`instructions_eval.py` registers a third capability, so the tripwires that pin
`capabilities("configure")` must grow rather than stay frozen.

### Changes Required

#### 1. Fixtures

**Files**: `tests/evals/skills/configure/fixtures/…` (new)

| Fixture | Contents | Scenario it pins |
|---|---|---|
| `instructions_skill_team_only` | `skills/configure/instructions.md`, with surrounding blank lines | block alone; blank-line trimming |
| `instructions_skill_both_levels` | `instructions.md` + `instructions.local.md` | team-then-personal combination |
| `instructions_skill_mixed_empty` | non-empty `instructions.md` + whitespace-only `instructions.local.md` | drop-empty join (no doubled blank) |
| `instructions_skill_empty` | whitespace-only `instructions.md` | no block emitted |
| `instructions_skill_behavioural` | `instructions.md` carrying a declarative directive | the block reaches the model |
| `context_and_instructions_ordering` | `config.md` + `skills/configure/context.md` + `skills/configure/instructions.md`, each with a distinguishable sentinel | context-early / instructions-last, all blocks reaching the model in order |

Fixtures are authored LF-only (guarded by the `.gitattributes` `text eol=lf`
entry 0017 added for `tests/evals/**/fixtures/**`). Behavioural bodies read as
**declarative directives** (a convention the agent applies), not an imperative
"emit this token" — the imperative form reads as a prompt injection the model
refuses, failing the arm for an unrelated reason (the reason 0017's dataset test
documents).

The `instructions_skill_both_levels` fixture is the committed witness that the
`.gitignore` negation commits a personal instructions file (the analogue of
0017's `context_skill_both_levels` witness that `TestGitignore` depends on).

#### 2. The capability module, scorer, and datasets

**Files**: `tests/evals/skills/configure/instructions_eval.py` (new),
`instructions_scorer.py` (new), `instructions_dataset.json` (new),
`instructions_behavioural_dataset.json` (new)
**Changes**: Mirror `context_eval.py` / `context_scorer.py` / `context_dataset.json`:

- `instructions_eval.py` declares `CAPABILITY = "instructions"` and a
  `configure_instructions_with_skill` task loading the behavioural dataset. It
  declares a with-skill arm and **no baseline arm** (passive injection has no
  no-skill control — same as context).
- `instructions_scorer.py` extracts `SCORER_ARGV = ["instructions",
  "--skill=configure", "--fail-safe"]` (the injected argv verbatim) as a module
  constant and re-executes exactly that against the seeded workdir.
- `instructions_dataset.json` carries the deterministic rows (with
  `expected_block` goldens for the render test); `instructions_behavioural_dataset.json`
  carries only the behavioural rows (`instructions_skill_behavioural`,
  `context_and_instructions_ordering`), each with structural guards mirroring the
  context dataset (every row parses, its sentinel is present in the referenced
  fixture body, each behavioural row equals its main-dataset twin).
  `context_and_instructions_ordering` carries a context sentinel **and** an
  instructions sentinel and the scorer requires **both** in the transcript.

#### 3. The golden-pinning chain and render test (net-new infrastructure)

**Files**: `tests/unit/evals/skills/configure/test_instructions_dataset.py`
(new), `test_instructions_render.py` (new), and the shared tripwire files.

Unlike 0017 — which was behavioural-only, left byte-exactness entirely to the Rust
binary tests, and carried **no** goldens in its dataset — 0018 adds a free CI-tier
byte grade for the deterministic scenarios. That grading machinery does **not**
exist yet (there is no `grade_block`, no `_trim`, no host-binary-path resolver, no
render test, and no Rust-source scraper; `test_dataset.py`'s `_DOMAIN_TEMPLATES` is
a hand-transcribed constant with a manual-refresh note, not an automated pin), so
this section is **net-new**, not reuse:

- `test_instructions_dataset.py` pins an `INSTRUCTIONS_BLOCK_PREFIX` — the
  `## Additional Instructions` header plus the three prose lines with the skill
  name substituted for `{skill}` — as a **hand-transcribed Python constant**
  mirroring `_DOMAIN_TEMPLATES`, carrying the same manual-refresh-trigger note (the
  Rust `instructions_prose` literal is unreachable from Python; the render test
  below is what actually proves the binary agrees). It pins `SCORER_ARGV` against
  the SKILL.md `!`-line, and asserts each deterministic golden equals its fixture
  body assembled the adapter's way (frontmatter stripped, blank-trimmed, combined
  team-then-personal). Reuse `_body` / `_frontmatter` from `test_context_dataset.py`
  (extract them to a shared helper module first) and **add** a `_trim` helper
  transcribing the Rust `trim_blank_lines` rule (it does not exist today).
- `test_instructions_render.py` is the pin for the seam the Rust tiers cannot see:
  it runs the **compiled** `luminosity` binary with the exact `SCORER_ARGV` scraped
  from the SKILL.md line, against each committed fixture directory, and
  byte-compares stdout against the golden. Its unique value over the Rust black-box
  `instructions.rs` is precisely this SKILL.md-argv × committed-eval-fixture seam —
  it is not re-proving block bytes for their own sake. It requires a **new**
  `grade_block` helper (defined here) for the trailing-newline / empty-output
  comparison semantics and a **new** host-binary-path resolver (with the actionable
  "run `mise run build:launcher`" message). The `build:launcher:host` task and its
  `test:unit:evals` dependency already exist (0017 pre-wired them for this render
  tier); only the resolver and the test that consume the built binary are new.
- **The exact-list capability tripwires grow by `instructions`** (0017 kept these
  frozen; here they must grow because a new `instructions_eval.py` registers a
  third capability):
  - `test_run.py`'s `capabilities(_SKILL) == ["context", "values"]` →
    `["context", "instructions", "values"]`, plus an
    `assert instructions_eval.CAPABILITY in capabilities(_SKILL)` alongside the
    existing context/values assertions
  - the corresponding capability references in `test_collection.py` and
    `test_results.py` (mirror the exact edit sites 0017 kept frozen)
- **The committed-log gate grows by `instructions`, marked `xfail(strict=True)`
  until Phase 5.** `TestCommittedGate.test_every_with_skill_arm_clears_the_floor`
  ([`test_results.py`](tests/unit/evals/skills/configure/test_results.py)) is
  parametrized over the capabilities; add the instructions arm as a
  `pytest.param(instructions_eval.CAPABILITY, marks=pytest.mark.xfail(strict=True,
  reason="…pending the Phase 5 live log"))`, and add an `xfail(strict=True)`
  instructions analogue of `test_the_committed_log_covers_the_behavioural_dataset`
  that reads `instructions_behavioural_dataset.json` — **not** the existing
  `_behavioural_scenarios()` helper, which hard-codes `context_dataset.json`;
  parametrise that helper by dataset (or add a sibling) so the instructions gate
  grades the instructions scenario set, not the context one.
  Because the mark is strict, Phase 4 merges **green** (the arm xfails cleanly with
  no committed log), and the instant Phase 5 commits the log the assertion xpasses —
  which strict xfail reports as a failure, forcing Phase 5 to remove the marker in
  the same change. No phase leaves a required check red.

#### 4. Solver coverage

**File**: `tests/unit/evals/skills/configure/test_solvers.py`
**Changes**: `_seed`'s `copytree` already handles nested `.luminosity/skills/`
(fixed in 0017), so add a case seeding a fixture carrying
`skills/configure/instructions.local.md` and assert the file lands at the
expected workdir path with the fixture's content.

### Tests (write first)

- `test_instructions_block_prefix_matches_the_rust_source`
- `test_the_instructions_prose_interpolates_the_skill_name`
- `test_the_scorer_argv_matches_the_skill_injection_line`
- `test_deterministic_golden_matches_the_fixture_body` (over the new scenarios)
- `test_both_levels_orders_team_before_personal_within_the_block`
- `test_mixed_empty_level_drops_the_empty_with_no_doubled_blank`
- `test_instructions_empty_expects_no_block`
- `test_context_and_instructions_carries_both_sentinels_present_in_both_bodies`
- `test_the_behavioural_dataset_rows_match_their_main_dataset_twins`
- `test_every_scenario_fixture_file_exists_on_disk`
- `test_instructions_render.py::test_binary_output_matches_each_golden`
- `test_run.py` / `test_collection.py` / `test_results.py` tripwire updates
- `test_solvers.py::seeds_a_personal_skill_instructions_file`

### Success Criteria

#### Automated Verification

- [ ] Eval-logic tests pass **green**: `mise run test:unit:evals` — the new
      `instructions` capability's committed-log assertions are marked
      `xfail(strict=True)` (no live log yet), so they xfail cleanly rather than
      failing; every other new eval-logic test passes outright.
- [ ] The updated capability tripwires pass: `mise run test:unit:tasks`
- [ ] Python format, lint, and types pass: `mise run check`
- [ ] The full local CI mirror is green: `mise run`

#### Manual Verification

- [ ] Each new fixture's `instructions.local.md` is actually tracked by git (the
      `.gitignore` negation from Phase 3 works).
- [ ] `tasks/README`'s eval-tier shape gains the byte-grade render tier: the
      `build:launcher:host` task and its `test:unit:evals` dependency were wired in
      0017, and this story adds the first test that consumes the built binary.

---

## Phase 5: Live eval run

### Overview

The eval-coverage acceptance criterion is satisfied only by a committed result
log for the new `instructions` capability. This is a live, **billed** `claude -p`
run, as 0016/0017's were. Only the two behavioural arms
(`instructions_skill_behavioural`, `context_and_instructions_ordering`) run live;
the deterministic scenarios are graded by the Phase 4 CI render test.

### Changes Required

**Command**: `mise run eval:skills:configure`
**Files**: `tests/evals/skills/configure/results/*.json` (new logs, scrubbed of
host paths by `readback.scrub_result_dir`)

The run drives the real `claude -p` against the staged plugin in a seeded temp
workdir, then re-executes the compiled `luminosity` binary with the injected argv
and byte-compares stdout against the goldens. Gated at the established
`PASS_K_FLOOR` over `TRIALS`. The behavioural prompts must route the agent
through the `configure` skill (injection fires at skill load), following the
proven-prompt shape 0017 landed on.

### Success Criteria

#### Automated Verification

- [ ] `mise run eval:skills:configure` exits 0 (every behavioural arm, including
      the new instructions arms, clears the pass^k floor)
- [ ] Phase 5 removes the `xfail(strict=True)` markers added in Phase 4 (the
      committed log now exists, so those arms would xpass and strict xfail would
      fail); the now-enforcing committed-log assertions — including the new
      `instructions` dataset-coverage pin — pass: `mise run test:unit:evals`
- [ ] No absolute host paths leak into the committed logs

#### Manual Verification

- [ ] The `context_and_instructions_ordering` transcript shows the agent applying
      **both** the context convention and the instructions directive — proving
      both blocks landed, context above and instructions below.
- [ ] Inspect the run in the log viewer:
      `mise run eval:view -- --skill configure`

---

## Phase 6: Full local CI mirror

### Overview

"Done" means the bare `mise run` default task exits 0 end-to-end. This is the
final gate; `mise run` must already have been green at the end of every prior
phase.

### Success Criteria

#### Automated Verification

- [ ] `mise run fix` applies cleanly (formatters and safe lint fixes)
- [ ] `mise run check` exits 0 (format + lint + types across all components, plus
      `deny:check` / `pup:check`)
- [ ] `mise run` exits 0 end-to-end — the full local CI mirror, including
      `build:launcher` and the whole test suite with coverage

#### Manual Verification

- [ ] No stray comments explaining what the code already says (the repo's
      standing bar).

---

## Testing Strategy

The three toolchains each guard a different seam, unchanged in division from
0017:

**Rust unit tests (`cli/config/`, `cli/config-adapters/`)** — the domain rules:
level combination, blank-line trimming, frontmatter mapping-only stripping,
`instructions` path construction, symlink refusal, and error propagation.
Exhaustive here because it is free.

**Rust unit tests (`cli/launcher/src/instructions_command/`)** — the render and
policy invariants: the byte-exact `## Additional Instructions` block, the
empty-output and independent-degrade policies, and the `--explain` line grammar —
pinned below the process boundary.

**Rust black-box tests (`cli/launcher/tests/instructions.rs`)** — the compiled
binary's contract: every level permutation, the empty/absent policy, the mixed-
empty drop-empty join, and the fail-safe boundary. Each test seeds a `.git`-marked
temp workdir so discovery roots inside the fixture.

**Python skill-wiring tests (`tests/unit/skills/`)** — that the end-of-body
instructions line exists, in the right place (after the context line and all
subsections), with a representable skill name, in **every** registered skill, and
that the personal file is git-ignored while the team file is tracked.

**Python eval-logic tests (`tests/unit/evals/`)** — that the goldens have not
drifted from the Rust literals, that the compiled binary's stdout matches the
goldens for every fixture, and that the committed live log covers the current
`instructions` dataset. Runs in CI; costs nothing.

**The live eval (`mise run eval:skills:configure`)** — that injection actually
reaches the model, and that context lands above instructions, for the two
behavioural arms. Excluded from CI for token cost; run once and its log committed.

### The edge cases that matter most

1. **An invalid `--skill` name under `--fail-safe`.** Must exit 0 with the
   unavailable notice — a non-zero exit discards the prompt, the worst failure
   mode.
2. **A present-but-empty personal level beside a non-empty team level** (and its
   symmetric twin). The empty level is dropped with no stray or doubled blank
   line — the drop-empty join path the story calls out.
3. **A malformed `instructions.md` under `--fail-safe`.** Degrades to a notice
   naming the instructions file, exit 0.
4. **Both a context file and an instructions file present.** The context block(s)
   land near the top and the instructions block lands last — asserted positionally
   by the Python test and behaviourally by the ordering eval.
5. **An `instructions.md` whose first line is `---`.** A terminated non-mapping
   fence (thematic break) is preserved whole; a valid mapping is stripped; an
   unterminated fence fails loud (degrading under `--fail-safe`).

## Migration Notes

None. Per-skill instructions are purely additive: no
`.luminosity/skills/**/instructions.md` exists in any repository today, the
`context` subcommand and its behaviour are unchanged, and Phase 0's rename touches
no on-disk format and no CLI contract. The `config` crate name and the
`ConfigError` taxonomy are deliberately left as-is (a follow-up may track the
generalised domain, per 0017's note).

## References

- Work item: `meta/work/0018-per-skill-instructions-injection.md`
- Research: `meta/research/codebase/2026-07-19-0018-per-skill-instructions-injection.md`
- Primary template (the direct predecessor):
  `meta/plans/2026-07-13-0017-per-skill-context-injection.md`
- Shared-mechanism story:
  `meta/plans/2026-07-11-0016-plugin-global-context-injection.md`
- Governing ADRs: `meta/decisions/ADR-0012-two-level-per-skill-context-with-frontmatter-stripped.md`
  (two-level + frontmatter-strip), ADR-0003 (`.luminosity/` layout + multi-level
  config), ADR-0009 (hexagonal core), ADR-0001 (skills-vs-CLI division of labour),
  ADR-0011 (Inspect as the eval harness)
- Eval framework: `meta/plans/2026-07-07-0010-apply-eval-framework-to-configure-skill.md`
- Key source: `cli/config/src/context.rs` (→ `fragment.rs`),
  `cli/config/src/source.rs`, `cli/config-adapters/src/store.rs`,
  `cli/launcher/src/context_command/inbound/cli.rs`,
  `skills/config/configure/SKILL.md`,
  `tests/unit/skills/test_context_injection.py`, `.gitignore`,
  `.claude-plugin/plugin.json`
