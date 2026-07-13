---
type: plan
id: "2026-07-11-0016-plugin-global-context-injection"
title: "Plugin-Global Additional Context Injection Implementation Plan"
date: "2026-07-11T19:17:39+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0016"
parent: "work-item:0016"
derived_from: ["codebase-research:2026-07-11-0016-plugin-global-context-injection"]
tags: [configuration, context-injection, rust-cli, skills, evals]
revision: "fd2a628df8f630d9f5a3b473e2253bdbe938a938"
repository: "luminosity"
last_updated: "2026-07-11T23:22:55+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Plugin-Global Additional Context Injection Implementation Plan

## Overview

Add a `luminosity context` reader that assembles the free-form Markdown bodies of
the team (`.luminosity/config.md`) and personal (`.luminosity/config.local.md`)
config files into a single `## Project Context` block, and inject that block near
the top of every registered skill prompt via the `!`-preprocessor. The reader
emits nothing when both bodies are empty or absent. The `configure` skill gains a
surface describing the capability, and the eval suite gains coverage of the four
injection scenarios plus a behavioural probe.

## Current State Analysis

The building blocks exist; the work is exposing and composing them.

- **Body extraction is already written and tested.** `frontmatter::split`
  (`cli/config-adapters/src/frontmatter.rs:21`) returns the body below the closing
  `---` and handles every edge case the acceptance criteria enumerate: first line
  not a fence → all-body (`:24-29`); only the first two fences delimit frontmatter
  (`:34-42`); body-internal `---` preserved; CRLF fences (`:49-55`); missing final
  newline. It is crate-private and returns the body untrimmed. Crucially, the
  reader's port is implemented **inside `config-adapters`**, so `split` needs no
  visibility change.
- **The read path discards the body.** `document::parse`
  (`cli/config-adapters/src/document.rs:30-33`) keeps only the frontmatter; the
  body is retained only on the write path via `preserved_body` (`:52-56`). There
  is no read path or domain type that surfaces a body.
- **Config resolution is a winner, not a merge.** `ConfigService::get`
  (`cli/config/src/service.rs:83-99`) resolves personal-over-team. Story 0016
  needs team-then-personal *concatenation* — a new domain operation sharing only
  file location/reading with the existing service.
- **File location and absent-file handling are reusable.** `FileConfigStore`
  (`cli/config-adapters/src/store.rs`) owns discovery (`:33-37,112-121`),
  team/personal filename selection (`:43-48`), and `NotFound → Ok(None)`
  (`:75-93`).
- **The hexagon + wiring pattern is established.** `version`
  (`cli/launcher/src/version/`) is a pure launcher-local hexagon; `config`
  (`cli/config/` + `cli/config-adapters/` + `cli/launcher/src/config_command/`)
  puts a domain core in a crate with a thin launcher inbound. Dispatch adds a
  `Command` arm (`cli/launcher/src/launch/mod.rs:32-42`), `main.rs:109-120`
  hard-codes built-in names in `is_root_help`, and new modules register in
  `cli/launcher/src/lib.rs`.
- **Skill injection is greenfield.** `.claude-plugin/plugin.json` registers one
  directory (`./skills/config/`); only `configure/SKILL.md` exists; no SKILL.md
  uses the `!`-preprocessor; there is no shared-partial mechanism.
- **The eval framework re-executes the real binary as source of truth.** Per-skill
  Inspect tasks (`tests/evals/skills/configure/`) run `claude -p` against a staged
  plugin, then grade by re-running `luminosity`. The `_seed` solver
  (`solvers.py:83-89`) copies every `.luminosity/*` fixture file, so body-bearing
  fixtures need no solver change. Every existing fixture is frontmatter-only. The
  existing scorer's "did the agent run the command" attribution
  (`scorer.py:113-137`) does not apply to passive injection.

### Key Discoveries

- `cli/config-adapters/src/frontmatter.rs:21` — the tested body-split primitive;
  reusable in-crate without exposing it.
- `cli/config-adapters/src/store.rs:75-93` — `ReadConfigLevel` impl to mirror for
  a new `ReadConfigBody` impl.
- `cli/config/src/service.rs:20-36` — the driven-port trait shape to follow.
- `cli/launcher/src/config_command/inbound/cli.rs` — the thin inbound (a pure
  `render` + a single `println!`) to mirror for the context inbound.
- `cli/launcher/src/launch/mod.rs:25-43`, `cli/launcher/src/main.rs:109-141`,
  `cli/launcher/src/launch/inbound/cli.rs:15-28` — the command-tree, dispatch,
  and composition-root seams to extend.
- `cli/launcher/tests/config.rs` — the black-box integration-test harness
  (`CARGO_BIN_EXE_luminosity`, per-test `.git`-rooted workdir) to mirror.
- `skills/config/configure/SKILL.md:9-11` — `allowed-tools` and the body to wire.
- `tests/evals/skills/configure/{solvers.py,scorer.py,dataset.json,configure_eval.py}`
  and `tests/unit/evals/skills/configure/` — the eval shape to extend.

## Desired End State

