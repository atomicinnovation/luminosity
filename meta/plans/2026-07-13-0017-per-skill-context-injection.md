---
type: plan
id: "2026-07-13-0017-per-skill-context-injection"
title: "Per-Skill Context Injection Implementation Plan"
date: "2026-07-13T21:18:06+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0017"
parent: "work-item:0017"
derived_from: ["codebase-research:2026-07-13-0017-per-skill-context-injection"]
tags: [configuration, context-injection, rust-cli, skills, evals]
revision: "459e98f792240b539fb5d6251722105893f5bbad"
repository: "luminosity"
last_updated: "2026-07-13T23:39:38+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Per-Skill Context Injection Implementation Plan

## Overview

Teach the Rust CLI to read two-level per-skill context —
`.luminosity/skills/<skill>/context.md` (team) and
`.luminosity/skills/<skill>/context.local.md` (personal) — combine them
team-then-personal, and render them as a `## Skill-Specific Context` block
immediately after the `## Project Context` block story 0016 already emits.

The two blocks are rendered by **one command**: `luminosity context
--skill=<name> --fail-safe`. That single decision is what makes the story's
ordering and absent-global acceptance criteria structurally true — guaranteed by
one pure `join_blocks(project, skill)` whose parameter order fixes the sequence,
rather than by two `SKILL.md` lines a future edit could reorder — and it is why
no `allowed-tools` change, no new subcommand, and no new eval arm are needed.

This plan **generalises** 0016's project-context machine into a single
two-level-document domain rather than copying it per document kind (an author
decision taken during review — see Implementation Approach). Story 0018
(per-skill instructions) then adds a document variant rather than a third
parallel domain.

## Current State Analysis

Story 0016 built almost exactly the machine this story needs. The work is a
generalisation of it — one new document kind on an existing two-level assembler,
not a new subsystem.

**What already exists and extends cleanly:**

- **The cross-crate hexagon.** `cli/config/` is the serde-free domain core;
  `cli/config-adapters/` owns every filesystem and serde concern (and
  `cli/deny.toml:84-101` names it as the *only* permitted `serde-saphyr` wrapper,
  so the purity is enforced, not merely intended); `cli/launcher/src/
  context_command/inbound/cli.rs` is the driving adapter that owns the byte-exact
  block and the empty-output policy. `context_command/` deliberately has no
  `core.rs` and no `outbound/` (`context_command/mod.rs:3-5`).
- **The exact combination rule this story needs**, already written and tested.
  `combine` (`cli/config/src/context.rs:87-98`) trims each level, drops the empty
  ones, and joins the survivors with one blank line; empty → `None` → nothing
  printed at all. `trim_blank_lines` (`:100-114`) strips whole leading and
  trailing blank lines while preserving leading indentation on the first kept line
  and every interior blank line, and already handles CRLF
  (`a_crlf_body_strips_its_terminator_and_keeps_interiors`). Generalising the
  assembler over these keeps the blank-line-trimming and level-combination
  criteria for free.
- **`LevelContribution` / `Assembly`** (`cli/config/src/context.rs:24-36`) — the
  `--explain` diagnostic shape, which the generalisation keeps as the single
  per-level record for any document kind.
- **The registry-walking contract test.**
  `tests/unit/skills/test_context_injection.py:29-41` already walks
  `plugin.json`'s `skills` array and `rglob`s `SKILL.md` beneath each entry, with
  a vacuity guard (`:51-54`). It auto-enrols any future skill, which is what makes
  the story's "every skill" requirement durable rather than a point-in-time
  snapshot. **Preserve that property.**
- **The golden-pinning chain.** Commit `ce39575` made
  `tests/unit/evals/skills/configure/test_context_dataset.py` *scrape the Rust
  literals* out of `context_command/inbound/cli.rs` and pin the Python copy
  against them (`:48-69,118-122`), rather than restating them. The chain is: Rust
  literals → `BLOCK_PREFIX` → derived expected block → dataset golden → live
  binary stdout (byte-compared). This story must extend that chain **and** close
  the two gaps review found in it (see Phase 4).

**What is missing or in the way:**

- **The CLI knows nothing of skills.** Grepping `skill` case-insensitively across
  `cli/**/*.rs` returns zero matches. This story introduces the first skill-aware
  concept into the config domain.
- **0016's ports are keyed on `Level` alone.** `ReadConfigBody::read_body(level)`
  (`cli/config/src/service.rs`) and `AssembleProjectContext::assemble()`
  (`context.rs:38-45`) have no notion of *which* document. The generalisation
  re-keys them on a `(source, level)` pair.
- **`FileConfigStore::read_raw` is keyed on `Level`, not on a path**
  (`cli/config-adapters/src/store.rs:50-66`). The per-skill reader needs the same
  read-and-split behaviour against a different path, so the primitive must be
  re-cut path-first.
- **`frontmatter::split` strips whatever sits between the first two `---` fences
  without checking it is YAML** (`cli/config-adapters/src/frontmatter.rs:21-47`).
  Safe for CLI-owned `config.md`, but `context.md` is free-form user prose: a file
  opening `---\nSection A\n---\nSection B` would silently lose "Section A". The
  body reader must only strip a fence block that parses as a YAML mapping (see
  Phase 1).
- **The filesystem follows symlinks.** `fs::read_to_string` on
  `.luminosity/skills/<name>/context.md` follows a committed symlink to its
  target. `SkillName` validation stops name-based traversal but not a symlinked
  file or directory component (see Phase 1).
- **`solvers.py::_seed` cannot copy a nested fixture directory.** It does a flat
  `source.glob("*")` + `shutil.copy` (`:83-89`), which raises `IsADirectoryError`
  the moment a fixture carries `.luminosity/skills/`. **This is the single hard
  blocker in the eval tier.**
- **`.gitignore` ignores `**/.luminosity/config.local.md` with a negation for the
  eval fixtures.** The per-skill personal file needs the equivalent pair, or the
  committed fixtures will not be tracked.

### Key Discoveries

- **The `!` preprocessor's all-or-nothing failure mode is the dominant design
  force.** A non-zero exit from an injected command discards the *entire prompt*.
  That is why `OnFailure::Degrade` exists
  (`context_command/inbound/cli.rs:22-32`). The consequence for this story is
  sharp and easy to get wrong: **the skill-name validation must happen inside
  `context_cli::run`, not in a clap `value_parser`.** A clap rejection exits with
  clap's own non-zero code *before* `--fail-safe` is ever consulted
  (`main.rs:184-188`: `Cli::try_parse` → `error.exit()`), so a mistyped skill name
  would silently disable the skill it was injected into. Phase 2 carries an
  explicit test for this.
- **The same failure mode reaches the wiring tier.** A skill whose frontmatter
  `name:` is not a bare `[A-Za-z0-9_-]+` token would generate an injection line
  (e.g. `--skill=my skill`, which the shell splits) that clap rejects non-zero
  *outside* the fail-safe boundary. The `--skill=<name>` equals form closes the
  leading-hyphen case, and the contract test rejects a non-representable name at
  CI time (Phase 3), so neither can blow up a prompt at runtime.
- **`Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)`
  (`skills/config/configure/SKILL.md:11`) has no space before the `*`** —
  deliberately. It already covers `context --skill=configure --fail-safe`, so the
  one-line injection shape needs **no `allowed-tools` change**, and `is_root_help`
  (`cli/launcher/src/main.rs:130-136`) needs no new entry.
- **Extending the existing `context` eval capability beats adding a new one.**
  Because one command now renders both blocks, per-skill context is naturally part
  of the same capability: new fixtures and dataset rows, and the scorer's argv
  grows `--skill=configure --fail-safe`. That means **no new eval arm** (no extra
  billed baseline), and the three exact-list tripwires —
  `tests/unit/tasks/shared/eval/test_run.py:20` (`capabilities(_SKILL) ==
  ["context", "values"]`), `test_collection.py`, `test_results.py:70-72` — all
  stay green rather than needing to be widened.
