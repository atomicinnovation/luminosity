---
type: plan-review
id: "2026-07-20-0018-per-skill-instructions-injection-review-1"
title: "Plan Review: Per-Skill Instructions Injection"
date: "2026-07-19T23:43:19+00:00"
author: "Toby Clemson"
producer: review-plan
status: complete
target: "plan:2026-07-20-0018-per-skill-instructions-injection"
reviewer: "Toby Clemson"
verdict: "APPROVE"
lenses: [architecture, code-quality, test-coverage, correctness, security, usability, standards, documentation]
review_number: 1
review_pass: 2
tags: [configuration, instructions-injection, rust-cli, skills, evals]
last_updated: "2026-07-20T08:09:21+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Plan Review: Per-Skill Instructions Injection

**Verdict:** REVISE

This is a disciplined, unusually well-grounded plan: a behaviour-neutral
`Fragment` kernel rename followed by folding a third document kind through an
already-proven, source-agnostic assembly core, sequenced into small test-first
phases that lean hard on the 0017 template. The domain modelling (kind-bearing
enum making illegal states unrepresentable, one shared port, context/instructions
distinction kept at the edges) is strong, and the fail-safe boundary is treated as
a first-class concern. It nets REVISE rather than APPROVE for a narrow set of
reasons: Phase 4 as written references eval infrastructure that does not exist in
the repo (verified) and lands a hard-red CI gate that contradicts the plan's own
per-phase-green mergeability guarantee, and a user-facing wording mismatch
("take precedence" vs the injected "in addition to") promises behaviour the
mechanism does not encode. The fixes are mostly to the plan's prose and Phase 4
scoping, not to the design.

### Cross-Cutting Themes

- **Phase 4 breaks the "every phase green and independently mergeable" invariant**
  (flagged by: Test Coverage, Correctness, Code Quality) — Phase 4 adds the new
  `instructions` capability to the committed-log gate, whose `_arm` helper calls
  `pytest.fail("no committed log for arm …")` (verified at
  `tests/unit/evals/skills/configure/test_results.py:78`). It is a hard failure,
  not an xfail/skip, so the required `test:unit:evals` check is red on `main`
  between Phases 4 and 5 — directly contradicting the plan's Phase-mergeability
  claim and CLAUDE.md's branch-protection gating.
- **Phase 4 references eval infrastructure that does not exist** (flagged by: Test
  Coverage) — the plan instructs the author to "reuse `grade_block`'s
  newline/empty semantics", add a byte-comparing `test_instructions_render.py`,
  and run a "golden-pinning chain [that] scrapes Rust literals into the Python
  goldens". Verified: there is no `grade_block` (only `grade_behaviour`,
  `grade_value`, `grade_precedence`), no render test, and
  `test_context_dataset.py` states outright that "nothing here re-derives goldens
  or scrapes the Rust source." This is net-new infrastructure presented as reuse.
- **"Precedence" vs "in addition to" — docs and injected prose disagree** (flagged
  by: Usability, Documentation, Security) — the configure-surface section is told
  to claim instructions "take precedence over the skill's own instructions", but
  the injected prose reads "Follow these instructions in addition to all
  instructions above" (additive). The only real mechanism is positional lastness.
- **The load-bearing fail-safe/degrade/`--explain` machinery risks duplication**
  (flagged by: Architecture, Code Quality) — `instructions_command` is a "single-
  source analogue" that re-owns the most correctness-sensitive code in the feature
  (a non-zero exit discards the whole prompt), with the plan committing only to
  sharing `OnFailure`.

### Tradeoff Analysis

- **Byte-exact confidence vs test-pyramid shape** (Test Coverage): Phase 4's Python
  render tier would be a *third* byte-exact assertion of the block, above the fast
  Rust unit and black-box tiers that 0017 deliberately kept as the only byte tiers.
  Recommendation: keep byte-shape assertions in Rust; narrow any Python render test
  to the one thing Rust cannot see — that the exact injected argv from the SKILL.md
  line resolves the block against the committed eval fixtures.