- `luminosity context`, run anywhere inside a project, prints the exact
  `## Project Context` block wrapping the trimmed team-then-personal bodies, or
  prints nothing (empty stdout, exit 0) when both bodies are empty or absent. A
  malformed config body is a loud, non-zero-exit error naming the file, not a
  silent no-op.
- `luminosity context --explain` prints the same stdout plus a per-level stderr
  diagnostic (config filename, discovered, body non-empty), so a user can tell why
  the block was empty.
- Every skill registered in `plugin.json` carries the injection line directly under
  its H1, before its own instructions, and grants the `context` command in
  `allowed-tools`; a test enforces both halves over the registry.
- The `configure` skill describes managing the plugin-global project context via
  the config-file bodies, framed as a user body-edit distinct from the CLI's
  `get`/`set`.
- The eval suite asserts the four injection scenarios byte-for-byte and probes the
  agent's behavioural response to injected context.
- `mise run` (the full local CI mirror) exits 0.

## What We're NOT Doing

- Not building a shared-partial / snippet-include mechanism for SKILL.md — the
  injection is a single canonical `!`-preprocessor line per skill, enforced by a
  registry test (decided). This is the deliberate choice for the whole
  0016/0017/0018 arc, not just this slice: 0017 (per-skill context) and 0018
  (per-skill instructions) each add their own canonical line the same way, and the
  registry test grows to enforce each. The `AssembleProjectContext::assemble(&self)`
  port models only the plugin-global case; 0017's per-skill context is expected to
  add a sibling assembler over the same `ReadConfigBody` port (or a keyed method),
  extending — not replacing — this hexagon.
- Not hardening against a hostile team config body. The body of the committed
  `.luminosity/config.md` is injected verbatim into every skill prompt, which is a
  cross-user prompt-injection channel in principle; mitigating it in the tool is
  out of scope — vetting incoming changes to the committed config is the team's
  responsibility, the same trust model as any other committed file (accepted).
- Not implementing per-skill context (0017) or per-skill instructions (0018);
  this story only establishes the shared reader, the placement anchor, and the
  wiring convention they build on.
- Not changing `ConfigService::get` precedence, the config get/set surface, or the
  write path.
- Not changing `tasks/shared/eval/staging.py` — injection is wired only into
  `skills/config/`, which staging already copies (`staging.py:18`).
- Not adding a `pup.ron` block — the new domain lives in the pure `config` crate,
  which pup does not govern (pup governs launcher-crate cores only).

## Implementation Approach

Follow the `config` hexagon shape, driven strictly by TDD (red → green →
refactor):

- A new driven port `ReadConfigBody` on the `config` core, implemented by
  `FileConfigStore` in `config-adapters` by reusing `frontmatter::split`.
- A `ProjectContext` value object and a `ProjectContextAssembler<R: ReadConfigBody>`
  service in the pure `config` crate that, in a single read pass, trims each level's
  body independently, drops any that trims to empty, joins the survivors
  team-then-personal with a single blank line (yielding no context when nothing
  survives), and reports what each level contributed. It returns an `Assembly`
  carrying the optional combined `ProjectContext` plus a per-level
  `discovered`/`has_body` record — the data the `--explain` diagnostic formats,
  computed with the *same* trim predicate as the merge so the two never disagree.
  This keeps the merge logic unit-tested against a fake reader.
- A thin launcher inbound that owns the byte-exact `## Project Context` header and
  prose in a total pure `render(&ProjectContext) -> String`, with the absent case
  handled once at the boundary (the reporter matches the `Option` and prints
  nothing for `None`).
- A `--explain` stderr diagnostic that reports, per level, the config filename,
  whether it was discovered, and whether its body was non-empty — leaving stdout
  unchanged — so a user can tell why the block was empty.
- Command wiring (`Command::Context { explain }`, dispatch, `is_root_help`,
  `lib.rs`).

The reader is **fail-loud**: a present-but-unsplittable config body propagates
`ConfigError::MalformedFrontmatter` to a non-zero exit with the offending file
named on stderr, matching the existing `config get` policy. Because the reader
runs at skill-load via the `!`-preprocessor, this means a malformed config
surfaces at skill invocation rather than being silently swallowed — the intended
behaviour (a broken config is a loud error to fix, not a silent degradation).

Contingency: if the Phase 2 manual verification finds the `!`-preprocessor renders
a non-zero exit opaquely, the fallback is **not** to degrade injection to empty
(which would hide a broken config from every skill). It is to keep the reader
fail-loud and lean on the direct `luminosity context` command — surfaced from the
configure surface — as the actionable diagnosis, since it names the offending file
regardless of how the preprocessor renders the failure.

The three phases are each a complete, green, mergeable increment. Phase 1 ships a
working command with no consumer. Phase 2 wires the (inert-until-invoked) line and
the surface. Phase 3 adds eval coverage. Phases 2 and 3 both depend only on
Phase 1 and are independent of each other; the behavioural arm in Phase 3 also
relies on Phase 2's line, which is why Phase 3 lands last.

---

## Phase 1: The `luminosity context` reader