- **Frontmatter is stripped** (author's decision). This is a deliberate divergence
  from the accelerator, whose per-skill readers inject the whole file. It means
  the per-skill reader reuses the frontmatter splitter, so there is one
  file-reading primitive in the adapter rather than two subtly different ones.

## Desired End State

A user writes `.luminosity/skills/configure/context.md` (shared with the team) or
`.luminosity/skills/configure/context.local.md` (personal, git-ignored), and that
content appears in the `configure` skill's prompt as a `## Skill-Specific
Context` block directly beneath the `## Project Context` block — or, when no
project context exists, as the first injected block at that same point.

Verified by: `luminosity context --skill=configure` printing both blocks in
order; `cli/launcher/tests/context.rs` black-box tests covering every level and
ordering permutation and the independent-degrade policy; the registry-walking
contract test asserting every registered skill injects **its own** name; a CI
pytest that runs the compiled binary against each fixture and byte-compares
stdout against the goldens; and a live eval run in which the real `claude -p`
agent, driven through the real skill, demonstrably receives the block.

## What We're NOT Doing

- **Not adding a new subcommand.** `--skill` extends `context`. A `skill-context`
  subcommand would need a new grant in every skill, a new `is_root_help` entry,
  and a second fail-safe boundary.
- **Not validating the skill name against the known skill set.** If `--skill
  nonexistent` is passed, the file simply does not exist and nothing is emitted on
  the injection path. Silence is correct there: the CLI has no skill registry. The
  `--explain` diagnostic (Phase 2) is what turns that silence into a diagnosable
  signal for the human debugging it, and the contract test (Phase 3) catches the
  realistic wiring failure (a new skill copy-pasting a sibling's name).
- **Not building an interactive scaffolder.** The user creates the directory and
  file by hand, as with project context. `--explain` prints the exact paths it
  read so they are copy-pasteable; that is the whole of the onboarding affordance.
- **Not fixing `tasks/shared/eval/staging.py:18`'s hard-coded `skills/config`
  copytree.** It is a landmine for any skill added outside `skills/config/`, but
  no such skill exists and this story does not create one.
- **Not touching story 0018.** Per-skill *instructions* inject at the end of the
  body and remain a separate line and a separate story. Under the generalised
  domain, 0018 adds a `ContextSource::SkillInstructions(SkillName)` variant, an
  adapter path arm, and a renderer — not a third assembler. (0018 should very
  likely gain an `instructions.local.md` for symmetry with the two-level model
  this story establishes — flagged there for the author, not decided or built
  here.)

## Security and trust boundary

Per-skill context is **untrusted committed content**, carried forward from
0016's trust model. `.luminosity/skills/<name>/context.md` can arrive via an
outside PR, a cloned template, or a vendored dependency, and the CLI splices its
body near the top of the skill prompt under prose that frames it as instruction
to apply. It is therefore a cross-user / supply-chain prompt-injection channel —
one that is *less* visible in review than a top-level config change, and (with
the mapping-only strip) one a reviewer might skim past as frontmatter. The design
accepts the same boundary 0016 did — this is data spliced into a prompt, treated
as data, not a capability — with two consequences this plan commits to:

- The skill's own **binding constraints must be re-asserted after** the injected
  block, so a hostile body cannot shadow them by forging `##` headings. The
  `configure` skill already places its constraints below the injection line; the
  Phase 3 surface work must not move the injection point below them.
- Two smaller hardening measures below: the `SkillName` allow-list and the
  symlink-containment check (Phase 1) close the *path* side of the same boundary,
  and committed eval fixtures / result logs carry only opaque, non-sensitive
  sentinel bodies (Phase 4) because `readback.scrub_result_dir` scrubs host paths,
  not content.

One residual is **accepted, not fixed**: the `--fail-safe` degrade notice
interpolates the `ConfigError`'s absolute path into the injected prompt (as
0016's project notice already does), so a broken skill file discloses an absolute
host path to the model. The human-facing `--explain` diagnostic is root-relative,
but the injected notice is not; the disclosure is low-severity (the agent already
runs in the user's environment, and committed logs are path-scrubbed) and
relativising the notice would need the root threaded into the error render.
Recorded here so the choice is deliberate.

## Implementation Approach

**Generalise, don't mirror.** 0016's project-context assembler is already a
two-level combine-and-report machine; the only thing per-skill context adds is a
*second document kind*. So this story replaces 0016's project-only ports with
source-parameterised ones and models the document identity explicitly:

- A `ContextSource` value object names which document — `Project`, or
  `Skill(SkillName)` (0018 adds `SkillInstructions(SkillName)`).
- One driven port `ReadContextBody::read_body(&source, level)` reads a
  `(source, level)` body and reports the display path it read.
- One driving port `AssembleContext::assemble(&source)` combines the two levels
  via the existing `combine` / `trim_blank_lines` rule and returns the same
  `Assembly` shape for any document kind.

The distinct language that *must* stay distinct lives exactly where it differs
and nowhere else:

- the `ContextSource` variants (the domain identity),
- the adapter's per-source path arm (`.luminosity/config*.md` vs
  `.luminosity/skills/<name>/context*.md`),
- the launcher's per-source renderer (the `## Project Context` vs
  `## Skill-Specific Context` header and prose).

This is cheapest to do **now**, at two document kinds, with 0016's black-box
suite green to catch any regression in the refactor. It removes the fixed
`[LevelContribution; 2]` fold and the trim/combine rule from being copied per
kind, and it turns 0018 into "add a variant, a path arm, and a renderer".

Ordering is encoded in the one place the design already assigns it: a **pure**
`join_blocks(project, skill)` in the inbound adapter whose *parameters* fix the
project-then-skill order (not a push-order into a slice a future edit could
reorder) — unit-tested directly, so the story's headline ordering criterion is
pinned below the process boundary, not only above it.

### Phase mergeability

Phases 1–4 are each a complete, green, independently mergeable increment: every
one ends with `mise run check` and (for the Rust phases) `mise run test:unit:cli`
green. Phase 3a (the successor ADR) is a documentation deliverable that rides with
Phase 3. Phase 5 is the one-off billed live run whose committed log satisfies the
eval acceptance criterion. Phase 6 is the final full-CI-mirror gate. `mise run`
must be green at the end of **every** phase, not only the last.

---

## Phase 1: Domain and adapter

### Overview

The generalised two-level-document domain — `ContextSource`, `SkillName`, the
source-keyed ports, and the assembler — plus the adapter's per-source path rule,
the symlink-safe reader, and the mapping-validating frontmatter strip. No
user-visible surface changes; the CLI does not yet expose `--skill`.

### Changes Required

#### 1. Story correction (already applied — not part of this phase's diff)

`meta/work/0017-per-skill-context-injection.md` was amended during planning to
record the two-level model, the frontmatter-stripping divergence, and that
ADR-0020 names the *accelerator's* ADR (Luminosity's series ends at ADR-0011).
No further edit here; listed only so the trail is complete.

#### 2. The document-source value objects

**File**: `cli/config/src/source.rs` (new)
**Changes**: `SkillName` and `ContextSource`, each with a `//!` module doc in the
register of `context.rs`'s, an item-level `///` summary on every public type (the
crate's uniform standard), and the crate's uniform derives.

```rust
/// A validated skill name — the identity a skill is invoked by, safe to place
/// in a filesystem path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SkillName(String);

impl SkillName {
    /// Parses a skill name under an allow-list: non-empty, ASCII
    /// alphanumeric, `-`, or `_`.
    ///
    /// # Errors
    ///
    /// [`ConfigError::InvalidSkillName`] when `raw` is empty or carries any
    /// character outside the allow-list.
    pub fn parse(raw: &str) -> Result<Self, ConfigError> { /* allow-list */ }

    #[must_use]
    pub fn as_str(&self) -> &str { &self.0 }
}

impl fmt::Display for SkillName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Which two-level `.luminosity` document is being assembled.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContextSource {
    Project,
    Skill(SkillName),
}
```

