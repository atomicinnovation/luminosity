---
type: work-item-review
id: "0009-multi-level-configuration-system-review-1"
title: "Work Item Review: Multi-Level Configuration System — CLI Command + Thin configure Skill"
date: "2026-07-04T22:10:57+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0009"
work_item_id: "0009"
reviewer: Toby Clemson
verdict: COMMENT
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 2
tags: []
last_updated: "2026-07-05T12:42:01+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Multi-Level Configuration System — CLI Command + Thin configure Skill

**Verdict:** REVISE

This is a strong, well-bounded story — scope is consistent across Summary,
Requirements, and Acceptance Criteria; the skills-vs-CLI division is
unambiguous; and the criteria are unusually mechanical (concrete commands,
exit codes, `cargo tree`, `git check-ignore`). Two major issues push it to
REVISE: the hard upstream blocker (0007) lives only in prose and is absent
from the machine-readable frontmatter, and the acceptance criteria cover only
present-key happy paths with no error/edge behaviour pinned. Neither is
structural — both are addressable with targeted edits.

### Cross-Cutting Themes

- **Prose captures couplings the structured record doesn't** (flagged by:
  dependency) — the hard blocker 0007 and the directional "relies on" 0006 are
  reasoned about clearly in the Dependencies prose but the frontmatter either
  omits them (0007) or flattens their direction (0006), so any tool reading
  frontmatter sees a weaker dependency graph than the author intended.
- **Verification rigour tails off from happy path to edges and inspection**
  (flagged by: testability) — the functional happy-path criteria are
  exemplary, but error/edge behaviour is unspecified, and a few criteria fall
  back to human inspection (AC10) or ambiguous either/or checks (AC9).
- **Load-bearing references aren't self-resolvable** (flagged by: clarity) —
  scope justifications lean on "A2" and "the accelerator" without a first-use
  anchor, so a reader can't verify them from within the document.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Dependency**: Hard upstream blocker 0007 captured only in prose, absent
  from frontmatter
  **Location**: Frontmatter: blocks / Dependencies
  The Dependencies section states this story is "Blocked by: the scaffold story
  (0007)" — a hard prerequisite — yet 0007 appears nowhere in the frontmatter,
  while the softer "relies on" 0006 is recorded in `relates_to`. Dependency
  tracking that reads frontmatter won't see that 0009 cannot start until 0007
  lands.

- 🟡 **Testability**: No criterion specifies error / edge-case behaviour for
  get and set
  **Location**: Acceptance Criteria
  Every criterion covers present-key happy paths. There is no criterion
  defining the observable outcome for a key absent from both levels, an invalid
  `--level` value, or malformed YAML frontmatter — no expected exit code,
  output, or error text is stated, so an implementer could ship any behaviour
  and still pass.

#### Minor

- 🔵 **Clarity**: Cryptic cross-reference label "A2" is cited but never
  expanded
  **Location**: Open Questions / Assumptions / Drafting Notes
  "A2" (and "decision 1" / "decision 3") point to items in an external source
  (0001) that the document never identifies. "decision 1/3" are glossed inline,
  but "A2" — a load-bearing scope justification ("out of scope (A2)") — is only
  ever cited.

- 🔵 **Dependency**: Relied-on toolchain story 0006 recorded only as a
  `relates_to`, not a directional dependency
  **Location**: Frontmatter: relates_to / Dependencies
  The prose classifies 0006 as "Relies on" (directional), but the frontmatter
  records it in the undirected `relates_to` list alongside peer references, so
  a tool reconstructing the graph can't distinguish an enabling prerequisite
  from an incidental relation.

- 🔵 **Testability**: Dotted key semantics (`core.example`) undefined,
  ambiguous for fixture authoring
  **Location**: Acceptance Criteria
  No criterion states whether the dot denotes a nested YAML path (`core:\n
  example:`) or a literal flat key. A verifier constructing the fixture cannot
  know which structure produces a passing read.

