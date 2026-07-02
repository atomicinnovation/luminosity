---
type: work-item-review
id: "0008-on-demand-static-binary-distribution-and-launcher-review-1"
title: "Work Item Review: On-Demand Static-Binary Distribution & Launcher"
date: "2026-07-02T23:57:56+00:00"
author: Toby Clemson
producer: review-work-item
status: complete
target: "work-item:0008"
work_item_id: "0008"
reviewer: Toby Clemson
verdict: "APPROVE"
lenses: [clarity, completeness, dependency, scope, testability]
review_number: 1
review_pass: 3
tags: []
last_updated: "2026-07-03T00:26:22+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Work Item Review: On-Demand Static-Binary Distribution & Launcher

**Verdict:** REVISE

Work item 0008 is a structurally complete, densely written, and internally
coherent story: every story section is present and populated, its terminology
is unusually carefully disambiguated against the referenced ADRs and the 0014
relocation, and its seven acceptance criteria trace cleanly back to the
requirements. The reasons to revise are not gaps in intent but gaps in
*verifiability and prerequisite-capture*: three acceptance criteria assert
properties ("verifiably static", "statically linkable / no OpenSSL",
in-process minisign verification) without a defined check, the network/fetch
failure path has no criterion at all, and the operational prerequisites the
requirements imply — minisign key provisioning, GitHub Releases, the build
toolchain — are named in prose but never surfaced in Dependencies. The story's
large surface (self-flagged in Open Questions) reinforces that these seams
should be sharpened before planning.

### Cross-Cutting Themes

- **Asserted properties without a defined verification procedure** (flagged by:
  testability, and touching integrity/dependency) — several acceptance criteria
  state an outcome ("verifiably static", "statically linkable", "no OpenSSL",
  "verifies its minisign signature") without naming the check that produces a
  pass/fail. This is the single largest driver of the REVISE verdict.
- **Operational and external prerequisites named in prose but absent from
  Dependencies** (flagged by: dependency, testability) — minisign key
  provisioning, GitHub Releases (publish + fetch), the `gh` CLI, and the
  cargo-zigbuild/zig toolchain are all load-bearing preconditions that the body
  discusses but the Dependencies section does not capture, risking a
  mid-implementation block. The minisign key in particular is both an
  uncaptured dependency and an untested verification path.
- **Story breadth / split candidacy** (flagged by: scope, and self-flagged by
  the author in Open Questions) — the story bundles a release-side pipeline
  (build, sign, publish, version coherence) with a client-side runtime
  (resolve/verify/cache/exec, dispatch, help, bootstrap). These have a clean
  producer/consumer seam and could ship and be tested independently.
- **Missing negative-path coverage** (flagged by: testability, dependency) — the
  only failure path with a criterion is integrity mismatch; the
  network/fetch-failure path (which is exactly the GitHub Releases external
  coupling) is uncovered.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Testability**: "Verifiably static" lacks a defined verification procedure
  **Location**: Acceptance Criteria (first criterion)
  The first criterion requires binaries be "verifiably static" but names no
  procedure that produces a pass/fail, and the check differs between musl and
  darwin targets. Two reviewers could disagree on whether the core
  zero-dependency guarantee is met.

- 🟡 **Testability**: No criterion covers the network/fetch-failure path
  **Location**: Acceptance Criteria
  Fetch-on-demand is core and the Technical Notes flag musl DNS caveats, yet no
  criterion specifies behaviour when a fetch fails (network error, missing
  host-triple asset, Release unavailable). An implementation that panics, hangs,
  or reports cryptically would still pass every listed check.

- 🟡 **Dependency**: minisign key provisioning is a prerequisite but not
  captured as a dependency
  **Location**: Requirements (Integrity & signing); Technical Notes;
  Dependencies
  The release pipeline cannot sign until a minisign keypair exists and its
  secret is provisioned into the signing environment; ADR-0002 explicitly
  assigns this story the key storage / rotation / `.minisig` publishing work.
  It is discussed in Technical Notes as a "standing operational responsibility"
  but not surfaced as a blocking prerequisite, so the signing acceptance
  criterion is un-satisfiable until the key exists.