`SkillName` validates with an **allow-list** (ASCII alphanumeric, `-`, `_`,
non-empty) rather than a deny-list. A deny-list of `/`, `\`, `..` invites the
next traversal trick; the allow-list rejects all of them — and Unicode
lookalikes, NUL bytes, `.`, and `..` — by construction. The `Display` impl is
what the renderer and `--explain` use to interpolate the name (see Phase 2), so
the prose is compile-checked rather than filled by a stringly-typed template.

#### 3. The level qualifier

**File**: `cli/config/src/level.rs`
**Changes**: Replace `Level::file_name()` (which hard-codes `config.md`) with a
precedence-independent **qualifier**, so `Level` no longer knows any document's
filename — the (source, level) → filename mapping moves entirely into the
adapter's path arm.

```rust
impl Level {
    /// The filename qualifier for this level: empty for team, `.local` for
    /// personal. Composed with a document's base name by the adapter.
    #[must_use]
    pub const fn qualifier(self) -> &'static str {
        match self {
            Self::Team => "",
            Self::Personal => ".local",
        }
    }
}
```

This keeps `Level` a pure level identity and means 0018 adds no accessor here.

#### 4. The generalised assembler

**File**: `cli/config/src/context.rs`
**Changes**: Re-key the ports and assembler on `(source, level)`; keep the
`combine` / `trim_blank_lines` rule and the `Assembly` / `LevelContribution`
shape; rewrite this module's `//!` doc to describe assembly of **any**
`ContextSource`'s two levels (it currently says "the project-context block from
the two config-file bodies"). `LevelContribution` gains the adapter-supplied
display `path` so `--explain` need not reconstruct it — a deliberate DTO
concession: the core never interprets the string, it only couriers the adapter's
provenance to the diagnostic. Every public item carries a `///` summary.

```rust
/// A trimmed, combined body ready to wrap in a block — for any document source.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssembledContext {
    pub body: String,
}

/// What one level contributed, plus the display path it was read from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelContribution {
    pub level: Level,
    pub path: String,
    pub discovered: bool,
    pub has_body: bool,
}

/// The outcome of assembling one source: the optional combined body and the
/// per-level record, ordered `[team, personal]`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    pub context: Option<AssembledContext>,
    pub levels: [LevelContribution; 2],
}

/// One level's read: the display path, and its body when the file was present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelBody {
    pub path: String,
    pub body: Option<String>,
}

pub trait ReadContextBody {
    /// Reads `source`'s body at `level`, reporting the display path read.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when the file exists but cannot be read or is unsafe.
    fn read_body(
        &self,
        source: &ContextSource,
        level: Level,
    ) -> Result<LevelBody, ConfigError>;
}

pub trait AssembleContext {
    /// Reads both levels of `source` once and combines their bodies.
    ///
    /// # Errors
    ///
    /// A [`ConfigError`] when either level cannot be read.
    fn assemble(
        &self,
        source: &ContextSource,
    ) -> Result<Assembly, ConfigError>;
}

pub struct ContextAssembler<R> {
    reader: R,
}

impl<R> ContextAssembler<R> {
    #[must_use]
    pub const fn new(reader: R) -> Self {
        Self { reader }
    }
}
```

`assemble` reads both levels once, combines them team-then-personal via
`combine`, and records each level's contribution (including its path) using the
same trim predicate as the merge — so `has_body` can never disagree with block
membership, the invariant `context.rs`'s module doc already states. The
`AssembledContext` type (renamed from `ProjectContext`) is now document-neutral;
the launcher's renderer supplies the per-document header and prose.

**File**: `cli/config/src/error.rs`
**Changes**: Two new variants, mirroring `InvalidKey`'s shape and message style.

```rust
InvalidSkillName { name: String },
UnsafePath { path: String },
```

rendering as:

```
invalid skill name '<name>': expected non-empty alphanumeric, '-', or '_'
refused to read '<path>': it resolves outside the .luminosity directory
```

**File**: `cli/config/src/lib.rs`
**Changes**: Register `source` (and rename references from the old project-only
names). Re-export `AssembleContext`, `ReadContextBody`, `Assembly`,
`AssembledContext`, `ContextAssembler`, `LevelBody`, `LevelContribution`,
`ContextSource`, `SkillName`.

#### 5. The path rule and symlink-safe reader

**File**: `cli/config-adapters/src/store.rs`
**Changes**: Re-cut `read_raw` path-first, add the per-source path rule, the
mapping-validating body reader, the symlink-containment check, and the
`ReadContextBody` impl.

```rust
fn context_path(&self, source: &ContextSource, level: Level) -> PathBuf {
    match source {
        ContextSource::Project => self
            .config_dir()
            .join(format!("config{}.md", level.qualifier())),
        ContextSource::Skill(name) => self
            .config_dir()
            .join("skills")
            .join(name.as_str())
            .join(format!("context{}.md", level.qualifier())),
    }
}

/// Both level paths for a source, for a diagnostic that must name the paths
/// even when a read fails and yields no `Assembly`. Single source of the path
/// rule, so `--explain` never rebuilds `skills/<name>/<file>` itself.
#[must_use]
pub fn context_paths(&self, source: &ContextSource) -> [PathBuf; 2] {
    [
        self.context_path(source, Level::Team),
        self.context_path(source, Level::Personal),
    ]
}

impl ReadContextBody for FileConfigStore {
    fn read_body(
        &self,
        source: &ContextSource,
        level: Level,
    ) -> Result<LevelBody, ConfigError> {
        let path = self.context_path(source, level);
        Ok(LevelBody {
            path: display(&path),
            body: self.read_context_body(&path)?,
        })
    }
}
```

The layering is **two** functions, not one — the prior draft's "one primitive
shared by both readers" was contradictory (the config value path needs the
parsed frontmatter node and must fail loud on a malformed config mapping, and it
must not inherit the context-only rules):

- **`read_and_split(&Path) -> Result<Option<(String, Split)>, ConfigError>`** —
  the existing `read_raw` body, path-first: `Ok(None)` when absent, loud
  `MalformedFrontmatter` on an unterminated fence, else the raw content and its
  `Split`. Shared by the config-level readers **unchanged** (they discard the raw
  content and use the split), so `config.md` behaviour is untouched.
- **`read_context_body(&Path) -> Result<Option<String>, ConfigError>`** — the
  context reader. It applies the symlink-containment check, calls
  `read_and_split`, and chooses the body: `split.body` when `split.frontmatter`
  parses as a YAML mapping (via `document::parse_frontmatter`), else the retained
  **raw content** (never reconstructed from the `Split`, so a CRLF thematic-break
  body round-trips byte-exact). Documented on its own `///` (the contract lives
  there, not in an inline comment at the call site).

The two context-specific rules, each with a test below:

- **Symlink containment.** Canonicalise **both** sides. Resolve the file's parent
  with `fs::canonicalize` and verify it is within `fs::canonicalize(config_dir())`
  using a **component-wise `Path::starts_with`** over the fully-canonical paths
  (not a string prefix, which would admit a `.luminosity-evil/` sibling).
  Canonicalising the root too is load-bearing: on macOS `/tmp` → `/private/tmp`
  and `CARGO_TARGET_TMPDIR`/`temp_dir()` live under such symlinked roots, so
  comparing a canonical file path against a raw `config_dir()` would refuse every
  legitimate file and break the Phase-1 and black-box tests. An **absent** parent
  (`NotFound` from canonicalising the parent) is `Ok(None)`; a present parent
  whose canonical form escapes `config_dir()`, or a symlinked leaf (checked via
  `fs::symlink_metadata`, its fully-canonical target compared the same way) that
  escapes, is refused with `ConfigError::UnsafePath`. This covers both a symlinked
  file and a symlinked `skills/<name>/` directory component.
- **Mapping-only frontmatter strip.** A terminated fence is stripped when its
  content is **empty/null or parses as a YAML mapping**; a **non-empty
  non-mapping scalar** (a prose thematic break like `Section A`, or malformed
  YAML) is treated as body and injected whole — a deliberate divergence from
  `config.md`'s loud value-read path, chosen so free-form prose is never silently
  truncated (and an empty `---\n---\n` block is stripped rather than left as
  literal fences). A file whose first line is `---` with no closing fence is an
  unterminated block and fails loud (degrading to a skill notice under
  `--fail-safe`); a leading unterminated `---` in a prose file is therefore the
  one shape a user must avoid, noted on the configure surface.

`config-adapters` is the permitted `serde-saphyr` wrapper
(`cli/deny.toml:84-101`), so the mapping check adds no dependency to the core.

### Tests (write first)

**`cli/config/src/source.rs`**:

- `a_bare_name_parses`, `a_hyphenated_name_parses`, `an_underscored_name_parses`
- `an_empty_name_is_rejected`
- `a_name_with_a_path_separator_is_rejected` (`/` and `\`)
- `a_parent_directory_traversal_is_rejected` (`..`)
- `a_name_with_a_dot_is_rejected`
- `a_name_with_a_brace_is_rejected` (guards the renderer's `{skill}` capture)
- `display_round_trips_the_name`

**`cli/config/src/context.rs`** — against a `FakeReader` returning `LevelBody`:

- `both_levels_absent_is_no_context`, `both_levels_empty_is_no_context`
- `a_whitespace_only_level_is_no_context`
- `team_only_yields_the_team_body`, `personal_only_yields_the_personal_body`
- `both_levels_join_team_first_with_one_blank_line` (the one case that catches
  the levels being wired backwards)
- `a_team_read_error_propagates`, `a_personal_read_error_propagates`
- `reports_each_level_in_team_then_personal_order`
- `reports_discovered_has_body_and_path_per_level`
- `a_present_but_whitespace_level_is_discovered_without_a_body` (carried forward
  from 0016 — the case distinguishing `discovered=true, has_body=false`)
- `assembles_a_skill_source_identically_to_a_project_source` (parametrised over
  `ContextSource::Project` and `ContextSource::Skill(...)`)

The blank-line-trimming and combination cases (`surrounding_blank_lines`,
`interior_blank_lines_and_indentation`, CRLF strip and CRLF join,
`the_combined_body_ends_without_a_terminator`) stay as **direct** tests of
`combine` / `trim_blank_lines` in `context.rs` (they already exercise the shared
rule; they need not be duplicated per source).

**`cli/config/src/error.rs`** — `invalid_skill_name_names_the_offending_name`,
`unsafe_path_names_the_offending_path`.

**`cli/config-adapters/src/store.rs`**:

- `an_absent_skill_context_reads_as_none`
- `a_team_skill_context_reads_its_body`
- `a_personal_skill_context_reads_its_body`
- `a_skill_context_body_strips_its_frontmatter_mapping`
- `a_skill_context_without_frontmatter_returns_the_whole_content`
- `a_skill_context_opening_with_a_thematic_break_is_preserved`
  (`---\nSection A\n---\nSection B\n` → whole file is body)
- `a_skill_context_with_non_mapping_frontmatter_is_injected_whole`
- `an_empty_frontmatter_fence_is_stripped` (`---\n---\nbody` → `body`)
- `a_crlf_thematic_break_body_round_trips_byte_exact` (guards against
  reconstructing the raw content from the `Split`)
- `a_malformed_skill_context_fails_loud_naming_the_path` (unterminated fence)
- `a_symlinked_skill_context_file_pointing_outside_is_refused`
- `a_symlinked_skill_directory_component_pointing_outside_is_refused`
- `a_sibling_prefix_directory_is_not_mistaken_for_containment` (a
  `.luminosity-evil/` sibling must not pass the `starts_with` check)
- `a_skill_context_under_a_symlinked_root_is_read` (roots under a symlinked
  temp dir — pins that the containment root is canonicalised)
- `a_symlink_to_a_nonexistent_target_reads_as_none`
- `the_skill_context_path_nests_under_skills` (asserting
  `.luminosity/skills/<name>/context.md` and `…/context.local.md`)
- `read_body_reports_the_path_it_read`

### Success Criteria

#### Automated Verification

- [x] Rust format and lint pass: `mise run cli:check`
- [x] Workspace unit tests pass: `mise run test:unit:cli`
- [x] The new domain tests pass in isolation:
      `cd cli && cargo nextest run -p config -E 'test(source) + test(context)'`
- [x] The new adapter tests pass in isolation:
      `cd cli && cargo nextest run -p config-adapters -E 'test(skill_context)'`
- [x] `mise run deny:check` passes (confirming no serde/YAML crate entered the
      `config` core's closure — the serde ban lives in `deny.toml`, not `pup.ron`)

#### Manual Verification

- [x] `cli/config/` still has no filesystem or serde dependency — `SkillName` and
      `ContextSource` are value objects; the path rule, the symlink check, and the
      mapping validation live entirely in `config-adapters`.
- [x] Every new public item carries the crate's standard: a `///` summary on
      every public struct/enum/trait, `#[derive(Debug, Clone, PartialEq, Eq)]`,
      `# Errors` on fallible fns, `const fn new`, `//!` module docs on `source.rs`,
      and a rewritten `//!` on `context.rs` describing any-source assembly.

---

## Phase 2: CLI surface

### Overview

Expose `luminosity context --skill=<name>`, rendering `## Project Context` then
`## Skill-Specific Context`, either omitted when empty, each degrading
**independently** under `--fail-safe`. This is the phase that makes the ordering
acceptance criterion structurally true — in a pure, unit-tested `join_blocks`
whose parameter order fixes the sequence.

Shippable on its own: `luminosity context --skill=configure` works from a
terminal before any skill injects it.

### Changes Required

#### 1. The command arguments

**File**: `cli/launcher/src/launch/inbound/cli.rs`
**Changes**: `Command::Context` grows a `skill` argument, and its own summary doc
comment is updated so `--skill` is discoverable from `luminosity --help` /
`luminosity context --help`.

```rust
/// Print the project-context block assembled from the config-file bodies,
/// and — with `--skill` — that skill's own `## Skill-Specific Context` block
/// after it. Prints nothing when no block survives.
Context {
    /// Also render this skill's own context block, from
    /// `.luminosity/skills/<name>/context.md` and `context.local.md`.
    #[arg(long)]
    skill: Option<String>,
    #[arg(long)]
    explain: bool,
    #[arg(long)]
    fail_safe: bool,
},
```

It is deliberately an `Option<String>`, **not** a clap `value_parser` over
`SkillName`. A `value_parser` rejection is a clap parse error, which exits
non-zero *before* `--fail-safe` is consulted — and a non-zero exit in an injected
command discards the whole prompt. The validation belongs inside the fail-safe
boundary.

#### 2. The renderers and the pure composition

**File**: `cli/launcher/src/context_command/inbound/cli.rs`
**Changes**: A second header+prose, a second renderer, a pure `join_blocks`, and
a `run` that assembles each source independently and degrades each
independently. Rewrite this module's `//!` doc, which currently claims it "owns
the byte-exact `## Project Context` block" and "owns the fail-safe policy" — it
now owns two blocks and an independent per-source degrade policy.

The skill prose interpolates the skill name via an **inline `format!` capture**
(not a stringly-typed `.replace`), so a placeholder typo is a compile error and
the literal stays a single scrapable string for the golden-pinning test:

```rust
fn skill_prose(skill: &SkillName) -> String {
    format!("\
The following context is specific to the {skill} skill. Apply this
context in addition to any project-wide context above.")
}

#[must_use]
pub fn render_project(context: &AssembledContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

#[must_use]
pub fn render_skill(skill: &SkillName, context: &AssembledContext) -> String {
    format!(
        "## Skill-Specific Context\n\n{}\n\n{}",
        skill_prose(skill),
        context.body
    )
}

/// Joins the surviving blocks with one blank line, in a fixed
/// project-then-skill order encoded by the parameters; `None` when neither
/// survives.
#[must_use]
pub fn join_blocks(
    project_block: Option<String>,
    skill_block: Option<String>,
) -> Option<String> {
    let blocks: Vec<String> =
        [project_block, skill_block].into_iter().flatten().collect();
    if blocks.is_empty() {
        None
    } else {
        Some(blocks.join("\n\n"))
    }
}
```

The order is now a property of `join_blocks`'s signature, not of a push-order a
future edit could silently swap — so the ordering criterion holds by
construction and its unit tests pin it below the process boundary.

`Options` carries the raw name; `run` parses it, so an invalid name becomes a
`ConfigError` handled by the fail-safe policy for the **skill** block alone:

```rust
#[derive(Debug, Clone)]
pub struct Options {
    pub skill: Option<String>,
    pub explain: bool,
    pub on_failure: OnFailure,
}
```

(`Options` can no longer derive `Copy` once it holds a `String`; `run` takes it
by `&Options`, side-stepping `needless_pass_by_value`.)

`run` builds each block through a small per-source helper that maps a source to
`Ok(Some(block))`, `Ok(None)`, or — under `Degrade` — its own unavailable
notice; passes the project and skill results as the two ordered `join_blocks`
arguments; and prints the result once, printing **nothing** when `join_blocks`
returns `None` (so exactly one blank line separates the blocks, exactly one
terminating newline follows, and both-absent emits no stray blank line). Under
`OnFailure::Fail`, the first error propagates.

**Independent degradation** (the author decision from review): a failure in one
source never suppresses the other's healthy block, and each source degrades to
its *own* notice:

```rust
const SKILL_UNAVAILABLE_HEADER: &str = "## Skill-Specific Context Unavailable";

#[must_use]
pub fn render_project_unavailable(error: &ConfigError) -> String { /* as today */ }

#[must_use]
pub fn render_skill_unavailable(error: &ConfigError) -> String {
    format!("{SKILL_UNAVAILABLE_HEADER}\n\n{SKILL_UNAVAILABLE_PROSE}\n\n{error}")
}
```

The skill file is named by the `ConfigError`'s own path, so
`render_skill_unavailable` takes only the error (no unused `skill_name`
parameter, which would fail `-D warnings`); the header is a `const` so the
literal stays within 80 columns. So a malformed
`.luminosity/skills/configure/context.md` still prints the healthy
`## Project Context` block, followed by a `## Skill-Specific Context Unavailable`
notice whose error names the skill file — never the misleading
`## Project Context Unavailable`. An invalid `--skill` name degrades the same
way (its `InvalidSkillName` error names the offending value): a skill notice, the
project block intact.

#### 3. The `--explain` diagnostic

**File**: `cli/launcher/src/context_command/inbound/cli.rs`
**Changes**: `--explain` prints the discovered project root once (absolute), then
one line per level **in the established `<level> (<path>): <state>` grammar**,
each path rendered **relative to that root** (so the one absolute path is the
`root:` line and the level lines stay short and unambiguous). When `--skill` is
absent, only the two project-level lines print.

```
root: /Users/x/proj
team (.luminosity/config.md): discovered, body present
personal (.luminosity/config.local.md): not found
team (.luminosity/skills/configure/context.md): discovered, body present
personal (.luminosity/skills/configure/context.local.md): not found
```

Two specifics the diagnostic must honour:

- **Relative paths.** `LevelContribution.path` is the adapter's `display(&path)`,
  which is absolute; the renderer strips the root prefix for the level lines.
  Because the assembler carries the real path per level, the launcher never
  rebuilds the `skills/<name>/<file>` shape — closing the path-rule-duplication
  gap. (The `root:` line prints only the path; no `(.git marker)` suffix —
  `discover` does not report which marker matched, and the path alone answers
  "rooted where".)
- **Explain survives a degrade — two sub-cases.** When a source *errors* under
  `--fail-safe` there is no `Assembly`, so `--explain` must still say something
  useful, but the two failure shapes differ and the contract splits accordingly:
  - **A read/unsafe failure of a *valid* name** (malformed `context.md`, a
    refused symlink, an I/O error): surface the source's two attempted paths with
    an `unreadable` / `unsafe` state. The paths come from a pure adapter query
    `context_paths(&ContextSource) -> [PathBuf; 2]` (the same function
    `context_path` is built from — so the path rule stays single-sourced and the
    launcher still never rebuilds the `skills/<name>/<file>` shape).
  - **An `InvalidSkillName` degrade** (the raw value never parsed, so *no* path
    was ever constructed): print a single name-only line — `skill: invalid name
    '<value>' — expected non-empty alphanumeric, '-', or '_'` — and no path
    lines. Fabricating a `skills/../../etc/context.md` line for a value the CLI
    deliberately never touched would be both misleading and the very path-rebuild
    the design forbids.

#### 4. Dispatch and composition root

**File**: `cli/launcher/src/launch/mod.rs`
**Changes**: `dispatch` **stays at its current six positional collaborators**.
The generalisation replaces the existing `context: &impl AssembleProjectContext`
parameter with `context: &impl AssembleContext` in the same slot — it adds no
parameter — and 0018 adds a renderer, not a dispatch port. So the
`too_many_arguments` pressure that a parallel-domain design would have created
never arises, and no `Ports` bundle is introduced (it would repackage the same
five bounds behind a struct for no gain). `dispatch` threads the raw `skill` into
`context_cli::Options` and passes the single `AssembleContext` port; one
assembler serves both sources because the source selects the document.

**File**: `cli/launcher/src/main.rs`
**Changes**: A `LazyContextBody` implementing `ReadContextBody` over
`discover_store()` (mirroring `LazyConfigBody`); a `ContextAssembler::new(...)` in
`run`, passed to `dispatch`. `is_root_help`'s hard-coded list (`:130-136`) needs
no change.

### Tests (write first)

**`cli/launcher/src/context_command/inbound/cli.rs`** (unit — the byte-exact and
composition invariants, below the process boundary):

- `renders_the_byte_exact_project_block` (unchanged behaviour, renamed)
- `renders_the_byte_exact_skill_block`
- `the_skill_block_interpolates_the_skill_name`
- `the_skill_block_ends_at_the_last_body_byte`
- `join_blocks_orders_project_before_skill_with_one_blank_line`
- `join_blocks_of_a_single_survivor_is_that_block` (project-only and skill-only)
- `join_blocks_of_neither_is_none`
- `each_contribution_shape_renders_a_distinct_explain_line`
- `the_skill_unavailable_notice_names_the_skill_file_and_not_project`

**`cli/launcher/tests/context.rs`** (black-box, against the compiled binary):

- `a_team_skill_context_prints_the_skill_block`
- `a_personal_skill_context_prints_the_skill_block`
- `both_skill_levels_join_team_first_with_one_blank_line`
- `the_skill_block_follows_the_project_block_with_one_blank_line` — ordering
- `a_skill_block_with_no_project_context_is_the_only_block` — absent-global
- `a_skill_context_with_no_skill_flag_is_not_printed`
- `an_absent_skill_context_prints_only_the_project_block`
- `an_empty_skill_context_prints_only_the_project_block`
- `both_absent_prints_nothing_and_exits_zero`
- `surrounding_blank_lines_leave_no_leading_or_trailing_blanks`
- `a_skill_context_frontmatter_mapping_is_not_injected`
- `a_skill_context_thematic_break_body_is_injected_whole`
- `an_unknown_skill_name_prints_only_the_project_block` — silence, not an error
- **`an_invalid_skill_name_under_fail_safe_still_prints_the_project_block`** — the
  load-bearing one: `--skill=../../etc --fail-safe` exits 0, keeps the project
  block, appends a skill notice — it must **not** kill the prompt
- `an_invalid_skill_name_without_fail_safe_exits_non_zero`
- `a_malformed_skill_context_under_fail_safe_still_prints_the_project_block`
- `a_malformed_skill_context_names_the_skill_file_in_its_notice`
- `a_malformed_config_under_fail_safe_still_prints_the_skill_block`
- `both_sources_malformed_under_fail_safe_print_both_notices`
- `a_malformed_skill_context_without_fail_safe_fails_loudly`
- `explain_reports_the_root_and_both_skill_levels`
- `explain_surfaces_the_attempted_paths_when_a_valid_named_source_degrades` (a
  malformed skill context still yields the two skill path lines, via
  `context_paths`)
- `explain_reports_an_invalid_skill_name_as_a_single_name_only_line` (no path
  lines — the path was never constructed)
- `explain_without_a_skill_reports_only_the_config_levels`
- `help_describes_the_skill_flag`

### Success Criteria

#### Automated Verification

- [x] Rust format and lint pass: `mise run cli:check`
- [x] Workspace unit tests and the black-box suite pass: `mise run test:unit:cli`
- [x] The context black-box suite passes in isolation:
      `cd cli && cargo nextest run -p luminosity -E 'test(context)'`

#### Manual Verification

- [x] In a scratch repo with a `.luminosity/skills/configure/context.md`,
      `luminosity context --skill=configure` prints the project block then the
      skill block, separated by exactly one blank line, with no trailing blank.
- [x] `luminosity context --skill=configure --explain` prints the root and the
      four files' root-relative paths, and still prints the skill lines when the
      skill context is malformed.
- [x] `luminosity context --skill=../../etc --fail-safe` exits **0**, still
      prints the project block, and appends a `## Skill-Specific Context
      Unavailable` notice — confirming a bad name cannot discard a prompt or the
      other block.
- [x] `context_command/inbound/cli.rs`'s `//!` is rewritten to describe two
      blocks and the independent per-source degrade policy, and every new public
      item (`join_blocks`, `render_skill`, `render_skill_unavailable`) carries a
      `///` summary — there is no `missing_docs` lint to catch a miss.

---

## Phase 3: Skill wiring, contract test, and the configure surface

### Overview

Point the `configure` skill's injection line at the skill-aware command, upgrade
the registry-walking contract test to a per-skill template that also guards the
frontmatter-name allow-list, document the capability on the skill's surface, and
git-ignore the personal file with an automated check.

### Changes Required

#### 1. The injection line

**File**: `skills/config/configure/SKILL.md`
**Changes**: Line 16 becomes

```markdown
!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill=configure --fail-safe`
```

The `--skill=<name>` **equals form** is deliberate: a bare `--skill <name>` would
let a name beginning with `-` be parsed by clap as an option (a non-zero exit
*outside* the fail-safe boundary, discarding the prompt), whereas `--skill=<name>`
always binds the value. The injection point stays **above** the skill's binding
constraints (per Security and trust boundary). `allowed-tools` is unchanged: the
existing `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)` grant already
covers it.

#### 2. The configure surface

**File**: `skills/config/configure/SKILL.md`
**Changes**: A `## Managing skill-specific context` section after
`## Managing project context`, in the same register (editing framed as a **user**
action). It must contain, and the tests must assert, all of:

- both source paths, using the concrete skill name (`.luminosity/skills/configure/context.md`
  team/committed and `.luminosity/skills/configure/context.local.md`
  personal/git-ignored);
- the naming rule: the `<skill-name>` is the name the skill is **invoked by**
  (its frontmatter `name:`), *not* the `skills/config` category directory;
- that the nested directory is created by hand, and a wrong/mistyped name emits
  **nothing** rather than an error;
- to avoid opening a context file with an *unterminated* `---` line: a leading
  fence with no closing `---` is read as an open frontmatter block and degrades
  the block (a terminated `---…---` block whose content is not YAML is preserved
  whole, so the hazard is specifically the unterminated case);
- `${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill=configure --explain` as
  the diagnostic that shows the root and the exact paths.

Any command the section shows uses the `${CLAUDE_PLUGIN_ROOT}/bin/` prefix and
the `--skill=<name>` equals form, matching the existing `## Managing project
context` section's copy-pasteable style. That section's "run `luminosity
context`" line gains the `--skill=` form.

#### 3. Git-ignore the personal level

**File**: `.gitignore`
**Changes**: Mirror the existing `config.local.md` pair — the ignore rule plus the
eval-fixture negation.

```gitignore
**/.luminosity/skills/**/context.local.md
!tests/evals/skills/configure/fixtures/**/context.local.md
```

#### 4. The contract test

**File**: `tests/unit/skills/test_context_injection.py`
**Changes**: `INJECTION_LINE` becomes an `INJECTION_TEMPLATE` constant plus a
private `_injection_line(skill_name)` helper. The strengthening that matters:
**derive the expected name from the SKILL.md's own frontmatter `name:` field**,
assert it matches the Rust allow-list `^[A-Za-z0-9_-]+$` (so an unrepresentable
name fails at CI, not at runtime — see Key Discoveries), and assert the injected
`--skill` argument equals it.

```python
INJECTION_TEMPLATE = (
    "!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context "
    "--skill={skill} --fail-safe`"
)