- **Precedence semantics vs skill-author authority** (Security vs feature intent):
  framing userspace `instructions.md` as overriding the skill author's own guidance
  elevates a code-review-gated-but-lighter-scrutiny Markdown surface above the
  skill's encoded guardrails. Recommendation: resolve the wording (below) and, if
  "precedence" is genuinely intended, record the trust assumption explicitly.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Test Coverage / Correctness / Code Quality**: Phase 4 lands a hard-red
  committed-log gate, breaking per-phase-green mergeability
  **Location**: Phase 4 (Success Criteria) / Phase mergeability / Phase 5
  Adding the `instructions` arm makes `test_results.py`'s `_arm` call
  `pytest.fail("no committed log …")` (verified) until Phase 5 commits the billed
  log — a required CI check red on `main`, contradicting the plan's own
  independently-mergeable claim.

- 🟡 **Test Coverage**: Phase 4 cites eval infrastructure (`grade_block`, a
  Rust-literal scraper, a render test) that does not exist
  **Location**: Phase 4: "The golden-pinning chain and render test"; Current State
  Analysis
  Verified absent: no `grade_block`, no render test, and `test_context_dataset.py`
  disclaims scraping/golden-derivation. A significant slice of new scaffolding is
  presented as reuse, so its design and effort are unscoped.

- 🟡 **Usability / Documentation / Security**: The configure surface promises
  "precedence" while the injected prose says "in addition to"
  **Location**: Phase 3 §2 (configure surface) vs Phase 2 §1 (`instructions_prose`)
  The two authoritative descriptions — the user docs and the prompt the model
  actually sees — disagree on the mental model. The only mechanism is positional
  lastness; nothing encodes override.

- 🟡 **Architecture / Code Quality**: The fail-safe/degrade/`--explain` machinery
  is at risk of copy-paste duplication across two inbound modules
  **Location**: Phase 2 §1 & §3 (new render module / dispatch)
  The plan commits only to sharing `OnFailure` and leaves the rest "may be defined
  once or duplicated". This is the single most correctness-sensitive code in the
  feature; two implementations that must stay byte-identical can silently drift.

- 🟡 **Code Quality**: The arm-bearing `FragmentSource` forces the context
  consumer to handle a `SkillInstructions` arm it never produces
  **Location**: Implementation Approach (Option A) / Phase 1 §1
  The context command's exhaustive `match source` in `block()` (and
  `explain`/`section_lines`) will not compile without a `SkillInstructions` arm,
  forcing an `unreachable!()`/panic or a catch-all `_ =>` in prompt-critical code.
  The plan is silent on how those matches treat the foreign arm.

#### Minor

- 🔵 **Correctness**: `instructions --explain` has no always-present source to
  locate for the root line when `--skill` is invalid
  **Location**: Phase 2 §1 (`--explain` behaviour)
  Context obtains its root via `locate(&Project)`, which always exists;
  instructions' only source is `SkillInstructions(name)`, which needs a valid name.
  The invalid-name root-line handling is unspecified and asymmetric with context.

- 🔵 **Test Coverage**: No test for `instructions --explain` with no `--skill` (an
  instructions-only novelty)
  **Location**: Phase 2 (black-box `--explain` cases)
  With no project level to fall back to, an explain run with zero reportable levels
  is a genuinely new behaviour left unpinned.

- 🔵 **Test Coverage**: Phase 4's byte-exact render tier duplicates the Rust
  black-box coverage 0017 deliberately avoided
  **Location**: Phase 2 (`instructions.rs`) vs Phase 4 (render test)
  Three byte-exact tiers for the same block, one pushed to the slow Python+binary
  level, inverts the pyramid for marginal added confidence.

- 🔵 **Correctness**: The inverse positional test needs a sentinel default when a
  skill body has no `## ` subsections
  **Location**: Phase 3 (`test_line_sits_at_the_end_after_the_context_line…`)
  A `max()`/`next()` over the last `## ` heading is undefined for a subsection-free
  body; the context test guards the analogue with a `len(lines)` default.

- 🔵 **Standards**: The `Instructions` clap variant drops the per-argument `///`
  docs the `Context` variant carries
  **Location**: Phase 2 §2 (command arguments)
  `luminosity instructions --help` would render undocumented flags, inconsistent
  with every other subcommand (including that `--explain` writes to stderr).

