---
type: work-item-review
id: "0003-skill-evaluation-framework-selection-review-1"
title: "Work Item Review: Skill Evaluation Framework Selection"
date: "2026-06-23T22:49:36+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0003"
parent: "work-item:0001"
work_item_id: "0003"
reviewer: Toby Clemson
verdict: COMMENT
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 2
tags: []
last_updated: "2026-06-23T22:55:20+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Skill Evaluation Framework Selection

**Verdict:** REVISE

This is a structurally complete, well-framed spike: a genuinely open research
question, an explicit 2-day time-box, and exit criteria expressed as concrete
artefacts rather than vague "understand X" goals. The reason for REVISE is
narrow and concentrated in the Acceptance Criteria and Requirements — two major
testability gaps mean the spike's two most important obligations (the landscape
survey and the provisional-floor reconciliation) cannot be conclusively
verified as complete. These are addressable with targeted edits to the exit
criteria rather than a rethink of the work item.

### Cross-Cutting Themes

- **The open-ended survey is unverifiable and time-box-risky** (flagged by:
  testability, scope) — "survey the landscape… actively look for others" has no
  stopping condition, no required evidence-of-survey, and no breadth target.
  Testability sees this as tautological (any output can be claimed
  complete/incomplete beyond the 3-framework floor); scope sees an unbounded
  survey colliding with the 2-day box. A single fix — requiring the
  Recommendation to enumerate every framework considered with a one-line
  include/dismiss reason — closes both.
- **Acceptance Criterion 2 overloads multiple obligations into one bullet**
  (flagged by: testability, clarity, scope) — it bundles "define how the
  benchmark is produced/committed" with "confirm or raise the provisional
  floor", and juxtaposes two numeric figures (≥3 tasks vs 20–50 guidance)
  whose relationship is left implicit. The result is a criterion where any
  outcome passes and the two halves blur together. Splitting it and giving each
  half a concrete pass condition resolves the testability, clarity, and scope
  observations together.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Testability**: Second criterion bundles two checks with no defined pass
  condition for the variance comparison
  **Location**: Acceptance Criteria
  Part (b), "confirm or raise the epic's provisional floor", has no defined pass
  condition — both keeping and changing the floor satisfy it equally, so a
  verifier cannot distinguish a considered decision from a hand-wave.

- 🟡 **Testability**: "Survey the landscape… actively look for others" is
  unbounded and cannot be conclusively verified
  **Location**: Requirements
  The survey requirement provides no stopping condition or evidence-of-survey
  beyond the three-framework floor, so the obligation is tautological — any
  output can be argued to satisfy or fail it.

#### Minor

- 🔵 **Clarity**: ADR acronym used without expansion in this work item
  **Location**: Requirements
  "ADR" is used several times but never expanded to "Architecture Decision
  Record"; the expansion lives only in the parent epic, weakening the spike's
  stated role as a self-contained recommendation home.

- 🔵 **Clarity**: Compressed cross-references ("theme 1 decision 11") assume the
  epic is open
  **Location**: Requirements
  "theme 1 decision 11" uses a numbering scheme defined only in epic 0001; a
  standalone reader cannot resolve the referent locally.

- 🔵 **Completeness**: Promised Recommendation section not yet present as a
  placeholder
  **Location**: Acceptance Criteria
  The exit criteria promise a Recommendation section, but no placeholder exists
  yet, so the destination for the spike's primary output is implicit. (Expected
  for a draft spike, but a placeholder would make the intended final structure
  visible.)

- 🔵 **Testability**: "How a benchmark result is produced and surfaced" lacks a
  concrete verifiable deliverable
  **Location**: Acceptance Criteria
  "Define how" is satisfiable by prose of any depth, with no stated minimum
  (named command, target result path, file format) for a verifier to check
  against.

- 🔵 **Scope**: Requirements bundle survey-and-recommend with operational-model
  design
  **Location**: Requirements
  The spike bundles a research decision (recommend a framework) with a delivery-
  mechanism design (how a `configure` benchmark is produced/surfaced). Cohesive,
  but framing the operational model as a consequence of the choice would keep
  the spike's primary decision singular.

- 🔵 **Scope**: Open-ended survey plus two analytical deliverables inside a
  2-day box
  **Location**: Requirements
  An unbounded "look for others" survey combined with operational-model and
  floor-validation deliverables risks over-running the time-box or a cursory
  survey.

#### Suggestions