#### Minor

- 🔵 **Dependency**: GitHub Releases hosting/API and the `gh` CLI are external
  couplings left implicit
  **Location**: Requirements (Release orchestration; Launcher resolution);
  Dependencies
  Both the publish side (`gh` upload) and the fetch side (launcher download)
  depend on GitHub Releases and its URL/asset contract, which is shared between
  publisher and launcher and must agree. No external systems appear in
  Dependencies.

- 🔵 **Dependency**: cargo-zigbuild + zig toolchain is an implied but uncaptured
  build-environment dependency
  **Location**: Requirements (Cross-compile); Technical Notes; Dependencies
  Cross-compiling four static targets from one host requires cargo-zigbuild and
  a zig toolchain provisioned (and, per repo convention, pinned) in the build
  environment — a precondition of the build criterion, stated only as a
  technique.

- 🔵 **Dependency**: the 0014 soft ordering constraint is not surfaced
  **Location**: Dependencies (Relates to)
  0014 records that it should preferably land before 0008 so new subdomain
  crates are born under `cli/` rather than relocated later. 0008 records 0014
  only as "relates to", so a planner reading 0008 in isolation misses the
  rework-avoidance sequencing.

- 🔵 **Testability**: "statically linkable / no OpenSSL" asserts an
  implementation property with no defined check
  **Location**: Acceptance Criteria
  The criterion mixes a verifiable outcome with feature-list instructions but
  states no check confirming absence of OpenSSL/native-tls, which a transitive
  default-feature re-enable could silently violate.

- 🔵 **Testability**: in-process minisign verification is not distinguished from
  TLS-only verification in the check
  **Location**: Acceptance Criteria (fetch criterion)
  ADR-0002's distinguishing requirement — verification is in-process against our
  key, not mere TLS trust — is not expressed as a check; a test that only
  downloads over HTTPS could satisfy the literal wording.

- 🔵 **Testability**: "exit codes and signals propagate" lacks a concrete
  observable
  **Location**: Acceptance Criteria (dispatch criterion)
  No specific input/expected pair is given; signal propagation in particular is
  not trivially observable without a stated scenario, so the guarantee is
  effectively untested.

- 🔵 **Testability**: "confirm clap's derive enables external dispatch" is a
  task, not a testable outcome
  **Location**: Requirements (Dispatch)
  The confirmation describes an activity with no recorded pass/fail and is not
  reflected in any acceptance criterion, despite ADR-0010 flagging it as a
  to-be-confirmed assumption.

- 🔵 **Testability**: "all four target platforms" is unbounded relative to
  single-host CI verification
  **Location**: Acceptance Criteria (build criterion)
  The criterion does not state which triples are execution-verified versus only
  build-verified; "builds for all four" could be claimed on compile success
  while runtime behaviour is exercised on one triple.

- 🔵 **Scope**: story bundles two independently deliverable streams (release
  pipeline vs launcher runtime)
  **Location**: Requirements; Acceptance Criteria; Open Questions
  The release-side cluster (cross-compile, sign, publish, version coherence)
  produces verifiable assets with no launcher; the client-side cluster
  (resolve/verify/cache/exec, dispatch, help, bootstrap) is testable against
  fixture assets. The clean producer/consumer seam is a genuine split candidate,
  which the author raises in Open Questions.

- 🔵 **Scope**: sizing sits at the upper edge of a single story
  **Location**: Open Questions
  The breadth (four-target cross-compile, in-process minisign, hand-rolled
  release pipeline, resolve-once-and-cache, exec dispatch, help synthesis, bash
  bootstrap) is self-described as "a large surface". The open sizing question is
  best resolved before implementation rather than left live.

- 🔵 **Clarity**: "the manifest" / "the release manifest" referent is not
  consistently qualified
  **Location**: Requirements
  The version-coherence manifest, the help `description` source, and the
  "manifest-hash" the launcher watches are referred to under several phrasings
  with no single introduction establishing they are one artefact.

