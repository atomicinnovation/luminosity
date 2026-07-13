---
type: plan-validation
id: "2026-07-11-0016-plugin-global-context-injection-validation"
title: "Validation Report: Plugin-Global Additional Context Injection Implementation Plan"
date: "2026-07-13T17:11:58+00:00"
author: "Toby Clemson"
producer: validate-plan
status: complete
result: pass
parent: "work-item:0016"
target: "plan:2026-07-11-0016-plugin-global-context-injection"
tags: [configuration, context-injection, rust-cli, skills, evals]
last_updated: "2026-07-13T17:23:46+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Validation Report: Plugin-Global Additional Context Injection

**Result: pass.** All three phases are implemented, every automated check is green, and all eleven of work item 0016's acceptance criteria are satisfied.

Validation initially returned **partial**: the Phase 3 golden-coherence assertion did not guard the seam it claimed to guard, and its docstring asserted a guarantee the code did not provide. **That gap was closed during this validation** (see Deviations) and the verdict is now `pass`.

### Implementation Status

- ✓ **Phase 1: The `luminosity context` reader** — fully implemented. `ReadConfigBody` port, `ProjectContext` / `Assembly` / `LevelContribution`, `ProjectContextAssembler`, the `read_raw` extraction in `FileConfigStore`, `Level::file_name()`, the launcher inbound, and full command wiring all match the plan.
- ✓ **Phase 2: Skill injection and the configure surface** — fully implemented. The injection line, the `allowed-tools` grant, the registry-iterating wiring test, the `## Managing project context` surface, and the `test:unit:skills` leaf are all present.
- ✓ **Phase 3: Eval coverage** — fully implemented. The fixtures, the `context` capability eval, the scorer, and the mirrored CI unit tests are all present; the golden-coherence assertion the plan specified is now genuinely in place.

### Automated Verification Results

Every command the plan names was executed against the head commit:

- ✓ `mise run check` (full read-only CI mirror) — exit 0
- ✓ `mise run test` — exit 0; workspace coverage 86.31%, `context_command/inbound/cli.rs` at 100%
- ✓ `mise run` (bare default; the full local CI mirror incl. `build:launcher`, `deny:check`, `pup:check`) — **exit 0**
- ✓ `cargo nextest run -p config -p config-adapters -p luminosity` — green; 15 black-box (`tests/context.rs`), 16 domain (`config::context`), 5 render (`context_command`)
- ✓ `mise run test:unit:skills` — green (the leaf exists and `test:unit` depends on it)
- ✓ Context eval unit tests — green (20 tests across `test_context_dataset.py`, `test_context_scorer.py`, including the new Rust-source coherence guard)
- ✓ `mise run test:unit:evals` — green (103 tests)
- ✓ Committed eval logs: `configure_context_with_skill` 15/15 at accuracy **1.0**; `configure_values_with_skill` 27 samples at **1.0** vs a `configure_values_baseline` of **0.0**

### Code Review Findings

#### Matches plan

- The hexagonal layering is exactly as designed: driven port in `config`, adapter in `config-adapters`, thin inbound in the launcher owning the byte-exact block. The `explain` diagnostic is derived from a **single** `assemble()` pass, with no second read path and no `explain()` on the port, as the plan insisted.
- `has_body` and block membership are computed with the *same* `trim_blank_lines` predicate, so they cannot disagree — the invariant the plan called out is genuinely enforced (`cli/config/src/context.rs:74-84`).
- `read_raw` puts absent-file and IO-error semantics in one place; `read` and `read_body` provably agree over one raw read (pinned by a test).
- `Level::file_name()` is a single source for the two filenames, consumed by both the store and `explain_lines` — no hand-copied literals, as specified.
- The registry test walks `.claude-plugin/plugin.json` rather than a hard-coded list, with a vacuity guard, so a future skill is auto-enrolled and fails until wired.
- All 11 acceptance criteria on work item 0016 are met, including the load-bearing ones: byte-exact header/prose (AC-7, pinned by `renders_the_byte_exact_block`), placement before skill-specific instructions (AC-6, pinned by `test_line_sits_under_the_h1_before_any_subsection`), and the all-skills registry enumeration (AC-9).

#### Deviations from plan

Three are **recorded in the plan** and are sound. A fourth was **not** recorded — it was found during this validation and fixed.

