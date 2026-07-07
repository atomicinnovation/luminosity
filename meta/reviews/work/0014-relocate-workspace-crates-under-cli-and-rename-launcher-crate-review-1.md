---
type: work-item-review
id: "0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate-review-1"
title: "Work Item Review: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate"
date: "2026-07-02T01:20:15+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0014"
work_item_id: "0014"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 3
tags: []
last_updated: "2026-07-02T01:30:22+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: Relocate Workspace Crates Under cli/ and Rename the Launcher Crate

**Verdict:** REVISE

Work item 0014 is a precise, well-scoped, and unusually thorough refactor: every
expected section is populated, scope aligns tightly across Summary, Requirements,
and Acceptance Criteria, and the package-vs-directory distinction (`luminosity`
stays, directory becomes `launcher`) is stated repeatedly and unambiguously. The
verdict is REVISE only because three independent lenses each surfaced a major
issue — the tri-referent overloading of "launcher", the mislabelling of the 0007
crate scaffold as "recommended sequencing only" rather than a hard prerequisite,
and a CI required-check acceptance criterion that bundles an unverifiable manual
step into a pass/fail condition. None is a structural flaw; all three are
tractable wording/framing fixes.

### Cross-Cutting Themes

- **CI change is the weakest-specified area of an otherwise sharp work item**
  (flagged by: completeness, clarity, testability, scope) — The post-move build
  output `subject-path` is never stated (deferred to implementation), the
  required-check re-registration is emphasised as a no-local-signal step yet its
  acceptance criterion gives the least actionable guidance and mixes an
  unobservable manual action into a pass/fail check, and scope notes the CI/task
  rename is a separable, merge-blocking addition to an otherwise low-risk move.
  The CI slice is where the most attention is warranted.
- **A concrete expected value the reader most wants is left to inference**
  (flagged by: completeness, clarity) — The new attestation `subject-path`
  (likely `cli/launcher/bin/luminosity-*`) is referenced as "the new build-output
  path" but never written down, deferred entirely to implementation.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Clarity**: "launcher" overloaded across three distinct referents
  **Location**: Context / Drafting Notes
  The term names (1) the renamed crate directory `cli/launcher/`, (2) the bash
  bootstrap 0008 also calls the launcher, and (3) the 0008 fetch→verify→cache→exec
  resolution pipeline. The overload is acknowledged in Drafting Notes but not
  resolved, so "the launcher" points at different things across 0014 and 0008.

- 🟡 **Dependency**: 0007 prerequisite framed as "blocked by: none"
  **Location**: Dependencies
  Summary and Context state the relocated crates were "scaffolded by 0007", and
  0007 is status `ready` (not done). The work is impossible until those crates
  exist, so 0007 is a hard upstream blocker, not merely "recommended sequencing".

- 🟡 **Testability**: CI required-check criterion mixes an unobservable manual step into pass/fail
  **Location**: Acceptance Criteria
  The final criterion bundles a locally observable outcome (jobs run under new
  names) with a repo-settings action the Technical Notes themselves say "has no
  local signal". A code reviewer cannot conclusively pass or fail it, and "the PR
  is mergeable" can be true for unrelated reasons.

#### Minor

- 🔵 **Clarity**: kernel path constant left unnamed
  **Location**: Requirements: Build tasks
  The launcher path change is tied to a named constant (`CLI_DIR`→`LAUNCHER_DIR`)
  but "the kernel directory" is described with no constant named, leaving unclear
  whether a kernel path constant exists and whether it too should be renamed.

- 🔵 **Completeness**: build-output binary path unresolved across three sections
  **Location**: Requirements: CI / Assumptions
  The new `subject-path` target is never stated — Requirements says update it "to
  the new build-output path", Assumptions defers it to implementation, and no
  criterion pins it. A wrong value passes local checks yet breaks attestation
  silently.

