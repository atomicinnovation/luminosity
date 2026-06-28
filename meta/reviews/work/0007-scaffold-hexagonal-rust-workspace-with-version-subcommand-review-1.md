---
type: work-item-review
id: "0007-scaffold-hexagonal-rust-workspace-with-version-subcommand-review-1"
title: "Work Item Review: Scaffold the Hexagonal Rust Workspace with a version Subcommand"
date: "2026-06-28T19:37:46+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0007"
work_item_id: "0007"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 3
tags: []
last_updated: "2026-06-28T19:37:46+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Scaffold the Hexagonal Rust Workspace with a version Subcommand

**Verdict:** COMMENT

This is a strong, implementation-ready story: structurally complete, densely
populated, internally consistent, and well-scoped around a single coherent
purpose — proving the hexagonal architecture end-to-end with one minimal
vertical slice. Its Acceptance Criteria are unusually testable for a structural
scaffold, and its cross-references to ADR-0009/0010/0002 and the spike are
accurate. The findings are improvements rather than blockers: one major clarity
gap (the story never names which crate hosts the `version` hexagon), and a
recurring minor theme that the external-dispatch scope relocated to story 0008
is described as still outstanding when it has since landed. The work item is
acceptable as-is, but addressing the major finding before implementation would
remove a genuine ambiguity.

### Cross-Cutting Themes

- **Stale "0008 doesn't yet capture the relocated scope" claim** (flagged by:
  dependency, scope, completeness) — The Drafting Notes assert that
  external-subcommand dispatch was relocated to 0008 but that 0008 "does not yet
  capture" it and is "stale against ADR-0002". Three lenses independently flag
  that this cross-story note is now itself out of date (0008 has been updated),
  or at minimum needs confirmation that the relocated scope has a confirmed
  owner so it does not fall between the two stories.
- **Workspace layout is asserted but not pinned down** (flagged by: clarity,
  testability) — Clarity flags (major) that no crate is named as the home of the
  `version` hexagon; testability flags that AC2's "follows the subdomain-first
  layout" half has no concrete pass/fail procedure. Both point at the same
  underspecified structure — naming the concrete starting crates/modules
  resolves both.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Clarity**: Crate that hosts the version hexagon is never named
  **Location**: Requirements
  The item lists the crate set as `kernel`, `config`, `config-adapters`, `cli`,
  "one crate per subdomain", scopes the starting set to "just `cli` plus
  `kernel`", but never says which crate holds the `version` hexagon's inbound
  port, core, outbound port, adapter, and composition root. ADR-0010 reserves
  `cli` as a thin launcher that never depends on a subdomain and keeps `kernel`
  dependency-light, so neither obviously hosts a domain core — leaving the
  central deliverable's location open to incompatible interpretations.

#### Minor

- 🔵 **Clarity**: "one crate per subdomain" reads as contradicting the
  single-crate starting state
  **Location**: Summary
  The Summary's "one crate per subdomain" can be read as a per-subdomain split
  delivered now, when the intent (per ADR-0010) is the target shape the
  version-only scaffold does not yet reach.

- 🔵 **Clarity**: "genuinely external" build metadata leans on an unstated
  justification
  **Location**: Requirements
  The Requirement states the build-metadata port is for data "genuinely
  external" as settled fact, while the rationale for treating a near-constant
  read as a real port lives only in Assumptions/Drafting Notes, with no
  cross-reference connecting them.

- 🔵 **Dependency**: Stale downstream note about story 0008
  **Location**: Drafting Notes (External dispatch relocated)
  The note claims 0008 "does not yet capture" the relocated dispatch scope and
  is "stale against ADR-0002", but 0008 has since been updated to capture clap
  `external_subcommand` dispatch and realigned to ADR-0002's invoke+gh +
  minisign/sha256 pipeline — so the asserted follow-up coupling is already
  discharged.

- 🔵 **Dependency**: Hard dependency on 0006 recorded only as "paired"
  **Location**: Requirements (inward-direction enforcement; task-tree wiring)
  Two Requirements consume mechanisms owned by toolchain story 0006 (the
  cargo-pup lane and the component-based mise task tree), a genuine "cannot
  complete until X exists" prerequisite recorded only as "paired"/`relates_to`.
  Practical risk is nil because 0006 is `done`.

