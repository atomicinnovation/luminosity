---
type: codebase-research
id: "2026-07-13-0017-per-skill-context-injection"
title: "Research: Per-Skill Context Injection (story 0017)"
date: "2026-07-13T20:21:14+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0017"
parent: "work-item:0017"
relates_to: ["codebase-research:2026-07-11-0016-plugin-global-context-injection"]
topic: "Implementing per-skill context injection from .luminosity/skills/<skill>/context.md"
tags: [research, codebase, configuration, context-injection, cli, skills, evals]
revision: "97ca52868a55e8718b8dfa50bc3c02955f369bf7"
repository: "luminosity"
last_updated: "2026-07-13T20:21:14+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Per-Skill Context Injection (story 0017)

**Date**: 2026-07-13 20:21 UTC
**Author**: Toby Clemson
**Git Commit**: `97ca52868a55e8718b8dfa50bc3c02955f369bf7`
**Branch**: `main` (at the 0016 merge, `f40e707`)
**Repository**: luminosity

## Research Question

What does the codebase look like for implementing story 0017 (per-skill context
injection from `.luminosity/skills/<skill-name>/context.md`), given that story
0016 (plugin-global context injection) has just landed?

## Summary

**0016 built almost exactly the machine 0017 needs.** The hexagon, the
fail-safe rendering policy, the trimming rules, the skill-wiring contract test,
and the eval arm are all in place and all extend cleanly. The work is a
narrow extension, not a new subsystem.

Five things, however, are *not* what the story assumes, and each changes the
plan:

1. **There is no skill registry to iterate.** `.claude-plugin/plugin.json` lists
   a *directory* (`./skills/config/`), not skills. And there is exactly **one
   skill in the repo** — `configure`. The story's "wire into every skill" and
   "a test iterates the registry and asserts each entry" describe a set of size
   one. The good news: `tests/unit/skills/test_context_injection.py` already
   performs precisely that registry walk and auto-enrols any future skill, so
   the AC is satisfiable today and stays honest as skills are added.

2. **ADR-0020 does not exist.** The story's Technical Notes cite "ADR-0020
   (per-skill customisation directory)". The ADR series stops at ADR-0011. The
   `.luminosity/` layout is ADR-0003. The reference is almost certainly a slip
   for *work item* 0020 (composed configuration schema). The story needs a
   correction, and there is genuinely **no accepted ADR sanctioning the
   `.luminosity/skills/<skill>/` directory** — that decision is currently
   unrecorded.

3. **The accelerator's per-skill readers are not frontmatter-aware, but
   Luminosity's only file reader is.** `config-read-skill-context.sh` injects
   the *whole file*; `config-read-context.sh` strips YAML frontmatter first.
   Luminosity's `FileConfigStore::read_raw` unconditionally splits frontmatter,
   so naively reusing it would strip a leading `---` block out of a user's
   `context.md` — a silent divergence from the reference. This needs a
   deliberate decision, not an accident.

