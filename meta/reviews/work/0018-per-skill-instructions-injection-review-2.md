---
type: work-item-review
id: "0018-per-skill-instructions-injection-review-2"
title: "Work Item Review: Per-Skill Instructions Injection"
date: "2026-07-19T17:34:04+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0018"
relates_to: ["work-item-review:0018"]
work_item_id: "0018"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 2
review_pass: 3
tags: [configuration, context-injection]
last_updated: "2026-07-19T21:55:11+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Per-Skill Instructions Injection

**Verdict:** REVISE

Since review 1 (which closed at COMMENT), the story was enriched to the
two-level team/personal model with frontmatter stripping, and that expansion has
landed cleanly — the story is clear, complete, well-scoped, and thoroughly
dependency-mapped, with the earlier "override"/placement wording issues fully
reconciled. Two testability gaps hold it back from ready: the byte-for-byte
match criterion targets a prose block whose newline positions are undefined (so
two testers could compute different expected bytes), and the universal-wiring
criterion only checks skills that happen to carry a fixture, leaving an un-wired
fixtureless skill undetectable. Running underneath four of the five lenses is an
unresolved `config_assert_no_legacy_layout` Open Question that the item itself
marks "resolve before implementation" while the frontmatter says `status: ready`.

### Cross-Cutting Themes