- ✓ **`context --fail-safe`** (recorded). The plan's contingency mispredicted the failure mode: the `!`-preprocessor does not render a non-zero exit opaquely, it *discards the whole prompt*. The typed `OnFailure::{Fail, Degrade}` policy is a better answer than the plan's fallback, and the default stays fail-loud so every Phase 1 criterion still holds. Verified live against the built binary: malformed config → `## Project Context Unavailable` on stdout naming the file, exit 0; without the flag → exit 1, error on stderr.
- ✓ **Behavioural fixture redesigned** (recorded). Rewriting the imperative token-emission body as declarative project context is correct — the model rightly refuses the former as prompt injection.
- ✓ **Eval-harness stale-binary fix** (recorded). Genuinely out of the original scope and genuinely necessary: the eval was staging a binary that had no `context` subcommand.
- ⚠️ → ✓ **The golden-coherence assertion did not guard the Rust-to-Python seam** (**not recorded; the plan marked this item `[x]`**). Phase 3 required pinning the eval's header/prose "byte-for-byte against the same literal the Rust byte-exact `render` unit test asserts (a committed expected-string fixture the two tests share, or a check that re-runs `luminosity context` on a known body and compares)". **Neither was implemented.** `BLOCK_PREFIX` was an independent Python literal, and `_expected_block()` rebuilt the goldens *from that same literal* — so the test only pinned Python against Python.

  Proved empirically: mutating the Rust `PROSE` const failed the Rust suite but left **every Python test passing**. The module docstring's claim — *"a change to the Rust prose that is not mirrored here fails loudly rather than silently staling the eval"* — was false as written. A prose change would have been fixed on the Rust side, and the stale Python golden would then have surfaced only in a live eval run, never in CI.

  **Fixed during this validation.** `test_block_prefix_matches_the_rust_source` now extracts the `## Project Context` header and the `PROSE` const **from the Rust source** and pins `BLOCK_PREFIX` against them — catching drift in CI without making the unit suite depend on a built binary. This follows the repo's existing idiom for hand-synced mirrors (the `msrv`/rust-pin coherence test likewise reads both files and compares).

  Verified as a real guard rather than a tautology: mutating the Rust `PROSE` **or** the `render()` header each turns the test red, and the unmutated source is green. The extractor is anchored on `{PROSE}`, so `render_unavailable`'s separate heading is correctly ignored. The docstring now states only what the code enforces.

#### Potential issues

- **`--explain` is silently suppressed under a degraded failure.** `context --explain --fail-safe` against a malformed config prints the Unavailable notice and *no* per-level lines (the `Degrade` arm returns early). Verified live. This is defensible — the error *is* the diagnosis, and per-level `has_body` is meaningless for an unreadable file — but the interaction is unspecified in the plan, untested, and undocumented in the flag help.
- **The wrapper prose now exists in three hand-synced copies** (Rust `PROSE`, the integration test's `BLOCK_HEADER`, the Python `BLOCK_PREFIX`). The Rust pair guards itself; the Python copy is the unguarded one, per the finding above.
- **The `allowed-tools` grant is `…luminosity context*`** (no space), broader than the sibling `…luminosity config *`. Harmless and necessary for `--fail-safe`, but worth a conscious nod.
- **A config file with no `---` fence becomes 100% project context.** Pre-existing `frontmatter::split` behaviour, now newly load-bearing. Covered by a test and consistent with AC-8.
- **`LUMINOSITY_EVAL_LIVE` is a whole-suite gate, not the per-arm gate Phase 3 describes.** The plan said to "gate the behavioural arm behind the live-eval switch, keeping it out of the deterministic CI path". No per-arm gate was built — but the entire skill-eval suite already sits behind that switch and outside `mise run`, so the plan's *intent* is satisfied by construction. Benign.

### Manual Testing Required

The plan's manual steps were all re-verified during this validation against the freshly built binary — no outstanding manual testing:

1. Reader behaviour:
  - [x] Team + personal bodies → block printed, team first
  - [x] Both bodies empty/absent → empty stdout, exit 0
  - [x] Malformed body → exit 1, empty stdout, filename on stderr
  - [x] `--explain` → block on stdout, per-level diagnostics on stderr
2. Skill injection:
  - [x] Live `claude -p` probe reported the block present above the skill's own instructions, and absent with empty bodies (recorded in the plan's Phase 2 manual criteria)

### Recommendations

1. ~~**Close the golden-coherence gap.**~~ **Done during this validation** — see the fourth deviation above. `mise run check` and `mise run test` are green with the new guard in place.
2. **Add a test for `--explain --fail-safe`** pinning the current suppression as intended behaviour, and mention it in the flag's help text. (Open — a small robustness gap, not a plan requirement.)
3. **Bookkeeping before merge**: work item 0016 is still `status: ready` with all eleven acceptance criteria unchecked, despite being met. The branch is also behind `main` (`mergeable_state: behind`) and needs a rebase.
4. Consider a follow-up to memoise the project-root discovery walk — `LazyConfigBody::read_body` discovers the store per level, so one `assemble()` walks the filesystem twice. Cheap, pre-existing pattern, not worth blocking on.

**Plan status advanced to `done`** — every phase is implemented, every automated check is green, all eleven acceptance criteria are met, and the one gap this validation surfaced has been closed.