4. **The skill name flows into a filesystem path.** The accelerator interpolates
   `$SKILL_NAME` straight into `.accelerator/skills/$SKILL_NAME/context.md` with
   no validation. Luminosity should validate it (a `SkillName` value object
   rejecting `/`, `\`, `..`, and empty) rather than port the traversal hole.

5. **The eval fixture seeder cannot copy a nested directory.**
   `solvers.py::_seed` does a flat `source.glob("*")` + `shutil.copy`, which
   raises `IsADirectoryError` the moment a fixture contains
   `.luminosity/skills/`. This is the single hard blocker in the eval tier.

The most consequential *design* choice is whether one injection line renders
both blocks or two adjacent lines each render one. **I recommend one line**
(`context --skill <name> --fail-safe` emitting `## Project Context` then
`## Skill-Specific Context`) — it makes the story's ordering and
"absent-global" acceptance criteria structurally true rather than merely
tested, and it collapses the eval's hardest assertion into the existing
byte-exact comparison. See [Design Decision](#design-decision-one-injection-line-or-two).

## Detailed Findings

### The Rust hexagon (what 0016 built)

The workspace is `cli/`, members `["launcher", "kernel", "verify", "config",
"config-adapters"]` (`cli/Cargo.toml:5`).

Context assembly is a **cross-crate hexagon**, distinct from the in-crate shape
used by `version`/`launch`:

- **Domain core** — `cli/config/` (serde-free, depends only on `kernel`).
  `cli/config/src/context.rs` holds `ProjectContext`, `LevelContribution`,
  `Assembly`, the driving port `AssembleProjectContext` (`:38`), and the service
  `ProjectContextAssembler<R>` (`:48`), generic over the driven port
  `ReadConfigBody` (`cli/config/src/service.rs:31`).
- **Driven adapter** — `cli/config-adapters/src/store.rs`. `FileConfigStore`
  owns every filesystem and serde concern; `cli/deny.toml:84-101` names it as
  the *only* permitted `serde-saphyr` wrapper, which is what keeps the domain
  crate clean.
- **Driving adapter** — `cli/launcher/src/context_command/inbound/cli.rs`. It
  owns only the byte-exact block, the empty-output policy, and the `--explain`
  diagnostic. `context_command/` deliberately has **no `core.rs` and no
  `outbound/`** — stated in `cli/launcher/src/context_command/mod.rs:3-5`.

Naming conventions are applied consistently and should be mirrored: driven and
driving ports are verb-object traits (`ReadConfigBody`, `AssembleProjectContext`);
application services are agent nouns generic over their ports
(`ProjectContextAssembler<R>`); adapters arrive as `impl Trait` at call sites.

**Correction to a common misreading**: 0016's global context is *not* a
`.luminosity/context.md` file. It is the free-form Markdown **body beneath the
YAML frontmatter** of `.luminosity/config.md` (team) and `.luminosity/config.local.md`
(personal), trimmed, joined team-then-personal with one blank line. 0017's
`context.md` is a genuinely new file shape — the first standalone content file
in `.luminosity/`.

#### The rendering and fail-safe policy — the load-bearing constraint

`cli/launcher/src/context_command/inbound/cli.rs:13-20,41-49`:

```rust
const PROSE: &str = "\
The following project-specific context has been provided. Take this into
account when making decisions, selecting approaches, and generating output.";

pub fn render(context: &ProjectContext) -> String {
    format!("## Project Context\n\n{PROSE}\n\n{}", context.body)
}
```

And the reason `--fail-safe` exists (`:22-32`):

```rust
pub enum OnFailure {
    /// Exit non-zero with the error on stderr.
    Fail,
    /// Exit zero, rendering the error as a notice on stdout. For a caller that
    /// splices this command's stdout into a prompt: a non-zero exit there
    /// discards the whole prompt, so failing loudly would disable the caller
    /// rather than inform it.
    Degrade,
}
```

**The `!` preprocessor discards the entire prompt on a non-zero exit.** This is
the single most important constraint on 0017: any command spliced into a skill
body must never exit non-zero in the injection path. A malformed `context.md`
must degrade to a `## … Unavailable` notice, not a failure. Note this also means
a *missing `--skill` argument* — a clap parse error, which exits with clap's own
non-zero code before `--fail-safe` is ever consulted — would kill the prompt.
Worth a test.

#### Trimming rules (reusable verbatim)

`cli/config/src/context.rs:86-113`. `trim_blank_lines` strips whole leading and
trailing blank lines (blank = `trim().is_empty()`), while **preserving leading
indentation on the first kept line** and all interior blank lines. `"\n\n  hello\n"`
→ `"  hello"`. The combined body never ends with a newline terminator
(`the_combined_body_ends_without_a_terminator`, `:278-289`). Empty → `None` →
**nothing printed at all**, exit 0.

This is behaviourally equivalent to the accelerator's `config_trim_body` awk
(`config-common.sh:333-343`), so 0017 gets the story's blank-line-trimming AC
for free by reusing `trim_blank_lines`.

#### Config-dir discovery

`cli/config-adapters/src/store.rs:31-40,131-140` — a single upward walk from
`current_dir()` stopping at the nearest ancestor containing `.luminosity/` **or**
`.git` (matched with `.exists()`, so a worktree's `.git` *file* also stops it).
An enclosing `.git` bounds the walk, so discovery never escapes a repo boundary.
Per-skill paths are `config_dir().join("skills").join(name).join("context.md")` —
a new path rule in the same adapter, nothing structural.

#### Extension points (all currently untouched by any skill concept)

Grepping `skill` case-insensitively across `cli/**/*.rs` returns **zero
matches**. Nothing in the CLI knows skills exist. The seams are:

| Seam | File:line |
|---|---|
| Subcommand args | `cli/launcher/src/launch/inbound/cli.rs:26-35` (`Command::Context { explain, fail_safe }`) |
| Dispatch | `cli/launcher/src/launch/mod.rs:40-50` |
| Composition root | `cli/launcher/src/main.rs:149-173` (`LazyConfigBody`, `discover_store`) |
| **Hard-coded subcommand list** | `cli/launcher/src/main.rs:130-136` — `is_root_help` matches `Some("version" \| "config" \| "context" \| "help")`. **Must be extended if a new subcommand is added** (not needed if `--skill` extends `context`). |
| Path rule | `cli/config-adapters/src/store.rs:42-48` |
| Domain port | `cli/config/src/service.rs:31` (`ReadConfigBody` — a sibling `ReadSkillContext` goes here) |
| Help text | `cli/launcher/src/launch/help.rs` |

### The skill wiring contract

One skill exists: `skills/config/configure/SKILL.md` (93 lines). The injection
sits at **line 16**, directly under the H1, before all prose and before the first
`##`:

```markdown
# Configure

!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --fail-safe`
```

with the grant at `:9-11`:

```yaml
allowed-tools:
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)
  - Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)