### Overview

A `luminosity context` subcommand that assembles and prints the project-context
block. Delivered as a `config`-style hexagon: a driven port + domain service in
the pure crates, a thin launcher inbound, and command wiring. No consumer yet —
proven entirely by domain unit tests and black-box integration tests.

### Changes Required

#### 1. `ReadConfigBody` driven port (`config` core)

**File**: `cli/config/src/service.rs` (new trait alongside `ReadConfigLevel`)
**Changes**: Add a driven port that returns a level's raw body, or `None` when the
file is absent. Re-export from `cli/config/src/lib.rs`.

```rust
pub trait ReadConfigBody {
    /// # Errors
    ///
    /// [`ConfigError::MalformedFrontmatter`] or [`ConfigError::Io`] when a present
    /// file cannot be split or read.
    fn read_body(&self, level: Level) -> Result<Option<String>, ConfigError>;
}
```

#### 2. `ProjectContext` value object + assembler (`config` core)

**File**: `cli/config/src/context.rs` (new module; declared in `lib.rs`, exports
re-exported)
**Changes**: A value object holding the trimmed combined body, a driving port, and
the service that composes two levels. All pure; unit-tested with a fake
`ReadConfigBody`.

```rust
use crate::error::ConfigError;
use crate::level::Level;
use crate::service::ReadConfigBody;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectContext {
    pub body: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LevelContribution {
    pub level: Level,
    pub discovered: bool,
    pub has_body: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Assembly {
    pub context: Option<ProjectContext>,
    pub levels: [LevelContribution; 2],
}

pub trait AssembleProjectContext {
    /// # Errors
    ///
    /// A [`ConfigError`] when either level's body cannot be read.
    fn assemble(&self) -> Result<Assembly, ConfigError>;
}

pub struct ProjectContextAssembler<R> {
    reader: R,
}

impl<R> ProjectContextAssembler<R> {
    pub const fn new(reader: R) -> Self {
        Self { reader }
    }
}

impl<R: ReadConfigBody> AssembleProjectContext for ProjectContextAssembler<R> {
    fn assemble(&self) -> Result<Assembly, ConfigError> {
        ...
    }
}
```