- 🔵 **Clarity**: the fetch actor shifts between "the plugin" and "the launcher"
  **Location**: Context
  Context says "the plugin downloads … binaries" while Requirements split
  fetching between the thin bash bootstrap (the `luminosity` binary itself) and
  the Rust launcher (sub-binaries). The Context framing conflates two actors the
  Requirements deliberately separate.

#### Suggestions

- 🔵 **Clarity**: inline ADR quotes reuse `cli` as the crate name, colliding
  with `cli` as the workspace
  **Location**: Requirements
  The body reconciles the naming only in Drafting Notes; a reader following the
  ADR-0010 reference finds the launcher crate still called `cli` there. A
  one-line pointer at first use would flag the collision at the point of
  confusion.

- 🔵 **Clarity**: "the confirmation ADR-0009/ADR-0010 attribute to the scaffold"
  has a weakly-grounded referent
  **Location**: Requirements (Dispatch)
  ADR-0010 records the clap-derive confirmation as a to-be-confirmed
  consequence; ADR-0009 does not obviously speak to it. The dual attribution
  weakens traceability.

### Strengths

- ✅ Structurally complete: every story section (Summary, Context, Requirements,
  Acceptance Criteria, Open Questions, Dependencies, Assumptions, Technical
  Notes, Drafting Notes, References) is present and substantively populated, and
  the frontmatter is intact and valid.
- ✅ Requirements and Acceptance Criteria are tightly aligned — each of the seven
  criteria maps directly to a stated requirement, so there is no scope drift
  between sections and any future split has clear seams.
- ✅ Terminology is unusually carefully disambiguated: the launcher binary vs the
  workspace, and the ADR-0010 `cli`-crate naming vs the 0014 `launcher`-crate
  relocation, are explicitly reconciled, with concrete artefacts named
  (`cli/launcher/Cargo.toml`, `cli/Cargo.toml`).
- ✅ Scope boundaries are stated crisply — Windows out of scope, launcher
  self-update excluded, Sigstore/SLSA parked — and the author candidly
  self-flags the story's breadth rather than hiding it.
- ✅ Upstream couplings are well reasoned and internally consistent: frontmatter
  `blocked_by` (0007, 0002) and `relates_to` (0014) match the prose Dependencies
  section, each with a stated rationale, and the honest "Blocks: none directly"
  matches the ADR framing.
- ✅ Where criteria are concrete they are strong: the cache key
  (name + version + checksum), the integrity-mismatch refusal, and the
  three-artefact version-coherence check are all directly verifiable.

### Recommended Changes

1. **Add verification procedures to the property-asserting criteria** (addresses:
   "Verifiably static…", "statically linkable / no OpenSSL…", in-process minisign
   verification). State the concrete checks — e.g. musl targets: `file` reports
   "statically linked" and `ldd` reports "not a dynamic executable"; darwin:
   only system libraries in `otool -L`; `cargo tree -e features` shows no
   openssl-sys/native-tls; and a negative test where a valid-sha256 asset signed
   by a non-release key is refused (proving in-process signature validation
   independent of TLS).