```

Note `context*` has **no space before the `*`**, deliberately, so the glob covers
`context --fail-safe`. It will equally cover `context --skill configure --fail-safe`
— **no `allowed-tools` change is needed** if 0017 extends the `context` command
rather than adding a new one. (A new subcommand would need a new grant in every
skill.)

`${CLAUDE_PLUGIN_ROOT}/bin/luminosity` is **not the Rust binary** — it is a
bash-3.2 bootstrap shim (`bin/luminosity`, 147 lines) that resolves the platform
triple, reads the version out of `plugin.json` with `sed`, fetches and
minisign-verifies the launcher into a cache dir, and `exec`s it with argv passed
through.

#### The contract test — already does what AC 7 asks

`tests/unit/skills/test_context_injection.py` walks `plugin.json`'s `skills`
array and `rglob`s `SKILL.md` beneath each entry (`:29-41`), with a vacuity guard
that fails if zero skills are discovered (`:51-54`). Per discovered skill it
asserts three things: the exact injection line (`:62`), its placement under the
H1 before the first `##` (`:64-89`), and the `allowed-tools` grant (`:91-95`).

```python
INJECTION_LINE = "!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --fail-safe`"
CONTEXT_GRANT = "Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)"
```

**This constant is the thing 0017 breaks.** The per-skill line must carry the
skill name, so `INJECTION_LINE` stops being a literal and becomes a template
rendered per skill. The natural strengthening: derive the expected name from the
SKILL.md's own frontmatter `name:` field and assert the injected argument matches
it — which catches a copy-paste where a new skill injects a sibling's name. The
accelerator does the equivalent check out-of-band in `config-summary.sh:92-145`,
warning when a `.accelerator/skills/<n>/` dir matches no known skill name; a
compile-time-ish test is strictly better.

### The accelerator reference

`scripts/config-read-skill-context.sh` (36 lines) is the thing being ported.
Its emitted block, verbatim:

```
## Skill-Specific Context

The following context is specific to the $SKILL_NAME skill. Apply this
context in addition to any project-wide context above.

<trimmed content>
```

This matches the story's Technical Notes byte-for-byte. Note the prose says
*"in addition to any project-wide context above"* — the wording **presumes the
global block is rendered first and adjacently**, which is why the ordering AC
matters.

Behaviour: missing file → exit 0, no output. Trims to empty → exit 0, no output.
Missing `$1` → **exit 1** with usage on stderr (dangerous in an injection path
under Claude Code's preprocessor, though the accelerator gets away with it
because the argument is hard-coded in each SKILL.md).

The three wrappers compared:

| | `config-read-context.sh` | `config-read-skill-context.sh` | `config-read-skill-instructions.sh` |
|---|---|---|---|
| Argument | none | `<skill-name>`, required | `<skill-name>`, required |
| Source | `config.md` + `config.local.md`, **body only** | `skills/<n>/context.md`, **whole file** | `skills/<n>/instructions.md`, **whole file** |
| Header | `## Project Context` | `## Skill-Specific Context` | `## Additional Instructions` |
| Frontmatter stripped | **yes** | **no** | **no** |
| Empty → | no output, exit 0 | no output, exit 0 | no output, exit 0 |