- 🔵 **Testability**: AC9 "fails the build and/or is caught by cargo-deny"
  leaves the definitive check ambiguous
  **Location**: Acceptance Criteria
  The "and/or" does not tell a verifier which check is authoritative, so a run
  where one mechanism fires but not the other cannot be definitively judged —
  the guardrail could silently regress to a single active mechanism.

- 🔵 **Testability**: Skill round-trip (AC6) lacks a defined output-capture
  procedure
  **Location**: Acceptance Criteria
  AC6 compares a value read "via the `configure` skill" against `luminosity
  config get`, but skills operate through the conversation, not stdout, and no
  procedure defines how the skill result is captured and compared.

#### Suggestions

- 🔵 **Testability**: AC10 verifies an absence by manual inspection rather than
  an executable check
  **Location**: Acceptance Criteria
  Proving the skill "performs no YAML parsing… verifiable by inspecting the
  skill body" is judgemental; a positive, grep-able reframing ("every config
  read/write is a call to `luminosity config get`/`set`") would be checkable.

- 🔵 **Scope**: Story carries several architectural "firsts" alongside feature
  delivery
  **Location**: Context
  The feature surface is deliberately minimal, but the architectural scaffolding
  (new `config` + `config-adapters` crates, composition-root wiring, first
  cross-crate ban-list enforcement) is the heavier part. Likely correct to keep
  together per ADR-0010, but worth confirming it fits one increment and sizing
  it honestly rather than framing purely as "minimal".

- 🔵 **Scope**: Confirm the thin skill belongs in the same unit as the
  crate-level implementation
  **Location**: Requirements
  The deliverable spans the Rust crate split and the thin skill + `.gitignore`
  wiring. Keeping them together is defensible — proving the division
  end-to-end needs both — but flagged so the coupling is a conscious choice.

- 🔵 **Completeness**: Open Questions section holds a resolved scope decision,
  not an open question
  **Location**: Open Questions
  The sole entry states the config schema is out of scope — a settled decision
  duplicated in Assumptions/Context — so the section is effectively empty of
  genuine open questions.

- 🔵 **Clarity**: "the accelerator" used as a definite reference without a
  first-use anchor
  **Location**: Context
  Every "mirroring the accelerator" rationale leans on a referent never
  introduced as a specific named product on first mention.

- 🔵 **Clarity**: Composition-root phrasing differs between Requirements
  (singular) and Technical Notes (per-binary)
  **Location**: Requirements
  Requirements say "wired at the composition root" (singular); Technical Notes
  say "each sub-binary wires its own `config-adapters` at its composition
  root". Reconcilable, but the singular phrasing could read as one global point.

### Strengths

- ✅ Explicitly disambiguates the overloaded word "core" — both Requirements
  and Technical Notes state "core" here means the `config` crate.
- ✅ Names the actor for every action: the CLI parses YAML and resolves; the
  skill only orchestrates — the division of responsibility is unambiguous
  throughout.
- ✅ All standard sections present and densely populated; frontmatter complete
  and correct (`kind: story`, rich relationship fields, no placeholders).
- ✅ Ten acceptance criteria are concrete Given/When/Then scenarios with named
  example values, exact commands, and exit codes.
- ✅ Architectural criteria are mechanically verifiable: `cargo tree -p config`
  for the dependency closure, `git check-ignore` for gitignore, named
  core-crate unit tests for precedence.
- ✅ AC2 explicitly distinguishes fall-through from override, and AC5 verifies
  a full set/get round-trip — closing common verification loopholes.
- ✅ Scope is explicitly bounded (one value, two levels) with fuller parity
  deferred to epic 0011; Drafting Notes transparently flag the team-as-default
  decision for reviewer reconsideration.
- ✅ Dependencies prose is thorough — upstream blocker, relied-on toolchain,
  downstream consumers, and governing ADRs all reasoned through.

### Recommended Changes