def _injection_line(skill_name: str) -> str:
    return INJECTION_TEMPLATE.format(skill=skill_name)
```

The registry walk, the vacuity guard, the under-the-H1-before-the-first-`##`
placement assertion, and the `allowed-tools` assertion all stay as they are.

### Tests (write first)

- `test_carries_the_exact_injection_line` — parametrized over the discovered
  skills, expecting `_injection_line(<frontmatter name>)`
- `test_the_frontmatter_name_satisfies_the_skill_name_allow_list` (new — the
  Python mirror of `SkillName::parse`)
- `test_the_frontmatter_name_matches_the_skill_directory_name` (new — pins the
  name a user types to the directory they create)
- `test_line_sits_under_the_h1_before_any_subsection` (unchanged behaviour)
- `test_allowed_tools_grants_the_context_command` (unchanged)
- `TestConfigureSurface::test_carries_the_managing_skill_context_section`
- `TestConfigureSurface::test_names_both_skill_context_paths_as_the_source`
- `TestConfigureSurface::test_states_the_naming_rule_and_the_silence_caveat`
- `test_gitignore_hides_personal_but_tracks_team` (new — shells `git check-ignore`
  for a team and a personal file, both inside and outside the eval fixtures, and
  asserts the exact ignore/track outcome for each — the personal file ignored, the
  team file tracked)

### Success Criteria

#### Automated Verification

- [x] Skill-wiring tests pass: `mise run test:unit:skills`
- [x] A single test runs green:
      `uv run pytest tests/unit/skills/test_context_injection.py -v`
- [x] `git check-ignore -v .luminosity/skills/x/context.local.md` reports the new
      rule, and `git check-ignore` does **not** match
      `tests/evals/skills/configure/fixtures/*/.luminosity/skills/configure/context.local.md`
      nor any `context.md`

#### Manual Verification

- [x] The rendered `configure` skill reads coherently: project context, then
      skill-specific context, then the skill's own prose.
- [x] The new surface section frames editing as a user action, states the naming
      rule, and warns that a wrong name is silent.

---

## Phase 3a: Record the decision (ADR)

Rides with Phase 3 (a documentation deliverable, no code). ADR-0003 committed that
the per-skill extension surfaces "will be recorded as their own decisions when
built," and its layout description shows only a single-file per-skill
`context.md`. This story builds that surface and diverges from the accelerator
twice — a two-level personal `context.local.md`, and frontmatter stripping — so
the durable record must be produced by this story, not left to the work-item note.

### Changes Required

Raise a **short successor ADR** via `/accelerator:create-adr` recording the two
divergences (two-level per-skill context; frontmatter stripped) and the two-level
`.luminosity/skills/<name>/` layout, referencing ADR-0003. Because Luminosity
treats accepted ADRs as immutable (only proposed ADRs are edited; accepted ones
transition to superseded/deprecated), a successor is the mechanism; the author may
instead choose a non-substantive editorial amend to ADR-0003 if the team treats
layout descriptions as living — but *some* record ships. No ADR-0003 in-body
citation fix is needed: its "ADR-0020" references already sit unambiguously inside
the accelerator-adoption context (verified).

### Success Criteria

#### Automated Verification

- [x] A proposed successor ADR (or an amended ADR-0003) exists in
      `meta/decisions/`, recording the two-level per-skill layout and the
      frontmatter-stripping divergence, and referencing ADR-0003.
      (`ADR-0012-two-level-per-skill-context-with-frontmatter-stripped.md`)

---

## Phase 4: Eval coverage (CI tier)

### Overview

Extend the existing `context` eval capability — fixtures, dataset rows, scorer
argv, and the golden-pinning chain — and **close the two chain gaps review found**:
pin the block composition (not just the prose) to the Rust source via a CI pytest
that runs the compiled binary, and pin the committed live-eval log against the
current dataset so a stale log cannot pass. **No new capability module**, so no
new billed arm and no widening of the three exact-list tripwires.

### Changes Required

#### 1. Unblock nested fixtures

**File**: `tests/evals/skills/configure/solvers.py`
**Changes**: `_seed` (`:83-89`) does a flat `glob("*")` + `shutil.copy` and raises
`IsADirectoryError` on a nested `skills/` dir. Replace it with
`shutil.copytree(source, workdir / ".luminosity")` **and remove the preceding
`destination.mkdir()`** (copytree creates the destination; it raises
`FileExistsError` if it already exists).

#### 2. Fixtures

**Files**: `tests/evals/skills/configure/fixtures/…` (new)

| Fixture | Contents | Scenario it pins |
|---|---|---|
| `context_skill_team_only` | `skills/configure/context.md`, with surrounding blank lines | skill block alone; blank-line trimming |
| `context_skill_both_levels` | `skills/configure/context.md` + `context.local.md` | team-then-personal combination |
| `context_global_and_skill` | `config.md` + `skills/configure/context.md`, each carrying a *distinguishable* declarative convention | global-then-skill ordering, both blocks reaching the model |
| `context_skill_empty` | whitespace-only `skills/configure/context.md` | no block emitted |
| `context_skill_behavioural` | `skills/configure/context.md` carrying a declarative terminology convention | the block reaches the model |