- 🔵 **Clarity**: Bare assumption label "A4" has no local definition
  **Location**: Assumptions
  "(A4)" is the epic's assumption numbering; it appears with no introduction and
  reads as an undefined code to a standalone reader.

- 🔵 **Clarity**: Two distinct numeric floors stated in the same criterion
  without explicit relationship
  **Location**: Acceptance Criteria
  The criterion juxtaposes "≥ 3 tasks, ≥ 80% pass-rate" with "20–50… tasks"
  without stating that the latter is the external benchmark against which the
  former is reconsidered.

- 🔵 **Dependency**: Cross-epic reconciliation of decision-11 renumbering not
  captured as a coupling
  **Location**: Dependencies
  The decision-11 promotion couples to epic 0001's theme 1 numbering and first
  acceptance criterion, recorded only as a drafting note. (Epic 0001 already
  shows 11 decisions, so the reconciliation appears done.)

- 🔵 **Dependency**: Configuration story is an implied precondition for consumer
  0010, not for this spike
  **Location**: Assumptions
  The configure-before-application ordering is a property of 0010, correctly
  absent from this spike's "Blocked by: none". No change required.

- 🔵 **Testability**: Weighting criteria are listed but the recommendation has no
  required form for the comparison
  **Location**: Requirements
  The five weighing dimensions are enumerated, but nothing requires the
  recommendation to report a per-framework assessment against each, so coverage
  of all axes cannot be verified.

### Strengths

- ✅ The decision is explicitly framed as open-ended — the three named
  frameworks are reference shapes, not a fixed shortlist — removing a common
  ambiguity about whether the survey is constrained.
- ✅ Exit criteria are concrete, observable artefacts (a named Recommendation
  section with enumerated elements, an ADR citation) rather than open-ended
  "understand X" goals — exactly the testable form a spike should take.
- ✅ The execution-model constraint (run during development, commit results, not
  on every CI build, to control token cost) is stated consistently across
  Requirements and Acceptance Criteria with no contradiction.
- ✅ Frontmatter is complete and correct: recognised `kind` (spike), appropriate
  `status` (draft), and populated `priority`, `parent`, and `blocks`.
- ✅ Dependencies are well-mapped: both downstream consumers (0010 and 0005) are
  named as Blocks and reconcile with the frontmatter `blocks` array and epic
  0001's intra-epic ordering; upstream is correctly "Blocked by: none".
- ✅ An explicit 2-day time-box appears in both the Summary and Requirements,
  giving the spike a clear stopping point.
- ✅ The promptfoo longevity risk (OpenAI acquisition, Mar 2026) — the one
  external-vendor coupling with planning relevance — is explicitly surfaced as a
  factor the recommendation must weigh.

### Recommended Changes