2. **Add a network/fetch-failure acceptance criterion** (addresses: "No criterion
   covers the network/fetch-failure path"). E.g. "Given the host-triple asset
   cannot be fetched (network error or absent asset), when the launcher resolves,
   then it exits non-zero with a diagnostic naming the missing target and does
   not exec a stale or wrong binary."

3. **Surface the operational and external prerequisites in Dependencies**
   (addresses: minisign key provisioning; GitHub Releases + `gh`; cargo-zigbuild
   + zig). Add minisign keypair generation + CI-secret storage as a blocking
   prerequisite (ADR-0002 assigns it here), and record GitHub Releases and the
   build toolchain as external/environment couplings so provisioning is visible
   before implementation starts.

4. **Resolve the story-split open question rather than deferring it** (addresses:
   the two scope findings). Either commit to the single-story framing with a
   stated indivisibility rationale, or decompose along the producer/consumer seam
   (e.g. 0008a build/sign/publish; 0008b launcher resolution/dispatch/bootstrap,
   blocked_by 0008a). Note the bootstrap currently has no acceptance criterion
   regardless of the split decision.

5. **Make the two under-tested requirement-only items observable** (addresses:
   "confirm clap's derive…", "exit codes and signals propagate"). Fold the clap
   confirmation into the dispatch criterion (a test asserting an unknown
   subcommand reaches the `External(Vec<OsString>)` arm), and give the
   propagation criterion a concrete case (a sub-binary exiting 42 → parent exits
   42; SIGINT disposition propagates).

6. **Tighten the ambiguous referents** (addresses: the two minor clarity findings
   and two suggestions). Introduce "the release manifest" once as the single
   artefact and reference it consistently; clarify the Context fetch actor as
   "the plugin (via a thin bash bootstrap, then the Rust launcher)"; add a
   one-line `cli`-crate-vs-workspace pointer at first use; and correct the
   clap-confirmation ADR attribution.

## Per-Lens Results

### Clarity

**Summary**: The work item is unusually careful about referent clarity: it
consistently disambiguates the launcher binary from the workspace, explicitly
reconciles the ADR-0010 crate naming against the 0014 relocation, and names
concrete artefacts rather than vague ones. The main clarity risks are a small
number of overloaded terms — "the manifest"/"the release manifest", "the
plugin"/"the launcher" as fetch actors, and the residual `cli`-crate-vs-`cli`-
workspace collision inherited from ADR-0010 — that a reader who has not read
0014 could misread.

**Strengths**:
- The launcher-crate terminology is explicitly and repeatedly disambiguated,
  resolving the naming collision ADR-0010 leaves open.
- Concrete artefacts are named (`cli/launcher/Cargo.toml`, `cli/Cargo.toml`
  `[workspace.dependencies]`) rather than described vaguely.
- Drafting Notes make the intent behind each reconciliation explicit and
  traceable.
- Acceptance Criteria mirror the Requirements terminology exactly.

**Findings**:
- 🔵 minor (medium): "the manifest" / "the release manifest" referent is not
  consistently qualified (Requirements). The version-coherence manifest, the
  help-description source, and the launcher's manifest-hash are not introduced
  once as the same artefact.
- 🔵 minor (medium): "the plugin downloads" vs "the launcher fetches" — the fetch
  actor shifts across sections (Context). Context conflates two actors the
  Requirements deliberately separate (bootstrap vs launcher).
- 🔵 suggestion (low): inline ADR quotes reuse `cli` as the crate name, colliding
  with `cli` as the workspace (Requirements). Reconciled only in Drafting Notes;
  a first-use pointer would flag it at the point of confusion.
- 🔵 suggestion (low): "it"/the clap-confirmation sentence attributes the
  confirmation to ADR-0009/ADR-0010, but ADR-0010 records it as a to-be-confirmed
  consequence and ADR-0009 does not obviously speak to it (Requirements).

### Completeness

**Summary**: This story is exceptionally complete from a structural and
content-density standpoint: every section a story requires is present and
substantively populated, the frontmatter is intact and valid, and the Context
clearly explains the motivating architectural goals (ADR-0002, ADR-0010).
Acceptance Criteria comprise seven specific criteria mapping cleanly to the
Requirements. The only completeness-relevant observation is that the author has
self-flagged the story's large surface area in Open Questions, which is a scope
concern rather than a completeness gap.

**Strengths**:
- All story-appropriate sections are present and densely populated.
- Frontmatter is complete and valid — recognised kind (story), appropriate
  status (draft), and populated priority, parent, blocked_by, relates_to.
- Context genuinely explains motivation and grounds it in two accepted ADRs
  rather than restating the Summary.
- Seven concrete, outcome-oriented acceptance criteria trace directly to the
  Requirements.
- Kind-specific story content is well served: the system whose need is met (the
  end user who "installs nothing") is identified and Requirements are detailed
  enough to begin without follow-up.

**Findings**: None.

### Dependency

**Summary**: The work item's work-item-level couplings are well captured: it is
correctly blocked by the scaffold (0007) and architecture spike (0002), relates
to the relocation (0014), and its Dependencies/frontmatter are internally
consistent. The main gaps are external-system and operational couplings that the
body names but does not surface in Dependencies — GitHub Releases as the
artifact host/source, the `gh` CLI as the publishing dependency, and minisign
key provisioning (an operational prerequisite ADR-0002 explicitly assigns to this
story) — plus the soft ordering relationship with 0014 that 0014 itself flags but
0008 records only as "relates to".

**Strengths**:
- Upstream blockers are explicitly and correctly captured, with each blocker's
  rationale stated and frontmatter reconciled with the body.
- The 0014 relationship is captured in both frontmatter and prose with its
  reason.
- Assumptions explicitly captures the (adapted) accelerator pipeline coupling and
  deliberately records that its bash launcher is not carried over.
- The absence of a hard downstream Blocks edge is honestly stated and matches the
  ADR framing.

**Findings**:
- 🟡 major (high): minisign key provisioning is a prerequisite but not captured as
  a dependency (Requirements: Integrity & signing; Technical Notes;
  Dependencies). Signing and every signature-dependent criterion cannot be
  implemented/tested until the keypair exists and CI secrets are configured.
- 🔵 minor (high): GitHub Releases hosting/API and the `gh` CLI are external
  couplings left implicit (Requirements: Release orchestration; Launcher
  resolution). The asset/manifest URL contract is shared between publisher and
  launcher and must agree.
- 🔵 minor (medium): the 0014 soft ordering constraint (land 0014 before 0008 so
  new crates are born under `cli/`) is visible from 0014 but not surfaced in 0008
  (Dependencies).
- 🔵 minor (medium): cargo-zigbuild + zig toolchain is an implied but uncaptured
  build-environment prerequisite for the cross-compile criterion (Requirements:
  Cross-compile; Technical Notes).

### Scope

**Summary**: Work item 0008 is coherent in that every requirement serves one
theme — getting a zero-setup, on-demand static binary to the user and dispatching
to it — and the Summary, Requirements, and Acceptance Criteria describe the same
scope consistently. However, the story bundles two independently deliverable
value streams (the release-side build/sign/publish pipeline and the client-side
launcher/dispatch runtime) that could ship and be verified separately; the work
item candidly self-flags this large surface in Open Questions. The declared
`story` kind is defensible given the ADRs frame it as one launcher/distribution
unit, but the breadth sits at the upper edge of a single story and is a genuine
split candidate at planning.

**Strengths**:
- Summary, Requirements, and Acceptance Criteria are tightly aligned with no
  scope drift; each acceptance criterion maps to a requirement.
- All requirements orbit a single unifying purpose, giving a clear thematic
  centre.
- The work item is admirably self-aware about its sizing risk, naming a concrete
  candidate split axis.
- Scope boundaries (Windows out, no self-update, Sigstore parked) are stated
  crisply.

**Findings**:
- 🔵 minor (medium): story bundles two independently deliverable streams — release
  pipeline vs launcher runtime (Requirements). Clean producer/consumer seam;
  carrying both means the increment is only "done" when the whole chain lands,
  enlarging review/rollback blast radius. Recommend resolving the split at
  planning or recording an indivisibility rationale.
- 🔵 minor (low): sizing sits at the upper edge of a single story (Open
  Questions). The open sizing question is best resolved before implementation
  rather than left live.

_(An earlier pass of this lens rated the bundling finding **major**; it is
carried here at the lens's final severity of minor, but it is the dominant scope
concern and is surfaced as a cross-cutting theme above.)_

### Testability

**Summary**: The Acceptance Criteria are mostly well-framed as observable
Given/When/Then behaviours covering fetch, cache-reuse, verification-failure,
dispatch, help, and version coherence — a strong basis for verification. The main
testability gaps are unbounded "all four platforms" language without a defined
static-verification procedure, several criteria that assert properties
(static-linkability, in-process signature verification, exit-code/signal
propagation) without a defined check, and a missing negative-path threshold for
how the launcher must behave on network/fetch failure.

**Strengths**:
- Most criteria are framed as concrete Given/When/Then observable behaviours.
- The cache key is specified precisely (name + version + checksum).
- The verification-failure criterion specifies both trigger and required outcome.
- Version coherence is scoped to three named artefacts, directly checkable.

**Findings**:
- 🟡 major (high): "verifiably static" lacks a defined verification procedure
  (Acceptance Criteria). No named check; differs between musl and darwin targets.
- 🟡 major (high): no criterion covers the network/fetch-failure path (Acceptance
  Criteria). Only integrity mismatch is covered; a launcher that panics/hangs on
  fetch failure would still pass.
- 🔵 minor (high): "statically linkable / no OpenSSL" asserts an implementation
  property with no defined check (Acceptance Criteria). A transitive
  default-feature re-enable could silently violate it.
- 🔵 minor (medium): in-process minisign verification is not distinguished from
  TLS-only verification in the check (Acceptance Criteria). A HTTPS-only download
  could satisfy the literal wording.
- 🔵 minor (medium): "exit codes and signals propagate" lacks a concrete
  observable (Acceptance Criteria). No input/expected pair given.
- 🔵 minor (medium): "confirm clap's derive enables external dispatch" is stated
  as a task, not a testable outcome (Requirements), and is not reflected in any
  criterion.
- 🔵 minor (low): "all four target platforms" is unbounded relative to what a
  single-host CI run can verify (Acceptance Criteria). Build-verification vs
  runtime-verification is not distinguished.

---
*Review generated by /accelerator:review-work-item*

## Re-Review (Pass 2) — 2026-07-03

**Verdict:** REVISE

Re-ran the four lenses that had findings (clarity, dependency, scope,
testability). **Every finding from pass 1 is resolved** — the added verification
procedures, network-failure criterion, in-process/non-release-key signature test,
`cargo tree` OpenSSL check, observable dispatch, surfaced dependencies
(minisign key, GitHub Releases + `gh`, cargo-zigbuild, 0014 ordering), the
release-manifest definition, the fetch-actor clarification, and the retained
indivisibility rationale were all acknowledged as resolved and now appear as
strengths. The verdict remains REVISE only because the testability lens surfaced
**two new findings of the same class we were closing** — an acceptance criterion
asserting an outcome without a defined check — that were not among the pass-1
edits. All other new findings are minor polish.

### Previously Identified Issues

- 🟡 **Testability**: "Verifiably static" lacks a defined verification procedure —
  **Resolved** (`file`/`ldd` for musl, `otool -L` for darwin; build- vs
  execution-verified split stated).
- 🟡 **Testability**: No criterion covers the network/fetch-failure path —
  **Resolved** (new criterion: non-zero exit, diagnostic naming the target, no
  stale exec).
- 🟡 **Dependency**: minisign key provisioning not captured as a dependency —
  **Resolved** (now a blocking operational prerequisite in Dependencies).
- 🔵 **Dependency**: GitHub Releases + `gh` left implicit — **Resolved**
  (external systems, dual-sided contract).
- 🔵 **Dependency**: cargo-zigbuild/zig uncaptured — **Resolved**
  (build-environment prerequisite).
- 🔵 **Dependency**: 0014 soft ordering not surfaced — **Resolved** (recorded in
  the Relates-to note).
- 🔵 **Testability**: "no OpenSSL" without a check — **Resolved**
  (`cargo tree -e features`).
- 🔵 **Testability**: in-process minisign not distinguished from TLS-only —
  **Resolved** (non-release-key negative test).
- 🔵 **Testability**: exit-code/signal propagation lacked an observable —
  **Resolved** for exit codes (`42`→`42`); signal disposition stated but see new
  finding below.
- 🔵 **Testability**: "confirm clap's derive" stated as a task — **Resolved**
  (tied to the reachable-`External`-arm assertion).
- 🔵 **Testability**: "all four platforms" unbounded — **Resolved** (build- vs
  runtime-verification split).
- 🔵 **Scope**: bundles two independently deliverable streams — **Resolved**
  (indivisibility rationale in Context; accepted by the lens).
- 🔵 **Scope**: sizing at the upper edge — **Partially resolved** (rationale
  added and accepted; the story is inherently large — carried as a soft minor).
- 🔵 **Clarity**: "the release manifest" referent — **Resolved** (defined once).
- 🔵 **Clarity**: fetch actor "plugin" vs "launcher" — **Resolved**.
- 🔵 **Clarity** (suggestion): `cli`-crate-vs-workspace pointer — **Resolved**
  (added; re-review notes the parenthetical is now dense — see new findings).
- 🔵 **Clarity** (suggestion): clap-confirmation ADR attribution — **Resolved**
  (corrected to ADR-0010).

### New Issues Introduced

- 🟡 **Testability**: Version-coherence criterion states no verification
  procedure — "enforced by the release pipeline" asserts an outcome with no
  observable pass/fail (same defect class as the "verifiably static" major we
  fixed). Suggest a negative test: mismatched versions → pipeline exits non-zero
  naming the mismatching files; all three agree → proceeds.
- 🟡 **Testability**: Synthesised `--help` section has no input/output oracle —
  no sample manifest input or expected rendered output, so the manifest→help
  wiring is not mechanically verifiable. Suggest: manifest entry `foo` with
  `description: "Bar tool"` → `luminosity --help` output contains a line matching
  `foo` and `Bar tool`; `luminosity foo --help` emits the child's own help
  (sentinel string).
- 🔵 **Testability**: signal-propagation sub-clause lacks a concrete oracle
  (name a signal + observed `$?` = 128 + signum).
- 🔵 **Testability**: fetch-failure criterion enumerates three triggers without
  stating how each is induced under test.
- 🔵 **Testability**: minisign key provisioning prerequisite has no confirming
  acceptance criterion (or an explicit scope-out).
- 🔵 **Dependency**: manual CI required-check registration for new build/verify
  jobs not captured (0014 records this for itself).
- 🔵 **Dependency**: runtime network-availability/SLA implication of the GitHub
  Releases fetch not noted (ADR-0002's air-gapped caveat).
- 🔵 **Clarity**: "the launcher" denotes three things (crate/binary, resolution
  pipeline, bootstrap concept) without an in-item disambiguation.
- 🔵 **Clarity**: the crate-naming reconciliation parenthetical in Context is
  dense (a side-effect of the pass-1 fix); consider splitting it out.
- 🔵 **Clarity** (suggestion): Summary's "installs nothing" reads stronger than
  ADR-0002's "nothing beyond the plugin".
- 🔵 **Scope**: five substantial capabilities in one delivery unit (inherent
  size; indivisibility for end-to-end validation accepted).
- 🔵 **Scope** (suggestion): confirm minisign key-provisioning ownership; carve
  to a blocked_by prerequisite if a separate ops/security owner is required.

### Assessment

The pass-1 revisions fully landed: all fifteen-plus original findings are
resolved and the acceptance criteria are now, in the testability lens's words,
"unusually strong". The work item is materially closer to implementation-ready.
Two new **major** findings keep the verdict at REVISE — both narrow, unambiguous,
verification-procedure gaps of the exact class already being closed (the
version-coherence and `--help` criteria), each fixable with a one-line observable
rewrite. Once those two are given defined checks, the remaining items are all
optional minor polish and the work item is ready for planning.

## Approval (Pass 3) — 2026-07-03

**Verdict:** APPROVE

Following pass 2, the two REVISE-driving testability majors were closed — the
version-coherence criterion now carries a defined negative check (mismatched
versions → pipeline exits non-zero naming the files) and the `--help` criterion
now carries a concrete input/output oracle (a manifest `foo`/`"Bar tool"` entry
must appear in the synthesised section, with child-delegated `--help` verified by
a sentinel string). The minor polish across all four lenses was also applied:
signal-propagation oracle, fetch-trigger inducement, a minisign-provisioning
confirming criterion, the CI required-check and GitHub Releases availability
dependency notes, the "launcher" terminology disambiguation, the de-nested
crate-naming clause, and the qualified Summary wording. With every finding from
all passes resolved, the reviewer approves the work item for planning.
