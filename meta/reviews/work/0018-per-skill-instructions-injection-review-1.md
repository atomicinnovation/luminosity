---
type: work-item-review
id: "0018-per-skill-instructions-injection-review-1"
title: "Work Item Review: Per-Skill Instructions Injection"
date: "2026-07-11T12:47:25+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0018"
relates_to: ["work-item-review:0016", "work-item-review:0017"]
work_item_id: "0018"
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

## Work Item Review: Per-Skill Instructions Injection

**Verdict:** REVISE

The story is structurally complete and its core injection behaviour is
strongly specified — the path, the exact wrapper prose ("Follow these
instructions in addition to all instructions above."), and the load-bearing
context-early/instructions-last ordering are all pinned. It falls short of
ready on the same cross-cutting axes as its siblings: the configure-surface
and eval-coverage acceptance criteria have no observable pass condition; the
eval-coverage AC depends on story 0010's eval framework, absent from
Dependencies; and the ordering-verification AC (AC4) depends on 0016/0017
producing the context blocks it orders against, yet those are recorded only as
"relates to". A local clarity wrinkle: the Summary promises "override"
semantics the additive wrapper does not substantiate.

### Cross-Cutting Themes

- **Non-verifiable cross-cutting criteria** (flagged by: testability) — "the
  `configure` skill surfaces this capability" and "the eval suite covers the
  injection behaviour" name no observable outcome or coverage threshold.
- **Uncaptured eval-framework dependency** (flagged by: dependency) — the
  eval-coverage AC depends on story 0010's eval framework (per epic 0011), but
  0010 appears nowhere in Dependencies.
- **Load-bearing ordering AC depends on siblings** (flagged by: dependency) —
  AC4 (instructions-after-context) is vacuously unverifiable unless 0016/0017
  are in place, but they are recorded only as symmetric "relates to".
- **Requirements/AC scope mismatch** (flagged by: scope) — the Requirements
  scope only the injection mechanism; the configure-surface and eval-coverage
  deliverables appear only in the Acceptance Criteria.

### Findings

#### Critical

- None.

#### Major

- 🟡 **Dependency**: Ordering-verification AC depends on 0016/0017 but they are only "relates to"
  **Location**: Acceptance Criteria
  AC4 ("the instructions block appears after the context blocks") can only be
  verified once those context blocks (produced by 0016/0017) exist, yet they
  appear here only as "Relates to" — even though the Context calls this ordering
  load-bearing. If 0018 lands first, AC4 is vacuously unverifiable.

- 🟡 **Dependency**: Eval-coverage criterion depends on eval framework (0010), not in Dependencies
  **Location**: Acceptance Criteria
  The eval-coverage AC presupposes the framework epic 0011 attributes to story
  0010, which is not named anywhere in 0018's Dependencies (only 0009, 0011,
  0016, 0017).

- 🟡 **Testability**: "configure skill surfaces this capability" has no observable pass condition
  **Location**: Acceptance Criteria
  "Surfaces" could be satisfied by a single mention in help text, a documented
  sub-action, an interactive flow, or nothing — a verifier has no defined
  procedure to confirm it.

- 🟡 **Testability**: "eval suite covers the injection behaviour" is not a definitive pass/fail
  **Location**: Acceptance Criteria
  "Covers" has no defined scope — it can always be claimed passed by adding a
  single trivial eval, giving no assurance the load-bearing behaviours are
  exercised.

#### Minor