The four existing fixtures carry no `skills/` dir, so they now double as the
"per-skill context absent" coverage at no extra cost. Fixtures are authored LF-only
(a `.gitattributes` `text eol=lf` entry for `tests/evals/**/fixtures/**` guards it),
so the Python trim model and the Rust trimmer cannot disagree on a trailing `\r`.

The behavioural bodies must read as **declarative project context** (a convention
the agent applies), not an imperative "emit this token" — the existing dataset
test documents why (`test_context_dataset.py:157-161`): the model recognises the
imperative form as a prompt injection and refuses it, failing the arm for a reason
unrelated to injection.

#### 3. Dataset rows

**Files**: `tests/evals/skills/configure/context_dataset.json` and a new
`context_behavioural_dataset.json`
**Changes**: Five new records join `context_dataset.json`, the deterministic ones
carrying an `expected_block` golden — this file is the source for the CI render
test below. Separately, the **live** arm is pointed at a
`context_behavioural_dataset.json` holding only the two behavioural rows
(`context_global_and_skill`, `context_skill_behavioural`) — they are the arms
that prove both blocks reach the model in order. `context_eval.py` loads the
behavioural file for `configure_context_with_skill` (an explicit change, not an
in-scorer filter, documented in a one-line comment at the load site so a
maintainer sees which file the billed run reads and why), so only two arms run
billed, and the stale-log gate below has a single source of truth for "the graded
subset". The deterministic rows are graded by the CI render pytest, never by
billed trials.

To keep the billed copy honest, `context_behavioural_dataset.json` gets the same
structural guards the main dataset has: every row parses and carries its required
fields, its sentinel is present in the referenced fixture body, and each
behavioural row equals its `context_dataset.json` twin (so a drift or typo fails
in free CI, not mid-billed-run). `context_global_and_skill` carries **two**
sentinels — a project-convention token and a skill-convention token — and
`grade_behaviour` requires **both** present in the transcript, so the arm that
exists to prove "both blocks reach the model" actually asserts it rather than
clearing on one.

#### 4. Scorer argv

**File**: `tests/evals/skills/configure/context_scorer.py`
**Changes**: `_grade` hard-codes `_exec(["context"], …)` (`:74`). The skill now
injects `context --skill=configure --fail-safe`, so the scorer must re-execute
**exactly that** — the injected argv verbatim, including `--fail-safe`, so the
graded command is the shipped command on both the healthy and failure paths.
Extract the argv to a module constant so it is scrapable.

```python
SKILL = "configure"
SCORER_ARGV = ["context", f"--skill={SKILL}", "--fail-safe"]
...
result = await _exec(SCORER_ARGV, workdir=metadata["workdir"])
```

#### 5. Extend and repair the golden-pinning chain

**File**: `tests/unit/evals/skills/configure/test_context_dataset.py`
**Changes**:

- A `SKILL_BLOCK_PREFIX`, pinned against the Rust `skill_prose` literal and the
  `render_skill` header. Because `render_skill` now uses an inline `{skill}`
  capture and a plain header literal (no positional-only anchor), one generalised
  header scraper — parametrised by the prose-anchor name — pins **both**
  renderers; the scraper substitutes the skill name into the `{skill}` token.
- A `BLOCK_SEPARATOR = "\n\n"` pinned against `join_blocks`'s Rust join, so
  `_expected_block` composes the project and skill blocks from the **Rust
  separator**, not a hard-coded Python literal.
- Each dataset row **declares the source files** its scenario carries (e.g. a
  `sources` list). `_body(fixture, relative_path)` is generalised to take a path
  under `.luminosity/`, return the whole file when it has no frontmatter mapping
  (mirroring the adapter), and **raise on a missing file**; `_expected_block` calls
  it only for a scenario's *declared* sources, so a mis-pathed fixture raises
  loudly instead of degrading a scenario to "no context" — and single-level
  fixtures no longer break the both-levels composition path.
- `_trim` normalised to strip a trailing `\r` on the last kept line, matching the
  Rust trimmer exactly.

**File**: `tests/unit/evals/skills/configure/test_context_render.py` (new)
**Changes**: A CI-tier test that runs the compiled `luminosity` binary with
`SCORER_ARGV` against each fixture directory and byte-compares stdout against the
dataset golden, **reusing `grade_block`'s newline/empty semantics** (a non-empty
block prints with exactly one trailing `\n` while the golden carries none; an
empty scenario prints nothing). Its purpose is fixture↔golden coherence at the CI
tier (previously only checked in the live scorer) — complementary to
`context.rs`, which already proves composition against the binary. It resolves the
binary via `host_binary_path()` (the release artifact `build:launcher` produces)
rather than `LUMINOSITY_EVAL_PLUGIN_DIR` (unset at this tier), resolving through
the existence-checking helper so an absent artifact yields the actionable "run
`mise run build:launcher`" message (or a clean skip) instead of a raw
`FileNotFoundError` when the test is run standalone. Add `build:launcher` to
`test:unit:evals`'s `depends`. **This is a cost-profile change** — the eval-logic
tier was build-free ("costs nothing"); it now pulls a host-native release build,
so update `tasks/README`'s shape description to say so (and note that `check`
stays build-free, since it excludes the `test` roll-up). Include a
both-sources-present-and-absent matrix.

**File**: `tests/unit/evals/skills/configure/test_results.py`
**Changes**: Add an assertion pinning each committed log to the **behavioural**
dataset (its single source of truth) — `{sample scenario names} == {behavioural
dataset scenario names}` **and** `total_samples == len(behavioural_dataset) *
TRIALS` (both halves reference the same subset, so the gate is internally
consistent) — so a behavioural dataset that grows past the committed evidence
turns the gate red instead of leaving it green.

### Tests (write first)

- `test_skill_block_prefix_matches_the_rust_source`
- `test_the_skill_prose_interpolates_the_skill_name`
- `test_the_block_separator_matches_the_rust_join_blocks`
- `test_the_scorer_argv_matches_the_skill_injection_line` (scrapes the `!`-line out
  of `SKILL.md` and asserts `SCORER_ARGV` reproduces it — pins the new mirror)
- `test_deterministic_golden_matches_the_fixture_body` — extended to the new
  scenarios
