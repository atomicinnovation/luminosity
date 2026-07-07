---
type: plan-review
id: "2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-review-1"
title: "Plan Review: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate"
date: "2026-07-02T15:28:10+00:00"
author: "Toby Clemson"
producer: review-plan
target: "plan:2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate"
reviewer: "Toby Clemson"
verdict: "APPROVE"
lenses: [architecture, correctness, test-coverage, code-quality, safety, standards]
review_number: 1
review_pass: 2
tags: [rust, workspace, cargo, refactor, build-system, mise, ci]
last_updated: "2026-07-02T16:21:15+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Plan Review: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate

**Verdict:** REVISE

This is an exceptionally thorough, structurally sound refactor plan: the
directory-vs-package-name decoupling is stated as the load-bearing invariant
and threaded correctly through every edit, the gap sites the research surfaced
(the `tasks/__init__.py` explicit registrations, the function-named `build.cli`
task, the extra test files) are all folded into the edit list, and the atomic
single-merge delivery avoids any mixed-naming state on `main`. Four of the six
lenses (architecture, correctness, test-coverage, code-quality) found only minor
observations. The REVISE verdict is driven by three actionable majors — a
proposed constant line that breaches the 80-col limit and would fail the plan's
own green-build criterion, and two operational-safety gaps in the CI
required-check switchover (the rename-PR merge deadlock and the absent rollback
path) that the plan under-specifies.

### Cross-Cutting Themes

- **The `LAUNCHER_CRATE` line is a hotspot** (flagged by: standards,
  code-quality, test-coverage) — the single proposed line
  `LAUNCHER_CRATE = "luminosity"  # must equal cli/launcher/Cargo.toml [package] name`
  attracts three independent concerns: it is 82 chars (breaks 80-col), its
  name no longer telegraphs its value (`"luminosity"`, unlike sibling
  `KERNEL_CRATE`), and that value invariant is bound by no unit test.