1. **Split Acceptance Criterion 2 and make the floor-reconciliation checkable**
   (addresses: "Second criterion bundles two checks…", "Two distinct numeric
   floors…", "Requirements bundle survey-and-recommend with operational-model
   design")
   Break the bullet into two criteria. For the floor: require an explicit final
   floor (task count and pass-rate) **with a written rationale** referencing the
   20–50-task / multi-trial guidance for why the floor was kept or changed —
   replacing the always-passing "confirm or raise". Make explicit that the
   20–50 figure is the external benchmark the ≥3-task floor is reconsidered
   against, not a competing requirement.

2. **Make the landscape survey auditable** (addresses: "Survey the landscape…
   unbounded", "Open-ended survey plus two analytical deliverables inside a
   2-day box")
   Require the Recommendation to list every framework considered — at least the
   three named plus any surfaced — each with a one-line reason for inclusion or
   dismissal. This gives the survey a verifiable artefact and bounds it within
   the 2-day box.

3. **Give "how the benchmark is produced" a concrete minimum** (addresses: "How
   a benchmark result is produced and surfaced lacks a concrete deliverable")
   Specify the artefacts the definition must include: the command/entry point
   used to run the eval, the repo path where committed results live, and the
   result file format.

4. **Require the rationale to cover all five weighing dimensions** (addresses:
   "Weighting criteria are listed but the recommendation has no required form")
   Have the first acceptance criterion require the rationale to address each
   enumerated dimension (e.g. a comparison table or per-dimension note) for each
   surveyed framework.

5. **Improve standalone readability** (addresses: "ADR acronym…", "Compressed
   cross-references…", "Bare assumption label 'A4'…", "Promised Recommendation
   section not yet present")
   Expand "ADR" on first use; gloss "theme 1 decision 11" as "decision 11 in
   epic 0001's architecture-decision set"; qualify or drop the bare "(A4)"
   label; and add an empty Recommendation section placeholder so the document's
   intended final structure is visible.

6. **Optionally record the decision-11 ↔ epic-0001 coupling in Dependencies**
   (addresses: "Cross-epic reconciliation of decision-11 renumbering…")
   Note in Dependencies that this spike's decision-11 framing is coupled to epic
   0001's theme 1 numbering, so the two stay reconciled if either changes.

## Per-Lens Results

### Clarity

**Summary**: The work item communicates its intent clearly overall: the spike's
purpose, the open framing of the decision, and the recommended-approach output
are unambiguous and internally consistent with the parent epic. The main
weaknesses are an unexpanded acronym (ADR) and a few compressed parenthetical
references ("theme 1 decision 11", "A4") that assume the reader has the epic
open.

**Strengths**:
- The Context section is explicit that the decision is open-ended and the three
  named frameworks are starting points, not a fixed shortlist.
- Acceptance Criteria use concrete, observable phrasing so intended end states
  are unambiguous.
- The execution-model constraint is stated consistently in both Requirements and
  Acceptance Criteria with no contradiction.

**Findings**:
- 🔵 minor (high confidence) — **ADR acronym used without expansion in this work
  item** (Requirements): "ADR" is used several times but never expanded to
  "Architecture Decision Record"; the expansion exists only in the parent epic.
  A reader opening this spike standalone must consult another document.
- 🔵 minor (medium confidence) — **Compressed cross-references ("theme 1 decision
  11") assume the epic is open** (Requirements): the numbering scheme is defined
  only in epic 0001; within this work item "decision 11" has no resolvable
  referent.
- 🔵 suggestion (medium confidence) — **Bare assumption label "A4" has no local
  definition** (Assumptions): "(A4)" is the epic's assumption numbering, appears
  with no introduction, and reads as an undefined code.
- 🔵 suggestion (low confidence) — **Two distinct numeric floors stated in the
  same criterion without explicit relationship** (Acceptance Criteria): the
  ≥3-task floor and the 20–50 guidance are juxtaposed without stating the latter
  is the benchmark for reconsidering the former.

### Completeness

**Summary**: This spike is structurally complete and well-suited to its kind: an
explicit scoped question, a clear 2-day time-box, exit criteria as concrete
artefacts, and substantively populated Context, Requirements, Dependencies,
Assumptions, Technical Notes, and References. The only notable structural gap is
that the promised Recommendation section does not yet exist as a placeholder.

**Strengths**:
- Frontmatter is complete and correct: recognised `kind` (spike), appropriate
  `status` (draft), populated `priority`/`parent`/`blocks`.
- The spike question is explicit and scoped, with a 2-day time-box in both
  Summary and Requirements.
- Exit criteria are enumerable concrete artefacts, not vague goals.
- Context substantively explains the motivation.
- Open Questions, Dependencies, Assumptions, Technical Notes, and References are
  all populated with relevant content.

**Findings**:
- 🔵 minor (medium confidence) — **Promised Recommendation section not yet present
  as a placeholder** (Acceptance Criteria): the exit criteria and Requirements
  name a Recommendation section as the output destination, but no placeholder
  exists. Expected for a draft, but a placeholder would make the intended final
  structure visible.

### Dependency

**Summary**: As a spike, this work item is well-dependency-mapped: it names both
downstream consumers (0010 and 0005) in the Dependencies Blocks field, matching
the frontmatter `blocks` array and reconciling with parent epic 0001's
child-ordering notes. It correctly records no upstream blockers, consistent with
the decision being genuinely open and the surveyed frameworks being public
reference shapes. The only coupling worth a second look is the promptfoo
longevity risk, already surfaced in Requirements.

**Strengths**:
- Both downstream consumers (0010, 0005) are named explicitly as Blocks,
  consistent with the frontmatter `blocks` array.
- Upstream coupling is correctly recorded as "Blocked by: none".
- The parent relationship to epic 0001 is captured and reconciles with the
  epic's intra-epic ordering notes.
- The promptfoo longevity risk (OpenAI acquisition, Mar 2026) is explicitly
  surfaced as a factor the recommendation must weigh.

**Findings**:
- 🔵 suggestion (medium confidence) — **Cross-epic reconciliation of decision-11
  renumbering not captured as a coupling** (Dependencies): the decision-11
  promotion couples to epic 0001's theme 1 numbering and first acceptance
  criterion, recorded only as a drafting note. Epic 0001 already shows 11
  decisions, so the reconciliation appears done.
- 🔵 suggestion (low confidence) — **Configuration story is an implied
  precondition for consumer 0010, not for this spike** (Assumptions): the
  configure-before-application ordering is a property of 0010, correctly absent
  from this spike's "Blocked by". No change required.

### Scope

**Summary**: This is a well-bounded spike: it names a specific decision
(recommend a single framework or hybrid), states a concrete deliverable (a
Recommendation section feeding ADR decision 11), and is explicitly time-boxed to
2 days. The research questions all serve the single purpose of selecting an
evaluation approach, and the spike kind fits. The only scope tension is that the
spike bundles a second analytical sub-question (validating the provisional
thresholds) alongside the core selection, and the 2-day box is tight for the
breadth of the open-ended survey it also mandates.

**Strengths**:
- The research question is specific and bounded, naming exactly what is decided
  and the concrete deliverable — avoiding the open-ended "investigate X"
  anti-pattern.
- An explicit 2-day time-box appears in both Summary and Requirements.
- All requirements serve one unified purpose — selecting and operationalising a
  skill-evaluation approach.
- The spike-kind classification is appropriate: a genuine unknown resolved with
  a written recommendation rather than shippable code.

**Findings**:
- 🔵 minor (medium confidence) — **Requirements bundle survey-and-recommend with
  operational-model design** (Requirements): the spike bundles a research
  decision with a delivery-mechanism design. Cohesive, but framing the
  operational model as a consequence of the choice would keep the primary
  decision singular.
- 🔵 minor (low confidence) — **Open-ended survey plus two analytical deliverables
  inside a 2-day box** (Requirements): an unbounded "look for others" survey
  combined with two further deliverables risks over-running the box or a cursory
  survey. Tighten the survey's bound.

### Testability

**Summary**: As a spike, this work item is largely well-framed for verification:
its exit criteria name concrete deliverables (a Recommendation section, an ADR
citation) rather than open-ended exploration goals, and it specifies enumerable
surveyed frameworks. The main weaknesses are a verification gap around the
open-ended "survey the landscape" requirement and an under-specified
quantitative confirmation step that bundles two checks without defining a
definitive pass.

**Strengths**:
- Exit criteria are framed as concrete, checkable artefacts — a Recommendation
  section with specific enumerated elements — the testable form a spike should
  take.
- The first criterion specifies a verifiable minimum scope (at least
  skill-creator, promptfoo, DeepEval).
- The third criterion (the ADR cites this work item) is binary and unambiguously
  verifiable.
- The Requirements enumerate concrete evaluation dimensions, giving the rationale
  defined axes a verifier can check.

**Findings**:
- 🟡 major (high confidence) — **Second criterion bundles two distinct checks
  with no defined pass condition for the variance comparison** (Acceptance
  Criteria): part (b) "confirm or raise the floor" passes under any outcome, so
  a verifier cannot distinguish a considered decision from a hand-wave. Split
  into two criteria and make (b) checkable (explicit final floor + written
  rationale referencing the 20–50-task guidance).
- 🟡 major (medium confidence) — **"Survey the landscape… actively look for
  others" is unbounded and cannot be conclusively verified** (Requirements): no
  stopping condition or evidence-of-survey beyond the three-framework floor, so
  the obligation is tautological. Make it auditable (list every framework
  considered with a one-line include/dismiss reason).
- 🔵 minor (medium confidence) — **"How a benchmark result is produced and
  surfaced" lacks a concrete verifiable deliverable** (Acceptance Criteria):
  "define how" is satisfiable by prose of any depth; specify a named command,
  committed-results path, and result file format.
- 🔵 minor (low confidence) — **Weighting criteria are listed but the
  recommendation has no required form for the comparison** (Requirements):
  nothing requires a per-framework assessment against each dimension, so coverage
  of all five axes cannot be verified. Require a comparison table or per-dimension
  note.

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-06-23T22:55:20+00:00

**Verdict:** COMMENT

Both major findings are resolved. The revised work item splits the overloaded
Acceptance Criterion into five individually-checkable criteria, makes the
benchmark-production deliverable concrete (command / committed-results path /
file format), requires per-dimension rationale coverage, and adds the
Recommendation placeholder and standalone-readability glosses. No critical or
major findings remain across any lens; the work item is acceptable for
implementation. The residual items are minor refinements, chiefly that the
"survey the landscape" obligation is now a minor (not major) testability gap and
the AC1/AC2 split introduced a small ambiguity about which frameworks need the
full per-dimension treatment.

### Previously Identified Issues

- 🟡 **Testability** (major): Second criterion bundles two checks with no defined
  pass condition for the variance comparison — **Resolved**. Split into AC3
  (benchmark production) and AC4, which now requires an explicit final floor with
  written rationale referencing the 20–50-task guidance for why it was kept or
  changed.
- 🟡 **Testability** (major): "Survey the landscape… actively look for others" is
  unbounded — **Partially resolved**. AC2 now requires every framework considered
  to be listed with a one-line include/dismiss reason; the lens downgraded the
  concern to minor but notes "every framework considered" still has no verifiable
  lower bound beyond the three named anchors.
- 🔵 **Testability** (minor): "How a benchmark result is produced" lacks a
  concrete deliverable — **Resolved**. AC3 now names the command/entry point,
  committed-results repo path, and result file format.
- 🔵 **Testability** (minor): Weighting criteria listed but no required form —
  **Resolved**. AC1 now requires the rationale to address each weighing dimension
  per surveyed framework (e.g. a comparison table).
- 🔵 **Clarity** (minor): ADR acronym unexpanded — **Resolved**. Expanded to
  "Architecture Decision Record (ADR)" on first use.
- 🔵 **Clarity** (minor): Compressed "theme 1 decision 11" reference —
  **Resolved**. Glossed as "decision 11 in epic 0001's architecture-decision
  set".
- 🔵 **Clarity** (suggestion): Bare "(A4)" label — **Resolved**. Qualified as
  "epic 0001 assumption A4".
- 🔵 **Clarity** (suggestion): Two numeric floors without explicit relationship —
  **Resolved**. AC4 now states the 20–50 figure is the external benchmark, not a
  competing requirement; the clarity lens confirmed the disambiguation.
- 🔵 **Completeness** (minor): Promised Recommendation section not present —
  **Resolved**. Added a Recommendation section placeholder marked "to be
  completed on conclusion".
- 🔵 **Dependency** (suggestion): Decision-11 ↔ epic-0001 reconciliation coupling
  not captured — **Resolved**. Recorded as a reconciliation-coupling entry in
  Dependencies.
- 🔵 **Scope** (minor): Bundles survey-and-recommend with operational-model
  design — **Resolved** (downgraded to suggestion). The scope lens now treats the
  two as cohesive within one research question.
- 🔵 **Scope** (minor): Open-ended survey plus deliverables inside the 2-day box —
  **Partially resolved** (downgraded to suggestion). Survey breadth is now bounded
  by the AC2 listing requirement; the lens suggests confirming the box covers both
  decisions or marking the floor decision as the deferrable secondary output.
- 🔵 **Dependency** (suggestion): Configure-before-0010 ordering — **Still
  present** (low). Correctly a property of 0010, not a blocker here; no change
  required.

### New Issues Introduced

All new findings are minor or suggestion severity.

- 🔵 **Clarity** (minor): AC1 ("for each surveyed framework") and AC2 ("a one-line
  reason… per framework") leave ambiguous whether the full five-dimension
  treatment applies to every surveyed framework or only to shortlisted/recommended
  ones — a small tension introduced by the AC split. Echoed by testability, which
  suggests scoping AC1's coverage to "each framework listed under AC2".
- 🔵 **Clarity** (minor): The same downstream items are referenced by descriptive
  name in Summary/Requirements but by numeric ID (0005/0010) in
  frontmatter/Dependencies, forcing the reader to cross-map names to IDs.
- 🔵 **Testability** (minor): AC2's "plus any surfaced during the survey" and the
  "survey the landscape" requirement still lack a checkable completion artefact;
  the lens suggests recording the search sources/queries consulted to confirm
  breadth rather than asserting exhaustiveness.
- 🔵 **Dependency** (minor): The promptfoo OpenAI-acquisition longevity risk is
  named in Requirements but not tracked as an external coupling in Dependencies —
  optionally record it there once the framework is chosen.
- 🔵 **Clarity / Completeness / Scope** (suggestions): grading-method jargon
  (g-eval, llm-rubric, pass@k/pass^k) used without gloss; optional token/effort
  guardrail alongside the 2-day box; confirm the box realistically covers both the
  framework choice and the floor calibration.

### Assessment

The work item is ready for implementation. The two blocking testability gaps are
resolved, and every other prior finding is resolved or correctly deferred. The
remaining items are minor polish — most usefully, reconciling the AC1/AC2
per-dimension scope and using numeric IDs consistently — and can be folded in
opportunistically or left for the spike author to address when filling in the
Recommendation. No further review pass is required before the spike proceeds.
