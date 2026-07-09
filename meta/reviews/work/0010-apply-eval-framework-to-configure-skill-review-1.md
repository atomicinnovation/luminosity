---
type: work-item-review
id: "0010-apply-eval-framework-to-configure-skill-review-1"
title: "Work Item Review: Apply the Eval Framework to the configure Skill"
date: "2026-07-06T17:39:47+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
parent: "work-item:0001"
target: "work-item:0010"
work_item_id: "0010"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 2
tags: [evaluation, skills, configure]
last_updated: "2026-07-06T21:45:07+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Apply the Eval Framework to the configure Skill

**Verdict:** REVISE

Work item 0010 is an unusually strong story — every section is present and
substantively populated, scope is tight and single-purpose, and the framework
decision is concretely lifted from spike 0003 with correct disambiguation of the
`pass^k` statistic. The verdict is REVISE (not because the item is weak but)
because three major findings cluster around two fixable gaps: the frontmatter
does not encode the blocking edges its prose and its upstream siblings already
declare, and the acceptance criteria measure surface artefacts (files, exit
codes) without pinning down the eval's *substance* — how a task is graded and
whether the with-skill-vs-baseline A/B (the story's stated purpose) is actually
exercised.

### Cross-Cutting Themes

- **Frontmatter omits the blocking edges** (flagged by: dependency, completeness)
  — The prose Dependencies section names spike 0003 and story 0009 as blockers,
  and both upstream items declare `blocks: ["work-item:0010"]`, yet 0010's
  frontmatter carries only `parent`. The machine-readable graph is asymmetric:
  tooling that traverses frontmatter links will treat 0010 as startable when it
  is not.
- **Acceptance criteria verify the shell, not the eval's substance** (flagged by:
  testability, completeness) — The criteria confirm paths, a committed log, a
  numeric gate, and pytest non-collection, but never require a defined per-task
  grading rule, the baseline arm of the A/B, or that the ramp commitment the
  Requirements ask to "record" is actually recorded. The gate is only as
  meaningful as the (currently unspecified) pass definition beneath it.

### Findings

#### Critical

- None.

#### Major

- 🟡 **Dependency**: Frontmatter omits `blocked_by` despite prose blockers and reciprocal `blocks` declarations
  **Location**: Frontmatter
  The prose names 0003 and 0009 as blockers and both declare `blocks: ["work-item:0010"]`, yet 0010's frontmatter has no `blocked_by` field (only `parent`). Scheduling/readiness tooling can treat it as startable when it is not. (Also flagged by completeness as a frontmatter field-parity gap vs siblings 0003/0009.)

- 🟡 **Testability**: `pass^k` gate presupposes an undefined per-task grading criterion
  **Location**: Acceptance Criteria
  AC3 gates on `pass^k ≥ 0.8` but no criterion defines how an individual task is judged pass/fail — the grading rubric appears only obliquely in Technical Notes. Two authors could produce very different `pass^k` numbers from the same dataset, so the 0.8 gate could be satisfied by a weak or tautological grader.

- 🟡 **Testability**: With-skill-vs-baseline A/B intent is not verified by any criterion
  **Location**: Acceptance Criteria
  The Summary, Requirements, and Residual Risk all frame proving the A/B comparison as the point of the story, yet every criterion measures only the with-skill `pass^k`. All criteria could pass while the baseline arm was never run — leaving the story's stated attribution purpose unverified.

#### Minor

- 🔵 **Clarity**: "bootstrap floor" (Requirements) vs "final gate" (Acceptance Criteria) name the same bar
  **Location**: Requirements / Acceptance Criteria
  The single threshold (≥ 3 tasks, `pass^k ≥ 0.8`, k = 3) is labelled two ways in an item that elsewhere distinguishes a "provisional floor" from the spike's decided bar, so a reader may briefly wonder whether one or two bars govern acceptance.

- 🔵 **Dependency**: Inspect harness tooling dependency not captured in Dependencies
  **Location**: Dependencies
  The story rests on the Inspect library (a new `uv`-installed, pinned dev dependency), but Inspect appears only in Requirements/Technical Notes, not Dependencies — so the tool-provisioning prerequisite can be overlooked in planning.