`assemble` reads each level exactly once and returns both the combined block and
what each level contributed. `context` is `combine`'s output. Each
`LevelContribution` records `discovered` (the level's `read_body` yielded `Some`)
and `has_body` (the body survives `trim_blank_lines` non-empty — the *same*
predicate `combine` uses to decide survival, so a level's `has_body` can never
disagree with whether it appears in the block). This single-pass result is what the
`--explain` diagnostic formats — there is no second read path and no separate
`explain()` on the port. The diagnostic's *derivation* stays out of the pure core's
concerns (`assemble` reports what it read); only its human-readable *formatting*
lives in the launcher shell (`explain_lines`). `levels` is a fixed `[team, personal]`
array — the fixed arity encodes the exactly-two-levels domain, and the
team-then-personal ordering is an invariant `explain_lines` and the diagnostic tests
rely on (asserted: `levels[0].level == Team`, `levels[1].level == Personal`).

```rust
fn combine(team: &str, personal: &str) -> Option<String> {
    let parts: Vec<&str> = [team, personal]
        .into_iter()
        .map(trim_blank_lines)
        .filter(|part| !part.is_empty())
        .collect();
    if parts.is_empty() {
        None
    } else {
        Some(parts.join("\n\n"))
    }
}

fn trim_blank_lines(body: &str) -> &str {
    ...
}
```

Trim contract (spec, load-bearing): `trim_blank_lines` returns the substring
spanning the first through the last line that is *not* empty or whitespace-only,
with the outer line terminators fully removed (including a trailing `\r\n`);
interior lines — interior blank lines and the horizontal indentation of content
lines — are preserved byte-for-byte. A line consisting only of whitespace
(spaces, tabs, or a lone `\r`) counts as blank. Because `frontmatter::split`
preserves CRLF bodies verbatim, blank-line detection and terminator stripping
operate on bytes, not `str::lines()` (which silently drops `\r`).

`combine` trims each level's body independently, drops any that trims to empty,
then joins the survivors with a single `\n\n`. Trimming the two parts
*independently before joining* — not trimming the concatenation — is what
guarantees exactly one blank line between a non-empty team body and a non-empty
personal body regardless of either body's own trailing/leading blank lines. No
trailing terminator survives `combine`, so the reader's stdout ends in exactly
one `\n` — the one `println!` adds — satisfying the no-trailing-blank-line
criterion.

#### 3. `ReadConfigBody` adapter (`config-adapters`)

**File**: `cli/config-adapters/src/store.rs`
**Changes**: Implement `ReadConfigBody` for `FileConfigStore`. The existing
`ReadConfigLevel::read` impl and the new `read_body` share the same
`level_path → read_to_string → NotFound → Ok(None) → io_error` scaffolding and
diverge only in the final step (`document::parse` for the node vs `split.body`
for the body). Extract that scaffolding into a private
`read_raw(level) -> Result<Option<Split>, ConfigError>` (returning the parsed
`Split`, mapping a split failure to `MalformedFrontmatter`) and build both public
methods on it, so absent-file and IO-error semantics live in one place. `read`
then takes `split.frontmatter`, `read_body` takes `split.body`. Reuses the
in-crate `frontmatter::split` — no visibility change.

```rust
impl ReadConfigBody for FileConfigStore {
    fn read_body(&self, level: Level) -> Result<Option<String>, ConfigError> {
        Ok(self.read_raw(level)?.map(|split| split.body))
    }
}
```

`read_raw` propagates `ConfigError::MalformedFrontmatter` (naming the file) when a
present body cannot be split — the fail-loud path the reader relies on.

Lift the `Level → filename` mapping (`Level::Team => "config.md"`,
`Level::Personal => "config.local.md"`) off `FileConfigStore::level_path` and onto
the `Level` type as `Level::file_name()` (underscore-compound, matching the crate's
`level_path`/`config_dir` idiom and `std::path::Path::file_name`), so `level_path`
and the launcher's `explain_lines` share one source instead of two hand-copied
literals.

#### 4. Context inbound adapter (launcher)

**File**: `cli/launcher/src/context_command/inbound/cli.rs` (new), plus
`cli/launcher/src/context_command/{mod.rs,inbound/mod.rs}` and a
`pub mod context_command;` in `cli/launcher/src/lib.rs`.
**Changes**: A total pure `render` owning the byte-exact block, and a `report`
that handles absence once by matching the `Option`. `PROSE` is written so the
source reads the way the two output lines look (a leading `\`-continuation
suppresses the opening newline; the interior newline is literal).

```rust
use config::{
    AssembleProjectContext, ConfigError, LevelContribution, ProjectContext,
};

const PROSE: &str = "\
The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.";

#[must_use]
pub fn render(context: &ProjectContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}

/// # Errors
///
/// A [`ConfigError`] when a config body cannot be read.
pub fn report(assembler: &impl AssembleProjectContext) -> Result<(), ConfigError> {
    if let Some(context) = assembler.assemble()?.context {
        println!("{}", render(&context));
    }
    Ok(())
}
```

The `--explain` diagnostic writes to **stderr** and never touches stdout, so a
piped/injected `context` invocation is byte-identical with or without it. It
reports, per level, the config filename, whether the file was discovered, and
whether its body was non-empty. The diagnostic is derived in the shell from the
single `assemble()` pass — `report_explain` prints the block from
`assembly.context`, then formats `assembly.levels` to stderr via a pure
`explain_lines`. There is no second read and no second port method:

```rust
#[must_use]
pub fn explain_lines(levels: &[LevelContribution]) -> Vec<String> {
    ...
}

/// # Errors
///
/// A [`ConfigError`] when a config body cannot be read.
pub fn report_explain(
    assembler: &impl AssembleProjectContext,
) -> Result<(), ConfigError> {
    let assembly = assembler.assemble()?;
    if let Some(context) = &assembly.context {
        println!("{}", render(context));
    }
    for line in explain_lines(&assembly.levels) {
        eprintln!("{line}");
    }
    Ok(())
}
```

`explain_lines` names each level's file via a single-source `Level::file_name()`
(`Level::Team => "config.md"`, `Level::Personal => "config.local.md"`) — lifted
from `FileConfigStore::level_path` so the store and the diagnostic share one
mapping rather than a second hand-copied copy. On a **malformed** body,
`report_explain` propagates the fail-loud `MalformedFrontmatter` from
`assemble()?` before printing any per-level line: the user sees the offending
filename on stderr (the intended diagnosis), not the discovered/has-body lines.

The rendered block, byte-for-byte:

```
## Project Context

The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.

<combined team-then-personal body>
```

#### 5. Command wiring (launcher)

**Files**: `cli/launcher/src/launch/inbound/cli.rs`,
`cli/launcher/src/launch/mod.rs`, `cli/launcher/src/main.rs`.
**Changes**:

- Add a `Context { explain: bool }` variant to `enum Command`
  (`launch/inbound/cli.rs:15-28`) with a `--explain` flag and a doc line that
  states the empty-output contract, e.g. "Print the project-context block assembled
  from the config-file bodies (prints nothing when both bodies are empty or
  absent)."
- Thread a `&impl AssembleProjectContext` through `dispatch` and add the arm,
  branching on the flag (`launch/mod.rs`):
  `Command::Context { explain } => Ok(if explain { context_cli::report_explain(context)? } else { context_cli::report(context)? })`.
- Add `"context"` to the `is_root_help` built-in name list
  (`main.rs:113-119`).
- In `run` (`main.rs:132-141`), build the reader over a lazy body-reader that
  discovers the store per call (mirroring `LazyConfigAccess`), and pass it to both
  `dispatch` call sites:

```rust
struct LazyConfigBody;

impl config::ReadConfigBody for LazyConfigBody {
    fn read_body(
        &self,
        level: Level,
    ) -> Result<Option<String>, ConfigError> {
        discover_store()?.read_body(level)
    }
}
```

  (Refactor `discover_config_service` to reuse a `discover_store` helper.)

### Test Strategy (write first)

- **`config` core (unit, `context.rs`):** both-empty → `None`; both-absent (reader
  yields `None`) → `None`; a single whitespace-only body (blank/whitespace lines,
  distinct from the empty string) → `None`; team-only → team body; personal-only →
  personal body; both → `team\n\npersonal` (exactly one blank-line separator, even
  when each part carries its own trailing/leading blank lines); surrounding blank
  lines trimmed; interior blank lines and indentation preserved; a single-CRLF-body
  case asserts the exact resulting bytes (trailing `\r\n` stripped, interior
  preserved) **and** a two-CRLF-body join pins the LF `\n\n` separator against
  CRLF interiors; the assembled body ends with no trailing terminator; a
  **team**-level read error propagates *and* a **personal**-level read error
  propagates (both short-circuit branches); `assemble` reports per-level
  `discovered`/`has_body` (using the same `trim_blank_lines` predicate as `combine`,
  so `has_body` matches block membership) across absent / present-but-empty /
  present-with-content in one read pass, with `levels` in the fixed
  `[Team, Personal]` order (assert `levels[0].level == Team`,
  `levels[1].level == Personal`); a present-with-content team plus a
  present-but-whitespace personal yields the team body only with no trailing
  separator, and marks personal `discovered: true, has_body: false`.
- **`config` core (`level.rs`):** `Level::Team.file_name()` and
  `Level::Personal.file_name()` return `"config.md"` / `"config.local.md"` (pins the
  single-source mapping independently of its two consumers).
- **`config-adapters` (`store.rs`):** body returned untrimmed for a normal file;
  absent file → `None`; first-line-not-a-fence → whole content as body;
  unterminated frontmatter → `MalformedFrontmatter` (naming the file); `read` and
  `read_body` share `read_raw` (a normal file round-trips both frontmatter and
  body from one read).
- **Launcher inbound (unit):** `render(&ctx)` is the byte-exact block (assert the
  full literal, including the two prose lines and that it ends at the last body
  byte with no trailing newline); `explain_lines` renders a **distinct** line for
  each of the three `LevelContribution` shapes — absent (`discovered: false`),
  present-but-empty (`discovered: true, has_body: false`), and present-with-content
  (`discovered: true, has_body: true`) — so a mutation collapsing two shapes fails
  at the unit tier.
- **Black-box (`cli/launcher/tests/context.rs`, mirroring `config.rs`):** team
  body only; personal body only; both (team first, one blank-line separator); both
  empty → empty stdout, exit 0; no config dir at all → empty stdout, exit 0;
  bodies with surrounding blank lines → no leading/trailing blank lines in output
  (stdout ends in exactly one `\n`); a malformed config body → non-zero exit, empty
  stdout, the filename on stderr (mirroring `config.rs`'s malformed-file test);
  `context --explain` → block on stdout unchanged, per-level diagnostics on stderr;
  `context --explain` with one **absent** level and one **present-but-empty** level
  → empty stdout, exit 0, and stderr text that differs per level (the diagnostic's
  reason for being); resolves from a subdirectory; `context --help` succeeds.

### Success Criteria

#### Automated Verification

- [x] Workspace fmt + clippy pass: `mise run cli:check`
- [x] Domain + adapter + integration tests pass:
      `cd cli && cargo nextest run -p config -p config-adapters -p luminosity`
- [x] `luminosity context` byte-exact block is asserted by
      `cli/launcher/tests/context.rs` (run via the command above)
- [x] Full read-only CI mirror passes: `mise run check`
- [x] Host-native release build passes (bare default): `mise run`

#### Manual Verification

- [x] In a scratch repo, `.luminosity/config.md` and `config.local.md` with bodies
      → `luminosity context` prints the block, team first
- [x] Deleting both bodies (or the files) → `luminosity context` prints nothing
      and exits 0
- [x] A body with leading/trailing blank lines renders with none
- [x] A malformed config body → `luminosity context` exits non-zero with empty
      stdout and the filename on stderr
- [x] `luminosity context --explain` prints the block on stdout and the per-level
      discovery diagnostics on stderr; with empty/absent bodies, stdout is empty
      and stderr explains why

---

## Phase 2: Skill injection and the configure surface

### Overview

Wire the injection line into every registered skill (today: `configure`), enforce
it with a registry-iterating test, and expand the `configure` skill to describe
managing the plugin-global project context. Depends on Phase 1 (the command must
exist), but the line is inert text until a skill is invoked, so this phase is a
self-contained, mergeable increment.

### Changes Required

#### 1. Injection line in `configure/SKILL.md`

**File**: `skills/config/configure/SKILL.md`
**Changes**: Place the canonical line immediately under the `# Configure` H1,
before the first instructional prose:

```markdown
# Configure

!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context`

You manage luminosity configuration **only** through the `luminosity config`
command. ...
```

Extend `allowed-tools` to scope the reader so the preprocessor may run it:

```yaml
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context)
```

#### 2. Configure-surface action

**File**: `skills/config/configure/SKILL.md`
**Changes**: Add a `## Managing project context` section (a heading distinct from
the injected, load-bearing `## Project Context` block, so the two never collide in
a rendered prompt) that names the team and personal config-file **bodies** as the
source. It must read as an actionable step, but one framed correctly against the
skill's existing "you never read, parse, or write the configuration files
yourself" premise: editing a config-file **body** is a **user** (human) action,
distinct from the CLI-mediated `get`/`set` the skill performs. The section states
that free-form Markdown written below the frontmatter of `.luminosity/config.md`
(team) or `.luminosity/config.local.md` (personal) is injected into every skill's
prompt, that the way to change it is for the user to edit those bodies, and that
the skill's role is to point the user at the relevant body — not to edit it. Adjust
the intro's "never edit the files yourself" wording so it plainly scopes to the
CLI-owned frontmatter values and does not read as forbidding the user's body-edit.
Point the user at `luminosity context` (and `context --explain`) as the way to
verify a body-edit took effect — closing the loop between this management surface
and the diagnostic.