- 🔵 **Completeness**: CI required-check acceptance criterion lacks the detail the body emphasises
  **Location**: Acceptance Criteria
  The step the item repeatedly flags as easiest to forget has the criterion that
  gives least guidance — it neither references the `CONTRIBUTING.md` runbook nor
  names the repo-settings location where it is verified.

- 🔵 **Dependency**: downstream ordering link to 0008/0012 not recorded
  **Location**: Dependencies
  The stated rationale is to land before 0008/0012 so their crates are born under
  `cli/`, yet "Blocks: none" records no forward link and neither 0008 nor 0012's
  Dependencies mention 0014, so the ordering benefit can be silently lost.

- 🔵 **Testability**: "each is unchanged" is unbounded
  **Location**: Acceptance Criteria
  The package-preservation criterion says `pup.ron`, `plugin.json`,
  `checksums.json`, and the binary name are "unchanged" with no baseline;
  `checksums.json` legitimately changes on rebuild, so the invariant is ambiguous.

- 🔵 **Testability**: several concrete requirements lack a matching verifiable criterion
  **Location**: Requirements
  The doc/comment edits (`CLAUDE.md`, `deny.toml`) and the CI `subject-path`/
  target edits have no criterion that fails if forgotten — a green build does not
  exercise the attestation upload or `CLAUDE.md`.

#### Suggestions

- 🔵 **Clarity**: build-output binary path referred to inconsistently
  **Location**: Assumptions / Requirements: CI
  The reader must infer the post-move value (likely `cli/launcher/bin/luminosity-*`);
  state the expected value even if final confirmation is deferred.

- 🔵 **Scope**: CI/task rename is a separable, merge-blocking addition
  **Location**: Requirements: CI / Drafting Notes
  The rename adds a manual, no-local-signal required-check step to an otherwise
  low-risk relocation. The coupling is disclosed; consider whether it must ship in
  the same unit or could be a fast-follow. If kept together for coherence, no
  change needed.

### Strengths

- ✅ Every expected section (Summary, Context, Requirements, Acceptance Criteria,
  Open Questions, Dependencies, Assumptions, Technical Notes, Drafting Notes,
  References) is present and substantively populated, with no placeholders.
- ✅ The package-vs-directory distinction is stated explicitly in Summary,
  Requirements, out-of-scope, Technical Notes, and Drafting Notes, leaving no room
  to conflate the preserved package `luminosity` with the renamed `launcher` dir.
- ✅ Requirements are grouped by concern (Filesystem & Cargo, Build tasks, CI,
  Tests & docs) and name specific files, constants, and task/job names, so an
  implementer can start without clarification.
- ✅ An explicit "Explicitly out of scope" block sharply bounds the work
  (package/binary rename, `pup.ron`, version fields, new crates), fitting the
  `task` kind for a mechanical, indivisible refactor.
- ✅ The green-build criteria (`mise run` exits 0 end-to-end; `mise run check`
  exits 0) are strong integration-level verifications that transitively exercise
  most requirements, and the negative "no `*:cli:*` task remains" check makes the
  rename falsifiable.
- ✅ The `pup.ron` / version-coherence non-coupling is proactively reasoned about
  and placed out of scope with justification, pre-empting a plausible hidden
  coupling.

### Recommended Changes

1. **Record 0007 as a hard "Blocked by" dependency** (addresses: dependency
   major on 0007) — Move 0007 from "recommended sequencing only" to a true
   `Blocked by:` entry in Dependencies (the relocated crates do not exist until
   0007 lands), keeping the "recommended before 0008/0012" note separately as
   soft sequencing. Optionally add the forward link so 0008/0012 see 0014 should
   precede them.

2. **Disambiguate "launcher"** (addresses: clarity major) — Either commit to a
   sharper directory name (`dispatch` / `cli-launcher`) or add a one-line note
   fixing the referent: within this repo "the launcher crate" hereafter means the
   `cli/launcher/` directory whose package is `luminosity`, distinct from the bash
   bootstrap and the 0008 resolution pipeline.