- 🔵 **Dependency**: Claude Code / model-API runtime coupling captured only as a residual risk
  **Location**: Technical Notes
  Running the eval requires an authenticated, drivable Claude Code / model API plus token budget. This operational prerequisite is documented as a residual risk, not framed as an external dependency, risking discovery only at run time.

- 🔵 **Testability**: "task exits non-zero below the bar" has no stated verification procedure
  **Location**: Acceptance Criteria
  AC3's fail-path clause is a real behaviour to verify, but a committed passing run only demonstrates the pass path. The gate could be silently non-functional (always exit 0) and still satisfy every other criterion.

#### Suggestions

- 🔵 **Testability**: At the 3-task floor, `pass^k ≥ 0.8` collapses to "all tasks pass all trials" (achievable rates are 0/0.33/0.67/1.0). Worth noting so a 2-of-3 result isn't mistaken for a pass.
- 🔵 **Testability**: AC1 gates task *count* only; the intended scenarios (get/set, precedence, missing/malformed key) live in Drafting Notes — three trivial tasks would satisfy it. Consider tying the criterion to coverage.
- 🔵 **Completeness**: The 4th Requirement asks to "record the ramp commitment" as a deliverable, but no AC confirms it and it lives only in Technical Notes narrative — reword as already-captured, or add a matching criterion.
- 🔵 **Dependency**: ADR decision 11 (work item 0005) is cited as authority but not clarified in Dependencies as a non-blocker (the authoritative decision already lives in done spike 0003).
- 🔵 **Clarity**: Expand AISI on first use ("UK AI Safety Institute (AISI) Inspect").
- 🔵 **Clarity**: `k` appears in `Epochs(k, pass_k(k))` before it is pinned to 3 two bullets later; gloss it as the trial count at first mention.
- 🔵 **Scope**: The 2nd Requirement folds the reusable eval-*tier* infrastructure in with the `configure`-specific application — intentional and correct here (proves the harness end-to-end); no action, but extract a shared helper if a second skill eval is later planned.

### Strengths

- ✅ The confusable metric is explicitly disambiguated at first use — `pass^k ≥ 0.8 over k = 3 trials (Inspect's pass_k — all-k-succeed, not a mean pass-rate)` — so it cannot be mistaken for the epic's earlier ≥ 80% mean bar despite the shared 0.8 figure.
- ✅ Every section is present and substantively populated; Context genuinely explains motivation (proof-of-architecture for the skills-vs-CLI division, A4) and records why the spike reversed the epic's `skill-creator` hypothesis.
- ✅ Requirements are specific enough to start work: exact paths, file names, the `Epochs`/`pass_k` wiring, the JSON log format, and the numeric floor.
- ✅ Well-scoped, single-purpose story — one framework applied to one skill; Summary, Requirements, and Acceptance Criteria describe the same scope with no drift; `story` kind fits.
- ✅ Both upstream blockers are named in prose with rationale, the downstream side is correctly "none / epic DoD", and the one genuinely uncertain coupling (Inspect-driving-Claude-Code A/B) is surfaced as a residual risk with a pre-vetted fallback (promptfoo).
- ✅ Open Questions is explicitly resolved ("None") with reasoning captured rather than left dangling.

### Recommended Changes

1. **Add the blocking edges to frontmatter** (addresses: Frontmatter omits `blocked_by`)
   Add `blocked_by: ["work-item:0003", "work-item:0009"]` so the machine-readable
   graph matches the prose and the reciprocal `blocks` entries upstream. (Note: at
   authoring time these were deliberately left off on the "canonical `blocks` lives
   on the other side" convention — worth a quick decision on which convention this
   repo standardises, since siblings 0003/0009 carry both directions.)

2. **Add an acceptance criterion pinning the per-task grading rule** (addresses: `pass^k` gate presupposes undefined grading)
   e.g. "each task is graded by outcome — the resolved config value the skill
   produces equals the task's expected value — and the grading rule is recorded in
   `configure_eval.py`."