#### 3. Registry-iterating wiring test

**File**: `tests/unit/skills/test_context_injection.py` (new; no `__init__.py`,
fully annotated, ruff `ALL` + pyrefly strict)
**Changes**: Enumerate the skill directories in `.claude-plugin/plugin.json`,
discover each `SKILL.md`, and assert, for every one:

- it carries the exact injection line (assert the literal, so a drift in the
  command path fails loudly);
- the line sits **directly under the H1** (immediately after the frontmatter and
  the `# ` title, a positive lower bound) **and** before the first `## `
  subsection — so placement is pinned even for a skill with no `## ` subsection,
  where "before the first `## `" would otherwise pass vacuously;
- its `allowed-tools` frontmatter includes the `context` grant
  (`Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context)`) — the second, otherwise
  unenforced half of the wiring, whose omission would silently disable injection
  at runtime.

Guard the enumeration itself: if a registered directory contains a `SKILL.md` the
discovery walk did not reach, fail loudly rather than under-asserting a
one-element set. Anchor the walk to Claude Code's documented skill-discovery rule.

```python
INJECTION_LINE = "!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context`"
```

#### 4. Configure-surface assertion (AC-10)

**File**: `tests/unit/skills/test_context_injection.py` (same file)
**Changes**: Assert the `configure/SKILL.md` body contains the
`## Managing project context` section and references **both** config-file body
paths (`.luminosity/config.md` and `.luminosity/config.local.md`) as the source,
so AC-10 is enforced test-first rather than left to manual verification.