3. **Split the CI required-check acceptance criterion** (addresses: testability
   major, completeness minor) — Separate into (a) a locally verifiable check
   ("the workflow YAML defines `check-launcher`/`build-launcher` and no
   `check-cli`/`build-cli` remain") and (b) an explicit manual-verification step
   naming the `CONTRIBUTING.md` runbook and the repo-settings location (Settings →
   Branches) where required-check names are confirmed.

4. **State the expected post-move `subject-path`** (addresses: completeness minor,
   clarity suggestion) — Write the anticipated value (e.g.
   `cli/launcher/bin/luminosity-*`) in the CI requirement even if flagged "confirm
   during implementation", so the intended outcome is explicit rather than
   inferred.

5. **Tighten the package-preservation criterion** (addresses: testability minor)
   — Replace the blanket "each is unchanged" with per-file invariants (e.g.
   `[package] name`/`[[bin]] name` remain `luminosity`; `plugin.json` version
   field unchanged; `pup.ron` still references `luminosity::version::core`).

6. **Add coverage criteria for the reference sweep** (addresses: testability
   minor) — Add a criterion such as "grep for `cli/`, `build:cli`,
   `test:unit:cli` crate references in `CLAUDE.md`, `deny.toml`, and the workflow
   YAML returns nothing" and "the CI attestation `subject-path` matches the path
   `build:launcher` actually writes to".

7. **Name the kernel path constant** (addresses: clarity minor) — In the
   `paths.py` requirement, name the kernel path constant (or state there is none)
   and say whether it is renamed or only repointed, mirroring the
   `CLI_DIR`→`LAUNCHER_DIR` treatment.

8. **Decide the CI-rename coupling deliberately** (addresses: scope suggestion) —
   Confirm whether the task/CI naming realignment must ship with the relocation or
   could be a fast-follow that isolates the merge-blocking required-check step. If
   kept together for coherence, no change needed — the coupling is disclosed.

## Per-Lens Results

### Clarity

**Summary**: The work item is unusually precise and internally consistent: scope
aligns tightly across Summary, Requirements, Acceptance Criteria, and
out-of-scope, and it distinguishes the preserved package name `luminosity` from
the renamed directory `launcher` explicitly and repeatedly. The one substantive
clarity risk is the deliberate overloading of the term "launcher" — used
simultaneously for the renamed crate directory, the bash bootstrap, and the
on-demand fetch/verify/cache/exec pipeline in 0008 — which the author has flagged
but not resolved. A few minor referent and naming inconsistencies remain but do
not obscure intent.

**Strengths**:
- The package-vs-directory distinction is stated explicitly across five sections,
  leaving no room to conflate them.
- Scope is coherent end-to-end from Summary through every Acceptance Criterion,
  with an explicit out-of-scope fence.
- The CI required-check re-registration is called out with unambiguous
  consequence in both Requirements and Technical Notes.
- Referenced work items (0007, 0008, 0012) corroborate the terminology, grounding
  the domain vocabulary rather than inventing it.

**Findings**:
- 🟡 **major** (confidence: high) — Context / Drafting Notes — "launcher" is used
  for three distinct referents (the `cli/launcher/` directory, the bash bootstrap,
  the 0008 resolution pipeline). Acknowledged in Drafting Notes but chosen anyway,
  leaving "the launcher" ambiguous when read alongside 0008. Suggestion: commit to
  `dispatch`/`cli-launcher` or add a one-line note fixing the referent.
- 🔵 **minor** (confidence: medium) — Requirements: Build tasks — the launcher path
  is tied to a named constant (`CLI_DIR`→`LAUNCHER_DIR`) but "the kernel directory"
  names no constant, leaving unclear whether one exists and whether it is renamed
  or only repointed.
- 🔵 **suggestion** (confidence: medium) — Assumptions / Requirements: CI — the
  build-output binary path is referred to inconsistently; the concrete post-move
  `subject-path` (likely `cli/launcher/bin/luminosity-*`) is left to inference and
  deferred entirely. State the expected value even if final confirmation is
  deferred.

### Completeness

**Summary**: This is a well-populated task work item: every expected section is
present and substantively filled, with requirements organised into clear
functional groupings and an explicit out-of-scope list. The frontmatter is
complete and coherent, and the `task` kind is well-matched to the enumerated,
concrete work. Completeness gaps are minor — the strongest is that the emphasised
CI required-check re-registration step is described but not backed by an
acceptance criterion a reader could act on without knowing the external runbook.

**Strengths**:
- All expected sections for a task are present and substantively populated — no
  empty or placeholder sections.
- Requirements are grouped by concern and name specific files, constants, and
  task/job names, so an implementer can start without clarification.
- An explicit out-of-scope block sharply defines what "done" does not include.
- Frontmatter is complete and internally coherent (kind, status, priority,
  parent, relates_to, tags).
- Acceptance Criteria are concrete Given/When/Then statements covering tree
  layout, both mise entry points, preserved package name, task renames, and CI job
  renames.

**Findings**:
- 🔵 **minor** (confidence: medium) — Requirements: CI / Assumptions — the new
  build-output binary path is referenced as something to update but never stated;
  Assumptions defers it and no criterion pins it. A wrong `subject-path` passes
  local checks yet breaks attestation silently.
- 🔵 **minor** (confidence: medium) — Acceptance Criteria — the CI required-check
  re-registration criterion lacks the actionable detail the body emphasises;
  it neither references the `CONTRIBUTING.md` runbook nor names the settings
  location where it is verified.

### Dependency

**Summary**: The work item is a self-contained refactor with genuinely low
external coupling, and it does a strong job capturing the one non-obvious external
coupling — the manual GitHub branch-protection required-check re-registration —
across Requirements, Assumptions, and Technical Notes. The main gap is that the
Dependencies section frames the hard prerequisite on 0007 (which scaffolds the
very crates being relocated) as "recommended sequencing only, blocked by: none",
understating a true upstream blocker; the downstream relationship to 0008/0012 is
handled defensibly as a sequencing preference rather than a hard Blocks edge.

**Strengths**:
- The CI required-check re-registration — a coupling to GitHub repo settings with
  no local signal — is captured redundantly and clearly across three sections.
- The relationship to 0008/0012 is explicitly named and correctly modelled as a
  soft sequencing preference rather than a hard blocker.
- The pup.ron / version-coherence non-coupling is proactively reasoned about and
  placed out of scope with justification, pre-empting a plausible hidden coupling.

**Findings**:
- 🟡 **major** (confidence: high) — Dependencies — "Blocked by: none (recommended
  sequencing only)" understates 0007 as a hard upstream prerequisite: the crates
  being relocated were "scaffolded by 0007", which is status `ready` (not done).
  Record 0007 as a true Blocked-by entry.