3. **Add an acceptance criterion requiring the baseline arm** (addresses: A/B intent not verified)
   e.g. "the committed log records both the with-skill and baseline solvers over
   the same dataset, so the attribution comparison is a checkable outcome."

4. **Specify how the fail path of the gate is verified** (addresses: exit-non-zero has no verification procedure)
   e.g. "a unit test drives the threshold logic with a synthetic `pass_k` below 0.8
   and asserts a non-zero exit."

5. **Resolve the terminology drift and minor clarity nits** (addresses: bootstrap-floor/final-gate label, AISI, `k` gloss)
   Use one label for the single bar; expand AISI on first use; gloss `k` as the
   trial count where introduced.

6. **Tighten AC1 toward coverage and reconcile the ramp-commitment deliverable** (addresses: AC1 count-only, ramp-commitment without AC)
   Tie AC1 to the intended scenarios rather than a bare count, and either add a
   criterion for the recorded ramp commitment or reword the requirement as
   already-captured.

7. **Optionally lift two couplings into Dependencies** (addresses: Inspect tooling, model-API runtime)
   Note the Inspect library (pinned via `uv`) and the drivable-Claude-Code /
   token-budget prerequisite as explicit dependencies, and clarify ADR-0005 /
   decision 11 as a non-blocker.

## Per-Lens Results

### Clarity

**Summary**: Work item 0010 is unusually clear and internally consistent: pronouns resolve cleanly, actors are named where they matter, and the key statistical term `pass^k` is explicitly disambiguated from a mean pass-rate. The only clarity concerns are minor terminology drift ("bootstrap floor" vs "final gate") and an unexpanded acronym (AISI), neither of which prevents a domain-aware reader from reaching a single interpretation.

**Strengths**:
- The potentially confusable metric is disambiguated at first substantive use ("pass^k ≥ 0.8 over k = 3 trials (Inspect's pass_k — all-k-succeed, not a mean pass-rate)").
- Pronouns and referents resolve to exactly one subject throughout, and the actors behind each action are named (invoke task exits non-zero; developer commits by hand; author owns skill-invocation detection).
- Scope is consistent across Summary, Context, Requirements, and Acceptance Criteria — one Inspect eval suite, dev-time-only, committed JSON log — kept coherent by tight cross-referencing to spike 0003.

**Findings**:
- 🔵 minor (confidence medium) — *Requirements / Acceptance Criteria*: The same gating threshold is labelled the "bootstrap floor" in Requirements but the "final gate" in Acceptance Criteria; in an item that elsewhere distinguishes a "provisional floor" from the spike's decided bar, a reader could wonder whether these name two bars. Suggestion: use one consistent label.
- 🔵 suggestion (confidence low) — *Summary*: "UK AISI Inspect" never expands AISI in the body (only via the linked reference). Suggestion: expand to "UK AI Safety Institute (AISI) Inspect".
- 🔵 suggestion (confidence low) — *Requirements*: `k` appears in `Epochs(k, pass_k(k))` before it is pinned to 3 two bullets later. Suggestion: gloss `k` as the trial count at first mention.

### Completeness

**Summary**: A highly complete story: every expected section is present and substantively populated, and the story-kind requirements (Context explaining why, criteria defining done) are well met. Content is tightly grounded in spike 0003 and story 0009. The only completeness gap worth noting is the frontmatter, which omits the machine-readable dependency link fields its sibling items carry.

**Strengths**:
- Summary is a clear, unambiguous action statement naming the concrete command, gate, and durable artefact.
- Context explains motivation (proof-of-architecture, A4) rather than restating the summary, and records why the spike reversed the `skill-creator` hypothesis.
- Five specific acceptance criteria, each a concrete definition of done.
- Requirements are specific enough to start work (exact paths, file names, `Epochs`/`pass_k` wiring, JSON format, numeric floor).
- Open Questions explicitly resolved with reasoning; `kind: story` present and justified.
- Dependencies, Assumptions, Technical Notes all populated with relevant, non-placeholder content.