**The frontmatter asymmetry is the trap.** Luminosity's `FileConfigStore::read_raw`
(`cli/config-adapters/src/store.rs:50-66`) unconditionally calls `frontmatter::split`
and returns the body. Reusing it for `context.md` would strip a leading `---`
block that the accelerator would have injected literally. Since `context.md` is a
free-form prose file with no frontmatter contract, the right behaviour is
**read the whole file, do not split** — matching the reference. That means a new
read path in the adapter, not a reuse of `read_raw`.

#### Rendered ordering in the accelerator

1. `# <Skill Title>` (H1)
2. optional other injections (`vcs-status.sh`, …)
3. `## Project Context` ← `config-read-context.sh`
4. `## Skill-Specific Context` ← `config-read-skill-context.sh <skill>`, on the
   **immediately following line**
5. … the authored skill prompt …
6. `## Additional Instructions` ← `config-read-skill-instructions.sh <skill>`,
   the **final line of the file** (story 0018's territory — deliberately last so
   user instructions win conflicts).

Confirmed at `skills/vcs/commit/SKILL.md:12-15` and `:66`,
`skills/planning/create-plan/SKILL.md:13-14` and `:464`.

#### What this repo's own `.accelerator/` actually contains

`.accelerator/config.md` is **frontmatter only** (visualiser kanban columns), so
the accelerator's global-context path is live but silent here. Under
`.accelerator/skills/` there are three `instructions.md` files (`create-plan`,
`implement-plan`, `review-plan`) and **no `context.md` anywhere**. So the
mechanism being mirrored is exercised in this repo only through the
*instructions* limb — there is no live per-skill *context* example to copy from.

### The eval suite

Inspect AI (`inspect-ai==0.3.244`), Python. Two tiers:

- **Live tier** (`mise run eval:skills:configure`, `mise.toml:115-131`) — drives
  the real `claude -p` against a staged plugin in a seeded temp workdir, then
  the scorer **re-executes the real compiled `luminosity` binary** in that same
  workdir and byte-compares stdout against a golden. Gated at
  `PASS_K_FLOOR = 0.8`. **Excluded from CI** for token cost.
- **CI tier** (`mise run test:unit:evals` → `tests/unit/evals/`) — pytest over
  the eval *logic*: golden coherence, dataset shape, and the committed result
  logs.

A "golden" is the `expected_block` string in `context_dataset.json`. Commit
`ce39575` ("Pin the eval golden against the Rust source") made
`tests/unit/evals/skills/configure/test_context_dataset.py` **scrape the Rust
literals out of `cli/launcher/src/context_command/inbound/cli.rs`** and pin the
Python copy against them (`:48-69`, `:118-122`), rather than restating them:

```python
def test_block_prefix_matches_the_rust_source() -> None:
    # The scorer byte-compares the goldens against the real binary, but only in
    # a live run. Pinning the prefix against the Rust literals is what makes a
    # drift in the header or prose fail in CI rather than stale them unseen.
    assert f"{_rust_header()}\n\n{_rust_prose()}\n\n" == BLOCK_PREFIX
```

The chain is: Rust literals → `BLOCK_PREFIX` (pinned) → derived expected block
(pinned) → dataset golden (pinned) → live binary stdout (byte-compared).
**0017 must extend this chain**, and its prose *interpolates the skill name*, so
the extraction regex must cope with a `{skill}`-bearing format string.

#### What 0017 costs in the eval tier

| Change | Effort |
|---|---|
| New capability module `skill_context_eval.py` | **Free** — `capabilities()` globs `*_eval.py` (`tasks/shared/eval/run.py:71-74`) and `min(graded)` auto-gates it. No mise/invoke change. |
| **`solvers.py::_seed` recursion** | **The blocker.** `:83-89` does flat `source.glob("*")` + `shutil.copy` → `IsADirectoryError` on a nested `skills/` fixture dir. Needs `copytree`. |
| New dataset + fixtures | Straightforward; mirror `fixtures/context_*/`. |
| New/parameterised scorer | `context_scorer._grade` hard-codes `_exec(["context"], …)` (`:74`). The argv must come from metadata or a sibling scorer. |
| Golden-pinning test | Mirror `test_context_dataset.py:118-122` for the new header/prose. |
| **Three exact-list assertions go red** | By design — they are tripwires. `tests/unit/tasks/shared/eval/test_run.py:20` (`capabilities(_SKILL) == ["context", "values"]`); `test_collection.py:12-59`; `test_results.py:70-72`. |
| **A committed result log for the new arm** | `test_results.py` `pytest.fail`s until one exists — so **a live, billed eval run is part of landing this story**. |