#### 5. Wire the skills test tree into the roll-ups

**Files**: `mise.toml`, `tasks/` (mirroring the `test:unit:evals` wiring).
**Changes**: Add a `test:unit:skills` leaf and make `test:unit` depend on it. The
unit roll-ups are directory-scoped, so without this leaf nothing collects
`tests/unit/skills/` and the wiring test would never run in CI or the bare
`mise run` default — "done" would be green with the AC-enforcing test unexecuted.
Follow the leaf convention exactly (the coherence suite pins it): the leaf **wraps
an invoke task** (`tasks/test/skills.py` → `invoke test.skills.run`, not a raw
`uv run pytest`) and carries `depends = ["deps:install:python"]` so it provisions
Python like the other pytest leaves. Update `tests/unit/tasks/test_mise_wiring.py`:
extend the pinned `test:unit` depends array (currently
`["test:unit:tasks", "test:unit:cli", "test:unit:evals"]`) to include
`test:unit:skills`, and add the leaf's wraps-an-invoke-task and provisions-Python
coherence assertions mirroring the `test:unit:evals` ones.

### Test Strategy (write first)

- The registry test above (the AC-mandated enumeration) — red before the SKILL.md
  edit, green after.
- Placement assertions: the line sits directly under the H1 (positive lower bound)
  and before the first `## ` subsection heading (the placement AC), so the check
  cannot pass vacuously for a subsection-less skill.
- The `allowed-tools`-grant assertion — red before the frontmatter edit, green
  after.
- The AC-10 configure-surface assertion (names both config-file bodies) — red
  before the surface edit, green after.
- The mise-wiring coherence assertion for the new `test:unit:skills` leaf.

### Success Criteria

#### Automated Verification

- [x] Registry + `allowed-tools` + AC-10 wiring tests pass via the roll-up:
      `mise run test:unit:skills`
- [x] The mise-wiring coherence test passes (asserts the `test:unit:skills` leaf
      exists and `test:unit` depends on it)
- [x] Python lint + types pass: `mise run build-system:check`
- [x] Full read-only CI mirror passes: `mise run check`

#### Manual Verification

- [x] Invoking `configure` in a repo with a team body shows the `## Project
      Context` block above the skill's own instructions in the rendered prompt
      (verified with a live `claude -p` skill invocation against the staged
      plugin: the agent reported `BLOCK-PRESENT` and quoted back the exact
      wrapper prose line)