**Findings**:
- 🔵 minor (confidence medium) — *Frontmatter*: Carries only `parent`; omits the `blocked_by`/`blocks` fields siblings use (0003 declares `blocks: ["work-item:0005","work-item:0010"]`; 0009 declares both), despite the prose stating it is blocked by 0003 and 0009. Suggestion: add `blocked_by: ["work-item:0003","work-item:0009"]` for frontmatter parity.
- 🔵 suggestion (confidence low) — *Requirements*: The 4th bullet asks to "record the ramp commitment" as a deliverable, but no acceptance criterion confirms it (it appears only in Technical Notes). Suggestion: add a matching criterion or reword as already-captured.

### Dependency

**Summary**: The prose Dependencies section captures the two upstream blockers well — spike 0003 (framework decision) and story 0009 (skill under test) — each with rationale, and correctly reports no downstream dependants. The main gaps are structural: the frontmatter carries no `blocked_by` despite both blockers declaring `blocks: 0010`, and the two external couplings the eval rests on (Inspect as a new tool; driving Claude Code as an external agent with token budget/credentials) appear only in Technical Notes.

**Strengths**:
- Both upstream blockers named in prose with the reason each is a prerequisite, making the ordering explicit.
- Downstream side correctly captured ("Blocks: none; part of the epic's definition of done").
- The unproven Inspect-driving-Claude-Code A/B integration is explicitly recorded as a residual risk with a pre-vetted fallback (promptfoo).

**Findings**:
- 🟡 major (confidence high) — *Frontmatter*: Omits `blocked_by` despite prose blockers and reciprocal `blocks` declarations upstream (0003 line 12; 0009 line 13). Tooling relying on frontmatter will not see 0010 as blocked. Suggestion: add `blocked_by: ["work-item:0003","work-item:0009"]`.
- 🔵 minor (confidence medium) — *Dependencies*: The Inspect (UK AISI) harness — a new `uv`-installed, pinned dev dependency — appears only in Requirements/Technical Notes, not Dependencies. Suggestion: note it as an explicit tooling dependency, cross-referencing 0003.
- 🔵 minor (confidence medium) — *Technical Notes*: Running the eval requires an authenticated, drivable Claude Code / model API plus token budget; captured as a residual risk, not as an external dependency. Suggestion: record the model-API access and token-budget requirement as an explicit external coupling.
- 🔵 suggestion (confidence low) — *Acceptance Criteria*: ADR decision 11 (work item 0005) is cited as authority but not clarified in Dependencies as a non-blocker (the authoritative decision lives in done spike 0003). Suggestion: note that 0005 is a parallel record, not a prerequisite.

### Scope

**Summary**: A well-scoped, coherent story: one eval framework (Inspect) applied to one skill (configure) as a single bounded deliverable, with Summary, Requirements, and Acceptance Criteria describing the same scope consistently. Boundaries are clear (one skill, one dataset at the ≥ 3-task floor, one committed log), it sits within a single ownership domain, and `story` is the appropriate kind. The only observation is the intentional folding of the general eval-tier infrastructure into the first skill application.

**Strengths**:
- All four Requirements serve a single unified purpose — no "and also" bundling.
- Summary, Requirements, and Acceptance Criteria tightly aligned with no section-to-section scope drift.
- `story` kind fits: a bounded increment a single team can own end-to-end, neither trivial nor decomposition-warranting.
- Boundaries explicit and defensible: the ≥ 3-task floor is a deliberate proof-of-architecture smoke test, with the 20–50-task ramp explicitly deferred.
- Clear standalone value (a durable committed benchmark); the parent epic lists it as exactly one child story.

**Findings**:
- 🔵 suggestion (confidence low) — *Requirements*: The 2nd Requirement bundles the reusable eval-*tier* infrastructure (the `mise run eval` roll-up, the `tests/evals/` root, pytest-non-collection) with the `configure`-specific application. Impact low — splitting it out would yield an artefact with no standalone value, and spike 0003 deliberately couples them to prove the harness end-to-end. No action needed; extract a shared helper only if a second skill eval is later planned.

### Testability