1. **Record the hard blocker 0007 in the frontmatter** (addresses: "Hard
   upstream blocker 0007 captured only in prose"). Add `work-item:0007` to a
   `blocked_by` field if the schema supports one, or at minimum to
   `relates_to`, so the prerequisite lives in the same structured field family
   as the `blocks` list it already carries.

2. **Add error/edge acceptance criteria for get and set** (addresses: "No
   criterion specifies error / edge-case behaviour"). Pin at least the
   not-found path (e.g. "Given `core.example` set in neither level, `config get
   core.example` exits non-zero and prints nothing to stdout") and an invalid
   `--level` value, even while the fuller schema stays out of scope.

3. **Define the dotted-key mapping and show the fixture** (addresses: "Dotted
   key semantics undefined"). State in AC1 or Requirements whether `core.example`
   is a nested YAML path or a flat key, and show the literal frontmatter block
   a test writes into `.luminosity/config.md`.

4. **Make AC9 name a single authoritative check** (addresses: "AC9 and/or
   ambiguous"). Replace "fails the build and/or is caught by cargo-deny" with a
   definitive check, e.g. "`cargo deny check` fails when serde is added to
   `config`'s manifest", keeping the build failure as a secondary note.

5. **Give AC6 a defined comparison surface** (addresses: "Skill round-trip
   lacks output-capture procedure"). State the observable, e.g. the skill emits
   the CLI's stdout verbatim, so the assertion is "skill output == `config get`
   stdout for the same key".

6. **Reframe AC10 as a positive, checkable assertion** (addresses: "AC10
   verifies an absence by manual inspection"). E.g. "every config read/write in
   the skill body is a call to `luminosity config get`/`set` with no other
   command reading `.luminosity/config*.md`".

7. **Anchor load-bearing references** (addresses: clarity "A2" and "the
   accelerator" findings). Expand "A2" on first use (or add a one-line legend
   mapping it to 0001) and name "the accelerator" once as a specific product.

8. **Optionally move 0006 to a directional dependency field, tidy Open
   Questions, and align composition-root phrasing** (addresses: remaining minor
   findings) — low-effort polish.

## Per-Lens Results

### Clarity

**Summary**: The work item is generally clear and internally consistent: scope
matches across Summary, Context, Requirements, and Acceptance Criteria; actors
are explicitly named (the CLI reads/writes, the skill orchestrates); and it
proactively disambiguates the overloaded term "core" and the
cargo-deny-vs-cargo-pup enforcement split. The main clarity gaps are cryptic
cross-reference labels ("A2", "decision 1", "decision 3") whose source is not
identifiable from within the document and a few pervasive domain terms ("the
accelerator") used without a first-use anchor.

**Strengths**:
- Explicitly disambiguates the overloaded word "core" — Technical Notes and
  Requirements both state that "core" in this story means the `config` crate.
- Names the actor for every action: the CLI parses YAML and executes
  resolution, the skill only orchestrates by invoking the CLI.
- Resolves a potential internal contradiction directly: the Drafting Notes
  record the sharpening from "first multi-crate hexagon" to "first cross-crate
  hexagon," and Technical Notes clarify cargo-deny (not cargo-pup) enforces the
  cross-crate direction here.
- Scope is consistent across sections — two levels, personal-over-team
  precedence, and minimal single-key proof appear identically throughout.

**Findings**:
- 🔵 **minor** (confidence: medium) — _Open Questions / Assumptions / Drafting
  Notes_: The reference labels "A2" and "decision 1" / "decision 3" point to an
  external source but the document never states which document defines them.
  "decision 1/3" are glossed inline; "A2" is only ever cited, never expanded, so
  a load-bearing scope justification ("out of scope (A2)") rests on an
  unresolvable reference. Suggestion: expand "A2" on first use or add a legend.
- 🔵 **suggestion** (confidence: low) — _Context_: "the accelerator" is used as
  a definite reference throughout but never introduced as a specific named
  product on first use, weakening every "mirroring the accelerator" rationale.
  Suggestion: name the referent once on first mention or link to it.
- 🔵 **suggestion** (confidence: low) — _Requirements_: Requirements say
  concerns are "wired at the composition root" (singular) while Technical Notes
  say "each sub-binary wires its own `config-adapters` at its composition root"
  (per-binary). Reconcilable, but the singular phrasing could be read as a
  single global wiring point. Suggestion: align the Requirements phrasing.

### Completeness

**Summary**: This story is exceptionally complete: every expected section is
present and substantively populated, the frontmatter is fully specified with a
recognised `kind`, and the ten acceptance criteria are concrete and enumerable.
The Context clearly motivates the work (proof-of-architecture for the
skills-vs-CLI division), and kind-specific story content is fully present. Only
marginal observations remain, none of which would block an implementer.

**Strengths**:
- All standard sections present and densely populated.
- Frontmatter complete and correct — `kind: story`, `status: draft`,
  `priority: high`, plus rich relationship fields — with no placeholders.
- Ten specific scenario-driven acceptance criteria covering resolution,
  fall-through, level-scoped reads, set defaults, round-trip, skill parity,
  gitignore, and dependency-closure enforcement.
- Context and Assumptions explicitly bound scope and record motivating ADRs
  (ADR-0003, ADR-0009, ADR-0010).
- Drafting Notes transparently document the item's evolution and flag an author
  decision for reviewer reconsideration.

**Findings**:
- 🔵 **suggestion** (confidence: low) — _Open Questions_: The sole entry states
  the config key namespace/schema is out of scope — a settled scope decision,
  not an unresolved question, and duplicated as an Assumption/Context note.
  Suggestion: move it to Assumptions/Context and mark Open Questions as "None",
  or leave as-is since the boundary is useful where it sits.

### Dependency

**Summary**: The prose Dependencies section is thorough and well-reasoned: it
names the upstream blocker (0007 scaffold), the relied-on toolchain story
(0006), the downstream consumers (0010, 0011), and the parent epic (0001), and
the body carefully explains each coupling. The one real gap is a mismatch
between the prose couplings and the machine-readable frontmatter — the hard
upstream blocker 0007 is captured only in prose and is absent from the
frontmatter entirely, while its softer sibling 0006 is present in relates_to.
No external-system or cross-team couplings are implied that go uncaptured.

**Strengths**:
- Downstream consumers captured consistently in both prose and frontmatter
  (0010, 0011 in `blocks`).
- The relied-on toolchain coupling (0006) is explained precisely — the
  cargo-deny ban-list this story activates already exists as inert entries.
- Governing decisions (ADR-0003, ADR-0009, ADR-0010) all captured in
  `relates_to`, and the follow-on 0012 is explicitly named and linked.

**Findings**:
- 🟡 **major** (confidence: high) — _Frontmatter: blocks / Dependencies_: The
  Dependencies section states the story is "Blocked by: the scaffold story
  (0007)" — a hard prerequisite — yet 0007 appears nowhere in the frontmatter,
  while the softer "relies on" 0006 is recorded in `relates_to`, creating an
  asymmetry where the stronger coupling is omitted from the structured record.
  Any dependency tracking reading frontmatter won't see that 0009 cannot start
  until 0007 lands. Suggestion: add `work-item:0007` to a `blocked_by` field or
  at minimum to `relates_to`.
- 🔵 **minor** (confidence: medium) — _Frontmatter: relates_to /
  Dependencies_: The prose classifies 0006 as "Relies on" (directional) but the
  frontmatter records it only in the undirected `relates_to` list, flattening
  the enabling direction. Practical risk is low only because 0006 is done.
  Suggestion: move 0006 into a directional depends-on/relies-on field if the
  schema offers one.

### Scope

**Summary**: This is a coherent, well-bounded story: every requirement serves
the single unified purpose of proving the skills-vs-CLI division through a
minimal two-level configuration feature, and the Summary, Requirements, and
Acceptance Criteria describe the same scope consistently. The domain scope is
deliberately and explicitly narrowed (one resolvable value across two levels,
with fuller parity pushed to epic 0011), which keeps it atomic. The main scope
tension is breadth of concern-types rather than concern-count — the story
delivers a feature and stands up the workspace's first cross-crate hexagon with
its architecture enforcement — but these are genuinely coupled by ADR-0010 and
not independently deliverable, so decomposition is not warranted.

**Strengths**:
- Scope explicitly bounded with clear in/out-of-scope statements; fuller parity
  deferred to epic 0011.
- Summary, Requirements, and Acceptance Criteria internally consistent — no
  drift between sections.
- Single-team, single-repo unit of work with cleanly sequenced dependencies
  (blocked by 0007, relies on 0006, blocks 0010/0011).

**Findings**:
- 🔵 **suggestion** (confidence: medium) — _Context_: Beyond the config
  feature, the story is explicitly loaded with landmark architectural
  significance ("proof-of-architecture for the whole approach"; "first
  cross-crate hexagon" activating the cargo-deny ban-list). The architectural
  scaffolding is the heavier part despite the minimal feature surface, which
  concentrates delivery risk. Likely correct to keep together per ADR-0010, but
  confirm it fits one increment and consider explicit sizing acknowledgement.
- 🔵 **suggestion** (confidence: low) — _Requirements_: The deliverable spans
  the deterministic Rust crate split and the thin `configure` skill +
  `.gitignore` wiring — layers that are often separable. Keeping them together
  is defensible (proving the division end-to-end needs both) and probably
  correct; flagged only so the coupling is a conscious choice.

### Testability

**Summary**: The Acceptance Criteria are unusually strong for testability: most
are framed as concrete Given/When/Then pairs with named example values, explicit
commands, exit codes, and mechanical verifiers (`git check-ignore`, `cargo
tree`, unit-test coverage). The main gaps are the absence of any criterion
covering error/edge behaviour (missing key, invalid `--level`, malformed
frontmatter), unspecified semantics for the dotted key that a tester must assume
when authoring fixtures, and a few criteria whose verification is
inspection-based or offers an ambiguous either/or check.

**Strengths**:
- Functional criteria are observable input-output pairs with concrete example
  values and exact commands.
- AC2 explicitly distinguishes fall-through from override, closing a common
  verification loophole.
- Architectural criteria are mechanically verifiable rather than aspirational
  (`cargo tree -p config`, `git check-ignore`, named core-crate unit tests).
- The set/get round-trip criterion (AC5) verifies persistence end-to-end.

**Findings**:
- 🟡 **major** (confidence: medium) — _Acceptance Criteria_: Every criterion
  covers only present-key happy paths. No criterion defines the outcome for a
  key absent from both levels, an invalid `--level` value, or malformed YAML
  frontmatter — no exit code, output, or error text is stated, so an
  implementer could ship any behaviour and pass. Suggestion: add a not-found
  criterion and an invalid-`--level` criterion.
- 🔵 **minor** (confidence: medium) — _Acceptance Criteria_: No criterion
  states whether `core.example`'s dot denotes a nested YAML path or a literal
  flat key, so a verifier cannot know which fixture structure produces a passing
  read. Suggestion: state the mapping and show the exact fixture content.
- 🔵 **minor** (confidence: medium) — _Acceptance Criteria_: AC9's "fails the
  build and/or is caught by cargo-deny" does not tell a verifier which check is
  authoritative, so a partial regression (one mechanism firing) still reads as
  satisfied. Suggestion: specify the definitive check (`cargo deny check`
  fails).
- 🔵 **minor** (confidence: low) — _Acceptance Criteria_: AC6 compares a value
  read "via the `configure` skill" against `luminosity config get`, but skills
  operate through the conversation, not stdout, and no capture/compare procedure
  is given. Suggestion: state the observable used (skill emits CLI stdout
  verbatim).
- 🔵 **suggestion** (confidence: medium) — _Acceptance Criteria_: AC10 proves
  an absence of behaviour by human inspection, which is judgemental. Suggestion:
  reframe positively toward a checkable/grep-able assertion.

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-05

**Verdict:** COMMENT

Both original majors are resolved. The re-review pass (all five lenses re-run
against the edited item) found the work item acceptable, with one newly
introduced major — a direct byproduct of the round-1 requirement edit — plus a
pre-existing frontmatter inconsistency and some polish. All of these were
addressed in a follow-up edit round after the pass, leaving no blocking issues.

### Previously Identified Issues

- 🟡 **Dependency**: Hard upstream blocker 0007 absent from frontmatter —
  **Resolved**. `blocked_by: ["work-item:0007", "work-item:0006"]` added; the
  dependency lens now lists this as a strength.
- 🟡 **Testability**: No error/edge acceptance criteria — **Resolved**.
  Not-found and invalid-`--level` criteria added; the testability lens now cites
  the negative tests as strengths.
- 🔵 **Dependency**: 0006 recorded only as undirected `relates_to` —
  **Resolved**. Moved to `blocked_by`; blocker-vs-relies-on nuance kept in prose.
- 🔵 **Testability**: Dotted-key semantics undefined — **Resolved**. Pinned to
  nested paths in Requirements and AC1.
- 🔵 **Testability**: AC9 "and/or" ambiguous — **Resolved**. `cargo deny check`
  is now the authoritative check.
- 🔵 **Testability**: AC6 lacked a comparison surface — **Partially resolved,
  then resolved**. Round-1 added the "skill output == `config get` stdout" check;
  the re-review flagged that capturing skill output needs an eval harness not in
  this story, so a follow-up edit scopes the in-story proof to the grep-verifiable
  thin-skill criterion and defers behavioural equivalence to 0010.
- 🔵 **Clarity**: "A2" unexpanded — **Resolved**. Anchored to work item 0001.
- 🔵 **Clarity**: "the accelerator" unanchored — **Resolved**. Named on first
  use with its `../accelerator` path.
- 🔵 **Clarity**: composition-root singular/plural — **Resolved**. Aligned to
  "each sub-binary's composition root".
- 🔵 **Testability**: AC10 verified an absence by inspection — **Resolved**.
  Reframed as a positive grep-verifiable assertion.
- 🔵 **Completeness**: Open Questions held a resolved decision — **Resolved,
  then refined**. Round-1 set it to "None"; the re-review noted the flagged
  team-vs-personal `set`-default decision belonged there, so a follow-up edit
  surfaces it as a genuine open question.
- 🔵 **Scope** (x2): architectural "firsts" bundled with feature — **Confirmed
  intentional** (per ADR-0010 the crate has no standalone value); the re-review
  agreed no split is warranted.

### New Issues Introduced (all addressed after the pass)

- 🟡 **Testability**: Empty-vs-unset distinction stated as a requirement but only
  the unset side verified — **Fixed**. Added an AC pinning "present but empty →
  exit 0, empty stdout" as distinct from the not-found path. (This major was a
  direct consequence of the round-1 requirement wording.)
- 🔵 **Dependency**: 0011 classified under both `blocks` and `relates_to` —
  **Fixed**. Removed from `relates_to` (it is downstream / blocked by this story).
- 🔵 **Scope**: Summary omitted the cross-crate hexagon dimension — **Fixed**.
  Summary now names the architectural-proof dimension.
- 🔵 **Testability**: invalid-`--level` AC asserted the unobservable "no config
  file is read" — **Fixed**. Reframed to "no config file is created or modified".
- 🔵 **Testability**: success exit code / stdout format unspecified — **Fixed**.
  Added the fixed output contract (get: value + single trailing newline, exit 0;
  set: exit 0).
- 🔵 **Completeness**: flagged `set`-default decision not in Open Questions —
  **Fixed** (see above).
- 🔵 **Clarity**: "eval target" and "userspace" unglossed — **Fixed**. "eval"
  glossed on first use; "userspace" replaced with "project-level".
- 🔵 **Dependency**: accelerator not recorded as a coupling in Dependencies —
  **Fixed**. Added as an explicit reference-input coupling.
- 🔵 **Dependency**: 0012 reads as downstream but only `relates_to` —
  **Noted, left as related**. Clarifying note added; not promoted to `blocks`
  because per-subdomain enforcement is not clearly hard-gated by this story.

### Assessment

The work item is ready for planning. Both blocking (REVISE-triggering) majors
from the initial review are resolved, the one major surfaced by the re-review
(empty-vs-unset) has been fixed with a dedicated acceptance criterion, and the
frontmatter dependency graph is now internally consistent. The remaining items
are polish already applied; no further review pass is required before
`/create-plan`.