Also note `tasks/shared/eval/staging.py:18` hard-codes
`copytree(repo_root / "skills" / "config", …)`. Fine while `configure` is the
only skill; a landmine for any skill added outside `skills/config/`.

## Design Decision: one injection line, or two?

This is the choice that shapes the plan, and the story does not settle it.

**Option A — two adjacent `!` lines** (mirrors the accelerator):

```markdown
# Configure

!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --fail-safe`
!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity skill-context configure --fail-safe`
```

**Option B — one line, both blocks** (recommended):

```markdown
# Configure

!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --skill configure --fail-safe`
```

Option B renders `## Project Context` followed by `## Skill-Specific Context`,
omitting either when empty.

Option B is better here for four concrete reasons:

1. **The ordering AC becomes structurally true, not merely tested.** The story's
   "immediately after the `## Project Context` block" and "when absent, the skill
   block is first at that same point" are guaranteed by one `format!` in the
   renderer, rather than by two SKILL.md lines that a future edit could reorder
   or separate.
2. **It collapses the eval's hardest assertion.** As the eval analysis notes: if
   both blocks come from one command, the existing byte-exact `grade_block`
   covers ordering for free. With two commands, ordering is a *prompt-assembly*
   property invisible to the eval and only assertable on SKILL.md source.
3. **No `allowed-tools` churn.** `Bash(…/luminosity context*)` already covers
   `context --skill configure --fail-safe`. A new subcommand needs a new grant in
   every skill, plus an entry in the hard-coded `is_root_help` list
   (`main.rs:130-136`).
4. **One fail-safe boundary, not two.** A single command means a single place
   where a non-zero exit could nuke the prompt.

The cost of Option B: it diverges from the accelerator's script shape (three
independent readers), and it makes `luminosity context`'s output skill-dependent,
so the `--explain` diagnostic and the `configure` skill's own documentation of
"run `luminosity context` to confirm" need to grow a skill dimension. Story 0018
(per-skill *instructions*) is unaffected either way — it injects at the **end**
of the body, so it is necessarily a separate line regardless.

Worth noting Option B does not preclude the accelerator's ergonomics: `context`
with no `--skill` continues to behave exactly as it does today.

## Code References

- `cli/config/src/context.rs:38,48,58-113` — `AssembleProjectContext` port,
  `ProjectContextAssembler`, `assemble`/`combine`/`trim_blank_lines`.
- `cli/config/src/service.rs:31-40` — `ReadConfigBody`, the driven port to mirror.
- `cli/config-adapters/src/store.rs:31-48,50-66,108-112` — discovery walk, path
  rules, `read_raw` (frontmatter-splitting — **do not reuse for `context.md`**).
- `cli/launcher/src/context_command/inbound/cli.rs:13-20,22-32,41-49,59-80` —
  prose constants, `OnFailure`, `render`, `run`.
- `cli/launcher/src/launch/inbound/cli.rs:26-35` — `Command::Context` args.
- `cli/launcher/src/launch/mod.rs:40-50` — dispatch.
- `cli/launcher/src/main.rs:89-103,130-136,149-173` — `LazyConfigBody`,
  `is_root_help` hard-coded list, composition root.
- `cli/launcher/tests/context.rs:15-52,133-142,172-184` — black-box test harness
  and the fail-safe tests.
- `skills/config/configure/SKILL.md:9-11,16,35-58` — grants, injection line, and
  the `## Managing project context` section to mirror.
- `.claude-plugin/plugin.json:10-12` — `"skills": ["./skills/config/"]`.
- `tests/unit/skills/test_context_injection.py:25-26,29-41,64-89,98-105` — the
  contract test, the registry walk, and the `TestConfigureSurface` assertions.
