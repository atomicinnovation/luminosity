---
type: work-item-review
id: "0017-per-skill-context-injection-review-1"
title: "Work Item Review: Per-Skill Context Injection"
date: "2026-07-11T12:47:25+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0017"
relates_to: ["work-item-review:0016", "work-item-review:0018"]
work_item_id: "0017"
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

## Work Item Review: Per-Skill Context Injection

**Verdict:** REVISE

The story is structurally complete and its core injection behaviour is well
specified — the path, wrapper header/prose (quoted verbatim), and the
global-then-skill ordering are stated consistently, and the outcomes are
observable prompt states. It falls short of ready on the same cross-cutting
axes as its siblings: the configure-surface and eval-coverage acceptance
criteria have no observable pass condition; the eval-coverage AC depends on
the eval framework (story 0010), which is absent from Dependencies; and the
load-bearing ordering AC (global-then-skill) depends on 0016's output, yet
0016 is recorded only as a symmetric "relates to".

### Cross-Cutting Themes

- **Non-verifiable cross-cutting criteria** (flagged by: testability) — "the
  `configure` skill surfaces this capability" and "the eval suite covers the
  injection behaviour" name no observable outcome or coverage threshold.
- **Uncaptured eval-framework dependency** (flagged by: dependency) — the
  eval-coverage AC depends on story 0010's eval framework (per epic 0011), but
  0010 appears nowhere in Dependencies.
- **Ordering dependency on 0016 under-captured** (flagged by: dependency,
  clarity) — AC4 (global-then-skill) can only be verified once 0016's
  `## Project Context` block exists, but 0016 is recorded only as a symmetric
  "relates to"; the placement rule when no global block exists is also only
  implied.

### Findings

#### Critical

- None.

#### Major

- 🟡 **Dependency**: Ordering dependency on 0016 captured only as "relates to"
  **Location**: Dependencies
  AC4 ("the ordering is global-then-skill") defines 0017's injection point
  relative to 0016's output, yet 0016 is listed only as "Relates to". A planner
  scheduling 0017 first finds AC4 unverifiable — no `## Project Context` anchor
  exists.

- 🟡 **Dependency**: Uncaptured upstream dependency on story 0010 eval framework
  **Location**: Acceptance Criteria
  The eval-coverage AC requires the framework epic 0011 attributes to story
  0010, but 0017 names only 0009 as blocked-by and never references 0010.

- 🟡 **Testability**: "The configure skill surfaces this capability" has no observable outcome
  **Location**: Acceptance Criteria
  "Surfaces" is not tied to a concrete artefact (a listed sub-action, prompt
  string, invocable command, documented path), so a verifier cannot produce a
  definitive pass/fail.

- 🟡 **Testability**: "The eval suite covers the injection behaviour" lacks a defined pass/fail
  **Location**: Acceptance Criteria
  "Covers" does not specify which behaviours or what constitutes coverage, so it
  is effectively tautological — any eval touching context injection satisfies it.

#### Minor

- 🔵 **Clarity**: Placement when the plugin-global block is absent is only implied
  **Location**: Requirements
  "Inject immediately after the plugin-global `## Project Context`" presumes the
  global block exists; where the skill block lands when no global block is
  present is only inferable from "near the top".

- 🔵 **Testability**: Universal-wiring criterion does not define the verified observable
  **Location**: Acceptance Criteria
  For a skill with no `context.md`, "receives the injection" produces no output,
  so the pass condition for that skill is undefined; the procedure (enumerate
  `plugin.json` vs spot-check) is unstated.

#### Suggestions

- 🔵 **Clarity**: Read/wrap vs inject actor split not carried into the Requirements bullets
  **Location**: Requirements
  The Context assigns reading/wrapping to the CLI and injection to the
  preprocessor, but the Requirements are unattributed imperatives.

- 🔵 **Clarity**: Generic `<config-dir>` placeholder not tied to the concrete `.luminosity` path
  **Location**: Context
  Context uses `<config-dir>/skills/…` while Summary/Requirements hardcode
  `.luminosity/skills/…`; the equivalence is left to the reader.