- 🔵 **Scope**: Relocated external-dispatch scope not yet absorbed by the
  receiving story (0008)
  **Location**: Drafting Notes
  The scope was correctly excised from 0007 but the Drafting Notes say 0008
  "does not yet capture" it — so it risks sitting in a gap that no work item
  owns, despite ADR-0009/0010 attributing external-dispatch confirmation to "the
  scaffold".

- 🔵 **Testability**: "Follows the subdomain-first layout" half of AC2 has no
  defined pass/fail procedure
  **Location**: Acceptance Criteria
  AC2 couples a mechanically verifiable clause (a violation trips cargo-pup)
  with a qualitative one (the workspace "follows the subdomain-first layout")
  that names no observable check, and the concrete starting set is explicitly
  deferred to implementation — so a verifier cannot confirm conformance.

- 🔵 **Testability**: "Injected at build time rather than hard-coded" in AC4
  lacks a verification procedure
  **Location**: Acceptance Criteria
  A hard-coded constant and a build-time-injected value both simply appear in
  `version` output, so AC4's "injected at build time rather than hard-coded"
  half states an implementation property with no test that would fail if it were
  violated.

#### Suggestions

- 🔵 **Clarity**: "inert" vs "sole enforcer" phrasing repeated across four
  sections risks reader fatigue, not ambiguity
  **Location**: Requirements / Acceptance Criteria / Technical Notes / Drafting
  Notes
  The inert-ban-list / cargo-pup-sole-enforcer relationship is restated
  consistently in four places; consider stating it once canonically to ease
  reading and avoid future drift between copies.