- `tests/evals/skills/configure/solvers.py:83-89` — **`_seed`, the eval blocker**.
- `tests/evals/skills/configure/context_scorer.py:28-34,68-77` — `grade_block`.
- `tests/unit/evals/skills/configure/test_context_dataset.py:48-69,118-122` — the
  Rust-source golden pinning.
- `tasks/shared/eval/run.py:71-74,146-148` — capability discovery, `min(graded)`.
- `tasks/shared/eval/staging.py:18` — hard-coded `skills/config` copy.
- Accelerator: `scripts/config-read-skill-context.sh`,
  `scripts/config-common.sh:333-343` (`config_trim_body`).

## Architecture Insights

- **The `!` preprocessor's all-or-nothing failure mode is the dominant design
  force.** It explains `--fail-safe`, and it should drive 0017's error handling:
  degrade, never fail, and prefer a flag on an existing subcommand over a new
  argument that clap could reject before the fail-safe policy is consulted.
- **The domain crate's purity is enforced, not merely intended.**
  `cli/deny.toml:84-101` names `config-adapters` as the sole `serde-saphyr`
  wrapper. A `SkillName` value object belongs in `config`; the path rule belongs
  in `config-adapters`.
- **Goldens are pinned against source, not restated.** The `ce39575` pattern
  (scrape the Rust literal, assert the Python copy matches) is the house style
  for any byte-exact contract that spans the three toolchains. 0017's wrapper
  prose must join that chain.
- **Contract tests walk the registry rather than enumerate.**
  `test_context_injection.py` auto-enrols future skills. Preserve that property —
  it is what makes the story's "every skill" requirement durable rather than a
  point-in-time snapshot.
- **The CLI knows nothing of skills today.** 0017 introduces the first
  skill-aware concept into the Rust core. That is a real (small) conceptual
  expansion of the config domain, and a good moment to record an ADR.

## Historical Context

- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — the
  `.luminosity/` layout and team/personal levels.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
  — the layering 0017's code must respect.
- `meta/decisions/ADR-0001-skills-vs-cli-division-of-labour.md` — governs what
  goes in SKILL.md versus the Rust CLI.
- `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md` — the
  eval harness decision.
- `meta/work/0016-plugin-global-context-injection.md` (done),
  `meta/plans/2026-07-11-0016-plugin-global-context-injection.md` (done),
  `meta/research/codebase/2026-07-11-0016-plugin-global-context-injection.md`,
  `meta/validations/2026-07-11-0016-plugin-global-context-injection-validation.md`,
  `meta/prs/22-description.md` — the four-document trail for the sibling story;
  the closest template for 0017's plan.
- `meta/reviews/work/0017-per-skill-context-injection-review-1.md` — review 1
  (COMMENT), whose amendments produced the story's current Technical Notes.
- `meta/work/0018-per-skill-instructions-injection.md` — the successor, which
  shares the per-skill directory and injects at the *end* of the body.

## Open Questions

1. **Which injection shape?** One line (`context --skill <name> --fail-safe`,
   both blocks) or two adjacent lines mirroring the accelerator. Recommendation
   above is one line; this needs the author's call before planning.
2. **Frontmatter in `context.md`** — confirm the intended behaviour is
   "whole file, no frontmatter split" (matching the accelerator). If a user
   writes a `---` block, it gets injected literally. Is that acceptable, or
   should a frontmatter block be stripped for consistency with `config.md`?
3. **ADR-0020 does not exist.** Should the story's citation be corrected to
   ADR-0003, and should a new ADR be raised to sanction the
   `.luminosity/skills/<skill>/` per-skill customisation directory? Nothing
   currently records that decision.
4. **Skill-name validation.** Confirm a `SkillName` value object rejecting `/`,
   `\`, `..` and empty is wanted, and decide what an invalid name does — degrade
   to a notice (safe in the injection path) or exit non-zero (safe for a human
   at a terminal, fatal for a prompt).
5. **Unknown skill name.** If `--skill nonexistent` is passed, the file simply
   won't exist and nothing is emitted. Should the CLI additionally *validate the
   name against the known skill set* (as the accelerator's `config-summary.sh`
   warns), or is silence correct?
6. **A live billed eval run is required to land this story** (the committed-log
   gate). Confirm that is acceptable and budgeted.
7. **`staging.py`'s hard-coded `skills/config`** — fix opportunistically in this
   story, or leave until a second skill category exists?