- 🔵 **Dependency**: Exact-match requirement creates a verification coupling to the external accelerator checkout
  **Location**: Assumptions
  The load-bearing exact-match AC makes the `../accelerator` checkout the source
  of truth that must be available to author and verify the string.

- 🔵 **Scope**: Sibling stories 0016/0017/0018 share an identical mechanism — consolidation already settled
  **Location**: Dependencies
  The near-duplicate split is defensible (each is an independently authorable
  extension point) and the rationale is recorded; no action needed.

### Strengths

- ✅ Acceptance criteria state outcomes as observable system states (block
  present/absent, no leading/trailing blank lines, global-then-skill ordering).
- ✅ The concrete path and header are used consistently across Summary,
  Requirements, and AC; the load-bearing wrapper prose is quoted verbatim.
- ✅ Every expected section is present and substantively populated; frontmatter
  is valid and complete; Open Questions explicitly resolved.
- ✅ A genuine end-to-end vertical slice (CLI engine, universal wiring, configure
  surface, eval coverage) serving one capability.
- ✅ The decomposition decision is explicitly recorded and attributed.

### Recommended Changes

1. **Make the configure-surface and eval-coverage criteria observable**
   (addresses: "The configure skill surfaces…", "The eval suite covers…") —
   restate the configure AC as a concrete invocation/output (the skill lists a
   per-skill-context action naming `.luminosity/skills/<skill>/context.md`), and
   enumerate the required eval scenarios (block present when `context.md` exists,
   omitted when absent/empty).