- `test_global_and_skill_orders_project_before_skill_with_one_blank_line`
- `test_skill_empty_expects_no_skill_block`
- `test_skill_both_levels_orders_team_before_personal_within_the_block`
- `test_every_scenario_fixture_file_exists_on_disk` (the dataset vacuity guard)
- `test_a_mispathed_declared_source_raises` (pins `_body`'s raise-on-missing)
- `test_the_behavioural_dataset_rows_match_their_main_dataset_twins` (guards the
  billed copy against drift)
- `test_global_and_skill_carries_two_sentinels_present_in_both_bodies`
- `test_one_case_per_scenario` — `_SCENARIOS` grows the five new names
- `test_context_render.py::test_binary_output_matches_each_golden` (every fixture,
  both-present-and-absent matrix, via `host_binary_path()`)
- `test_results.py::test_the_committed_log_covers_the_behavioural_dataset`
- `tests/unit/evals/skills/configure/test_solvers.py` — seeds a fixture carrying
  `.luminosity/skills/configure/context.local.md`, then asserts the file landed at
  `workdir/.luminosity/skills/configure/context.local.md` with the fixture's
  content and that `workdir/.git` exists (placement and content, not merely
  "did not raise")

### Success Criteria

#### Automated Verification

- [x] Eval-logic tests pass: `mise run test:unit:evals` — with the single
      deliberate exception of `test_the_committed_log_covers_the_behavioural_dataset`,
      which is red *by design* until Phase 5's live run replaces the stale log.
- [x] The three exact-list tripwires stay green **without modification** —
      `capabilities("configure") == ["context", "values"]` in
      `tests/unit/tasks/shared/eval/test_run.py`, plus `test_collection.py` and
      `test_results.py`: `mise run test:unit:tasks`
- [x] Python format, lint, and types pass: `mise run check`

#### Manual Verification

- [x] Each new fixture's `.luminosity/skills/configure/context.local.md` is
      actually tracked by git (the `.gitignore` negation from Phase 3 works).

---

## Phase 5: Live eval run

### Overview

The eval-coverage acceptance criterion is only satisfied by a committed result log
— `test_results.py` `pytest.fail`s until one exists for every graded arm. This is
a live, **billed** `claude -p` run, as story 0016's was. Only the two behavioural
arms (`context_global_and_skill`, `context_skill_behavioural`) run live; the
deterministic scenarios are graded by the Phase 4 CI pytest, so the marginal
billed cost is two arms × `TRIALS`, not five.

### Changes Required

**Command**: `mise run eval:skills:configure`
**Files**: `tests/evals/skills/configure/results/*.json` (new logs, scrubbed of
host paths by `readback.scrub_result_dir`)

The run drives the real `claude -p` against the staged plugin in a seeded temp
workdir, then re-executes the real compiled `luminosity` binary in that same
workdir with the injected argv and byte-compares stdout against the goldens. Gated
at `PASS_K_FLOOR = 0.8` over `TRIALS = 3`.

### Success Criteria

#### Automated Verification

- [x] `mise run eval:skills:configure` exits 0 (every behavioural arm clears the
      pass^k floor) — both context arms at pass^k 1.000 (6/6 samples).
- [x] The committed-log assertions pass, including the new dataset-coverage pin:
      `mise run test:unit:evals`
- [x] No absolute host paths leak into the committed logs (asserted by
      `TestCommittedLog::test_carries_no_absolute_host_path`)

#### Manual Verification

- [x] The `context_global_and_skill` transcript shows the agent applying **both**
      the project-wide and the skill-specific convention — proving both blocks
      landed, in order. (The agent wrote "How configuration works here
      (**Lantern**) … resolved across two **Tiers**" — `Lantern` comes only from
      the project body, `Tier` only from the skill body.)
- [x] Inspect the run in the log viewer: `mise run eval:view -- --skill configure`

#### Two grading defects the first run exposed (fixed, then re-run)

Both were flaws in the *grader/fixtures*, not in injection — in every failing
sample the block had demonstrably landed:

1. **Case-sensitive sentinels.** An agent that applied the skill convention and
   wrote "resolved across two **tiers**" scored incorrect purely on
   capitalisation. A sentinel asserts a terminology *convention*, and English
   prose lower-cases a term used as a common noun, so `grade_behaviour` now
   matches case-insensitively.
2. **A prompt that did not reliably trigger the skill.** Injection fires at skill
   *load*, so an agent that never invokes the skill never receives the block.
   "Briefly describe how configuration levels work" sent the agent
   filesystem-spelunking until it exhausted `MAX_TURNS`. Both behavioural rows now
   lead with the explicit config read that story 0016's proven prompt used, which
   routes the agent through the skill.

---

## Phase 6: Full local CI mirror

### Overview

"Done" means the bare `mise run` default task exits 0 end-to-end. This is the
final gate; `mise run` must already have been green at the end of every prior
phase.

### Success Criteria

#### Automated Verification

- [x] `mise run fix` applies cleanly (formatters and safe lint fixes)
- [x] `mise run check` exits 0 (format + lint + types across all components, plus
      `deny:check` / `pup:check`)
- [x] `mise run` exits 0 end-to-end — the full local CI mirror, including
      `build:launcher` and the whole test suite with coverage

#### Manual Verification

- [x] No stray comments explaining what the code already says (the repo's standing
      bar).

---

## Testing Strategy

The three toolchains each guard a different seam, and the division is deliberate:

**Rust unit tests (`cli/config/`, `cli/config-adapters/`)** — the domain rules.
Level combination, blank-line trimming, frontmatter mapping-only stripping,
skill-name validation, path construction, symlink refusal, and error propagation.
Exhaustive here because it is free: no process spawn, no agent, no tokens.

**Rust unit tests (`cli/launcher/src/context_command/`)** — the render and
composition invariants. The byte-exact blocks, the pure `join_blocks`
(both/one/none/ordering),
the independent-degrade notices, and the `--explain` line grammar — pinned below
the process boundary so the ordering criterion is not carried by black-box alone.

**Rust black-box tests (`cli/launcher/tests/context.rs`)** — the compiled binary's
contract. Every level and ordering permutation, the empty-output policy, and the
independent fail-safe boundary at each source. Each test gets a temp workdir
carrying a `.git` marker so `FileConfigStore::discover` roots inside the fixture
(load-bearing: `CARGO_TARGET_TMPDIR` resolves inside the repo, so without the
marker the walk would escape upward).

**Python skill-wiring tests (`tests/unit/skills/`)** — that the injection line
exists, in the right place, with the right and *representable* skill name, in
**every** registered skill, and that the personal file is git-ignored while the
team file is tracked. The only tier that can see the SKILL.md source.

**Python eval-logic tests (`tests/unit/evals/`)** — that the goldens have not
drifted from the Rust literals (prose, header, and separator), that the compiled
binary's stdout matches the goldens for every fixture (`test_context_render.py`),
and that the committed live log still covers the current dataset. Runs in CI;
costs nothing.

**The live eval (`mise run eval:skills:configure`)** — that injection actually
reaches the model through the real Claude Code preprocessor, for the two
behavioural arms. Excluded from CI for token cost; run once per story and its log
committed.

### The edge cases that matter most

1. **A `--skill` name that fails validation, under `--fail-safe`.** Must exit 0,
   keep the project block, and append a skill notice. If it exits non-zero the
   prompt is discarded — the single worst failure mode in this design.
2. **A malformed `context.md` under `--fail-safe`.** Same: the project block still
   prints; the skill degrades to its own correctly-named notice, never the
   project one.
3. **No project context, but a skill context.** The skill block must be the first
   injected block at the same structural point, not shifted or omitted.
4. **A `context.md` whose first line is `---`.** A terminated fence whose content
   is not a YAML mapping (a thematic break) is preserved whole; a valid mapping is
   stripped; an unterminated fence fails loud.
5. **A committed symlink at the skill path** — a symlinked `context.md` file *or*
   a symlinked `skills/<name>/` directory component whose target escapes
   `.luminosity`. Refused with `UnsafePath` (both sides canonicalised so a
   legitimate file under a symlinked root such as macOS `/tmp` is *not* refused),
   degrading under `--fail-safe` to a skill notice — never followed to its target.
   A symlink to a non-existent target reads as `Ok(None)`.

## Migration Notes

None. Per-skill context is purely additive: no `.luminosity/skills/` directory
exists in any repository today, and every existing behaviour of `luminosity
context` (with no `--skill`) is unchanged, which the existing black-box suite
already pins. The generalisation renames internal ports/types (`ProjectContext` →
`AssembledContext`, `AssembleProjectContext` → `AssembleContext`, `ReadConfigBody`
for context → `ReadContextBody`) but changes no on-disk format and no CLI
contract.

One naming tension is deliberately **left for a follow-up**, not resolved here:
the crate is still `config` and errors still surface as `ConfigError`, though the
domain has generalised beyond configuration to all `.luminosity/` two-level
documents. Renaming the crate/error taxonomy is out of scope for this story; noted
so 0018 (a third document kind) can decide whether the names should track the
generalised domain.

## References

- Work item: `meta/work/0017-per-skill-context-injection.md` (amended 2026-07-13
  for the two-level model)
- Research: `meta/research/codebase/2026-07-13-0017-per-skill-context-injection.md`
- Plan review: `meta/reviews/plans/2026-07-13-0017-per-skill-context-injection-review-1.md`
  (REVISE — this plan revised in response)
- The sibling story's four-document trail, and the closest template for this one:
  `meta/work/0016-plugin-global-context-injection.md`,
  `meta/plans/2026-07-11-0016-plugin-global-context-injection.md`,
  `meta/validations/2026-07-11-0016-plugin-global-context-injection-validation.md`,
  `meta/prs/22-description.md`
- Successor: `meta/work/0018-per-skill-instructions-injection.md` — injects at the
  **end** of the body; under the generalised domain it adds a `ContextSource`
  variant, a path arm, and a renderer; should very likely gain an
  `instructions.local.md` for symmetry with the two-level model this story
  establishes
- ADR-0003 (`.luminosity/` layout and the multi-level config model), ADR-0009 (the
  hexagonal core), ADR-0001 (skills-vs-CLI division of labour), ADR-0011 (Inspect
  as the eval harness)
- Accelerator reference: `scripts/config-read-skill-context.sh`