**Summary**: Unusually well-specified for verification: concrete numeric gates (≥ 3 tasks, `pass^k ≥ 0.8`, k = 3), named paths, a named run command, and a mechanically checkable pytest-collection criterion. The main gaps are that the `pass^k` gate presupposes a per-task grading/scorer definition no criterion requires, and that the with-skill-vs-baseline A/B — central to the Summary's "prove the eval approach end-to-end" intent — is not captured in any criterion.

**Strengths**:
- Acceptance Criteria use concrete, measurable thresholds rather than subjective quality language.
- AC1/AC2 name the exact artefacts and command to check.
- AC5 (pytest non-collection) is mechanically verifiable by running collection.
- AC4's CI exclusion is verifiable by inspecting task/CI configuration.
- The gate is framed as `pass^k` with the aggregation method explicitly named (Inspect `pass_k`).

**Findings**:
- 🟡 major (confidence medium) — *Acceptance Criteria*: AC3 gates on `pass^k ≥ 0.8` but no criterion defines how a task is judged pass/fail — the grading rubric appears only obliquely in Technical Notes. The 0.8 gate could be satisfied by a weak or tautological grader. Suggestion: require the per-task pass definition to be explicit and deterministic, recorded in `configure_eval.py`.
- 🟡 major (confidence medium) — *Acceptance Criteria*: The A/B intent (baseline comparison) is framed as the story's purpose but every criterion measures only the with-skill `pass^k`; the baseline arm could never be run and all criteria still pass. Suggestion: add a criterion that the committed log records both arms over the same dataset.
- 🔵 minor (confidence medium) — *Acceptance Criteria*: AC3's "exits non-zero below that bar" has no verification procedure; a committed passing run only demonstrates the pass path. Suggestion: a unit test drives the threshold logic with a synthetic sub-0.8 `pass_k` and asserts non-zero exit.
- 🔵 suggestion (confidence medium) — *Acceptance Criteria*: At exactly 3 tasks the achievable rates are 0/0.33/0.67/1.0, so `pass^k ≥ 0.8` resolves to "all tasks pass all trials". Suggestion: note this so a 2-of-3 result isn't mistaken for a pass.
- 🔵 suggestion (confidence low) — *Acceptance Criteria*: AC1 gates task *count* only; the intended scenarios live in Drafting Notes, so three trivial tasks would satisfy it. Suggestion: tie the criterion to coverage.

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-06

**Verdict:** COMMENT

Re-ran the four lenses that carried actionable findings (clarity, completeness,
dependency, testability). All three original majors are resolved: `blocked_by` is
now in frontmatter, the per-task grading rule (AC2) and the with-skill/baseline
A/B capture (AC3) are now explicit criteria. The verdict moves from REVISE to
COMMENT. One new major surfaced — a real inconsistency introduced by the edits:
the AC2 value-equality grading rule does not cover the missing/malformed-key
scenario AC1 now mandates (an error, not a value). A handful of new minors/
suggestions accompany it. None block; the item is acceptable as-is but would
improve with the AC2 error-path fix.

### Previously Identified Issues

- 🟡 **Dependency**: Frontmatter omits `blocked_by` — **Resolved** (`blocked_by: ["work-item:0003","work-item:0009"]` added; dependency lens confirms frontmatter/prose now consistent).
- 🟡 **Testability**: `pass^k` gate presupposes undefined per-task grading — **Resolved** (AC2 now defines outcome grading) — but see new major below on the error-path sub-case.
- 🟡 **Testability**: A/B baseline not verified — **Partially resolved** (AC3 now requires both arms in the log; no pass/fail attached to the with-skill-vs-baseline delta — now a minor).
- 🔵 **Clarity**: "bootstrap floor" vs "final gate" terminology drift — **Resolved** (unified on "bootstrap floor (its decided gate for this epic)").
- 🔵 **Dependency**: Inspect harness tooling not in Dependencies — **Resolved** (added as a pinned-via-`uv` tooling dependency).
- 🔵 **Dependency**: Claude Code / model-API coupling only a residual risk — **Resolved** (added as an explicit runtime prerequisite with the promptfoo contingency).
- 🔵 **Testability**: gate fail-path had no verification procedure — **Resolved** (AC6 specifies a synthetic-sub-0.8 unit test asserting non-zero exit).

### New Issues Introduced