- 🔵 **Clarity**: "extend or override" conflicts with additive wrapper framing
  **Location**: Summary
  The Summary says instructions can "extend or **override**" the skill's own,
  but the Context and AC describe a purely additive mechanism ("in addition to
  all instructions above"). Nothing establishes what "override" means or how it
  is achieved.

- 🔵 **Clarity**: Placement target drifts between "skill body" and "prompt"
  **Location**: Acceptance Criteria
  The injection point is "end of the prompt" (Summary/AC1) and "end of the skill
  body" (Requirements/Context) interchangeably; for a load-bearing placement it
  is not stated whether the two coincide.

- 🔵 **Dependency**: Shared injection mechanism with 0016/0017 has uncaptured build ordering
  **Location**: Dependencies
  Whichever sibling lands first must build the shared reader/injection harness;
  the others depend on it, but this build-ordering is not captured — risking the
  harness being built twice or each sibling assuming the other builds it.

- 🔵 **Scope**: Acceptance Criteria introduce configure-surface and eval deliverables absent from Requirements
  **Location**: Acceptance Criteria
  The five Requirements bullets concern only the injection mechanism; the
  configure-skill expansion and eval extension appear only in the AC, so an
  implementer sizing from Requirements alone would miss them.

- 🔵 **Testability**: Universal-wiring criterion is bounded but its verification procedure is undefined
  **Location**: Acceptance Criteria
  AC6 is bounded to the finite registered-skill set but does not say whether
  universality is verified by enumerating `plugin.json` or by spot-checking a
  sample — materially different guarantees.

- 🔵 **Testability**: Internal arrangement of the emitted block is not fully specified
  **Location**: Acceptance Criteria
  AC5 pins the header/prose and AC1 pins the block's position, but no criterion
  states the arrangement within the block (content after the prose line vs
  interleaved), so the full block string is not byte-verifiable.

#### Suggestions

- 🔵 **Clarity**: `<config-dir>` placeholder vs concrete `.luminosity` path
  **Location**: Context
  Context uses `<config-dir>/skills/…` while Summary/Requirements use
  `.luminosity/skills/…`; the mapping is left implicit.

- 🔵 **Dependency**: Implied dependency on a legacy-layout assertion precondition
  **Location**: Technical Notes
  The Technical Notes say the accelerator's readers call
  `config_assert_no_legacy_layout` first; if the Luminosity equivalent is
  separate infrastructure, it is an uncaptured prerequisite.

- 🔵 **Scope**: Three injection stories share one mechanism and each re-mandates universal wiring
  **Location**: Dependencies
  Each of 0016/0017/0018 independently mandates wiring every skill; without a
  stated sequencing the universal-wiring effort may be paid three times.

- 🔵 **Testability**: "override" intent in the Summary is not reflected in any criterion
  **Location**: Summary
  No criterion ties end-of-prompt placement to override precedence; if override
  is an emergent property of ordering, the spec should say so.

### Strengths

- ✅ The exact wrapper prose and `## Additional Instructions` header are quoted
  identically across Context, Requirements, and AC.
- ✅ The load-bearing ordering (context near the top, instructions at the end) is
  stated explicitly with a rationale (the header references "all instructions
  above").
- ✅ Every expected section is present and substantively populated; frontmatter
  is intact with a valid kind and all required fields; Open Questions resolved.
- ✅ A self-contained vertical slice (CLI engine, universal wiring, configure
  surface, eval coverage) matching the epic's per-theme delivery pattern.
- ✅ The decomposition decision to keep 0018 separate from 0016/0017 is recorded
  and attributed.

### Recommended Changes

1. **Make the configure-surface and eval-coverage criteria observable**
   (addresses: "configure skill surfaces…", "eval suite covers…") — restate the
   configure AC as a concrete invocation/output (the skill lists a per-skill
   instructions action naming `.luminosity/skills/<skill>/instructions.md`), and
   enumerate the required eval scenarios (block at end for non-empty file, no
   block for absent file, exact header/prose).

2. **Capture the eval-framework dependency** (addresses: "Eval-coverage criterion
   depends on eval framework (0010)…") — add 0010 to Dependencies with its
   status.

3. **Record the ordering dependency on 0016/0017** (addresses: "Ordering-
   verification AC depends on 0016/0017…", "Shared injection mechanism… build
   ordering") — note that AC4 requires at least one of 0016/0017 in place, and
   state which story owns the shared injection harness.

4. **Reconcile the "override" wording** (addresses: "'extend or override'
   conflicts…", "'override' intent… not reflected") — either drop "override"
   from the Summary to match the additive wrapper, or state that end-of-prompt
   placement is the sole override mechanism (an emergent property of ordering).

5. **Fix the placement-target term and specify the block skeleton** (addresses:
   "Placement target drifts…", "Internal arrangement… not fully specified") — use
   one term consistently (e.g. "end of the skill body") and add the expected
   block skeleton (header line, prose line, trimmed content).

6. **Mirror the cross-cutting deliverables into Requirements and name the wiring
   registry** (addresses: "Acceptance Criteria introduce configure-surface and
   eval deliverables absent from Requirements", "Universal-wiring… procedure…
   undefined") — add Requirements bullets for the configure-surface and eval
   extension, and reference `plugin.json` as the universal-wiring enumeration
   source.

## Per-Lens Results

### Clarity

**Summary**: Largely unambiguous — paths, wrapper header text, and the
load-bearing ordering are stated precisely and consistently. Two concerns: the
Summary promises "override" semantics the additive mechanism does not
substantiate, and the placement target drifts between "skill body" and "prompt".

**Strengths**:
- Exact wrapper prose and header quoted identically across sections.
- Load-bearing ordering stated explicitly with rationale.
- File paths and empty/absent-file behaviour stated consistently.

**Findings**:
- 🔵 minor (medium): "extend or override" conflicts with additive wrapper
  framing (Summary).
- 🔵 minor (medium): Placement target drifts between "skill body" and "prompt"
  (Acceptance Criteria).
- 🔵 suggestion (low): `<config-dir>` placeholder vs concrete `.luminosity` path
  (Context).

### Completeness

**Summary**: A highly complete story. Every expected section present and
substantively populated: a well-formed user-story Summary, a Context capturing
the load-bearing ordering constraint, five Requirements, eight ACs, and
populated Dependencies/Assumptions/Open Questions/Technical Notes/References.
Frontmatter intact with valid kind. No material completeness gaps.

**Strengths**:
- Canonical user-story Summary naming user and need.
- Eight specific ACs well beyond the minimum.
- Context captures the non-obvious load-bearing constraint; kind-appropriate
  content complete; frontmatter coherent; optional sections populated honestly.

**Findings**: None.

### Dependency

**Summary**: The foundational blocker (0009, done) and the sibling relationship
are captured with rationale, and there are no external-system couplings.
However, two ACs carry implied upstream dependencies the section does not
capture: eval-coverage depends on story 0010, and the ordering-verification AC
depends on 0016/0017 being present.

**Strengths**:
- Foundational blocker 0009 named with status.
- Sibling coupling captured with rationale; parent recorded; no external
  couplings, consistent with a self-contained internal feature.

**Findings**:
- 🔵 major (medium): Eval-coverage criterion depends on eval framework (0010),
  not in Dependencies (Acceptance Criteria).
- 🟡 major (medium): Ordering-verification AC depends on 0016/0017 but they are
  only "relates to" (Acceptance Criteria).
- 🔵 minor (medium): Shared injection mechanism with 0016/0017 has uncaptured
  build ordering (Dependencies).
- 🔵 suggestion (low): Implied dependency on a legacy-layout assertion
  precondition (Technical Notes).

### Scope

**Summary**: A well-scoped, coherent story; every requirement serves the single
purpose of injecting per-skill instructions at the end of a skill's prompt, with
clear in/out boundaries. Sizing as a `story` is appropriate. The only signals
are minor: the AC introduce two deliverables the Requirements omit, and the
three near-identical stories each mandate universal wiring.

**Strengths**:
- All five Requirements serve one unified purpose; no bundling.
- Boundaries crisp; deliverable as a single increment.
- Decomposition deliberate and recorded; a self-contained vertical slice.

**Findings**:
- 🔵 minor (medium): Acceptance Criteria introduce configure-surface and eval
  deliverables absent from Requirements (Acceptance Criteria).
- 🔵 suggestion (low): Three injection stories share one mechanism and each
  re-mandates universal wiring (Dependencies).

### Testability

**Summary**: Core injection behaviour is strongly specified — most ACs are
Given/When/Then, the edge cases are enumerated, and the load-bearing header
prose is pinned to an exact string. Testability weakens sharply in the two
cross-cutting criteria (configure-surface, eval-coverage), which name no
observable outcome; the universal-wiring criterion is bounded but its procedure
undefined.

**Strengths**:
- AC5 pins the header/wrapper prose to an exact string for byte-level pass/fail.
- Behavioural ACs 1–4 are clear Given/When/Then pairs.
- Edge cases (absent/empty, blank-line trimming, ordering) each a dedicated
  criterion.

**Findings**:
- 🟡 major (medium): "configure skill surfaces this capability" has no observable
  pass condition (Acceptance Criteria).
- 🟡 major (medium): "eval suite covers the injection behaviour" is not a
  definitive pass/fail (Acceptance Criteria).
- 🔵 minor (medium): Universal-wiring criterion is bounded but its verification
  procedure is undefined (Acceptance Criteria).
- 🔵 minor (low): Internal arrangement of the emitted block is not fully
  specified (Acceptance Criteria).
- 🔵 suggestion (low): "override" intent in the Summary is not reflected in any
  criterion (Summary).

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-11

**Verdict:** COMMENT

Lenses re-run: clarity, dependency, scope, testability. Both pass-1 major
findings are resolved. The pass-2 re-review surfaced two new majors introduced
by the pass-1 amendments — an AC5 enumeration that dropped a blank line the
reference block includes, and a `config_assert_no_legacy_layout` precondition
left as a "confirm whether it exists" note while Open Questions still said "None
outstanding". Both are now fixed in this same session, so the verdict moves from
REVISE to COMMENT.

### Previously Identified Issues
- 🟡 **Dependency**: Ordering-verification AC depends on 0016/0017, recorded only
  as "relates to" — **Resolved** (0016/0017 are now Blocked-by with rationale).
- 🟡 **Dependency**: Eval-coverage AC depends on eval framework (0010) — **Resolved**
  (0010 recorded).
- 🟡 **Testability**: "configure skill surfaces this capability" not verifiable —
  **Resolved** (concrete `configure` action naming the `instructions.md` path).
- 🟡 **Testability**: "eval suite covers the injection behaviour" no pass/fail —
  **Resolved** (scenarios enumerated).
- 🔵 **Clarity**: "extend or override" conflicts with additive framing —
  **Resolved** (override stated as emergent from instructions-last ordering).
- 🔵 **Clarity**: "skill body" vs "prompt" placement drift — **Resolved**
  (declared equivalent).

### New Issues Introduced (and fixed this pass)
- 🟡 **Clarity / Testability**: AC5's inline enumeration omitted the blank line
  after the header that the Technical Notes reference block includes — a
  contradiction in a byte-for-byte contract. **Fixed**: AC5 now defers to the
  Technical Notes block as the single source of truth and lists the blank line.
- 🟡 **Dependency**: The `config_assert_no_legacy_layout` precondition was flagged
  "confirm whether it exists" in Technical Notes while Open Questions said "None
  outstanding". **Fixed**: recorded as an Open Question and a conditional
  prerequisite in Dependencies.

### Remaining (minor / optional)
- 🔵 **Testability**: Whether `<skill-name>` substitutes into fixed line breaks
  vs reflows is unstated (matters for the byte-for-byte check); whitespace-only
  content not distinctly covered; configure-surface "action" threshold loose.
- 🔵 **Clarity**: "the reader" floating referent (accelerator script vs Rust CLI).

### Assessment
Ready to progress. The blocking majors — plus the two regressions the pass-1
amendments introduced — are resolved; only minor determinism/wording polish
remains.