- 🔵 **Completeness**: First open question restates a settled decision rather
  than an open one
  **Location**: Open Questions
  The first Open Questions bullet (starting crate set "confirmed during
  implementation") is already asserted as settled in Summary and Requirements,
  so it reads as a confirmation note rather than a genuine unknown.

- 🔵 **Completeness**: Note about downstream item 0008's incompleteness is
  informational only
  **Location**: Drafting Notes
  The only loose end the document leaves for itself is the tracking note about
  0008; confirm the relocated scope is captured as a tracked action so it does
  not silently lapse.

- 🔵 **Scope**: Task-tree wiring is a thin adjacent concern bundled into the
  scaffold story
  **Location**: Requirements
  The `<crate>:check` wiring is a build-system integration concern adjacent to
  proving the hexagon, but is correctly co-delivered because a `:check` target
  is meaningless without the crate it targets. No action needed.

- 🔵 **Testability**: AC2's cargo-pup clause asserts an enforcement capability
  without a witnessing case
  **Location**: Acceptance Criteria
  The criteria require the clean scaffold to pass, but never demonstrate the
  enforcer actually fires; a negative witness (a deliberate inward-direction
  violation confirmed to fail `pup:check`) would prove the lane is live, not
  merely configured.

### Strengths

- ✅ Structurally complete: every expected section (Summary, Context,
  Requirements, Acceptance Criteria, Open Questions, Dependencies, Assumptions,
  Technical Notes, Drafting Notes, References) is present with substantive,
  non-placeholder content, and the frontmatter carries valid `kind`, `status`,
  `priority`, and full parent/blocks/relates_to linkage.
- ✅ High internal consistency: the "structural proof not the feature" framing,
  the cargo-pup-as-sole-enforcer claim, and the build-time-injection constraint
  are stated identically wherever they appear; every acronym and architectural
  term is anchored to a referenced ADR.
- ✅ Well-scoped and atomic: all five requirement clusters converge on one
  deliverable, the "story" kind fits, and scope is actively narrowed by
  relocating external-subcommand dispatch to 0008 with explicit in/out-of-scope
  lines.
- ✅ Strongly testable for a scaffold: AC1 names exact observable output and
  pins the triple to ADR-0002's four; AC3 makes the port boundary itself the
  thing under test against an in-memory fake; AC5 reduces "checks pass" to a
  binary exit-0 procedure.
- ✅ Dependencies well-mapped: all three downstream consumers (0008/0009/0010)
  appear in both frontmatter and prose, the spike is correctly framed as
  "informed by" now that it is done, and all referenced files exist.

### Recommended Changes

1. **Name the crate that hosts the `version` hexagon** (addresses: "Crate that
   hosts the version hexagon is never named"; "Follows the subdomain-first
   layout half of AC2 has no defined pass/fail procedure")
   State explicitly where the inbound port, core, outbound port, adapter, and
   composition root live in the `cli`+`kernel` starting set, and reconcile that
   with ADR-0010's thin-`cli` / dependency-light-`kernel` roles. Reflect the
   concrete crate/module list in AC2 so structural conformance becomes checkable
   against a named set rather than a qualitative "follows the layout".

2. **Refresh the 0008 relocation note** (addresses: "Stale downstream note about
   story 0008"; "Relocated external-dispatch scope not yet absorbed by the
   receiving story")
   Update the Drafting Note to record that the relocated external-dispatch scope
   and ADR-0002 realignment have now landed in 0008, removing the "does not yet
   capture" / "stale against ADR-0002" claims — or, if not yet landed, track the
   0008 update as an explicit follow-up so the scope has a confirmed owner.

3. **Make AC4's build-time-injection clause observable** (addresses: "Injected
   at build time rather than hard-coded in AC4 lacks a verification procedure")
   Restate as an observable consequence — e.g. the commit SHA in `version`
   output matches the build commit and the build date reflects the build run —
   or name the artefact (build script / vergen value consumed at the composition
   root) that proves injection.

4. **Tighten residual minor items** (addresses: clarity and dependency minors)
   Frame the Summary's "one crate per subdomain" as the eventual target axis;
   cross-reference the "genuinely external" build-metadata claim to its
   Assumptions/Drafting-Notes rationale; and note that this story consumes
   0006's cargo-pup lane and task tree as now-satisfied prerequisites.

---
*Review generated by /accelerator:review-work-item*

## Per-Lens Results

### Clarity

**Summary**: The work item is, on the whole, written with strong referent
discipline and high internal consistency — its cross-references to ADR-0009,
ADR-0010, ADR-0002, and the spike are accurate, and "the core", "the hexagon",
and "the inward rule" resolve consistently against the referenced ADRs. The most
material clarity gap is that the document never states which crate holds the
`version` hexagon's modules: it lists a crate set including "one crate per
subdomain" yet scopes the starting set to only `cli` plus `kernel`, leaving the
home of the inbound port, core, and outbound port ambiguous. A handful of
compressed phrasings and a dense parenthetical-heavy style add minor friction
but do not obscure meaning.

**Strengths**:
- Every acronym and architectural term is either standard within the project's
  domain or anchored to a referenced ADR, so a competent developer joining the
  team can resolve each term.
- Internal consistency across Summary, Context, Requirements, and Acceptance
  Criteria is high.
- Actors and triggers are generally explicit, so responsibility for each
  behaviour is clear rather than buried in passive voice.
- Acceptance Criteria use Given/When/Then framing with concrete observable
  outcomes.

**Findings**:
- 🟡 **Major** (high): _Crate that hosts the version hexagon is never named_ —
  Requirements. The item lists the workspace crate set and scopes the starting
  set to "just `cli` plus `kernel`", but the second Requirement places a full
  hexagon somewhere without saying which crate holds it. ADR-0010 reserves `cli`
  as a thin launcher and keeps `kernel` dependency-light, so neither obviously
  hosts a `version` domain core, yet no subdomain crate exists in the starting
  set either. An implementer cannot tell whether the core lives in `cli`,
  `kernel`, or a new crate.
- 🔵 **Minor** (medium): _"one crate per subdomain" reads as contradicting the
  single-crate starting state_ — Summary. The Summary's parenthetical may be
  read as a per-subdomain split delivered now, when the intent is the target
  shape.
- 🔵 **Minor** (medium): _"genuinely external" build metadata leans on an
  unstated justification_ — Requirements. The Requirement states the port as
  settled fact while the justification lives only in Assumptions/Drafting Notes,
  with no cross-reference.
- 🔵 **Suggestion** (low): _"inert" vs "sole enforcer" phrasing repeated across
  sections risks reader fatigue, not ambiguity_ — Requirements. The
  inert/sole-enforcer relationship is restated consistently in four places;
  state it once canonically to ease reading and avoid future drift.

### Completeness

**Summary**: This story is structurally complete and densely populated: every
expected section is present with substantive content, and the frontmatter
carries a valid `kind`, `status`, and `priority`. The kind-specific requirements
for a story are well met — the Context explains why the work is wanted and the
five Acceptance Criteria define when it is done. The only completeness
observations are minor: one open question is effectively pre-decided and the
build-metadata-injection choice is split across two sections.

**Strengths**:
- All expected sections are present and substantively populated rather than
  placeholders.
- Frontmatter integrity is sound: `kind: story`, `status: draft`, `priority:
  high`, with parent/blocks/relates_to relationships fully specified.
- Story-kind requirements met — Context motivates the work and names who it
  serves.
- Five specific Acceptance Criteria define "done", each tied to a concrete
  observable.
- Requirements are implementation-ready, decomposed into five clusters.
- References link every source document, and Drafting Notes record rationale.

**Findings**:
- 🔵 **Suggestion** (medium): _First open question restates a settled decision
  rather than an open one_ — Open Questions. The first bullet is already
  asserted as settled in Summary and Requirements, reading as a confirmation
  note rather than a genuine unknown.
- 🔵 **Suggestion** (low): _Note about downstream item 0008's incompleteness is
  informational only_ — Drafting Notes. Confirm the relocated scope is captured
  as a tracked action against 0008 so the relocation does not silently lapse; no
  change to 0007's own section content is required.

### Dependency

**Summary**: Work item 0007 is well-dependency-mapped: its upstream inputs
(spike 0002, toolchain story 0006) and its three downstream consumers (0008,
0009, 0010) are captured both in frontmatter and in the Dependencies prose, and
all referenced work items exist on disk. The one substantive gap is that the
Drafting Notes assert downstream story 0008 "does not yet capture" the relocated
external-dispatch scope and is "stale against ADR-0002" — but 0008 has since been
updated to capture exactly that scope, so the stated downstream follow-up
coupling is now itself stale. A secondary, lower-confidence concern: the
inward-direction enforcement and mise task-tree wiring depend hard on toolchain
story 0006's mechanisms, recorded only as "paired"/relates_to (acceptable
because 0006 is done).

**Strengths**:
- All three downstream consumers are named in both the frontmatter `blocks`
  array and the Dependencies prose, and each referenced file exists.
- The upstream input from spike 0002 is correctly captured as "informed by" now
  that 0002 is done, with a Drafting Note recording the transition.
- The relocation of external-subcommand dispatch into 0008 is documented in both
  stories' Drafting Notes, making the handoff traceable.
- Build metadata is correctly framed as an internal build-time outbound port,
  not an external runtime service, so no cross-team coupling is owed.

**Findings**:
- 🔵 **Minor** (high): _Stale downstream note about story 0008_ — Drafting Notes.
  The note claims 0008 "does not yet capture" the relocated scope and is "stale
  against ADR-0002", but 0008 has since been updated to capture clap
  `external_subcommand` dispatch and realigned to ADR-0002's invoke+gh +
  minisign/sha256 pipeline — so the asserted follow-up coupling is already
  discharged.
- 🔵 **Minor** (medium): _Hard dependency on 0006 recorded only as "paired"_ —
  Requirements. Two Requirements consume 0006's cargo-pup lane and component task
  tree as genuine prerequisites; recording them only as "paired" understates the
  coupling, though risk is nil because 0006 is done.

### Scope

**Summary**: Work item 0007 is a well-scoped, atomic story: every requirement
serves the single unified purpose of proving the hexagonal architecture
end-to-end with one minimal vertical slice. The kind ("story") fits the bounded,
single-team, single-increment scope, and the author has actively narrowed scope
by relocating external-subcommand dispatch to 0008. The one scope concern is a
cross-item coherence gap: the scope relocated out of this story is acknowledged
as not yet captured in the receiving story.

**Strengths**:
- All five requirement clusters converge on one deliverable; none could be
  delivered as standalone value.
- Scope boundaries are explicitly stated across Summary, Assumptions, and
  Drafting Notes.
- The "story" kind fits the scope, consistent with the source spike and
  ADR-0009/0010 which both name 0007 as "the scaffold".
- Summary, Requirements, and Acceptance Criteria describe the same scope
  consistently.

**Findings**:
- 🔵 **Minor** (medium): _Relocated external-dispatch scope not yet absorbed by
  the receiving story (0008)_ — Drafting Notes. The scope was correctly excised
  from 0007 but 0008 "does not yet capture them; it needs a follow-up update" —
  so it currently sits in a gap between the two stories. Track the 0008 update as
  an explicit follow-up so the relocated dispatch scope has a confirmed owner
  before 0007 closes.
- 🔵 **Suggestion** (low): _Task-tree wiring is a thin adjacent concern bundled
  into the scaffold story_ — Requirements. The `<crate>:check` wiring is a
  build-system integration concern, but is correctly co-delivered because a
  `:check` target is meaningless without the crate it targets. No action needed.

### Testability

**Summary**: For a structural-scaffold story, the Acceptance Criteria are
unusually testable: most criteria name concrete observable outcomes (printed
fields, exit codes, an in-memory-fake test, a cargo-pup trip) and the story
embeds its own verification framing (red-green, ports exercised against a fake).
The main gaps are two criteria that bundle a verifiable mechanism with a softer
qualitative claim — "follows the spike's subdomain-first layout" and "injected at
build time rather than hard-coded" — where the qualitative half lacks a defined
pass/fail procedure.

**Strengths**:
- AC1 specifies the exact observable output of `luminosity version` and pins the
  triple to one of ADR-0002's four named triples, giving a concrete oracle.
- AC3 is strongly testable: it names the verification artefact (a test
  exercising the core against an in-memory fake of the outbound port), making the
  port boundary itself the thing under test.
- AC5 reduces "the checks pass" to a definitive procedure — `mise run check` and
  the bare `mise run` default both exit 0.
- The story repeatedly binds criteria to mechanical enforcers (cargo-pup trips on
  an inward-direction violation).

**Findings**:
- 🔵 **Minor** (medium): _"Follows the subdomain-first layout" half of AC2 has no
  defined pass/fail procedure_ — Acceptance Criteria. The layout clause names no
  observable check and the concrete starting set is explicitly deferred to
  implementation, so a verifier cannot confirm conformance. Split AC2 and make
  the layout one concrete (named crates/modules).
- 🔵 **Minor** (medium): _"Injected at build time rather than hard-coded" in AC4
  lacks a verification procedure_ — Acceptance Criteria. A hard-coded constant
  and a build-time-injected value both simply appear in output; restate as an
  observable consequence (SHA matches build commit) or name the proving artefact.
- 🔵 **Suggestion** (low): _AC2's cargo-pup clause asserts an enforcement
  capability without a witnessing case_ — Acceptance Criteria. Add a negative
  witness (a deliberate inward-direction violation confirmed to fail `pup:check`)
  to prove the enforcer is live, not merely configured.

## Re-Review (Pass 2) — 2026-06-28

**Verdict:** COMMENT

The major finding and almost all minors/suggestions from Pass 1 are resolved.
The remaining items are fresh, low-severity polish plus one newly-surfaced
dependency asymmetry; none block implementation. Re-ran all five lenses.

### Previously Identified Issues

- 🟡 **Clarity**: Crate that hosts the version hexagon is never named —
  **Resolved**. Workspace-layout and hexagon Requirements now state the start is
  exactly `cli` + `kernel` and the hexagon's concerns live as modules within
  `cli` (with the composition root at the `cli` entry point); no lens re-flagged
  the home of the hexagon as ambiguous.
- 🔵 **Clarity**: "one crate per subdomain" reads as contradicting the
  single-crate state — **Partially resolved**. Context now frames the
  per-subdomain split as the *eventual* shape; clarity downgraded the residual to
  a suggestion that the Summary's "subdomain-first" label still precedes its
  scope qualifier.
- 🔵 **Clarity**: "genuinely external" build metadata leans on an unstated
  justification — **Resolved**. The Requirement now cross-references the
  Assumptions/Drafting-Notes rationale; not re-flagged.
- 🔵 **Clarity**: inert/sole-enforcer phrasing repeated across sections —
  **Resolved** (not re-flagged).
- 🔵 **Completeness**: first open question restates a settled decision —
  **Resolved**. The pre-decided bullet was removed and replaced with a
  genuinely-deferred one (internal module naming).
- 🔵 **Completeness**: note about 0008's incompleteness is informational —
  **Resolved**. The relocation is now confirmed as landed in 0008.
- 🔵 **Dependency**: stale downstream note about 0008 — **Resolved**. Verified
  bidirectionally: 0008 now owns the dispatch scope and is ADR-0002-aligned; the
  Drafting Note records this.
- 🔵 **Dependency**: hard dependency on 0006 recorded only as "paired" —
  **Resolved**. 0006 is now recorded as a true (now-satisfied) prerequisite with
  its specific couplings named.
- 🔵 **Scope**: relocated external-dispatch scope not absorbed by 0008 —
  **Resolved**. Confirmed owner; scope lens raised no coherence gap this pass.
- 🔵 **Scope**: task-tree wiring bundled — **Still present** (suggestion, no
  action needed — correctly co-delivered).
- 🔵 **Testability**: AC2 "follows the layout" has no pass/fail procedure —
  **Resolved**. AC2 now enumerates the exact crate set and the five hexagon
  modules (a residual "distinct modules" subjectivity is noted below).
- 🔵 **Testability**: AC4 "injected at build time" lacks a procedure —
  **Resolved**. AC now ties injection to observable consequences (SHA equals the
  build commit; build date an RFC 3339 timestamp within the build window).
- 🔵 **Testability**: cargo-pup clause asserts enforcement without a witness —
  **Resolved**. AC3 now requires a deliberate violation to be rejected and its
  removal to restore a green run.

### New Issues Introduced

- 🟡 **Testability**: AC5 build-date "reflects the build run" had no tolerance
  (flagged major, but the agent itself notes the SHA check alone substantiates
  injection, so effectively minor) — **Fixed during this pass**: AC5 now requires
  the date to parse as an RFC 3339 timestamp within the build's wall-clock window.
- 🔵 **Testability**: AC3's deliberately-introduced violation had no specified
  post-verification disposition — **Fixed during this pass**: AC3 now requires
  removal of the violation to restore a green cargo-pup run.
- 🔵 **Clarity**: AC5's "named artefact proving injection" parenthetical was hard
  to parse — **Fixed during this pass**: rephrased so the referent is explicit.
- 🔵 **Dependency**: the `blocks: 0010` claim is not reciprocated by 0010 and is
  only transitive (via 0009) — **Resolved**. Dependencies now splits Blocks into
  directly (0008, 0009) and transitively (0010 via 0009), and the frontmatter
  `blocks` array drops the direct 0010 edge to match.
- 🔵 **Testability**: AC2 "distinct modules" remains somewhat subjective given
  internal module naming is deferred — **Open** (minor). The cargo-pup rule (AC3)
  and fake-port test (AC4) are the real structural proofs.
- 🔵 **Testability**: "no logic in the command layer" Requirement has no
  verifiable check — **Open** (minor, pre-existing). Add a proxy check or mark as
  a design guideline.
- 🔵 **Testability**: AC1's output assertion granularity is undefined — **Open**
  (suggestion). Specify presence-vs-format assertion shape.
- 🔵 **Clarity**: "vergen-style" / "SHA" used without gloss — **Open**
  (suggestion).
- 🔵 **Completeness**: `kernel`'s minimum scaffold content is unstated —
  **Resolved**. The Workspace layout Requirement now states `kernel` is
  present-but-minimal at this stage — a starter error type (home of the
  cross-cutting error taxonomy), not an empty placeholder.
- 🔵 **Completeness**: core's own unit-test coverage not mirrored as an AC —
  **Open** (suggestion).
- 🔵 **Dependency**: cargo-pup pinned-nightly provisioning is an implicit
  prerequisite — **Open** (suggestion).

### Assessment

The work item is ready for implementation. The Pass-1 major and its supporting
themes are fully resolved, and the three issues that my Pass-1 edits introduced
(AC5 tolerance, AC3 disposition, AC5 parenthetical) were corrected in this pass.
The two strongest remaining items — the `blocks: 0010` asymmetry and `kernel`'s
unstated scaffold content — were also resolved after this pass. What remains is
suggestion-level polish only (vergen/SHA glosses, AC1 assertion granularity,
"distinct modules" subjectivity, the "no logic in command layer" check, core
unit-test coverage as an AC, cargo-pup nightly provisioning), none of which
change the deliverable's shape. Verdict holds at COMMENT.

## Re-Review (Pass 3) — 2026-06-28

**Verdict:** APPROVE

After the two strongest remaining items were resolved (the `blocks: 0010`
asymmetry and `kernel`'s scaffold content), the reviewer accepted the work item
as ready for implementation. All Pass-1 findings and the Pass-2 regressions are
resolved; only suggestion-level polish remains, none of which blocks
implementation. The verdict is upgraded from COMMENT to APPROVE.