- 🔵 **minor** (confidence: medium) — Dependencies — the downstream-ordering
  coupling to 0008/0012 (land first so their crates are born under `cli/`) has no
  recorded forward link, and neither 0008 nor 0012's Dependencies mention 0014, so
  the ordering benefit can be silently lost.

### Scope

**Summary**: Work item 0014 is a well-scoped, atomic refactor: a single mechanical
relocation of the two existing workspace crates under a `cli/` container with a
coherent directory rename, driven end-to-end by one guaranteeing acceptance
criterion (`mise run` exits 0). The Summary, Requirements, and Acceptance Criteria
all describe the same unified purpose, with an explicit out-of-scope section that
sharpens the boundary. The one bundled concern (the invoke/mise task-module
rename, and its consequent CI job rename plus manual required-check
re-registration) is disclosed and integral rather than independent, so it does not
fracture the unit of delivery.

**Strengths**:
- Requirements, Summary, and Acceptance Criteria all describe one coherent unit
  with no drift between sections.
- An explicit out-of-scope block sharply bounds the work.
- The `task` kind fits a mechanical, indivisible refactor with no user-visible
  value increment.
- Deferred adjacent efforts (new subdomain crates, a future `cli/`→`crates/`
  rename) are correctly pushed to 0008/0012 or explicitly postponed.