- **Unresolved legacy-layout precondition vs `status: ready`** (flagged by:
  completeness, dependency, scope, testability) — the story carries an Open
  Question ("does a `config_assert_no_legacy_layout` equivalent already exist, or
  must this story provide it?") annotated "Resolve before implementation", yet
  the frontmatter is `ready`. Four lenses see a different facet of the same
  unresolved edge: a readiness-signal mismatch (completeness), an indeterminate
  upstream graph and mis-attributed provider (dependency), an unfixed scope
  boundary (scope), and an unverifiable precondition path (testability).

### Findings

#### Critical

- None.

#### Major

- 🟡 **Testability**: Byte-for-byte match target has undefined newline positions in the interpolated prose
  **Location**: Acceptance Criteria
  The exact-match AC requires the emitted block to match the Technical Notes
  wrapper block byte-for-byte, but that prose is wrapped across three lines for
  the document's 80-column width and interpolates `<skill-name>` mid-line. It is
  not stated whether the prose newlines are fixed hard breaks or a paragraph
  reflowed to width — so a real skill name of a different length would shift a
  reflow, and no single expected byte string can be derived.

- 🟡 **Testability**: Universal-wiring criterion only verifies skills that carry a fixture
  **Location**: Acceptance Criteria
  Requirements demand wiring the injection into *every* registered skill, but the
  criterion asserts emission only for "each skill with a fixture instructions
  file". A registered skill missing the wiring but also lacking a fixture emits
  nothing and passes unnoticed, so the "all skills" scope is not conclusively
  verified.

#### Minor

- 🔵 **Completeness**: Status is `ready` despite an unresolved blocking Open Question
  **Location**: Frontmatter: status / Open Questions
  The frontmatter sets `status: ready`, but Open Questions carries a
  `config_assert_no_legacy_layout` question explicitly annotated "Resolve before
  implementation" and described in Dependencies as a potential upstream
  prerequisite. A reader taking `ready` at face value could start and hit an
  unresolved precondition.

- 🔵 **Dependency**: Legacy-layout prerequisite provider analysis omits 0016/0017, its named blockers
  **Location**: Dependencies
  The conditional precondition is scoped as "a blocker only if not already
  delivered by 0009", but 0016 (which owns the shared injection/wiring mechanism)
  and 0017 read the same `.luminosity/skills/<skill-name>/...` files and are
  named blockers here — so they are the likelier providers, and if this story
  must build it, ownership among 0016/0017/0018 is unassigned.

- 🔵 **Dependency**: Unresolved conditional blocker leaves the upstream graph indeterminate while status is ready
  **Location**: Open Questions
  With `status: ready` but the precondition unresolved, it is unknown whether an
  additional upstream edge (build-and-land a legacy-layout assertion) exists, so
  a scheduler cannot fully sequence the work and a hidden blocker could surface
  at implementation time.

- 🔵 **Clarity**: "The reader" used as a defined term but only introduced mid-Context
  **Location**: Dependencies
  The bare phrase "the reader" carries the legacy-layout precondition in Open
  Questions, Dependencies, and Technical Notes, but is only implicitly defined
  once in Context ("the reader is implemented in the Rust CLI") — and competes
  with the human "reader" of the document.

- 🔵 **Testability**: Legacy-layout precondition has no verifying criterion
  **Location**: Open Questions
  The Open Questions and Technical Notes flag that the reader may need to call a
  `config_assert_no_legacy_layout` equivalent, but no acceptance criterion
  specifies the expected behaviour when a legacy layout is (or is not) present.

#### Suggestions

- 🔵 **Clarity**: Elliptical referents in the Summary's precedence clause
  **Location**: Summary
  "extend the skill's own (and, by landing last, take precedence over them)"
  elides the noun "instructions" twice, forcing the reader to reconstruct that
  "them" refers to the skill's own instructions at the document's most-read line.

- 🔵 **Clarity**: "First-slice scope" jargon used without a local gloss
  **Location**: Requirements
  "first-slice scope is all skills, not a subset" uses "first-slice" as a scoping
  term without defining it; the parenthetical resolves intent here, so the risk
  is small.

- 🔵 **Dependency**: Blocker readiness status annotated for 0009 but not for 0016/0017
  **Location**: Dependencies
  0009 is annotated "— done", but 0016 and 0017 are named as hard blockers with
  no status marker, so a reader cannot tell at a glance whether those edges are
  cleared given the `ready` status.

- 🔵 **Scope**: Legacy-layout precondition leaves the story's scope boundary unfixed
  **Location**: Open Questions
  If a `config_assert_no_legacy_layout` equivalent does not already exist,
  resolving it as in-scope would expand the story beyond injection into
  config-surface groundwork; the boundary is sound only under the current "it is
  upstream" assumption.

### Strengths

- ✅ The "skill body" vs "prompt" placement ambiguity from review 1 is now
  pre-empted by an explicit equivalence statement, and "override"/precedence is
  disambiguated as emergent from ordering, not a separate mechanism.
- ✅ Every section a story needs is present and substantively populated, with an
  extensive set of observable Given/When/Then acceptance criteria well beyond the
  minimum, and the exact wrapper block embedded as a single source of truth.
- ✅ Unusually well dependency-mapped: 0009 (done), 0016/0017 (with reasons),
  0010 (eval framework), parent 0011, and the conditional legacy-layout
  prerequisite are all captured, with the load-bearing context-early/
  instructions-last ordering named as the coupling to 0016/0017.
- ✅ Well-scoped and coherent — every requirement serves the single per-skill
  injection capability, and the decomposition from 0016/0017 is explicitly
  justified in the Drafting Notes.
- ✅ Negative and edge cases (absent/empty → no block, blank-line trimming,
  frontmatter stripping, ordering) each have a dedicated, isolated criterion.
- ✅ ADR references are carefully qualified (ADR-0020 flagged as an accelerator
  ADR, governing Luminosity ADRs named), preventing cross-repo confusion.

### Recommended Changes

1. **Resolve the `config_assert_no_legacy_layout` Open Question or reconcile the
   status** (addresses: "Status is `ready` despite an unresolved blocking Open
   Question", "Unresolved conditional blocker leaves the upstream graph
   indeterminate", "Legacy-layout prerequisite provider analysis omits
   0016/0017", "Legacy-layout precondition leaves the story's scope boundary
   unfixed") — confirm whether 0009, 0016, or 0017 already delivers the
   equivalent (widen the provider check beyond 0009), and either drop the
   prerequisite / promote it to a firm Blocked-by edge, or move the item off
   `ready` until it resolves. This single action clears the dominant cross-cutting
   theme.

2. **Make the byte-for-byte contract deterministic** (addresses: "Byte-for-byte
   match target has undefined newline positions") — state explicitly whether the
   wrapper prose is emitted with fixed hard line breaks at the shown positions
   (independent of skill-name length) or as a single logical line that reflows, so
   the expected output for a given skill name is fully determined.

3. **Close the universal-wiring verification gap** (addresses: "Universal-wiring
   criterion only verifies skills that carry a fixture") — either require a
   fixture for every registered skill so the registry-iterating test covers all
   entries, or add a criterion asserting the injection invocation line is present
   in every `SKILL.md` regardless of fixture presence.

4. **Add a criterion (or explicit out-of-scope note) for the legacy-layout path**
   (addresses: "Legacy-layout precondition has no verifying criterion") — once
   the Open Question resolves, specify the observable outcome under a legacy
   layout, or record that it is out of scope for this story.

5. **Minor wording polish** (addresses: "'The reader' used as a defined term",
   "Elliptical referents in the Summary's precedence clause", "'First-slice
   scope' jargon", "Blocker readiness status annotated for 0009 but not for
   0016/0017") — name "the reader" consistently (e.g. "the per-skill instructions
   reader"), spell out the elided "instructions" in the Summary precedence clause,
   gloss "first-slice", and annotate the live status of the 0016/0017 blockers.

## Per-Lens Results

### Clarity

**Summary**: Unusually clear and internally consistent — actors are named, the
accelerator-vs-Luminosity divergences are explicitly demarcated, and prior
placement-term drift and "override" wording were already reconciled in review 1.
Residual issues are minor elliptical or lightly-defined referents.

**Strengths**:
- The "skill body" vs "prompt" placement ambiguity is pre-empted by an explicit
  equivalence statement.
- "override"/precedence semantics are disambiguated as emergent from ordering,
  not a separate precedence mechanism.
- ADR references carefully qualified (ADR-0020 flagged as accelerator's).
- Actors consistently named in Requirements (each begins "The Rust CLI …").

**Findings**:
- 🔵 suggestion (medium): Elliptical referents in the Summary's precedence clause
  (Summary) — "the skill's own [instructions]" and "take precedence over them"
  elide the noun.
- 🔵 minor (medium): "The reader" used as a defined term but only introduced
  mid-Context (Dependencies) — carries the legacy-layout precondition with no
  local antecedent in Open Questions/Dependencies.
- 🔵 suggestion (low): "First-slice scope" jargon used without a local gloss
  (Requirements).

### Completeness

**Summary**: Structurally and informationally complete — every section a story
needs is present and substantively populated (user-story Summary, divergence-
explaining Context, detailed Requirements, extensive ACs, populated Dependencies/
Assumptions/Open Questions/Technical Notes with a byte-exact wrapper block).
Frontmatter intact with valid kind/status/priority. The only tension is
`status: ready` coexisting with a self-declared blocking Open Question.

**Strengths**:
- Well-formed user-story Summary naming actor, capability, and reason.
- Context explains motivation and captures the two deliberate divergences.
- Numerous Given/When/Then ACs tied to concrete observables.
- Kind-specific story content fully present; Technical Notes embeds the exact
  wrapper block as single source of truth.
- Frontmatter complete and coherent.

**Findings**:
- 🔵 minor (high): Status is `ready` despite an unresolved blocking Open Question
  (Frontmatter: status / Open Questions).

### Dependency

**Summary**: Unusually well dependency-mapped — upstream blockers (0009 done,
0016 shared mechanism, 0017 template), the 0010 eval-framework relation, parent
0011, and a conditional legacy-layout prerequisite are all captured, with the
load-bearing ordering coupling to 0016/0017 named. No external systems implied.
The soft spot is the conditional precondition whose provider analysis considers
only 0009, leaving an upstream edge indeterminate while the story is `ready`.

**Strengths**:
- 0016/0017 couplings captured with reasons, making the 0016 → 0017 → 0018
  sequence explicit.
- The context-early/instructions-last ordering named as the concrete reason
  0016/0017 must land first.
- 0010 eval dependency captured in both frontmatter and Dependencies.
- Conditional legacy-layout precondition surfaced consistently rather than left
  implicit.

**Findings**:
- 🔵 minor (medium): Legacy-layout prerequisite provider analysis omits 0016/0017,
  its named blockers (Dependencies).
- 🔵 minor (medium): Unresolved conditional blocker leaves the upstream graph
  indeterminate while status is ready (Open Questions).
- 🔵 suggestion (low): Blocker readiness status annotated for 0009 but not for
  0016/0017 (Dependencies).

### Scope

**Summary**: Well-scoped and coherent — every requirement serves the single
capability of injecting per-skill instructions at the end of a skill's prompt,
and Summary/Requirements/AC describe the same scope consistently. The story kind
fits, and the decomposition from 0016/0017 is explicitly justified. The one
scope-adjacent observation is the unresolved legacy-layout precondition, which
the item already externalises as upstream.

**Strengths**:
- All requirements orbit one deliverable; the two accelerator divergences are
  variations of the same capability, not separate features.
- The CLI reader + all-skill wiring + configure surface + eval coverage bundle is
  a deliberate end-to-end unit mandated by epic 0011, not scope sprawl.
- Decomposition rationale explicit and defensible in Drafting Notes.
- No section-to-section scope drift.

**Findings**:
- 🔵 suggestion (low): Legacy-layout precondition leaves the story's scope
  boundary unfixed (Open Questions) — sound only under the "it is upstream"
  assumption.

### Testability

**Summary**: Unusually strong on verification — nearly every AC is an observable
Given/When/Then covering positive, negative, combination, frontmatter, trimming,
ordering, and universal-wiring scenarios, with an exact wrapper block as single
source of truth. Two gaps remain: the byte-for-byte target's newline positions
are undefined, and the universal-wiring criterion only checks fixture-carrying
skills. A minor gap: the unresolved legacy-layout precondition has no criterion.

**Strengths**:
- Every injection scenario has a dedicated, isolated, observable criterion.
- Negative cases explicit (no files / both empty → no block), preventing a
  tautological pass.
- Exact wrapper block nominated as single source of truth; registry-iterating
  wiring test concretely specified.
- Context-then-instructions ordering gives a concrete relative-position check.

**Findings**:
- 🟡 major (medium): Byte-for-byte match target has undefined newline positions in
  the interpolated prose (Acceptance Criteria).
- 🟡 major (medium): Universal-wiring criterion only verifies skills that carry a
  fixture (Acceptance Criteria).
- 🔵 minor (medium): Legacy-layout precondition has no verifying criterion (Open
  Questions).

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-19

**Verdict:** COMMENT

Lenses re-run: all five. **Every finding from pass 1 is resolved** — both majors,
all five minors, and all four suggestions. Completeness now reports no findings,
and testability praises the amended byte-for-byte and dual universal-wiring
criteria by name. The pass-2 re-review surfaced one new major — a *latent* gap
not introduced by the amendments: the load-bearing "drop the empty level" join
path has no verifying criterion. Because there is a single major (and no
critical), the verdict moves from REVISE to COMMENT.

### Previously Identified Issues
- 🟡 **Testability**: Byte-for-byte match target had undefined newline positions —
  **Resolved** (prose pinned to fixed hard line breaks, independent of skill-name
  length; testability now calls the expected bytes "fully determined").
- 🟡 **Testability**: Universal-wiring criterion only verified fixture-carrying
  skills — **Resolved** (new criterion asserts the invocation line is present in
  every registered `SKILL.md` regardless of fixture).
- 🔵 **Completeness**: `status: ready` despite a blocking Open Question —
  **Resolved** (Open Question retired as not-applicable; completeness clean).
- 🔵 **Dependency**: Legacy-layout provider analysis omitted 0016/0017 —
  **Resolved** (precondition retired: no legacy layout on an unreleased plugin).
- 🔵 **Dependency**: Unresolved conditional blocker left the upstream graph
  indeterminate — **Resolved** (retired; all three blockers annotated done).
- 🔵 **Clarity**: "the reader" used as an underspecified defined term —
  **Resolved** (named "the per-skill instructions reader (the Rust CLI
  component)").
- 🔵 **Testability**: Legacy-layout precondition had no verifying criterion —
  **Resolved** (explicitly out of scope).
- 🔵 **Clarity**: Elliptical referents in the Summary precedence clause —
  **Resolved** (noun "instructions" spelled out).
- 🔵 **Clarity**: "first-slice scope" jargon — **Resolved** ("this story's initial
  delivery scope").
- 🔵 **Dependency**: 0016/0017 blockers lacked a status marker — **Resolved**
  (both annotated "done").
- 🔵 **Scope**: Legacy-layout precondition left the scope boundary unfixed —
  **Resolved** (declared out of scope).

### New Issues Introduced (latent gaps surfaced, not caused by the amendments)
- 🟡 **Testability**: The mixed empty-level combination case (non-empty team +
  present-but-empty personal, or the symmetric case) — the load-bearing
  "drop the empty level" join path — has no verifying acceptance criterion. The
  criteria cover team-only, personal-only, both-non-empty, and both-empty, but
  not the drop-empty survivor path, so a stray/doubled blank line there would
  pass every listed criterion.
- 🔵 **Clarity**: The ordering criteria refer to "the context blocks" / "when both
  files exist" without naming which blocks/files (the `## Project Context` and
  `## Skill-Specific Context` blocks from 0016/0017), so the criterion is not
  self-contained.
- 🔵 **Testability**: The byte-for-byte block **terminator** (trailing newline or
  none) and the inter-block **separator** between the context and instructions
  blocks are unpinned, so a fully assembled byte assertion still has an
  undetermined seam.
- 🔵 **Dependency**: The eval framework (0010) is a de-facto prerequisite for the
  eval-coverage criterion but is filed under "Relates to" without the done-status
  annotation the three hard blockers carry.

### Assessment
Ready to progress. Every blocking issue from pass 1 is resolved and the verdict
moves REVISE → COMMENT. The one new major and the minors are determinism/coverage
refinements (a missing empty-level AC, an unpinned block terminator, unnamed
ordering referents) rather than blockers — worth a quick follow-up amendment but
not gating implementation.

## Approval (Pass 3) — 2026-07-19

**Verdict:** APPROVE

The follow-up amendments after pass 2 closed every non-suggestion item the
re-review surfaced: the mixed empty-level (drop-empty join) case now has a
dedicated acceptance criterion; the ordering criterion and Requirements name the
`## Project Context` / `## Skill-Specific Context` blocks and scope the check to
relative position; the block terminator is pinned in Technical Notes (final
content line + single newline, no trailing blank line); and the 0010
eval-framework relation is annotated done. Only three deliberately-deferred
suggestion-level polish items remain (split the dense Summary sentence, a
downstream "Blocks epic 0011" note, a note that precedence is verified
positionally), none of which gate implementation. With all three blockers
(0009/0016/0017) done and the eval framework (0010) done, the work item is
approved and ready for implementation.