2. **Capture the eval-framework dependency** (addresses: "Uncaptured upstream
   dependency on story 0010") — add 0010 to Dependencies with its status.

3. **Record the ordering dependency on 0016** (addresses: "Ordering dependency
   on 0016 captured only as relates to") — note that AC4's global-then-skill
   verification requires 0016's injection in place, sequencing 0016 first (or
   co-delivered).

4. **State the no-global-context placement rule** (addresses: "Placement when the
   plugin-global block is absent is only implied") — after `## Project Context`
   if present, otherwise at the top of the skill body.

5. **Name the wiring registry and clarify the placeholder** (addresses:
   "Universal-wiring… observable", "Generic `<config-dir>` placeholder…") —
   reference `plugin.json` as the enumeration source for universal wiring, and
   note once that `<config-dir>` resolves to `.luminosity`.

## Per-Lens Results

### Clarity

**Summary**: Clear and internally consistent — path, header/prose, and
global-then-skill ordering are stated consistently and outcomes are observable.
Minor ambiguities remain: the no-global-block placement is only implied, the
read/wrap vs inject actor split is not carried into Requirements, and the
generic `<config-dir>` is not tied to `.luminosity`.

**Strengths**:
- ACs state outcomes as observable system states.
- Concrete path and header used consistently.
- Context assigns actors (CLI reads, preprocessor surfaces).

**Findings**:
- 🔵 minor (medium): Placement when the plugin-global block is absent is only
  implied (Requirements).
- 🔵 suggestion (low): Read/wrap vs inject actor split not carried into
  Requirements (Requirements).
- 🔵 suggestion (low): Generic `<config-dir>` placeholder not tied to the
  concrete `.luminosity` path (Context).

### Completeness

**Summary**: Structurally and informationally complete for its kind. Every
expected section is present and substantively populated; a well-formed user
story, eight concrete acceptance criteria, valid and complete frontmatter.

**Strengths**:
- Textbook user story identifying actor, capability, motivation.
- Numerous, specific ACs beyond the happy path.
- Concrete, actionable Requirements; sound frontmatter; optional sections
  handled honestly (Open Questions resolved).

**Findings**: None.

### Dependency

**Summary**: The resolved blocker (0009), parent (0011), and sibling
relationships are captured, but two implied couplings are weak or absent: the
placement contract makes 0017 an ordering consumer of 0016's output (captured
only as "relates to"), and the eval-coverage AC's dependency on story 0010 is
missing entirely.

**Strengths**:
- Upstream blocker 0009 named with status.
- Sibling couplings named with rationale; parent captured.
- Open Questions explicitly resolved.

**Findings**:
- 🟡 major (medium): Ordering dependency on 0016 captured only as "relates to"
  (Dependencies).
- 🟡 major (medium): Uncaptured upstream dependency on story 0010 eval framework
  (Acceptance Criteria).
- 🔵 suggestion (low): Exact-match requirement creates a verification coupling to
  the external accelerator checkout (Assumptions).

### Scope

**Summary**: A single, coherent unit of work with tight, well-bounded scope; the
`story` kind is appropriate and boundaries against 0016/0018 are explicit. The
only signal — near-duplicate siblings sharing one mechanism — is already
settled with recorded rationale.

**Strengths**:
- All requirements serve one unified purpose.
- Scope boundaries explicit; sibling delineation clear.
- A genuine vertical slice; decomposition deliberate and recorded.

**Findings**:
- 🔵 suggestion (low): Sibling stories share an identical mechanism —
  consolidation is a reasonable question already settled; no action needed
  (Dependencies).

### Testability

**Summary**: Core injection behaviour has strong Given/When/Then criteria and the
load-bearing header is pinned to an exact string. Testability weakens sharply in
the two cross-cutting criteria (configure-surface, eval-coverage), which name no
observable outcome; the universal-wiring criterion is bounded but its procedure
is undefined.

**Strengths**:
- ACs 1–4 are clear Given/When/Then pairs with observable outputs.
- Load-bearing wrapper prose quoted verbatim.
- Empty/absent-file suppression and blank-line trimming each a dedicated
  criterion.

**Findings**:
- 🟡 major (high): "The configure skill surfaces this capability" has no
  observable outcome (Acceptance Criteria).
- 🟡 major (high): "The eval suite covers the injection behaviour" lacks a
  defined pass/fail (Acceptance Criteria).
- 🔵 minor (medium): Universal-wiring criterion does not define the verified
  observable (Acceptance Criteria).

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-11

**Verdict:** COMMENT

Lenses re-run: clarity, dependency, scope, testability. Both pass-1 major
findings are resolved. The pass-2 re-review surfaced one new major — an
imprecise "near the top" fallback placement introduced by the pass-1
amendment — which has now been fixed in this same session, so the verdict moves
from REVISE to COMMENT.

### Previously Identified Issues
- 🟡 **Dependency**: Ordering dependency on 0016 captured only as "relates to" —
  **Resolved** (0016 is now a Blocked-by with rationale; 0017 Blocks 0018).
- 🟡 **Dependency**: Uncaptured upstream dependency on story 0010 — **Resolved**
  (0010 recorded).
- 🟡 **Testability**: "configure skill surfaces this capability" not verifiable —
  **Resolved** (concrete `configure` action naming the `context.md` path).
- 🟡 **Testability**: "eval suite covers the injection behaviour" no pass/fail —
  **Resolved** (scenarios enumerated).
- 🔵 **Clarity**: Placement when the global block is absent only implied —
  **Resolved** (defined explicitly), then **corrected** (see below).

### New Issues Introduced (and fixed this pass)
- 🟡 **Clarity / Testability**: The pass-1 fix defined the missing-global
  placement as "near the top of the skill body" — still imprecise for a
  load-bearing position. **Fixed**: reworded to a fixed near-top injection point
  (the same structural point the block occupies after `## Project Context`, which
  is simply absent), in both the Requirement and the AC.

### Remaining (minor / optional)
- 🔵 **Testability**: Byte-for-byte reference block does not pin terminal
  whitespace / blank-line counts.
- 🔵 **Scope**: Tri-surface bundling (injection + configure + eval) is a
  deliberate epic-mandated vertical slice; no action.

### Assessment
Ready to progress. The two blocking majors are resolved and the placement
imprecision the fix introduced has been corrected; only minor whitespace-pinning
polish remains.