- **The reference sweep is a task/path guarantee, not a prose guarantee**
  (flagged by: correctness, code-quality, standards) — the grep targets
  task/constant tokens (`build:cli`, `CLI_CRATE`, …) but not bare-noun `cli`
  prose, so stale/ambiguous wording survives it: the `test/launcher.py` docstring
  ("cli-crate"), `README.md`/`CLAUDE.md` phrases ("Rust cli crate", "cli unit
  tests"), several `mise.toml` task descriptions (lines 31, 59, 153, 232's "cli
  tests" clause), and — most materially — **CLAUDE.md line 69's `cli/Cargo.toml`
  reference, which becomes a dead path** after the move. The work item explicitly
  asked for CLAUDE.md's `cli/` references to be updated, so this is an in-scope
  miss, not just cosmetic drift.
- **The CI required-check switchover is the highest-risk, no-local-signal
  step** (flagged by: safety; touched by architecture) — Group H is the one
  action with no local feedback, and the plan describes it as "add the new
  names" without spelling out the deadlock, the removal of the old names, or a
  rollback path.

### Tradeoff Analysis

- **Scope minimalism vs naming clarity**: The container is named `cli/` — the
  exact directory the launcher crate is vacating — while the `cli/` → `crates/`
  rename is deferred. This keeps the change small (architecture lens endorses
  the deferral) but leaves a transitional overload where `cli/` denotes a
  container that also holds the domain `kernel` crate. Recommendation: accept
  for this atomic change; ensure the eventual `crates/` rename stays tracked so
  the overload doesn't calcify.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Standards**: Proposed `LAUNCHER_CRATE` comment line breaches the 80-col limit
  **Location**: Phase 1, Group B — Path + crate constants (`tasks/shared/rust.py`)
  The literal line `LAUNCHER_CRATE = "luminosity"  # must equal cli/launcher/Cargo.toml [package] name`
  is **82 characters** (verified; current `CLI_CRATE` line is 67). `pyproject.toml`
  sets ruff `line-length = 80`, so this trips E501 and would fail `mise run check`
  / `mise run` — contradicting the plan's own success criterion.

- 🟡 **Safety**: Rename PR is gated by old required-check names that will never report
  **Location**: Group H; Implementation Approach step 9; Migration Notes
  The jobs `check-cli` / `build-cli` are renamed in the same PR that must merge
  through branch protection, which still requires the old display names. Those
  names no longer exist on the PR head, so the required checks sit permanently as
  "Expected — waiting for status to be reported". Group H says re-register "after
  the renamed jobs have run" but never states the old names must be **removed** as
  part of the same action — otherwise the PR wedges unmergeable, or an admin
  force-merge opens a window where main's Rust guard-rail jobs gate nothing.

- 🟡 **Safety**: No stated recovery/rollback path if the required-check switch fails mid-way
  **Location**: Phase 1 — atomic delivery; Migration Notes ("same merge window")
  The plan commits to doing the merge and the manual re-registration "in the same
  merge window" but gives no recovery procedure if the manual step is interrupted
  or done wrong. Because the workflow triggers on both `push` and `pull_request`,
  a half-applied protection rule affects every open and subsequent PR.

#### Minor

- 🔵 **Correctness**: CLAUDE.md directory-path prose omitted from the edit list — one becomes a dead path
  **Location**: Group G — Docs / prose (`CLAUDE.md`)
  The CLAUDE.md edit list enumerates only the task-token lines (20,24,25,27,28,47),
  but CLAUDE.md also carries directory-path prose the move invalidates: line 69
  ("version lives in `cli/Cargo.toml`"), line 65 (the "Rust workspace" heading
  path), and line 83 ("The `cli/` crate is a throwaway bootstrap"). After the move
  `cli/Cargo.toml` no longer exists (it is `cli/launcher/Cargo.toml`). These use
  bare `cli/`, which is not a sweep pattern, so the grep passes while the primary
  onboarding doc points at a dead path — and the work item explicitly asked for
  CLAUDE.md's `cli/` references to be updated.

- 🔵 **Correctness**: `mise.toml` bare-word "cli-crate" descriptions left stale, uncaught by the sweep
  **Location**: Group D — mise tasks (`mise.toml`)
  Group D names only lines 157 and 232, but descriptions at line 31 ("the cli
  checks need"), line 59 ("Run cli-crate unit tests"), line 153 ("Run all
  cli-crate format and lint checks"), and the "(cli tests carry coverage)" clause
  on line 232 still call the relocated crate "cli". None match the sweep patterns,
  so the renamed tasks' own `mise tasks` descriptions still refer to the crate by
  its old name.

- 🔵 **Code Quality**: `tasks/test/launcher.py` docstring left as "cli-crate"
  **Location**: Group C — `tasks/test/launcher.py`
  The edit list names the `CLI_CRATE` import, the two `-p {…}` uses, and the
  failure message, but not the docstring ("Run cli-crate unit tests …"). The
  module becomes `launcher.py` with a `launcher` task but keeps "cli-crate" prose;
  the reference-sweep grep does not search the bare word "cli-crate".

- 🔵 **Code Quality**: `LAUNCHER_CRATE` name no longer telegraphs its value
  **Location**: Group B — `tasks/shared/rust.py`
  `LAUNCHER_CRATE = "luminosity"` sits beside `KERNEL_CRATE = "kernel"`, whose
  name mirrors its value. A maintainer may misread `LAUNCHER_CRATE` as holding
  `"launcher"` and propagate a `-p launcher` flag — the exact mistake the plan
  flags as a regression. The retained invariant comment is the sole in-code signal
  reconciling the divergence (and is a justified comment under the low-tolerance
  rule).

- 🔵 **Test Coverage**: Many flipped assertions pass trivially — weak red-then-green signal
  **Location**: Group F (`test_mise_wiring.py`); Success Criteria (red-first)
  A large fraction of the flipped assertions are negative/absence checks
  (`"build:cli" not in …`, `"coverage:cli:check" not in names`) or invariants for
  tasks that never exist in either state; they pass both before and after. Genuine
  red→green rests on the positive exact-array/exact-dependency assertions. The
  "confirms the assertions bind" step should sanity-check those specifically.

- 🔵 **Test Coverage**: No unit test binds `LAUNCHER_CRATE`'s value to the Cargo package name
  **Location**: Group B; Testing Strategy (value-preservation edge)
  The chief correctness risk (rewriting `luminosity`→`launcher`) is only caught at
  integration level (`build:launcher`, `CARGO_BIN_EXE_luminosity`). A lockstep
  value-rewrite in both source and test would survive the fast unit suite. The
  edition-coherence test already parses `cli/launcher/Cargo.toml`; one assertion
  that `LAUNCHER_CRATE == [package].name` would convert the invariant comment into
  a tested invariant.

- 🔵 **Standards**: Bare-noun `cli` prose collides with the new `cli/` container
  **Location**: Group G — Docs / prose (`tasks/README.md`, `CLAUDE.md`)
  Post-rename, bare `cli` legitimately denotes the container directory, but prose
  like "Rust cli crate" (README:14) and "cli unit tests" (README:32) still means
  the launcher crate — now ambiguous, and not targeted by the sweep.

- 🔵 **Architecture**: Attestation `subject-path` remains a hand-maintained triplicate of `BIN_DIR`
  **Location**: Group E — CI; Group B — Path constants
  The change repoints three `subject-path` copies but leaves them a hand-synced
  mirror of `BIN_DIR` — the deferred `cli/`→`crates/` rename will require the same
  lockstep edit with no automated binding. Acknowledged pre-existing; a follow-up
  could derive the path from `BIN_DIR`.

- 🔵 **Safety**: Release/attestation path depends on the rename being internally consistent
  **Location**: Group E — prerelease `needs:` edges (main.yml:234-235)
  The `prerelease` job's two `needs` edges and three `subject-path` copies are the
  only thing between a merge and an attested build; a single missed edge breaks
  provenance on the first post-merge push. Keep the Group E criterion and verify
  the first prerelease run attaches a non-empty attestation.

#### Suggestions

- 🔵 **Correctness**: CLAUDE.md line 28 carries both `build:cli` and `build-cli`; only `build:cli` is called out
  **Location**: Group G — Docs / prose (`CLAUDE.md` line 28)
  The Group G note lists only the `build:cli`→`build:launcher` rename on line 28,
  not the co-located `build-cli` CI-job token. Unlike the prose gaps, `build-cli`
  IS a sweep pattern, so this is self-correcting (a missed edit fails the sweep)
  rather than a latent defect — but call it out so a line-by-line implementer isn't
  surprised.

- 🔵 **Code Quality**: Broaden or re-frame the reference sweep for prose
  **Location**: Success Criteria — reference-sweep grep
  Either state the sweep is a task/path guarantee only (prose coherence resting on
  the enumerated Group C/G edits), or add a case-insensitive `\bcli\b` pass over
  `tasks/` docstrings/comments as a final coherence check.

- 🔵 **Test Coverage**: Flag the orphaned `fake_repo_tree` fixture explicitly
  **Location**: Group F — `tests/conftest.py`
  The fixture is unused and guards no test (confirmed); its edit is pure coherence.
  The `CARGO_TOML`/`CHECKSUMS` constants it mirrors have no unit coverage
  (no `test_version.py`). Out of scope to fix, but note it so a reviewer isn't
  misled that the conftest edit adds regression protection.

- 🔵 **Architecture**: Track the `cli/` → `crates/` rename so the container-name overload doesn't calcify
  **Location**: What We're NOT Doing; Overview
  The `cli/` container name overloads the abandoned crate-directory name and now
  holds a non-cli `kernel` crate. No action for this change; ensure the eventual
  rename stays tracked.

### Strengths

- ✅ The directory-vs-package-name decoupling is stated as the load-bearing
  invariant and applied consistently — `pup.ron`, `deny.toml` cross-crate bans,
  and version coherence need no edits and stay correct by construction.
- ✅ The `../kernel` sibling path dep is preserved (both crates move together) and
  the plan insists on *proving* it via a green `build:launcher` rather than
  assuming.
- ✅ Delivered atomically as one merge — no window where directory layout and
  task/CI-job names disagree on `main`.
- ✅ The reference sweep is genuinely exhaustive over task/constant tokens; an
  independent grep of the non-meta files confirms every hit is accounted for, and
  the token list is deliberately specific so surviving `cli/launcher/…` paths
  don't false-positive.
- ✅ The two dangling-import loci (`tasks/__init__.py` explicit `from_module`
  registrations AND the submodule `__init__.py` re-exports) are both caught — a
  subtle Python namespace hazard a superficial module rename would miss.
- ✅ The complete set of tests pinning old names is covered, including the gap
  sites (`test_build.py`, `test_format.py`, `test_lint.py`, `conftest.py`) beyond
  the three the work item named.
- ✅ The task-tree shape convention is preserved exactly: lint/format/test stay
  `<verb>/<component>.py` modules while build stays a function-named task, matching
  what `tasks/README.md` documents; the `kernel:check` asymmetry (and its stale
  `mise.toml:157` prose) is handled.
- ✅ The integration backstop is strong: `cli/tests/version.rs` pins
  `CARGO_BIN_EXE_luminosity` and the `luminosity ` output prefix, so a
  value-rewrite regression fails the compiled test even though no unit test binds
  the constant.

### Recommended Changes

1. **Shorten the `LAUNCHER_CRATE` comment to fit 80 cols** (addresses: 80-col
   breach). Replace the proposed Group B line with one ≤ 80 chars — e.g.
   `LAUNCHER_CRATE = "luminosity"  # = cli/launcher/Cargo.toml [package] name`
   (72 chars), or move the invariant note to a standalone `#` line above the
   constant. This directly protects the plan's own "`mise run check` exits 0"
   criterion.

2. **Turn Group H into an explicit ordered runbook** (addresses: rename-PR
   deadlock, no rollback path). Spell out: (1) push the branch so `Check launcher`
   / `Build launcher (…)` run once on the PR head; (2) in the same
   branch-protection visit **add the three new names AND remove the three old
   `cli` names**; (3) then merge. Add a rollback note: if the switch can't be
   completed, either revert the one atomic commit (restoring the old job names so
   the still-registered old checks report) or temporarily drop the affected checks
   from the required list. Note the merger must hold branch-protection edit rights.

3. **Add the `tasks/test/launcher.py` docstring to the Group C edit list**
   (addresses: half-renamed "cli-crate"). "Run cli-crate unit tests" → "Run
   launcher-crate unit tests" (value/behaviour unchanged).

4. **Extend the edit list to the stale/dead prose the sweep can't catch**
   (addresses: CLAUDE.md dead path, mise.toml stale descriptions, bare-noun
   ambiguity, "cli-crate" docstring). Highest priority: repoint CLAUDE.md line 69
   `cli/Cargo.toml` → `cli/launcher/Cargo.toml` (currently a dead path) and adjust
   lines 65/83. Also update the `mise.toml` descriptions (lines 31, 59, 153, 232's
   "cli tests" clause) and reword README/CLAUDE.md "Rust cli crate" / "cli unit
   tests" → "launcher crate" / "launcher unit tests" so bare `cli` reads
   unambiguously as the container directory. Note CLAUDE.md line 28 carries both
   `build:cli` and `build-cli`.

5. **(Optional) Add one unit assertion binding `LAUNCHER_CRATE` to the manifest
   `[package].name`** (addresses: untested value invariant). Alongside the existing
   edition-coherence test that already parses `cli/launcher/Cargo.toml`, assert
   `LAUNCHER_CRATE == [package].name` — converting the hand-maintained comment into
   a tested invariant and catching a lockstep value-rewrite in the fast unit suite.

6. **(Optional) Clarify the reference sweep's scope** (addresses: prose escapes the
   grep). State that the sweep guarantees task/path tokens only and prose coherence
   rests on the Group C/G edits, or add a `\bcli\b` prose pass as a final check.

## Per-Lens Results

### Architecture

**Summary**: A well-scoped, structurally sound refactor — a pure directory
relocation plus an identifier/task rename that deliberately preserves the
package/binary name `luminosity` and every package-name-driven reference. The
plan correctly identifies the load-bearing invariant (directory identity vs
package identity are decoupled) and threads it through every edit, keeping
architecture enforcement (cargo-pup inward rule, cargo-deny cross-crate
ban-list, `../kernel` sibling path dep) unaffected. Atomic single-merge delivery
avoids any mixed-naming intermediate state; the reference-sweep-as-safety-net
compensates well for the repo's acknowledged lack of an automated cross-reference
check.

**Strengths**:
- The directory-vs-package-identity insight is stated and applied consistently,
  so `pup.ron`, `deny.toml` bans, and version coherence need no edits.
- The `../kernel` sibling relationship is preserved and proven via green
  `build:launcher` rather than assumed.
- Atomic single-merge delivery eliminates mixed-naming windows on `main`.
- The reference sweep is genuinely exhaustive (independent grep of the 17
  non-meta files confirms every hit is accounted for) and deliberately specific.
- Both dangling-import loci are identified.

**Findings**:
- 🔵 minor / high — **Attestation subject-path remains a hand-maintained
  triplicate of BIN_DIR after the move** (Group E; Group B). Repoints three
  copies but leaves the coupling; a future `crates/` rename repeats the lockstep
  edit with no automated binding. Acknowledged pre-existing; consider a follow-up
  deriving the path from `BIN_DIR`.
- 🔵 suggestion / medium — **Container name `cli/` overloads the abandoned
  crate-directory name** (What We're NOT Doing; Overview). Now denotes a container
  that also holds the domain `kernel` crate while the `crates/` rename is
  deferred. No action required; keep the eventual rename tracked.

### Correctness

**Summary**: On the axis that matters for a rename/relocate — completeness and
accuracy of reference edits — the plan is exceptionally thorough. Every
line-number citation checked against the live tree is exact (mise.toml depends
edges 70/110/114/154/213/217/229/233; the six run-body invoke renames; main.yml
job keys 106/129, needs 234/235, subject-path 272/327/342; the
paths.py/rust.py/build.py/targets.py/deps.py/conftest.py sites), the invariant
value `luminosity` is preserved wherever it must be, and the two-step `mv` dance
is a correct, self-avoiding relocation under jj. The only defects are stale prose
references the sweep won't catch because they use bare `cli` as a word — most
materially CLAUDE.md's `cli/Cargo.toml`, which becomes a dead path.

**Strengths**:
- Every verified line-number citation is exact across mise.toml, main.yml,
  paths.py/rust.py/build.py/targets.py/deps.py/conftest.py, and the test files.
- The directory-vs-package decoupling is applied correctly: the value
  `luminosity` is preserved at every `-p`, `--bin`, `[[bin]]`, pup.ron rule, and
  source import; only identifiers/task/module/job names change.
- The two-step `mv` dance avoids the self-nesting trap; plain `mv` (not `jj mv`)
  is right under jj's content-tracked working copy.
- The non-obvious gap sites are captured (the two `Collection.from_module`
  registrations, the function-named `build.cli` task, the split namespace
  assembly).
- `pup.ron` correctly left untouched — verified to contain no `cli` token; rules
  key on package-name module paths.

**Findings**:
- 🔵 minor / high — **CLAUDE.md directory-path prose omitted; one becomes a dead
  path** (Group G). Lines 65/69/83 use bare `cli/`; line 69's `cli/Cargo.toml` no
  longer exists after the move. Not a sweep pattern, so the grep passes while the
  onboarding doc points at a dead path. Add these to the Group G edit list.
- 🔵 minor / high — **mise.toml bare-word "cli-crate" descriptions left stale**
  (Group D). Lines 31, 59, 153 and 232's "cli tests" clause still call the crate
  "cli"; none match the sweep patterns. Extend Group D or note them as intentional
  generic prose.
- 🔵 suggestion / medium — **CLAUDE.md line 28 carries both `build:cli` and
  `build-cli`; only `build:cli` is called out** (Group G). Self-correcting
  (`build-cli` is a sweep pattern), but call it out for a line-by-line
  implementer.

### Test Coverage

**Summary**: The test-flip strategy is fundamentally sound: it identifies every
existing test pinning an old task/job/path name, and explicitly guards the
load-bearing value invariant (`luminosity` must not become `launcher`). The main
weakness is that a large fraction of the flipped assertions are negative/absence
checks or invariant guards that pass trivially in both states, so they don't
deliver a genuine red-then-green signal — the real protection rests on a handful
of exact-array positive assertions plus the whole-repo `mise run`. Coverage is
otherwise proportional to a low-risk rename, and the integration backstops
(compiled `CARGO_BIN_EXE_luminosity` test plus `build:launcher`) meaningfully
protect the invariants the unit suite leaves unbound.

**Strengths**:
- Complete set of name-pinning tests covered, including the gap sites beyond the
  three the work item named; clean suites correctly identified.
- Explicitly flags the value-preservation hazard.
- Strong integration backstop pairs the red-first flip with the compiled version
  test and the real `cargo build --bin luminosity`.
- `TestFinalEnumeratedArrays` gives genuine mutation-resistant coverage for mise
  wiring.

**Findings**:
- 🔵 minor / high — **Many flipped assertions pass trivially and give no
  red-then-green signal** (Group F; Success Criteria). Negative/absence checks and
  never-exist-task invariants pass both before and after; genuine red→green rests
  on the positive exact-array/exact-dependency assertions. Sanity-check those
  specifically transition red→green.
- 🔵 minor / medium — **No unit-level test binds `LAUNCHER_CRATE`'s value to the
  Cargo package name** (Group B; Testing Strategy). A lockstep value-rewrite
  survives the fast unit suite; only `build:launcher` / `CARGO_BIN_EXE_luminosity`
  catch it. Add one assertion alongside the edition-coherence test.
- 🔵 minor / medium — **conftest fixture edit guards no test; underlying
  `version.py` path handling is untested** (Group F; Current State Analysis). The
  orphaned `fake_repo_tree` and the absence of `test_version.py` mean the
  `CARGO_TOML`/`CHECKSUMS` repointing is covered only by `mise run`. Flag the
  fixture explicitly so the edit isn't mistaken for regression protection.

### Code Quality

**Summary**: A well-scoped, exhaustively-researched mechanical rename; it
correctly separates directory/task-name-driven references (change) from
package-name-driven ones (keep `luminosity`), and the reference sweep is a sound
safety net given no automated cross-reference check. The main risks are two
naming/coherence smells: the constant `LAUNCHER_CRATE` now holds the value
`luminosity` (a name that no longer telegraphs its value, unlike its
`KERNEL_CRATE` sibling), and a couple of prose/docstring sites that still say
`cli` are not enumerated for renaming, leaving half-renamed identifiers the sweep
won't catch.

**Strengths**:
- Crisp directory-vs-package distinction; repeatedly warns that rewriting
  `luminosity`→`launcher` is a regression.
- The sweep is an appropriate, verifiable safety net enumerating the stale tokens.
- Group C folds in the non-obvious gap sites (explicit registrations, the
  function-named build task, targets/deps strings).
- The retained invariant comment is justified under the low-comment-tolerance rule.

**Findings**:
- 🔵 minor / high — **`tasks/test/launcher.py` docstring left as "cli-crate"**
  (Group C). Add the docstring to the edit list: "Run cli-crate unit tests" →
  "Run launcher-crate unit tests".
- 🔵 minor / medium — **`LAUNCHER_CRATE` name no longer telegraphs its value**
  (Group B). Beside `KERNEL_CRATE = "kernel"` the divergence invites a `-p
  launcher` mistake; keep the invariant comment adjacent as the reconciling signal.
- 🔵 minor / medium — **Reference sweep doesn't catch prose fragments the plan
  itself rewrites** (Success Criteria). It won't flag "cli-crate"/"cli tests"
  prose; either re-frame the sweep as a task/path guarantee or add a `\bcli\b`
  prose pass.

### Safety

**Summary**: A low-criticality build-tooling refactor with no committed data at
risk — `checksums.json` and the `luminosity-*` binaries are uncommitted build
artifacts that regenerate, so the data-loss surface is near-zero and the `mv`
dance is correct and reversible. The dominant hazard is operational: the Group H
required-check re-registration is a manual GitHub-settings step with no local
signal, and the plan under-specifies the ordering deadlock it creates — the
rename PR is itself gated by the OLD required-check names, which never report once
the jobs are renamed, so the PR can wedge unmergeable and/or a window opens where
main's guard-rail jobs don't gate. The rollback story for a mid-way failure is
unstated.

**Strengths**:
- No committed data at risk; regeneration correctly treated as expected.
- The two-step `mv` dance correctly avoids the move-into-itself hazard and is
  VCS-reversible under jj.
- The `mise run` + reference-sweep gate strongly signals main won't be left broken
  by the code/config portion.
- The plan explicitly flags Group H as the sole no-local-signal coupling.

**Findings**:
- 🟡 major / high — **Rename PR is gated by old required-check names that will
  never report — merge deadlock / ungated window** (Group H; step 9; Migration
  Notes). Make Group H an explicit ordered runbook that ADDS the new names AND
  REMOVES the old ones in the same action; note an admin bypass leaves an ungated
  window until that completes.
- 🟡 major / medium — **No stated recovery/rollback path if the switch fails
  mid-way** (Phase 1; Migration Notes). Add a rollback note (revert the atomic
  commit, or temporarily drop the affected checks) and confirm the merger holds
  branch-protection edit rights.
- 🔵 minor / medium — **Release/attestation path depends on internal YAML
  consistency** (Group E; main.yml:234-235). A missed `needs` edge or
  `subject-path` copy breaks prerelease provenance on the first post-merge push;
  keep the Group E criterion and verify the first run attaches a non-empty
  attestation.

### Standards

**Summary**: Strongly convention-aware — preserves the documented task-tree shape
(lint/format/test stay `<verb>/<component>.py` modules while build stays a
function-named task), keeps the `<component>:check` roll-up and `build:<component>`
naming, leaves the package/binary name and all package-name-keyed references
invariant, and handles the `kernel:check` asymmetry (including the stale
`mise.toml:157` prose). Two issues remain: one proposed literal line breaches the
hand-synced 80-col limit and would fail `mise run check`, and the rename leaves
bare-noun `cli` prose that the sweep doesn't target, colliding with the new `cli/`
container.

**Strengths**:
- Preserves the task-tree module/function asymmetry exactly as documented.
- Keeps naming conventions intact (`launcher:check` entity-first roll-up;
  `build:launcher` continues the directory-basename convention).
- Correctly handles the `kernel:check` asymmetry and its stale description.
- Keeps the four hand-synced mirrors coherent by scope (no crate/package name
  change → msrv/80-col mirrors untouched; `pup.ron`/`clippy.toml`/`rustfmt.toml`
  correctly left alone).
- The retained invariant comment is exactly the permitted kind under the
  low-comment-tolerance rule.

**Findings**:
- 🟡 major / high — **Proposed `LAUNCHER_CRATE` comment line breaches the 80-col
  limit** (Group B). The line is 82 chars (verified); ruff `line-length = 80`
  trips E501 and fails `mise run check`. Shorten the comment or move it to a
  standalone line above the constant.
- 🔵 minor / medium — **Bare-noun `cli` prose for the launcher crate collides with
  the new `cli/` container and escapes the sweep** (Group G). Reword "Rust cli
  crate" / "cli unit tests" in README/CLAUDE.md to "launcher crate" / "launcher
  unit tests".

---
*Review generated by /accelerator:review-plan*

## Re-Review (Pass 2) — 2026-07-02T16:21:15+00:00

**Verdict:** APPROVE

Re-ran the five lenses that carried findings (safety, standards, correctness,
code-quality, test-coverage) against the edited plan, each given its prior
findings to verify resolution. **All prior findings are resolved** (or, for one
test-coverage item, deliberately scoped out and transparently flagged). The
re-review surfaced **one new major** — the `CLI_CRATE`→`LAUNCHER_CRATE` rename
pushes `tasks/build.py:80`'s `cargo build --bin` line from 77 to **82 cols** (E501,
verified against the live file), which would have failed `mise run` at the last
step — plus two cosmetic residuals. All three were then fixed in the plan, so the
plan now carries no outstanding critical or major findings.

### Previously Identified Issues

- 🟡 **Safety**: Rename PR gated by old required-check names (merge deadlock) —
  **Resolved**. Group H is now an ordered runbook that adds new names and removes
  old ones in one settings visit, with the deadlock mechanism spelled out.
- 🟡 **Safety**: No stated recovery/rollback path — **Resolved**. A Rollback
  subsection + Migration Notes cross-reference give two recovery options and name
  the branch-protection-rights precondition. (A new residual on option wording was
  raised and fixed — see below.)
- 🟡 **Standards**: `LAUNCHER_CRATE` comment breaches 80 cols — **Resolved**. The
  reworded line is 79 cols (verified).
- 🔵 **Correctness**: CLAUDE.md dead path (`cli/Cargo.toml`) + lines 65/83 —
  **Resolved**. Added to Group G; line numbers verified exact against the live
  file.
- 🔵 **Correctness**: mise.toml bare-word "cli" descriptions (31/59/153/232) —
  **Resolved**. Enumerated in Group D; line numbers verified exact.
- 🔵 **Correctness**: CLAUDE.md line 28 both `build:cli` and `build-cli` —
  **Resolved**. Group G notes both tokens.
- 🔵 **Code Quality**: `test/launcher.py` docstring "cli-crate" — **Resolved**.
  Added to Group C (plus the `coverage_enabled` docstring in Group B).
- 🔵 **Code Quality**: `LAUNCHER_CRATE` name doesn't telegraph its value —
  **Resolved** via the reworded comment **and** the new machine-checked coherence
  test (the strongest available mitigation).
- 🔵 **Test Coverage**: trivially-passing flipped assertions — **Resolved**. The
  red-first criterion now distinguishes genuine red→green assertions from
  coherence-only ones.
- 🔵 **Test Coverage**: `LAUNCHER_CRATE` value not bound by a unit test —
  **Resolved**. New `TestToolchainCoherence` assertion binds it (sound red→green:
  ImportError before Group B, passes after).
- 🔵 **Test Coverage**: orphaned conftest fixture / untested `version.py` path
  resolution — **Partially resolved**. The misleading-guard concern is fixed (the
  edit is transparently labelled coherence-only); the deeper "no fast unit test for
  `version.py` path resolution" gap is deliberately left to end-to-end `mise run`,
  an accepted scoping choice for a directory-move refactor gated end-to-end.
- 🔵 **Architecture**: subject-path triplicate; `cli/` container overload — **Not
  re-run** (deferred follow-ups by design; no edits were made for them, so
  re-running would only re-surface the same known-deferred observations).

### New Issues Introduced

- 🟡 **Standards** (NEW, now **fixed**): `CLI_CRATE`→`LAUNCHER_CRATE` (+5 chars)
  pushed `tasks/build.py:80` to 82 cols (E501), which would fail `mise run`. Fixed
  by wrapping the f-string across two implicitly-concatenated lines (64 / 37 cols,
  verified; ruff-format leaves implicit concatenation unjoined). This was the one
  line the rename overflowed.
- 🔵 **Safety** (NEW, now **fixed**): the rollback's "revert the atomic commit"
  option assumed a merged commit, but the deadlock it pairs with is pre-merge.
  Fixed by splitting the rollback guidance into explicit pre-merge and post-merge
  cases.
- 🔵 **Code Quality / Standards** (NEW, now **noted**): the reworded comment uses
  "matches" while the sibling `KERNEL_CRATE` keeps "must equal". Addressed by a
  note in the plan marking the verb divergence a deliberate width workaround (and
  pointing at the new coherence test as the real guarantee).

### Assessment

The plan is in strong shape and ready for implementation. Every finding from the
initial review is resolved, the one genuine build-breaker the edits themselves
introduced (the `build.py` 80-col overflow) was caught and fixed, and the residual
test-coverage gap (`version.py` path resolution) is a low-risk, explicitly-accepted
reliance on the end-to-end `mise run` gate. Verdict upgraded REVISE → APPROVE.

---
*Re-review generated by /accelerator:review-plan*