- 🔵 **Documentation**: The surface section omits the purpose/when-to-use
  distinction between instructions and context
  **Location**: Phase 3 §2 (configure surface)
  Two nearly identical `## Managing skill-specific …` sections with no guidance on
  which mechanism to reach for — the core question the surface should answer.

- 🔵 **Documentation**: The crate `//!` doc's `[ContextSource]` intra-doc link is
  not listed for update
  **Location**: Phase 0 §1 (`cli/config/src/lib.rs`)
  After the rename, `lib.rs:9`'s `[`ContextSource`]` link becomes stale/broken; the
  plan lists the analogous `store.rs` reference but not this one.

- 🔵 **Architecture / Standards**: The `config` crate/`ConfigError` name diverges
  further from its now-`Fragment`-centred contents
  **Location**: What We're NOT Doing / Implementation Approach
  Deferral is acceptable, but record a concrete follow-up (crate + error-taxonomy
  rename) rather than an open-ended "a follow-up may track…", and signpost the
  residual split in the `fragment.rs` `//!` doc.

#### Suggestions

- 🔵 **Standards / Code Quality**: Commit to one organisation of the degrade
  vocabulary and one convention for the `context_command` locals
  **Location**: Phase 2 §3 / Phase 0 §3
  The plan leaves `Options` sharing "either/or" and the `context`-vs-`fragment`
  local rename "cosmetic if desired" — fix both as firm decisions so the file stays
  internally consistent.

- 🔵 **Security**: State the `instructions.md` trust assumption explicitly, and note
  the verbatim body splice (no demarcation) as a recorded choice
  **Location**: Phase 2 §1 / Phase 3 §2
  Instructions.md is a security-relevant, code-review-gated surface; the userspace
  body is spliced directly after the launcher's own framing with no fence.

- 🔵 **Usability**: Pair the two `--explain` diagnostics on the surface; consider a
  stderr hint for a bare interactive `luminosity instructions`
  **Location**: Phase 2 §1 / Phase 3 §2
  No single command answers "what is injected into this skill's prompt and from
  where?"; a bare invocation is a silent exit-0 no-op interactively.

- 🔵 **Usability**: The Unavailable notice will mislabel an `instructions.md` as a
  "config file"
  **Location**: Current State Analysis (`ConfigError` quirk)
  Consider whether the renderer's own prose (which the story owns) can name the
  file kind neutrally even while `ConfigError`'s wording stays out of scope.

- 🔵 **Test Coverage**: Make the empty-team twin of the drop-empty join an explicit,
  separately named test rather than a parenthetical
  **Location**: Phase 2 (`a_present_but_empty_personal_level_is_dropped…`)
  The two directions exercise different branches of the `[team, personal]` filter.

- 🔵 **Documentation**: Require a `//!` on the new `instructions_command/mod.rs` and
  `inbound/mod.rs` roots, not only `inbound/cli.rs`
  **Location**: Phase 2 §1
  Matches the sibling `context_command` tree; no `missing_docs` lint catches a miss.

### Strengths

- ✅ The `Fragment` rename cleanly separates the shared *mechanism* from its
  *consumers*, keeping the context/instructions distinction only at the real edges
  (renderers, headers, base names, subcommands).
- ✅ Option A (kind-bearing `FragmentSource`) makes illegal states unrepresentable
  — `SkillInstructions` is the only instructions arm, structurally forbidding
  project-global instructions — and a future document kind is an arm + path arm +
  renderer, not new machinery.
- ✅ A single `AssembleFragment` port serves both commands via the existing
  `dispatch` parameter; the document is selected purely by the source value.
- ✅ The `!`-preprocessor all-or-nothing failure mode is treated as a first-class
  boundary: `--fail-safe` degrade, name validation *inside* the boundary (not a
  clap `value_parser`), `--explain` degrading *with* the rest, all pinned by the
  load-bearing `an_invalid_skill_name_under_fail_safe_exits_zero_with_a_notice`.
- ✅ Sequencing is exemplary: Phase 0 is a pure rename with an explicit
  "no expected-value change in any test" guard; each later phase is a small,
  test-first, bisectable increment.