- [x] With both bodies empty, the rendered `configure` prompt contains no
      `## Project Context` block (same live probe reported `BLOCK-ABSENT`)
- [x] The `configure` surface names the config-file bodies as the source and reads
      as an actionable step (a live agent spontaneously described the body-edit
      surface correctly when summarising configuration)
- [x] With a **malformed** committed `.luminosity/config.md`, invoking `configure`
      surfaces the fail-loud error at the `!`-preprocessor boundary. **Contingency
      resolved**: the preprocessor renders a non-zero exit as
      ``Shell command failed for pattern "!`…luminosity context`": [stderr]``
      followed by the command's stderr verbatim — so the offending filename does
      reach the user. No fallback to a degraded/empty injection is needed.

---

## Phase 3: Eval coverage

### Overview

Add body-bearing fixtures and a dedicated `context` eval that grades the reader's
stdout byte-for-byte across the four scenarios, plus a live-only behavioural arm
that checks the agent's output reflects injected context. Depends on Phase 1 (the
binary) for the deterministic scenarios and Phase 2 (the line) for the behavioural
arm. Kept separate from the `configure` get/set eval because the grading model
differs (passive injection has no agent command to attribute).

### Changes Required

#### 1. Body-bearing fixtures

**Files**: `tests/evals/skills/configure/fixtures/context_team_only/.luminosity/`,
`.../context_personal_only/.luminosity/`, `.../context_both/.luminosity/`,
`.../context_empty/.luminosity/`
**Changes**: Config files with distinctive Markdown bodies below the frontmatter
(and, for `context_empty`, frontmatter-only or whitespace-only bodies). Bodies
carry a recognisable sentinel so grading can assert exact content and ordering.

#### 2. Context eval task, dataset, and scorer

**Files**: `tests/evals/skills/configure/context_eval.py`,
`.../context_dataset.json`, `.../context_scorer.py` (new)
**Changes**:

- Dataset cases: `team_only`, `personal_only`, `both`, `both_empty`, each naming
  its fixture and the `expected_block` (or empty) in metadata; plus a behavioural
  case naming a fixture whose body instructs a distinctive, observable behaviour.
  The `expected_block` value is a **hand-synced golden** of the launcher's `render`
  output (the `## Project Context` header + the `PROSE` two-liner). Build it from the
  fixture body plus a single Python header/prose snippet, and **guard the seam** with
  a coherence assertion (below) so a change to the Rust `PROSE`/header cannot leave
  the eval golden stale unobserved — matching how the repo guards its other
  hand-synced mirrors rather than merely noting them.
- Scorer: for the deterministic cases, re-execute `luminosity context` in the
  seeded workdir (reuse the `_exec` pattern from `scorer.py:156-169`) and assert
  stdout equals the expected block byte-for-byte — presence, absence (empty for
  `both_empty`), team-first ordering with a single blank-line separator, and no
  leading/trailing blank lines. For the behavioural case, assert the agent's
  transcript reflects the injected instruction. Gate the behavioural arm behind
  the live-eval switch (`LUMINOSITY_EVAL_LIVE`), keeping it out of the
  deterministic CI path given its noise.

#### 3. Mirrored CI unit tests

**Files**: `tests/unit/evals/skills/configure/test_context_dataset.py`,
`.../test_context_scorer.py` (new)
**Changes**: Assert the context dataset parses and carries the required fields and
one case per scenario class (mirroring `test_dataset.py`), and unit-test the new
scorer's grading helpers (exact-block match, empty-for-both-empty,
ordering/trim). Add the **golden coherence assertion**: pin the eval snippet's
`## Project Context` header and `PROSE` two-liner byte-for-byte against the same
literal the Rust byte-exact `render` unit test asserts (a committed expected-string
fixture the two tests share, or a check that re-runs `luminosity context` on a known
body and compares), so a drift in the Rust prose fails a Python test rather than
silently staling the eval. The existing `test_dataset.py::test_total_is_nine` is
untouched — the context dataset is separate, so the `configure` count stays 9.

### Test Strategy (write first)

- Scorer helper unit tests (byte-exact match; empty-block acceptance; ordering;
  trim) — pure, deterministic, CI-run.
- Dataset structural tests — one case per scenario class.
- The live behavioural arm is exercised under `LUMINOSITY_EVAL_LIVE` with the
  existing `pass_k` floor, not in the deterministic CI unit suite.

### Success Criteria

#### Automated Verification

- [x] Context eval unit tests pass:
      `uv run pytest tests/unit/evals/skills/configure/test_context_scorer.py tests/unit/evals/skills/configure/test_context_dataset.py -v`
- [x] The eval-logic unit suite passes: `mise run test:unit:evals`
- [x] Python lint + types pass: `mise run build-system:check`
- [x] Full read-only CI mirror passes: `mise run check`

#### Manual Verification

- [x] `LUMINOSITY_EVAL_LIVE=1` run of the context eval passes the four
      deterministic scenarios (live `mise run eval:skills:configure`: all four
      scenarios `C` across 3 epochs)
