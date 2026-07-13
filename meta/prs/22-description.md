---
type: pr-description
id: "22"
title: "[0016] Add global context"
date: "2026-07-13T16:52:55+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "0016"
parent: "work-item:0016"
relates_to: ["work-item:0011", "work-item:0010", "work-item:0017", "work-item:0018"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/22"
pr_number: 22
tags: [configuration, context-injection, cli, skills, evals]
revision: "da8f02543398036dc46bb5458d698524869840f2"
repository: "luminosity"
last_updated: "2026-07-13T18:04:14+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# [0016] Add global context

## Summary

Free-form Markdown written in the **bodies** of `.luminosity/config.md` (team) and `.luminosity/config.local.md` (personal) is now assembled by a new `luminosity context` subcommand and injected as a `## Project Context` block at the top of every skill's prompt, so skills act on project-specific context without the user restating it each invocation. This is the first of epic 0011's three context-injection themes, and it deliberately owns the shared mechanism — the reader, the `!`-preprocessor wiring, and the near-top placement anchor — that stories 0017 (per-skill context) and 0018 (per-skill instructions) extend.

## Changes

### Phase 1 — the `luminosity context` reader (Rust)

- **New `context` module in the `config` domain crate** (`cli/config/src/context.rs`): the value object `ProjectContext`, the driving port `AssembleProjectContext`, the application service `ProjectContextAssembler`, and `Assembly` / `LevelContribution` (a fixed-arity `[team, personal]` record backing `--explain`). A new driven port `ReadConfigBody` (`service.rs`) sits alongside the existing `ReadConfigLevel` / `WriteConfigLevel`, and `Level::file_name()` moves the two config filenames into the domain so the store and the `--explain` renderer share one owner.
- **Assembly semantics.** Bodies are trimmed with a *line-granular* blank-line trim — leading/trailing blank lines go, but the first content line's indentation and all interior blank lines survive — then joined team-first with a single blank line. Empty levels drop out; both empty yields `None`, and the command prints nothing at all (exit 0).
- **Single read, single error site.** `FileConfigStore` gains `impl ReadConfigBody` on top of a new private `read_raw()` that reads and frontmatter-splits the file once, so the frontmatter surface (`read`) and the body surface (`read_body`) can no longer disagree, and `MalformedFrontmatter` / `Io` are raised in exactly one place. `document.rs`'s `parse` is gone; `parse_frontmatter` is promoted to `pub` because the store now does the splitting.
- **The `context` subcommand** (`cli/launcher/src/context_command/`) owns presentation only: the byte-exact `## Project Context` header and two-line prose, the print-nothing-when-empty policy, `--explain` (per-level "not found" / "discovered, empty body" / "discovered, body present" lines, to **stderr**, stdout untouched), and the fail-safe policy.

### The `--fail-safe` flag — why it exists

The SKILL.md `!`-preprocessor **discards the entire prompt when the command exits non-zero**. Since the reader is fail-loud, a single malformed `.luminosity/config.md` would make *every* skill refuse to load — including `configure`, the one skill a user would reach for to diagnose it, and which can't repair it anyway (`config set` fails closed on a malformed file). It deterministically failed the configure eval's `malformed` sample.

The fix is a typed CLI policy (`OnFailure::{Fail, Degrade}`) rather than shell plumbing at the call site. The default stays loud (empty stdout, error on stderr, exit 1). `--fail-safe` instead renders the error into **stdout** as a distinct `## Project Context Unavailable` block — prose that tells the agent to report the error to the user and continue without project context — and exits **0**. Net effect: loud (the error text, naming the offending file, lands in the model's prompt) without bricking (the skill still loads). Skills invoke `context --fail-safe`; the diagnostic commands the skill prose points the user at stay bare and loud.

### Phase 2 — skill injection and the `configure` surface

- **Every registered skill is wired.** Each SKILL.md carries the exact line ``!`${CLAUDE_PLUGIN_ROOT}/bin/luminosity context --fail-safe` `` directly under its H1 — before any prose and before the first `##` subsection — plus the matching `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity context*)` grant in `allowed-tools`.
- **The wiring test walks the registry, not a list.** `tests/unit/skills/test_context_injection.py` reads `.claude-plugin/plugin.json`, `rglob`s `SKILL.md` under each registered dir (mirroring Claude Code's own discovery walk), and parametrises over what it finds — asserting the exact injection line, that only blank lines separate it from the H1, that it precedes the first subsection, and that the tool grant is present. Any skill added later is auto-enrolled and fails until wired.
- **`configure` gains a `## Managing project context` section.** Its opening rule is rescoped to configuration **values** ("the CLI owns the files, their frontmatter format, and level precedence"), and the new section explains that body edits are a **user** action: the skill points the user at the right file (`config.md` for shared, `config.local.md` for personal) rather than editing it itself, then verifies with `luminosity context` (prints the assembled block) or `context --explain` (per-level discovery/emptiness — the way to diagnose an empty or unexpected block).

### Phase 3 — eval coverage

- **Arms are renamed to a three-part `skill_capability_control` scheme** — `configure_values_with_skill`, `configure_values_baseline`, `configure_context_with_skill`. Capability was previously implicit in the arm name, which was only unambiguous while a skill had exactly one capability. Capabilities are now discovered by globbing `<skill>/*_eval.py` (hence `configure_eval.py` → `values_eval.py`), so both arms ride the single `eval:skills:configure` run, and the gate takes `min()` over the with-skill arms.
- **`context` has no baseline arm, deliberately.** Injection is passive — without the skill there is no prompt to inject into, so a no-skill run would not be a control, it would be a different experiment. `arms()` includes a baseline only when the module declares one, and `test_collection.py` asserts `context_eval` declares none.
- **Five samples**: `team_only`, `personal_only`, `both` (team-first ordering), `both_empty` (asserts *nothing* is emitted), and a **behavioural** sample that checks the model actually *used* the injected context — a "Lantern" terminology sentinel must appear in assistant-role transcript text (user messages are excluded from the concatenation, so the prompt can't satisfy it by echo).
- **The deterministic scorer grades the real binary.** It re-executes `luminosity context` in the solver's seeded workdir and byte-compares stdout against a golden block.
- **The eval golden is pinned to the Rust source.** `test_block_prefix_matches_the_rust_source` extracts the `## Project Context` header and the `PROSE` const *from* `cli/launcher/src/context_command/inbound/cli.rs` and pins the Python `BLOCK_PREFIX` against them. This was originally a self-referential check — `BLOCK_PREFIX` was a standalone literal that the goldens were rebuilt *from*, so it only ever confirmed Python agreed with itself, and a change to the Rust prose left every Python test green while staling the goldens (surfacing only in a live eval run, never in CI). Caught by `validate-plan`; see Testing.

### Eval-harness fixes carried by this PR

- **Evals staged a stale binary.** `_host_binary()` resolved into the *distribution* bin dir (`cli/launcher/bin/luminosity-<os>-<arch>`), which only a release build populates — so an eval could grade whatever launcher a past release left behind. For the new `context` capability that binary has no `context` subcommand at all. `host_binary_path()` now resolves `target/<host-triple>/release/luminosity` (exactly what `build:launcher` produces) and hard-fails with a "run `mise run build:launcher`" message if absent; `test_host_binary.py` pins that it never resolves under the distribution bin dir. New `host_triple()` in `tasks/shared/targets.py` narrows to the single triple this host builds (the existing `host_targets()` returns both arches).
- **New `test:unit:skills` task.** The directory-scoped `test:unit:tasks` pass never collected `tests/unit/skills/`, so the wiring test would have been lint- and type-checked but never actually run.
- **New `eval:view` task** — serves the Inspect log viewer over the committed logs with no live run (`--skill configure`, `--port`, `--host`).

### Work-item bookkeeping

Epic 0011 is retitled "Configuration Parity **and Enhancements** with Accelerator" (two of its five themes deliberately go beyond the accelerator) and decomposed into children 0016–0021; 0017 and 0018 are reviewed and ready. Completed workspace/eval work items are marked done.

## Context

Implements work item **0016** ("Plugin-Global Additional Context Injection"), under epic **0011**, following the plan `meta/plans/2026-07-11-0016-plugin-global-context-injection.md` and the codebase research `meta/research/codebase/2026-07-11-0016-plugin-global-context-injection.md` (both added here, along with the plan and work-item reviews). Builds on the eval framework from story **0010** and the multi-level config model from **0009**. **Blocks 0017 and 0018**, which extend this mechanism and its placement anchor.

The behaviour reimplements the accelerator's `scripts/config-read-context.sh` in Rust; the header and wrapper prose are byte-for-byte load-bearing, since downstream skill prose refers to the `## Project Context` block by name.

The completed implementation was validated (result: **pass**) — see `meta/validations/2026-07-11-0016-plugin-global-context-injection-validation.md`.

## Testing

- [x] `mise run check` — green (format, lint, types across all three toolchains, plus `deny:check` / `pup:check`).
- [x] `mise run test` — green. Workspace coverage 86.31%; both new launcher modules (`context_command/inbound/cli.rs`, `config_command/inbound/cli.rs`) at **100%**.
- [x] `mise run` (bare default — the full local CI mirror, including `build:launcher`) — green end-to-end.
- [x] **Rust, 36 tests on the feature**: 15 black-box integration tests of the compiled binary (`cli/launcher/tests/context.rs` — each in a fresh `.git`-marked temp dir so discovery can't escape into the real tree), 16 domain unit tests (`config::context`), 5 render tests (`context_command`), plus new `store.rs` / `level.rs` cases.
- [x] **Python, 84 tests** across the new/changed surfaces: skill-wiring registry walk, context dataset + scorer (incl. the new Rust-source coherence guard), eval `capabilities()`/`arms()` resolution, host-binary staging, eval locations, `eval:view`, and mise wiring.
- [x] **Edge cases covered**: both-empty emits nothing; blank-line trimming preserves indentation and interior blanks; CRLF bodies; malformed config fails loudly *without* `--fail-safe` and degrades to a stdout notice *with* it; `--fail-safe` leaves a healthy read byte-identical; discovery from a nested subdirectory; a fence-less file is treated as all-body.
- [x] **The new coherence guard was verified as a guard, not a tautology**: mutating the Rust `PROSE` const, and separately the `render()` header, each turns `test_block_prefix_matches_the_rust_source` red; the unmutated source is green.
- [x] **Evals green** — committed logs: `configure_context_with_skill` 15/15 samples at accuracy **1.0**; `configure_values_with_skill` 27 samples at **1.0** against a `configure_values_baseline` of **0.0**. `test_results.py` gates the committed logs against the floor and runs as part of `mise run test`. The live eval was not re-run for this description (it needs the Claude CLI and is billed) — the committed logs are the evidence.
- [x] **Plan validated** (`/validate-plan`, result **pass**): all three phases implemented, all eleven acceptance criteria met. Validation initially returned `partial` — it surfaced the unguarded eval-golden seam described above — and passes now that the gap is closed. Plan status is `done`.
- [x] **Rebased onto `main`** (0.3.0-pre.3) with no conflicts; `check` and `test` re-run green on the rebased tree.

## Notes for Reviewers

- **`--fail-safe` is the crux of the design** — read `cli/launcher/src/context_command/inbound/cli.rs` and the rationale in the plan (lines 789–808). The choice to make degradation a *typed CLI policy* rather than shell plumbing at each call site is the load-bearing one.
- **The wrapper prose exists in three hand-synced copies, and all three now fail loudly on drift**: the Rust `PROSE` const (pinned by the byte-exact `render` unit test), the integration test's `BLOCK_HEADER` (asserted against the compiled binary's stdout, so it self-guards), and the Python `BLOCK_PREFIX` (now pinned against the Rust source). The Python pin is new in this PR — before it, that copy could stale silently.
- **`--explain` is silently suppressed under a degraded failure** — `context --explain --fail-safe` against a malformed config prints the notice and *no* per-level lines. Verified live. Defensible (the error *is* the diagnosis, and per-level `has_body` is meaningless for an unreadable file), but the interaction is untested and undocumented in the flag help. Flagged as a follow-up in the validation report.
- **A config file with no `---` fence becomes 100% project context** (the splitter treats a fence-less file as all-body). Covered by a test, but worth a conscious nod.
- **CRLF asymmetry**: interior CRLF endings survive, but the team/personal join always uses `\n\n`, so a CRLF pair yields a mixed-ending block. Explicitly asserted, not accidental.
- **"Every skill" is currently 1 of 1** — `configure` is the only SKILL.md in the repo. The value of the registry walk is that the next skill added fails the test until it's wired.
- **Diff size is misleading**: of ~24k inserted lines, ~17.7k are regenerated Inspect eval logs (the two `values` result JSONs were renamed and re-run under the new arm names) and ~4.5k are meta documents (plan, research, four reviews, six work items, the validation report). The substantive code and tests are ~2k lines.
- **Outstanding bookkeeping**: work item 0016 is still `status: ready` with its eleven acceptance criteria unchecked, despite all being met.