- 🟡 **Testability** (major, high): AC2's value-equality grade does not cover the missing/malformed-key task class AC1 mandates (expected outcome is an error/non-zero exit, not a resolved value), so that third of the suite has no defined pass rule. *Fixable in one clause.*
- 🔵 **Clarity** (minor): AC5 states `pass^k ≥ 0.8` and then glosses it as "every task passing all three trials" (reads as 1.0); how per-task pass^k aggregates to the 0.8 suite figure is not stated, and "≥ 3 tasks" / "k = 3 trials" co-occur confusingly. (Introduced by the 3-task-floor clarification.)
- 🔵 **Testability** (minor): AC3 records both A/B arms but attaches no pass/fail to the delta — a run where the skill underperforms baseline still passes.
- 🔵 **Testability** (minor): AC2's capture point (how the produced value is extracted from the driven Claude Code transcript) is deferred entirely to `configure_eval.py`, making the criterion self-referential at the highest-risk seam.
- 🔵 **Dependency** (minor): model-version drift is not among the benchmark-refresh triggers, though the committed pass^k is coupled to the external model version.
- 🔵 **Dependency** (minor): 0010 discharges the behavioural-equivalence validation that story 0009 explicitly deferred to it, but this inbound obligation is only visible from 0009's side.
- 🔵 **Clarity** (suggestion): "benchmark" is overloaded between the committed log file and the pass^k score.
- 🔵 **Completeness** (suggestion): the beneficiary (skill maintainers relying on the committed signal) is implicit in Context.
- 🔵 **Testability** (suggestion): the gate happy-path (≥ 0.8 → exit 0) has no synthetic two-sided unit test to complement AC6.

### Assessment

The work item is now in good shape and acceptable as-is (COMMENT). The single new
major is a genuine, self-inflicted gap worth closing — extend AC2 so
missing/malformed-key tasks grade on the surfaced error/non-zero exit rather than
a value. The clarity nit on the `pass^k` gate (0.8 vs "all pass") is also worth a
one-line tightening since it touches the central acceptance condition. The
remaining minors/suggestions are optional polish and can be left to implementation
or a future refinement.

**Post-review follow-up (2026-07-06):** both priority fixes were applied to
0010 — AC2 now defines the missing/malformed-key pass condition (surfaced error /
non-zero exit), closing the new major; AC5 was rewritten to separate the trial-
count and task-count dimensions and explain the `pass_k` fraction aggregation,
closing the clarity nit.

**All remaining optional items subsequently applied (2026-07-06):** every
minor/suggestion from this pass was also addressed, so no findings remain open —

- 🔵 **Testability** (A/B delta pass/fail): AC3 now states the baseline arm is recorded for attribution only, with a with-skill result not exceeding baseline flagged as a signal to investigate rather than treated as failing.
- 🔵 **Testability** (AC2 capture point): AC2 now fixes the graded surface in the spec — "against the CLI stdout and exit code the skill emits."
- 🔵 **Testability** (happy-path gate test): AC6 is now two-sided — a synthetic `pass_k` ≥ 0.8 asserts exit zero alongside the existing sub-0.8 fail-closed test.
- 🔵 **Dependency** (model-version drift): added to the eval-refresh triggers (Technical Notes) and noted as a coupling on the runtime prerequisite (Dependencies).
- 🔵 **Dependency** (0009 deferred obligation): a "Discharges:" line in Dependencies records that closing 0010 completes 0009's deferred behavioural-equivalence validation.
- 🔵 **Completeness** (implicit beneficiary): Context now names the skill maintainers who rely on the committed log to catch `configure` regressions.
- 🔵 **Clarity** ("benchmark" overloaded): standardised on "eval log" for the committed file and "`pass_k` result" for the score across Summary, Context, AC5, and Assumptions; "benchmark-refresh" renamed to "eval-refresh".

Net effect: all findings from both review passes are resolved; 0010 carries 8
concrete, two-sidedly verifiable acceptance criteria.

**Verdict updated to APPROVE (2026-07-06):** with every finding from both passes
resolved and no open issues remaining, the review is marked APPROVE. The work
item is ready for implementation planning.