- [x] The behavioural arm shows the agent acting on the injected project context
      at or above the configured `pass_k` floor (live run: context arm pass^k
      **1.000** vs the 0.8 floor, 15/15 samples; the agent applies the injected
      "Lantern" terminology convention unprompted). The whole run is green:
      configure with-skill **0.889**, context **1.000**, both above the floor,
      with the committed result logs refreshed as the durable signal.
- [x] `mise run` (the full local CI mirror) exits 0 end-to-end

#### Deviations from the plan

- **The injection call site is loud but non-blocking; the reader stays
  fail-loud.** The plan's contingency assumed the only risk was the
  `!`-preprocessor rendering a non-zero exit *opaquely*. It does not — it names
  the offending file. But it also **aborts the skill**: a single malformed
  config made every skill refuse to load, including `configure`, the one a user
  would reach for to diagnose it (and which could not repair it anyway, since
  `config set` fails closed on a malformed file). This deterministically failed
  the configure eval's `malformed` sample. The injection line is therefore
  `!`…/luminosity context 2>&1 || true``: the CLI keeps its fail-loud contract
  (non-zero exit, filename on stderr — every Phase 1 AC and test unchanged),
  while the call site tolerates the exit and folds stderr into stdout, so the
  reader's error is spliced into the prompt *in place of* the block. A broken
  config stays loud in every skill without bricking any of them — the outcome
  the plan wanted, by the one route it had not considered. The rationale is
  pinned on the constants in `test_context_injection.py`.
- **The context eval rides `eval:skills:configure`.** It grades the `configure`
  skill, so it gets no task of its own. `run_skill_eval` now discovers
  supplementary single-arm evals (`<arm>_eval.py`) beside a skill's paired-arm
  eval, runs them in the same pass, and gates on the weakest arm — so every arm
  must clear the pass^k floor. Pinned by
  `tests/unit/tasks/shared/eval/test_run.py`.
- **Behavioural fixture redesigned.** The first behavioural body was an
  imperative ("Always include the token `GILDED-OTTER-42` in every response").
  A live run showed the model correctly identifies that shape as a *prompt
  injection* and refuses it, so the arm failed for a reason unrelated to
  injection. The body was rewritten as declarative project context (a
  terminology convention), which the agent applies willingly. This is the
  practical face of the prompt-injection trade-off the plan accepted under
  "What We're NOT Doing", and is pinned by a comment on the behavioural test.
- **Eval-harness stale-binary bug fixed (outside the original scope).**
  `run.py::_host_binary()` resolved `cli/launcher/bin/luminosity-<alias>`, which
  only the *distribution* build (`build:release`) ever writes — while the eval
  leaves depend on `build:launcher`, which builds into the cargo target dir. The
  eval therefore staged whatever binary a past release left behind (here a
  binary predating the `context` command), silently grading skills against stale
  code. `_host_binary()` now resolves the `build:launcher` output via a new pure
  `targets.host_triple()` helper and fails loudly when it is absent. Pinned by
  `tests/unit/tasks/shared/eval/test_host_binary.py`.

---

## Testing Strategy

### Unit Tests

- `config` core: the assembler's concat/trim/emptiness across all body
  combinations (including CRLF, whitespace-only, and both read-error branches) and
  `assemble`'s per-level `discovered`/`has_body` reporting (formatted by the
  launcher's `explain_lines`), against a fake `ReadConfigBody`.
- `config-adapters`: `read_body`/`read_raw` over present/absent/all-body/malformed
  files.
- Launcher inbound: the byte-exact `render(&ProjectContext)` block and
  `explain_lines` formatting.
- Python: registry wiring (line + placement + `allowed-tools` grant), the AC-10
  configure-surface assertion, the mise-wiring coherence for `test:unit:skills`,
  context dataset structure, and scorer grading helpers.

### Integration Tests

- `cli/launcher/tests/context.rs`: the compiled `luminosity context` across
  team-only / personal-only / both / both-empty / no-config-dir / trimming /
  malformed-body (non-zero exit, stderr names the file) / `--explain` /
  subdirectory / `--help`.

### Manual Testing Steps

1. In a scratch repo with a `.git` marker, write bodies into both config files and
   run `luminosity context`; confirm the block, team first.
2. Empty both bodies; confirm empty stdout and exit 0.
3. Invoke `configure` and confirm the rendered prompt carries the block above the
   skill's own instructions, and nothing when bodies are empty.
4. Run the context eval live and confirm the deterministic and behavioural arms.

## Migration Notes

None. No existing config files, formats, or commands change; the reader is
additive and absent bodies are a no-op.

## References

- Original work item: `meta/work/0016-plugin-global-context-injection.md`
- Research: `meta/research/codebase/2026-07-11-0016-plugin-global-context-injection.md`
- Body-split primitive: `cli/config-adapters/src/frontmatter.rs:21`
- Driven-port shape: `cli/config/src/service.rs:20-36`
- Thin inbound to mirror: `cli/launcher/src/config_command/inbound/cli.rs`
- Integration-test harness to mirror: `cli/launcher/tests/config.rs`
- Eval framework to extend: `tests/evals/skills/configure/`