- ✅ All four coordinated subcommand-wiring sites (enum, dispatch, `main.rs`
  builtin-name list, exhaustive-match test) are covered explicitly and completely,
  with the alphabetical tripwire ordering and no-space grant form respected.
- ✅ Reused controls are not weakened: the allow-list `SkillName`, path-keyed
  symlink containment, and the empty-output/independent-degrade policies all carry
  over, with a dedicated leaf-file symlink test correctly added.
- ✅ The "edge cases that matter most" section is a real, risk-proportional test
  charter, and the registry-walking contract test auto-enrols future skills.

### Recommended Changes

1. **Resolve the Phase 4 mergeability contradiction** (addresses: "Phase 4 lands a
   hard-red committed-log gate"). Either (a) merge Phases 4 and 5 into one
   increment and drop the per-phase-green claim for Phase 4, or (b) introduce the
   `instructions` dataset-coverage pin in Phase 5 alongside the log it asserts, or
   (c) mark the new capability's committed-log parametrization `xfail(strict=True)`
   so it is green until the log lands then flips on regression. State which
   mechanism keeps CI green.

2. **Rewrite Phase 4 to specify net-new eval infrastructure explicitly**
   (addresses: "Phase 4 cites eval infrastructure that does not exist"). Define
   `grade_block`, any render-test harness, and the Rust-prose scraper as new work
   (including how the scraper stays in step with the `format!` literal) rather than
   citing 0017 machinery that was never built. Correct the Current State Analysis
   claim that "the golden-pinning chain scrapes Rust literals into the Python
   goldens" — it does not. Consider narrowing the Python render tier to the one
   thing the Rust tiers cannot assert (the injected argv resolving the block
   against the committed fixtures).

3. **Reconcile the "precedence" wording** (addresses: "docs promise precedence but
   prose says in addition to"). Pick one framing and use it in both the
   configure-surface section and `instructions_prose`. Recommended: describe
   positional lastness without the override promise (e.g. "applied after, and in
   addition to, the skill's own instructions"), preserving the skill author as the
   higher authority; if precedence is genuinely intended, change the injected prose
   to assert it and record the trust assumption.

4. **Specify the shared/duplicated boundary for the fail-safe machinery**
   (addresses: "fail-safe machinery risks duplication"). Decide in the plan which
   of the resolve/degrade/`--explain`-grammar helpers are factored into one shared
   submodule both commands compose, so the safety-critical boundary has a single
   implementation. At minimum, fix the `OnFailure` re-export / own-`Options`
   decision firmly rather than "either/or".

5. **State how the context command's matches treat the foreign `SkillInstructions`
   arm** (addresses: "arm-bearing enum forces a foreign arm"). Specify an
   `unreachable!()` with a justifying invariant, or narrow the launcher's render
   match to a per-command type, so the maintainer isn't inventing the resolution at
   implementation time.

6. **Specify the `instructions --explain` boundary cases** (addresses: "no
   always-present source to locate"; "no test for no-`--skill` explain";
   "inverse positional test sentinel"). State that an invalid-name explain emits a
   name-only line (no root), add a no-`--skill` explain test, and give the inverse
   positional test an explicit sentinel default for subsection-free bodies.

7. **Close the smaller documentation/standards gaps** (addresses: per-argument
   `///` docs; the surface purpose/when-to-use line; the `lib.rs` `[ContextSource]`
   intra-doc link; `//!` on the new module roots; the concrete crate-rename
   follow-up).

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: A structurally disciplined extension of the 0017 mechanism. The
`Fragment` rename correctly separates the shared mechanism from its consumers;
Option A's kind-bearing enum keeps the assembly core kind-agnostic and makes
illegal states unrepresentable; a single `AssembleFragment` port serves both
commands. The main tension is that the load-bearing fail-safe/degrade/`--explain`
machinery is re-implemented in a sibling module rather than factored into a shared
component, and the `config` crate/error name diverges further from its now-
`Fragment`-centred contents.

**Findings**:
- 🟡 (medium) — The fail-safe/degrade/`--explain` machinery is re-owned by
  `instructions_command`; only `OnFailure` is shared. The safety-critical degrade
  policy that guarantees an invalid `--skill` still exits 0 now has two
  implementations that can drift. Factor the shared per-source resolve/degrade/
  explain-grammar into one reusable component.
- 🔵 (high) — Phase 0 leaves the crate `config`/`ConfigError` while renaming the
  kernel to `Fragment*`; each added consumer widens the gap and grows the eventual
  rename cost. Record a concrete follow-up rather than an open-ended one.
- 🔵 (medium) — The "context early / instructions last" ordering lives in template
  placement (two `!`-lines) with no code owning the relative order; the
  registry-walking positional test is a sound mitigation — ensure it asserts every
  registered skill and document the coupled invariant.

### Code Quality

**Summary**: Unusually disciplined: small, independently-mergeable, test-first
phases leaning on a proven source-agnostic kernel; a behaviour-neutral rename that
improves the domain vocabulary. The maintainability risks are copy-paste
duplication of the load-bearing fail-safe machinery and the arm-bearing enum
forcing the context consumer to handle an instructions arm it can never produce.

**Findings**:
- 🔴→🟡 (medium) — The most correctness-sensitive code (a non-zero exit discards
  the whole prompt) risks copy-paste into a second module committed only to sharing
  `OnFailure`. Factor the single-source resolve/degrade/explain helpers into one
  shared submodule.
- 🔴→🟡 (medium) — Adding `SkillInstructions` makes the context command's
  exhaustive `match source` require an arm it never constructs, forcing an
  `unreachable!()`/panic or catch-all in prompt-critical code — undercutting the
  "illegal states unrepresentable" rationale. Specify how the matches handle it.
- 🔵 (high) — A deliberately-red test spanning the Phase 4→5 boundary weakens the
  "every phase green" invariant; gate it behind an explicit skip/xfail referencing
  the pending live run.
- 🔵 (medium) — Context renderers reading `assembly.fragment` while emitting
  `## …Context` headers is mild naming dissonance; name the fragment-vs-context
  relationship in the `context_command` `//!` doc so it reads as intentional.

_(Severities normalised: the two code-quality items marked 🔴 by the agent are
majors, not criticals, and are recorded as 🟡 in the aggregate above.)_

### Test Coverage

**Summary**: A genuinely strong Rust matrix (unit + black-box faithfully mirroring
the proven `context` suites; the load-bearing invalid-skill fail-safe case pinned
at every tier; a risk-proportional edge-case charter). The weaknesses concentrate
in the Python eval tier (Phase 4): it cites byte-exact golden/render infrastructure
that does not exist and that 0017 declined to build, and it knowingly commits a
hard-red coverage gate spanning Phases 4→5.

**Findings**:
- 🟡 (high, **verified**) — Phase 4 cites `grade_block`, a Rust-literal scraper,
  and a render test that do not exist; `test_context_dataset.py` disclaims
  scraping/goldens. Rewrite Phase 4 as net-new infrastructure.
- 🟡 (high, **verified**) — The committed-log gate uses a hard `pytest.fail`
  (`test_results.py:78`), so the new arm cannot merge past branch protection until
  Phase 5. Merge 4+5 or use `xfail(strict=True)`.
- 🔵 (medium) — The Python render tier is a third byte-exact tier the Rust tiers
  already cover; narrow it to the argv-resolves-fixtures delta.
- 🔵 (medium) — No test for `instructions --explain` with no `--skill` (zero
  reportable levels — an instructions-only novelty).
- 🔵 (low) — The symmetric empty-team twin of the drop-empty join is only a
  parenthetical; make it an explicit named test.

### Correctness

**Summary**: Builds on a proven source-agnostic kernel whose combine/trim/drop-empty
logic, frontmatter strip, symlink containment, and empty-output policy are reused
verbatim, so the core boundary conditions are inherited rather than re-derived. Two
concerns: the internal contradiction between per-phase-green mergeability and Phase
4's deliberately-red assertion, and an under-specified `--explain` root-line path
for the instructions command.

**Findings**:
- 🟡 (medium) — Phase 4 "red by design" contradicts the per-phase green/mergeable
  invariant; introduce the coverage pin in Phase 5 or declare 4+5 a single unit.
- 🔵 (medium) — `instructions --explain` has no always-present source to locate for
  the root line when `--skill` is invalid; state explicitly that it emits a
  name-only line (no root) or specify a source-independent root.
- 🔵 (low) — The inverse positional test needs a sentinel default for a
  subsection-free body, mirroring the context test's `len(lines)` guard.

### Security

**Summary**: Reuses a well-designed set of controls (allow-list `SkillName`,
path-keyed symlink containment, an explicitly-preserved fail-safe boundary) for a
new document kind without weakening any of them. The one substantive consideration
is a design property, not a defect: the `## Additional Instructions` block frames
userspace content as authoritative directives, lands it last, and (per the surface
docs) grants it precedence over the skill author's own instructions. Because
`instructions.md` is repo-committed and code-review-gated, the threat is bounded to
the existing commit trust boundary — hence minor.

**Findings**:
- 🔵 (medium) — The block elevates userspace content to directives that override the
  skill author's own guidance (including safety guardrails), within the skill's tool
  grants. State the trust assumption explicitly and reconsider the "precedence"
  framing so userspace cannot silently override a skill author's constraints.
- 🔵 (low) — The userspace body is spliced verbatim after the launcher's own framing
  with no fence/demarcation (a minor prompt-structure spoofing surface). Likely
  acceptable given the trust model and the "read as natural directives" eval
  requirement — record it as a deliberate choice.

### Usability

**Summary**: The sibling `instructions` subcommand mirrors `context` flag-for-flag,
a strong consistency and guessability win. The main risks are a mental-model
mismatch between docs ("take precedence") and injected prose ("in addition to"), a
fragmented diagnostic surface where `context --explain` and `instructions --explain`
each show only half the prompt, and the compounding of the silent-on-typo /
by-hand-directory friction into a second invisible file per skill.

**Findings**:
- 🟡 (medium) — Docs promise precedence but the prose is additive; the only
  mechanism is positional lastness. Pick one framing and use it in both places.
- 🔵 (high) — After the split, no single command answers "what is injected and from
  where?"; pair the two `--explain` diagnostics on the surface.
- 🔵 (medium) — Two invisible by-hand files per skill now share the same silent
  failure mode; lead the surface with the exact path and the `--explain` diagnostic.
- 🔵 (medium) — Bare `luminosity instructions` is a silent exit-0 no-op
  interactively; consider a TTY-only stderr hint.
- 🔵 (medium) — The Unavailable notice mislabels an `instructions.md` as a "config
  file"; consider neutral file-kind wording in the renderer's own prose.

### Standards

**Summary**: A convention-faithful clone of the 0017 template: all four coordinated
subcommand-wiring sites covered completely, the `context_command` module shape
mirrored, renderer/prose/test-naming vocabulary followed, phases kept independently
green, alphabetical tripwire ordering and no-space grant respected. The gaps are
small: the new clap variant drops per-argument docs, and the `Fragment` rename
leaves a deliberate crate/error vocabulary split.

**Findings**:
- 🔵 (medium) — The `Instructions` clap variant carries no per-argument `///` docs,
  unlike `Context`; `--help` would render undocumented flags (including that
  `--explain` writes to stderr).
- 🔵 (high) — After the rename the crate exposes `Fragment*` alongside `config`/
  `ConfigError`; signpost the residual split in the `fragment.rs` `//!` doc.
- 🔵 (medium) — The `context_command` local rename is left "cosmetic if desired";
  make a single explicit decision so the file is internally consistent.
- 🔵 (low) — The `OnFailure`/`Options` organisation is left either/or; commit to the
  stated preference firmly.

### Documentation

**Summary**: Unusually documentation-conscious — enumerates the `//!` updates across
every renamed file, establishes "prompt fragment" once, and compensates for the
absent `missing_docs` lint with an explicit manual check. The gaps are a user-facing
accuracy mismatch (surface "precedence" vs injected "in addition to"), a missing
purpose/when-to-use distinction on the surface, and one under-specified crate-doc
intra-link.

**Findings**:
- 🟡 (medium) — The surface says instructions "take precedence"; the injected prose
  says "in addition to". Incorrect docs are worse than missing ones — reconcile the
  two.
- 🔵 (medium) — The surface omits what instructions are *for* vs context; add a
  one-line framing (directives to follow vs information to consider).
- 🔵 (low) — The crate `//!` doc's `[ContextSource]` intra-doc link (lib.rs:9)
  becomes stale after the rename; list it for update.
- 🔵 (low) — Module docs are required only on `inbound/cli.rs`; require a `//!` on
  the new `mod.rs` roots too, matching `context_command`.

---

## Re-Review (Pass 2) — 2026-07-20

**Verdict:** APPROVE

The author addressed every finding from Pass 1, and a re-run of all eight lenses
confirmed each is resolved (or a deliberately-accepted deferral). The re-review
also surfaced four smaller items **introduced by the Pass-1 edits** — expected when
a review drives changes — and all four have since been fixed in a further edit
pass. The plan now carries no open findings.

### Previously Identified Issues

All Pass-1 findings — verified resolved by the re-run lenses:

- 🟡 **Test Coverage / Correctness / Code Quality**: Phase 4 hard-red committed-log
  gate — **Resolved.** Now `xfail(strict=True)`; Phase 4 merges green and Phase 5
  is mechanically forced to remove the marker when the log lands. Verified against
  `TestCommittedGate`'s real structure.
- 🟡 **Test Coverage**: Phase 4 cited nonexistent eval infrastructure —
  **Resolved.** Phase 4 §3 now labels `grade_block`, `_trim`, the host-binary
  resolver, and the render test as net-new, and the Current State Analysis
  correctly describes `_DOMAIN_TEMPLATES` as a hand-transcription.
- 🟡 **Usability / Documentation / Security**: "precedence" vs "in addition to" —
  **Resolved.** Every mention is now additive/positional-lastness, matching the
  injected prose; the trust boundary is recorded explicitly.
- 🟡 **Architecture / Code Quality**: fail-safe machinery duplication —
  **Resolved.** Factored into one shared scaffold both commands compose;
  `context_command` refactored to consume it.
- 🟡 **Code Quality**: arm-bearing enum forces a foreign arm — **Resolved** (then
  refined — see New Issues). Pass 1 specified an `unreachable!()` arm; the
  re-review flagged that as a panic-idiom regression, now superseded by a
  structurally-exhaustive resolution.
- 🔵 All Pass-1 minors/suggestions — **Resolved**, except two Usability
  suggestions **consciously deferred** with documented rationale (the bare-command
  silent no-op, kept for cross-command consistency; the `ConfigError` "config
  file" mislabel, scoped out but kept diagnosable by the exact-path notice).

### New Issues Introduced (by the Pass-1 edits) — now addressed

- 🟡 **Architecture**: The shared scaffold's stated contents omitted the
  load-bearing invalid-`--skill` parse/degrade slice, risking re-duplication of the
  highest-stakes path — **Fixed**: the scaffold now explicitly owns the
  raw-name-parse-inside-boundary and `Unresolved`/invalid-skill-name-line handling.
- 🔵 **Code Quality / Standards**: The scaffold name `fragment_command` mimicked a
  real subcommand module and collided with the kernel `fragment` — **Fixed**:
  renamed to `command_support` (shared scaffolding, `_command` reserved for real
  subcommands).
- 🔵 **Standards / Architecture**: The Pass-1 `unreachable!()` fix introduced the
  codebase's first panicking macro against a panic-free clippy convention —
  **Fixed**: the plan now prefers a structurally-exhaustive command-local render
  view (illegal state unrepresentable at that edge), with `unreachable!()` +
  explicit `clippy::unreachable` opt-in only as a justified fallback.
- 🔵 **Test Coverage**: The instructions coverage-gate analogue would have reused
  the context-hardcoded `_behavioural_scenarios()` helper — **Fixed**: it now reads
  `instructions_behavioural_dataset.json` (helper parametrised by dataset).

### Assessment

The plan is in good shape and ready for implementation. The design is sound, the
phases are independently mergeable and green, the test matrix is well-triangulated
across the three toolchains, and the fail-safe boundary — the feature's most
correctness-sensitive surface — is now specified as a single shared implementation.
The one residual is a judgment call the plan already frames as a preference (narrow
the render type vs the `unreachable!()`+lint-opt-in fallback), which is safe to
settle at implementation time.

---
*Re-review generated by /accelerator:review-plan*