**Findings**:
- 🔵 **suggestion** (confidence: medium) — Requirements: CI / Drafting Notes — the
  work bundles the core relocation with a separable task/CI-job rename that adds a
  manual, no-local-signal required-check step ("will silently block merges if
  missed"). Consider whether it must ship in the same unit or could be a
  fast-follow. If kept together for coherence, no change needed — the coupling is
  already disclosed.

### Testability

**Summary**: This is a well-specified refactor task whose Acceptance Criteria are
mostly concrete and mechanically verifiable — tree layout, task-tree contents, and
green `mise run`/`mise run check` all admit a definitive pass/fail. The main
testability gaps are the CI required-check criterion (which conflates an
observable outcome with an unobservable manual repo-settings step), an unbounded
"each is unchanged" clause in the package-preservation criterion, and a coverage
gap where several concrete requirements (the `../kernel` path, CI `mise run`
target renames, and the doc/comment edits) have no matching verifiable criterion.

**Strengths**:
- Most criteria are framed as observable Given/When/Then with concrete procedures
  producing a definitive pass/fail.
- The green-build criteria are strong integration-level verifications that
  transitively exercise most requirements.
- The negative criterion "no `*:cli:*` task remains" gives a clear falsifiable
  check that the rename is complete, not merely additive.

**Findings**:
- 🟡 **major** (confidence: high) — Acceptance Criteria — the final criterion
  bundles a locally observable outcome (jobs run under new names) with a
  repo-settings action the Technical Notes say "has no local signal"; a reviewer
  cannot conclusively pass/fail it, and "PR is mergeable" can be true for unrelated
  reasons. Split into a locally verifiable YAML check and an explicit manual
  repo-settings verification step.
- 🔵 **minor** (confidence: medium) — Acceptance Criteria — "each is unchanged" is
  unbounded; `checksums.json` legitimately changes on rebuild, so the invariant is
  ambiguous. State the exact per-file invariant.
- 🔵 **minor** (confidence: medium) — Requirements — the doc/comment edits and CI
  `subject-path`/target edits have no criterion that fails if forgotten (a green
  build does not exercise the attestation upload or `CLAUDE.md`). Add grep-based
  and `subject-path`-match criteria.

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-02T01:27:07+00:00

**Verdict:** COMMENT

All three pass-1 major findings are resolved by the edits. No major or critical
findings remain; the residual items are minor/suggestion-level polish, so the
verdict improves from REVISE to COMMENT — the work item is acceptable for
implementation as-is.

### Previously Identified Issues

- 🟡 **Clarity** (major): "launcher" overloaded across three referents — **Resolved.**
  Context now fixes the referent ("the launcher crate" = the `cli/launcher/`
  directory whose package/binary is `luminosity`, distinct from the bash bootstrap
  and the 0008 pipeline). Clarity re-review cites this as a model of proactive
  disambiguation.
- 🟡 **Dependency** (major): 0007 framed as "blocked by: none" — **Resolved.**
  Dependencies now records 0007 as a hard `Blocked by` (noting it is status
  `ready`, not done); dependency re-review now cites this as a strength.
- 🟡 **Testability** (major): CI required-check criterion mixed an unobservable
  manual step into pass/fail — **Resolved.** The criterion is split into a locally
  verifiable YAML check (job names + `subject-path`) and an explicit manual
  repo-settings step referencing the `CONTRIBUTING.md` runbook.
- 🔵 **Completeness** (minor): build-output `subject-path` unresolved — **Resolved.**
  Pinned to `cli/launcher/bin/luminosity-*` in Requirements and Assumptions,
  derived from `BIN_DIR = CLI_DIR / "bin"`.
- 🔵 **Completeness** (minor): CI required-check AC lacked actionable detail —
  **Resolved.** The AC now names the `CONTRIBUTING.md` runbook and Settings →
  Branches.
- 🔵 **Dependency** (minor): downstream ordering to 0008/0012 not recorded —
  **Resolved.** `Blocks` now states 0014 should precede 0008/0012 with the
  soft-ordering fallback spelled out.
- 🔵 **Testability** (minor): "each is unchanged" unbounded — **Resolved.**
  Replaced with explicit per-file invariants, with a note that `checksums.json`
  legitimately changes on rebuild.
- 🔵 **Testability** (minor): requirements lacking verifiable criteria —
  **Partially resolved.** A reference-sweep grep AC and a `subject-path`-match AC
  were added; testability re-review notes the grep is scoped to three files and
  the `../kernel` resolution still has no dedicated criterion (both minor).
- 🔵 **Clarity** (minor): kernel path constant unnamed — **Resolved.** The
  `paths.py` requirement now states there is no kernel constant and names the
  actual constants (`CLI_DIR`, `BIN_DIR`, `CHECKSUMS`, `CARGO_TOML`).
- 🔵 **Scope** (suggestion): CI/task rename bundling — **Acknowledged (kept by
  decision).** Author elected to keep the rename in this item for coherence; the
  coupling remains disclosed in Drafting Notes.

### New Issues Introduced

_All minor/suggestion — none block. These are optional polish surfaced by the
re-review._

- 🔵 **Clarity** (minor): the bare token `cli` now denotes three things (the new
  container directory, the crate being renamed away, the shipped binary) without a
  single consolidating gloss like the one added for "launcher".
- 🔵 **Clarity** (suggestion): ADR-0009/ADR-0010 are cited in Context but not
  linked in References; the "Rust `cli` binary" phrasing quoted from 0008 could
  note it is the same artefact as the launcher crate.
- 🔵 **Completeness** (suggestion): no AC explicitly confirms the Python task-module
  renames / wiring-test pass (covered transitively by `mise run`).
- 🔵 **Dependency** (suggestion ×2): the soft 0008/0012 ordering and the
  GitHub-settings coupling live in prose but not as machine-visible edges / in the
  Dependencies section.
- 🔵 **Testability** (minor ×2 + suggestion): reference-sweep grep scoped to three
  files could miss stale references elsewhere; the branch-protection criterion
  could name a concrete verifier (`gh api .../branches/main/protection`); the
  `../kernel` resolution has no dedicated AC.

### Assessment

The work item is ready for implementation. Every major finding from the first
pass has been addressed, and the acceptance criteria are now concrete and mostly
locally verifiable. The remaining minor/suggestion items (a `cli`-token gloss,
ADR links, broadening the reference-sweep grep, a concrete `gh api` verifier for
branch protection, and a dedicated `../kernel` criterion) are worthwhile polish
but none blocks proceeding to a plan.

## Approval (Pass 3) — 2026-07-02T01:30:22+00:00

**Verdict:** APPROVE

Following the re-review, the minor/suggestion polish items were also applied to
the work item: a `cli`-token gloss and a clarifier on 0008's "Rust `cli` binary"
phrasing (clarity); ADR-0009/ADR-0010 added to References with corrected titles
(clarity); an acceptance criterion for the Python task-module renames and wiring
tests (completeness); an "External coupling" line surfacing the branch-protection
step in Dependencies (dependency); a whole-repo reference-sweep grep, a concrete
`gh api` verifier for branch protection, and a `../kernel` resolution clause
(testability). With every major and minor finding now addressed and only
deliberately-declined tooling/scope suggestions remaining, the reviewer marks the
work item **APPROVED** and ready for implementation.
