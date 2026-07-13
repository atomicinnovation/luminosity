---
type: work-item-review
id: "0016-plugin-global-context-injection-review-1"
title: "Work Item Review: Plugin-Global Additional Context Injection"
date: "2026-07-11T12:47:25+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0016"
relates_to: ["work-item-review:0017", "work-item-review:0018"]
work_item_id: "0016"
reviewer: Toby Clemson
verdict: COMMENT
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 2
tags: [configuration, context-injection]
last_updated: "2026-07-11T13:03:03+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Plugin-Global Additional Context Injection

**Verdict:** REVISE

The story is structurally complete and its core injection behaviour is
specified with strong Given/When/Then acceptance criteria covering the edge
cases (team-only, personal-only, both-present, blank-line trimming,
both-empty, frontmatter split). It falls short of ready on three fronts: a
scope contradiction between the Context ("surfaces through the
`configure`/content skills") and the "every skill" injection requirement; two
cross-cutting acceptance criteria (configure-surface and eval-coverage) with
no observable pass condition; and an uncaptured upstream dependency on the
eval framework (story 0010). The load-bearing near-top placement is required
but not verified by any criterion.

### Cross-Cutting Themes

- **Non-verifiable cross-cutting criteria** (flagged by: testability) — both
  "the `configure` skill surfaces this capability" and "the eval suite covers
  the injection behaviour" name no observable outcome or coverage threshold, so
  either could be claimed met by almost any change.
- **Uncaptured eval-framework dependency** (flagged by: dependency) — the
  eval-coverage AC depends on story 0010's eval framework (per epic 0011), but
  0010 appears nowhere in Dependencies.
- **Load-bearing contract stated but not tested** (flagged by: testability,
  clarity) — near-top placement is declared load-bearing yet no AC verifies the
  block's *position* relative to skill-specific instructions; the exact wrapper
  prose is likewise never embedded, only referenced against the accelerator.

### Findings

#### Critical

- None.

#### Major

- 🟡 **Clarity**: "Surfaces this through the configure/content skills" appears to contradict the "every skill" injection scope
  **Location**: Context
  The Context reads as scoping the feature to `configure`/content skills, while
  Requirements and an AC say the injection reaches every registered skill. A
  reader cannot tell whether injected context appears only in `configure` or in
  every skill.

- 🟡 **Dependency**: Uncaptured upstream dependency on story 0010 eval framework
  **Location**: Dependencies
  The eval-coverage AC depends on the eval framework epic 0011 attributes to
  story 0010, but 0016 names only 0009, 0011, 0017, 0018 — the eval-framework
  prerequisite is invisible and could stall the story late.

- 🟡 **Testability**: "configure skill surfaces this capability" has no verifiable outcome
  **Location**: Acceptance Criteria
  "Surfaces" has no stated procedure, expected output, or invocation a verifier
  could run; the criterion could be claimed met by any change to the skill.

- 🟡 **Testability**: Load-bearing block placement is required but not verified by any criterion
  **Location**: Acceptance Criteria
  Every AC only asserts the prompt *contains* the `## Project Context` block;
  none verifies its position before skill-specific instructions. A block in the
  wrong location would pass all criteria.

#### Minor

- 🔵 **Clarity**: Inconsistent terms for the wrapper leave it unclear whether it is only the header or header-plus-prose
  **Location**: Requirements
  "Wrapper prose", "header line and wrapper prose", and "wrapper header text"
  are used variously; only `## Project Context` is named concretely, so it is
  unclear whether reproducing the header line alone suffices.

- 🔵 **Dependency**: Ordering relationship to 0017/0018 recorded as symmetric
  **Location**: Dependencies
  0016 is the "first of the three themes" and establishes the injection
  mechanism and `## Project Context` placement anchor that 0017 reuses, yet the
  siblings are recorded only as symmetric "Relates to".

- 🔵 **Testability**: Exact-match criterion defers expected value to unembedded accelerator source
  **Location**: Acceptance Criteria
  The expected `## Project Context` wrapper string is not reproduced in the work
  item; a verifier must inspect the accelerator's `config-read-context.sh`,
  whose Rust port the epic notes is not-yet-integrated.

- 🔵 **Testability**: "Eval suite covers the injection behaviour" has no defined coverage threshold
  **Location**: Acceptance Criteria
  "Covers" does not enumerate the scenarios the eval must exercise; it could be
  satisfied by a single trivial eval.

#### Suggestions

- 🔵 **Clarity**: "Content skills" is used without definition
  **Location**: Context
  The term is neither defined nor linked, and is not distinguished from
  `configure`.

- 🔵 **Clarity**: First three requirement bullets do not name the acting component
  **Location**: Requirements
  Only the "Inject…" bullet names the actor; read/concatenate/wrap leave the
  Rust CLI implicit.

- 🔵 **Scope**: Shared injection mechanism leaves 0016 implicitly heavier than sibling stories
  **Location**: Requirements
  As the first story, 0016 carries the one-time shared injection/wiring
  plumbing that 0017/0018 reuse, but is framed as an equal-sized sibling.

- 🔵 **Scope**: Universal "every skill" wiring may expand the story beyond a single increment
  **Location**: Requirements
  All-skills wiring couples a repeated edit across the whole skill set into the
  same story that builds the reader.

- 🔵 **Testability**: Universal-wiring criterion could name its enumeration source
  **Location**: Acceptance Criteria
  The authoritative registry of "registered skills" (e.g. `plugin.json`) is not
  named, leaving the enumerate-and-assert procedure implicit.

### Strengths

- ✅ Acceptance criteria are consistent Given/When/Then statements with concrete
  referents, leaving little room for divergent interpretation.
- ✅ The frontmatter/body split rule and blank-line trimming / empty-emission
  behaviour are stated precisely and consistently between Requirements and AC.
- ✅ Every expected section is present and substantively populated; frontmatter
  is complete and coherent (kind: story, valid parent/relates_to).
- ✅ Open Questions is explicitly resolved ("None outstanding") rather than left
  ambiguous.
- ✅ The decomposition decision to keep 0016 separate from 0017/0018 is
  explicitly recorded and attributed to the author.

### Recommended Changes

1. **Disambiguate the injection scope in Context** (addresses: "Surfaces this
   through the configure/content skills…") — reword so "surfaces" refers to the
   management surface (the `configure` skill, where the user edits config),
   distinct from the injection target (every skill's prompt). Define or drop
   "content skills".

2. **Make the configure-surface and eval-coverage criteria observable**
   (addresses: "configure skill surfaces…", "Eval suite covers…") — restate the
   configure AC as a concrete invocation/output (e.g. the skill lists a
   plugin-global-context action naming the config-body source), and enumerate
   the specific eval scenarios required (the body-presence combinations plus the
   empty-emits-nothing case).

3. **Capture the eval-framework dependency** (addresses: "Uncaptured upstream
   dependency on story 0010") — add 0010 to Dependencies (blocked-by or noted
   upstream with status) so the eval-coverage prerequisite is schedulable.

4. **Add a placement-verification criterion** (addresses: "Load-bearing block
   placement… not verified") — e.g. "Given a wired skill with skill-specific
   instructions, the `## Project Context` block appears before those
   instructions."

5. **Embed the exact wrapper text and name the wiring registry** (addresses:
   "Exact-match criterion defers…", "Universal-wiring… enumeration source",
   "Inconsistent terms for the wrapper") — quote the exact `## Project Context`
   header/prose in the work item, and reference `plugin.json` as the skill
   registry the universal-wiring check enumerates.

6. **Record the sibling ordering** (addresses: "Ordering relationship… recorded
   as symmetric", "Shared injection mechanism leaves 0016 heavier") — note that
   0016 establishes the shared mechanism/placement anchor that 0017/0018 extend,
   sequencing it first.

## Per-Lens Results

### Clarity

**Summary**: Generally clear and well-structured; the main risk is a scope
tension between the Context ("surfaces through the `configure`/content skills")
and the Requirements/AC ("every skill"), compounded by inconsistent wrapper
terminology and one undefined term ("content skills").

**Strengths**:
- Given/When/Then ACs with concrete referents.
- Frontmatter/body split and blank-line rules stated precisely and consistently.
- Open Questions explicitly resolved.

**Findings**:
- 🟡 major (medium): Context "surfaces through configure/content skills"
  contradicts the "every skill" injection scope (Context).
- 🔵 minor (medium): Inconsistent terms for the wrapper — header-only vs
  header-plus-prose (Requirements).
- 🔵 suggestion (medium): "Content skills" used without definition (Context).
- 🔵 suggestion (low): Read/concatenate/wrap bullets do not name the acting
  component (Requirements).

### Completeness

**Summary**: Structurally and informationally complete — every expected section
present and substantively populated, frontmatter fully specified with a
recognised kind and status, ten scenario-based acceptance criteria. No
completeness gaps of consequence.

**Strengths**:
- Well-formed user story naming actor, capability, benefit.
- Context explains why and how (accelerator reference) rather than restating the
  summary.
- Numerous scenario-based ACs; complete, coherent frontmatter; Open Questions
  explicitly closed.

**Findings**: None.

### Dependency

**Summary**: The foundational blocker (0009, done) and sibling relationships are
explicit, but the eval-coverage AC introduces an uncaptured upstream dependency
on story 0010, and the 0016→0017/0018 relationship is under-captured as
symmetric.

**Strengths**:
- Foundational blocker 0009 named with "done" status.
- Parent 0011 and mechanism-sharing siblings named; Open Questions empty.

**Findings**:
- 🟡 major (medium): Uncaptured upstream dependency on story 0010 eval framework
  (Dependencies).
- 🔵 minor (medium): 0016 is the upstream anchor/unblocker for 0017/0018 but
  recorded as a symmetric peer (Dependencies).

### Scope

**Summary**: A well-scoped, coherent story describing a single deliverable; kind
(story) appropriate, boundaries clear, configure-surface and eval-coverage
legitimately part of the end-to-end capability. The only tension is the shared
mechanism with 0017/0018 that leaves 0016 implicitly heavier.

**Strengths**:
- All requirements serve one unified purpose; no unrelated concern bundled in.
- Scope boundaries and the negative case are explicit.
- Decomposition decision recorded and attributed; Summary/Requirements/AC
  consistent.

**Findings**:
- 🔵 suggestion (medium): Shared injection mechanism leaves 0016 heavier than
  sibling stories (Requirements).
- 🔵 suggestion (low): Universal "every skill" wiring may expand the story beyond
  a single increment (Requirements).

### Testability

**Summary**: Core injection behaviours have strong Given/When/Then criteria with
concrete edge cases; two criteria are weak (configure-surface has no observable
outcome, eval-coverage has no threshold), and the load-bearing near-top
placement is not verified by any criterion. One criterion defers its expected
value to unembedded accelerator source.

**Strengths**:
- ACs 1–5 and 7 are Given/When/Then with observable outcomes.
- Edge cases enumerated rather than implied.
- Universal-wiring criterion bounds scope to "every registered skill".

**Findings**:
- 🟡 major (high): "configure skill surfaces this capability" has no verifiable
  outcome (Acceptance Criteria).
- 🟡 major (high): Load-bearing block placement required but not verified by any
  criterion (Acceptance Criteria).
- 🔵 minor (medium): Exact-match criterion defers expected value to unembedded
  accelerator source (Acceptance Criteria).
- 🔵 minor (medium): "Eval suite covers the injection behaviour" has no defined
  coverage threshold (Acceptance Criteria).
- 🔵 suggestion (low): Universal-wiring criterion could name its enumeration
  source (Acceptance Criteria).

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-11

**Verdict:** COMMENT

Lenses re-run: clarity, dependency, scope, testability (completeness had no
prior findings). All four major findings from pass 1 are resolved. The verdict
moves from REVISE to COMMENT; one residual (new) major is an optional
refinement, not a blocker.

### Previously Identified Issues
- 🟡 **Clarity**: Context "surfaces through configure/content skills" contradicts
  the "every skill" scope — **Resolved** (Context now separates the management
  surface from the injection target; "content skills" dropped).
- 🟡 **Dependency**: Uncaptured upstream dependency on story 0010 — **Resolved**
  (0010 recorded; only a classification nuance remains, below).
- 🟡 **Testability**: "configure skill surfaces this capability" not verifiable —
  **Resolved** (rewritten as a concrete `configure` action naming the config
  bodies).
- 🟡 **Testability**: Load-bearing placement not verified by any criterion —
  **Resolved** (added a placement AC: block before skill-specific instructions).
- 🔵 Minors (exact-match text unembedded, inconsistent wrapper terms,
  universal-wiring enumeration source) — **Resolved** (exact block embedded in
  Technical Notes; `plugin.json` named).

### New Issues Introduced
- 🟡 **Testability**: Content ACs phrased "when a wired skill is invoked, then the
  prompt contains…" don't state whether they verify the deterministic CLI stdout
  or the runtime-rendered prompt — two procedures with different determinism.
  (Optional refinement: re-anchor content/format ACs to "the CLI emits…" and
  reserve invocation phrasing for wiring/placement and eval ACs.)
- 🔵 **Dependency**: Frontmatter still lists 0017/0018 as `relates_to` while the
  body reframes them as `Blocks`; 0010 is filed under "Relates to" though it
  gates the eval-coverage AC. (Left as-is: the work-item frontmatter schema has
  no `blocks`/`blocked_by` field; the body carries the richer semantics.)
- 🔵 **Clarity**: Summary understates scope (omits the configure-surface and eval
  deliverables now in Requirements/AC); "wired skill" used before definition.

### Assessment
Ready to progress. The blocking testability and dependency gaps are closed; the
remaining items are minor polish and one optional testability re-anchoring that
the team can take or leave.
