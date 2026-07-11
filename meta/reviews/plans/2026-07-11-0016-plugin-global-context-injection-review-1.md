---
type: plan-review
id: "2026-07-11-0016-plugin-global-context-injection-review-1"
title: "Plan Review: Plugin-Global Additional Context Injection"
date: "2026-07-11T19:29:26+00:00"
author: Toby Clemson
producer: review-plan
status: complete
target: "plan:2026-07-11-0016-plugin-global-context-injection"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, code-quality, test-coverage, correctness, security, standards, usability]
review_number: 1
review_pass: 3
tags: [configuration, context-injection, rust-cli, skills, evals]
last_updated: "2026-07-11T23:22:55+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: Plugin-Global Additional Context Injection

**Verdict:** REVISE

The plan is architecturally sound and genuinely test-first: it extends the
established `config` hexagon faithfully (a driven `ReadConfigBody` port, a pure
fake-driven `ProjectContextAssembler`, a byte-exact `render()` in a thin
launcher inbound), reuses the already-tested `frontmatter::split` with no new
parser, and decomposes into three independently-green, mergeable increments. It
does not, however, reach the "ready to implement" bar: a cluster of majors
converge on three structural gaps — the passive, load-time injection path has
no designed behaviour for a malformed config file even though it now sits on
*every* skill invocation; the byte-exact block's correctness rests on an
un-sketched trim whose written contract contradicts its own code sketch; and
the AC-enforcing registry test is placed in a directory no `mise` roll-up
collects, so it would never run in CI. Layered on top are an unacknowledged
cross-user prompt-injection trust boundary and several fragile hand-maintained
wiring seams. None are hard to fix, but together they warrant a revision pass
before implementation.

### Cross-Cutting Themes

- **Malformed-config behaviour on the universal injection path is undesigned**
  (flagged by: Architecture, Usability, Test Coverage) — `read_body` returns
  `MalformedFrontmatter` on a present-but-unsplittable file, so `luminosity
  context` exits non-zero. Because the reader now runs at skill-load time via
  the `!`-preprocessor in *every* registered skill, one malformed
  `.luminosity/config.md` sits on the invocation path of every skill, and the
  plan never says what the preprocessor does with a non-zero exit (fail the
  skill, inject stderr, inject nothing). There is also no black-box test for
  this path, even though the sibling `config` command has one.

- **Byte-exact block correctness hinges on an un-sketched, under-specified
  trim** (flagged by: Correctness, Test Coverage) — the load-bearing output
  depends entirely on `trim_blank_lines` (shown as `...`). Two load-bearing
  details are unpinned: (1) the body's own trailing newline must be stripped or
  `render` + `println!` yields a trailing blank line that violates the
  no-trailing-blank-line AC; (2) CRLF bodies (which `frontmatter::split`
  preserves) flow into a `\n\n` LF join and whitespace-only-line detection with
  no specified behaviour. The Implementation-Approach prose ("trim the
  *combined* result") also contradicts the `combine` sketch (trim each part,
  then join) — and the two are not equivalent.

- **The "every skill" wiring convention is hand-maintained and only partly
  enforced** (flagged by: Standards, Usability, Architecture) — wiring a skill
  needs two hand-copied elements (the `!`-preprocessor line *and* a matching
  `allowed-tools` grant), of which the registry test enforces only the first;
  the registry test itself lives in `tests/unit/skills/`, which no test
  roll-up collects, so it never runs in CI; and there is no template, snippet,
  or CONTRIBUTING note to onboard future skill authors beyond a (never-run)
  failing test.

- **The no-comments convention is violated in a code sketch** (flagged by:
  Standards, Code Quality) — the prescribed `trim_blank_lines` inline comment
  restates what the name and adjacent contract already convey; the repo's
  no-comments rule is non-negotiable and the review-plan instructions
  explicitly require stripping such comments.

### Tradeoff Analysis

- **Security (untrusted-data framing) vs accelerator parity (load-bearing
  wrapper)**: The security lens recommends reframing the wrapper prose to
  present the injected body as reference *data* rather than an instruction
  ("Take this into account when making decisions...") and delimiting it as
  untrusted. But the work item pins that exact prose and near-top placement as
  *load-bearing*, matching the accelerator byte-for-byte, on the premise that
  downstream skill prose depends on it. These conflict: hardening the framing
  diverges from the parity the story treats as a constraint. Recommendation:
  keep the byte-exact block as specified for parity, but (a) record the
  prompt-injection trust boundary explicitly in the plan, and (b) close the
  gap on the *skill* side — re-assert the skill's binding constraints *after*
  the injected block so trusted prose keeps the last word — rather than
  altering the load-bearing wrapper.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Architecture / Usability / Test Coverage**: Malformed config body breaks
  the passive injection path across every skill, with no designed degradation
  and no test
  **Location**: Phase 1 §3 (`ReadConfigBody` adapter) / §4 (`report`); Phase 1
  Test Strategy (black-box)
  A single malformed `.luminosity/config.md` makes the injection line exit
  non-zero on *every* skill load; the plan neither specifies the preprocessor's
  handling of a non-zero exit nor covers the path with a black-box test (the
  `config` sibling has `a_malformed_personal_file_fails_a_full_stack_get_loudly`).

- 🟡 **Correctness**: The body's trailing newline must be stripped or the block
  gains a trailing blank line
  **Location**: Phase 1 §2 (`combine`/`trim_blank_lines`) and §4 (`render`/`report`)
  `frontmatter::split` returns bodies *with* their trailing `\n`; `render`
  appends the body raw and `report` adds a `println!` newline. Unless
  `trim_blank_lines` ends the slice at the last content byte, stdout ends
  `...body\n\n`, violating the no-trailing-blank-line AC.

- 🟡 **Correctness**: Prose says "trim the combined result"; the sketch trims
  each part — not equivalent
  **Location**: Implementation Approach and Phase 1 §2 (trim contract vs `combine`)
  The sketch (trim each part, drop empties, join with `\n\n`) is correct, but
  the load-bearing prose describes trimming the concatenation, which would leave
  interior blank lines between the bodies and produce a multi-blank-line
  separator, failing the single-blank-line-separator AC.

- 🟡 **Test Coverage**: The new `combine`/`trim` logic is untested against CRLF
  bodies
  **Location**: Phase 1 §2 and Test Strategy (config core)
  All config-core cases are LF; `frontmatter::split` preserves CRLF, so
  `trim_blank_lines` and the `\n\n` join operate on `\r`-terminated lines with
  no test pinning whether the block preserves or normalises them.

- 🟡 **Test Coverage**: No black-box test for the malformed-frontmatter error
  path of `luminosity context`
  **Location**: Phase 1 Test Strategy — Black-box (`cli/launcher/tests/context.rs`)
  The end-to-end error behaviour (non-zero exit, empty stdout, stderr naming the
  file) is unverified; the `config.rs` harness covers exactly this for `config`.

- 🟡 **Test Coverage**: AC-10 (configure surface names the config-file bodies)
  has no automated test
  **Location**: Phase 2 Test Strategy and §2 (Configure-surface action)
  The only Phase 2 tests are line-presence and placement; the surface-action
  content (naming `.luminosity/config.md` / `config.local.md` as the source) is
  covered only under Manual Verification and can regress green.

- 🟡 **Standards**: The new `tests/unit/skills/` directory is not wired into any
  test roll-up, so the AC-enforcing registry test never runs in CI or `mise run`
  **Location**: Phase 2 §3 (`tests/unit/skills/test_context_injection.py`)
  Roll-ups are directory-scoped (`test:unit` depends only on
  `tasks`/`evals`/`cli`); nothing collects `tests/unit/skills/`, so the
  universal-injection test runs only via a manual `uv run pytest` and "done"
  (`mise run` exits 0) is green with it unexecuted.

- 🟡 **Usability**: The `allowed-tools` grant is a second hand-copied element
  with no enforcement and a silent runtime failure mode
  **Location**: Phase 2 §1 (`allowed-tools`) and §3 (registry wiring test)
  Wiring needs the `!`-line *and* a `Bash(...luminosity context)` grant; the
  registry test asserts only the line. Forgetting the grant blocks the
  preprocessor and silently injects nothing at runtime, per-user, with no CI
  failure — the worse failure mode is the unenforced one.

- 🟡 **Usability**: No discoverable convention or onboarding for future skill
  authors beyond a failing test
  **Location**: Implementation Approach and Phase 2 §3
  The story's stated goal is a reusable wiring convention for 0017/0018 and all
  future skills, yet the only artifact an author meets is a (currently never-run)
  registry test — no template SKILL.md, no CONTRIBUTING/CLAUDE.md note, no
  copy-paste snippet, and no specified failure message naming the exact line and
  placement.

- 🟡 **Usability**: The configure-surface "action" contradicts the skill's own
  "never edit the files yourself" premise and isn't executable by the agent
  **Location**: Phase 2 §2 (configure-surface action)
  `configure` opens with "you never read, parse, or write the configuration
  files yourself"; the new action is precisely "edit the body by hand." There is
  no `config set-body` affordance and the skill's `allowed-tools` grants no
  `Edit`/`Write`, so the named action is a human file-edit the agent is neither
  told how to do nor permitted to do.

- 🟡 **Architecture**: The deferred shared-partial decision and an
  under-specified placement anchor will be reopened immediately by 0017/0018
  **Location**: What We're NOT Doing; Phase 2 §3
  0016 owns "the shared injection/wiring mechanism and placement anchor" the
  siblings extend, but the plan hand-copies a single line enforced only by
  presence-before-first-`##`. That pins region but not *ordering* among the
  multiple injection lines 0017/0018 add, so the anchor is under-defined and the
  shared-partial question is postponed, not resolved.

- 🟡 **Standards / Code Quality**: The prescribed inline comment in
  `trim_blank_lines` violates the non-negotiable no-comments convention
  **Location**: Phase 1 §2 (`trim_blank_lines`)
  The `// strips leading/trailing whitespace-only lines...` comment restates the
  function name plus the adjacent contract; CLAUDE.md and the review-plan
  instructions both require removing such comments.

- 🟡 **Security**: The committed team config body is an unacknowledged cross-user
  prompt-injection channel
  **Location**: Overview; Phase 2
  The body of the *committed* `.luminosity/config.md` is injected verbatim near
  the top of every skill prompt for every team member. Anyone who can land a
  commit can steer the agent for all downstream users; the plan frames the body
  purely as a formatting concern and never names this trust boundary.

- 🟡 **Security**: The wrapper prose promotes injected content to instructions
  with no data/instruction delimiting
  **Location**: Phase 1 §4 (`render` / `PROSE`)
  "Take this into account when making decisions, selecting approaches, and
  generating output" elevates untrusted body text to instruction status, and the
  body is concatenated raw (no fence, no untrusted-input marker), so a hostile
  body can also forge `##` headings that shadow the skill's own sections. (See
  the Tradeoff Analysis — the wrapper itself is load-bearing for parity;
  mitigate on the skill side.)

#### Minor

- 🔵 **Correctness**: CRLF bodies — blank detection, trailing-`\r` stripping, and
  the LF-only join are unspecified
  **Location**: Phase 1 §2 (`trim_blank_lines`) and §3 (`read_body`)
  A naive `split('\n')`/`lines()` implementation leaves a stray `\r` or mixes
  line endings within one block; the "byte-for-byte interior preservation"
  contract rules out `str::lines()` and needs explicit CRLF handling.

- 🔵 **Test Coverage**: Whitespace-only (non-empty but blank) single body → `None`
  is not named as a distinct case
  **Location**: Phase 1 Test Strategy (config core); Phase 3 §1 (`context_empty`)
  Only "both-empty → None" is named; a body of purely blank/whitespace lines
  (vs the empty string) is exactly what could regress into a spurious block.

- 🔵 **Architecture**: `read_body` duplicates `read`'s file-access + `NotFound →
  Ok(None)` + `io_error` scaffolding
  **Location**: Phase 1 §3 (`ReadConfigBody` adapter on `FileConfigStore`)
  Only the final step differs; extract a private `read_raw(level)` seam both
  build on so absent-file/IO semantics live in one place. (Also raised by Code
  Quality.)

- 🔵 **Architecture**: The registry test re-implements platform skill discovery,
  risking divergence from what Claude Code actually loads
  **Location**: Phase 2 §3
  `plugin.json` registers *directories*; the test must re-derive `SKILL.md`
  discovery. Anchor it to the platform's discovery rule and fail loudly if a
  registered directory holds a `SKILL.md` the enumeration didn't reach.

- 🔵 **Architecture**: Two independent sources of truth for "the set of skills"
  (`plugin.json` vs the hardcoded `staging.py` path) will drift
  **Location**: What We're NOT Doing (`staging.py`); Phase 3
  Both resolve to one directory today; when a second skill dir is registered, the
  registry test would assert it while eval staging silently omits it.

- 🔵 **Correctness / Architecture / Code Quality**: The no-argument
  `assemble(&self)` port models only the plugin-global case and may not
  accommodate 0017's per-skill context without a signature change
  **Location**: Phase 1 §2 (`AssembleProjectContext`)
  Confirm against 0017 whether per-skill context extends this port or replaces
  it, and note the intended extension point.

- 🔵 **Code Quality**: The load-bearing `PROSE` constant is written in an
  error-prone escaped form
  **Location**: Phase 1 §4 (`PROSE`)
  Mixing backslash line-continuations with an explicit mid-string `\n` is
  human-verification-hostile for a byte-exact value; express it so the source
  reads the way the output looks.

- 🔵 **Code Quality**: `report`'s parameter is named `reporter` but typed as an
  assembler
  **Location**: Phase 1 §4 (`report` signature)
  Rename to `assembler` to match its `AssembleProjectContext` role and the
  codebase's name-for-role convention.

- 🔵 **Security**: No size bound on the injected body enables a cost /
  context-exhaustion vector on every skill invocation
  **Location**: Phase 1 §2 (`combine`/`trim`)
  A large committed team body inflates tokens/cost or crowds out context for
  every downstream invocation; consider a defensive cap.

- 🔵 **Usability**: Help text doesn't communicate the empty-output contract, and
  the top-level `context` verb sits apart from the `config` family
  **Location**: Phase 1 §5 (`Context` doc line); Overview (naming)
  State that empty output is expected when both bodies are empty/absent; reconfirm
  the `context` name against 0017's forthcoming per-skill context.

- 🔵 **Code Quality**: The hard-coded `is_root_help` built-in name list is
  extended with no coherence test
  **Location**: Phase 1 §5 (`is_root_help`)
  The list string-duplicates the `Command` variants with nothing tying them
  together; a future command can be added to `Command` and silently miss its
  `--help`.

#### Suggestions

- 🔵 **Usability**: The intentional silent no-op gives users no way to tell *why*
  context did not inject
  **Location**: Desired End State; Phase 1 §4
  Empty stdout is identical whether the body is empty, whitespace-only, or the
  config file wasn't discovered (wrong cwd). Consider a stderr `--explain`/
  `--verbose` diagnostic that reports discovered files and why output was empty.

- 🔵 **Test Coverage**: Only one of the two read-error paths is named
  **Location**: Phase 1 Test Strategy (config core)
  Cover both a team-read failure and a personal-read failure to pin the
  short-circuit ordering.

- 🔵 **Test Coverage**: The before-first-`##` placement assertion may pass
  vacuously for a skill with no `##` subsection
  **Location**: Phase 2 Test Strategy
  Also assert the line sits immediately under the H1 / after the frontmatter, so
  placement is pinned regardless of subsections.

- 🔵 **Code Quality**: Absence is encoded as `Option`, flattened to an empty
  string, then re-derived via `if !rendered.is_empty()`
  **Location**: Phase 1 §4 (`render`/`report`)
  Make `render(&ProjectContext)` total and match the `Option` directly in
  `report`, handling absence once.

- 🔵 **Architecture / Code Quality**: `dispatch` accumulates positional port
  parameters as commands are added
  **Location**: Phase 1 §5 (command wiring)
  Acceptable within the established generics-DI pattern; if the trend continues
  past 0018, group the built-in collaborators into a `Builtins` struct.

- 🔵 **Standards**: The configure-surface heading casing (`## Project context`)
  diverges from the load-bearing `## Project Context` header
  **Location**: Phase 2 §2
  Two near-identical headings render in the same prompt; give the documentation
  section a distinct title (e.g. `## Managing project context`).

### Strengths

- ✅ Faithful hexagon reuse: a driven `ReadConfigBody` port mirroring
  `ReadConfigLevel`, a pure `ProjectContextAssembler` unit-tested against a fake,
  and the load-bearing block isolated in a single `render() -> String` with one
  `println!` at the edge — matching the proven `version`/`config` shape.
- ✅ Minimal blast radius: the already-tested `frontmatter::split` is composed
  in-crate with no visibility change and no new parser; absent/empty files stay a
  no-op via the existing `NotFound → Ok(None)` handling.
- ✅ Correctly models context assembly as a *distinct* domain operation
  (team-then-personal concatenation) rather than overloading `ConfigService::get`'s
  personal-over-team resolution, with domain-aligned naming throughout.
- ✅ Genuinely test-first: every phase carries a "Test Strategy (write first)"
  section ordering red-before-green, the load-bearing header/prose is guarded by
  byte-exact literal assertions at three layers, and the noisy behavioural arm is
  correctly gated behind `LUMINOSITY_EVAL_LIVE` out of the deterministic CI path.
- ✅ Correctly navigates the hand-synced seams the research flagged: rightly
  concludes no `pup.ron` block is needed (the new core lives in the pure `config`
  crate, not a launcher core), and rightly identifies the `is_root_help`,
  `lib.rs`, and staging scoping.
- ✅ Three independently-green, mergeable increments with an explicit,
  justified dependency order.
- ✅ The `allowed-tools` grant is an exact (wildcard-free) match — tighter
  least-privilege than the existing `config *` scope; and `luminosity context`
  doubles as a user-facing preview/inspection tool for an otherwise invisible
  mechanism.

### Recommended Changes

1. **Design and test malformed-config degradation on the injection path**
   (addresses: the malformed-config cross-cutting theme — Architecture /
   Usability / Test Coverage majors). Decide the reader's behaviour when a
   present config body cannot be split *given it now runs in every skill load*:
   either emit nothing to stdout (with a stderr diagnostic) so skills still load,
   or explicitly document that the `!`-preprocessor tolerates a non-zero exit.
   Add a black-box case in `context.rs` (mirroring `config.rs`) and, if the
   emit-nothing route is chosen, a config-core/adapter test pinning it.

2. **Pin the trim contract to the byte level and reconcile it with the sketch**
   (addresses: both Correctness majors + the CRLF Test-Coverage major + the CRLF
   minor). Rewrite the trim contract to (a) state the returned value ends at the
   last non-blank content byte with no trailing terminator; (b) describe
   *per-part* trim → drop empties → join with a single `\n\n` (matching the
   sketch), removing the "trims the combined result" phrasing; (c) specify CRLF
   handling (blank-detect `\r`-only lines, strip trailing `\r\n`, and whether the
   block normalises to LF or preserves CRLF). Add a CRLF config-core case, a
   whitespace-only-single-body → `None` case, and an integration assertion that
   output ends in exactly one `\n`.

3. **Make the registry test actually run, and enforce both halves of the wiring**
   (addresses: Standards "never runs in CI" major + Usability `allowed-tools`
   major + the placement-vacuity suggestion). Add a `test:unit:skills` roll-up
   (mirroring `test:unit:evals`) wired into `test:unit`'s `depends` (or relocate
   the test under a collected tree), and update Phase 2's automated-verification
   list to run it via that roll-up. Extend the test to also assert each wired
   SKILL.md's `allowed-tools` includes the `context` grant, and to assert the
   line sits directly under the H1 (not merely before the first `##`).

4. **Cover AC-10 with an automated assertion** (addresses: Test Coverage AC-10
   major). Assert in the skills unit test that `configure/SKILL.md`'s body
   contains the project-context action section and references both
   `.luminosity/config.md` and `config.local.md` bodies as the source.

5. **Reconcile the configure surface with the skill's "never edit files" premise**
   (addresses: Usability configure-surface major + Standards heading-casing
   suggestion). Frame the body-editing step explicitly as a *human* action
   distinct from the CLI-mediated `get`/`set` flow (the agent points the user at
   the body rather than editing it), adjust the "never edit the files" wording so
   it doesn't read as forbidding the named action, and give the section a
   distinct heading (e.g. `## Managing project context`).

6. **Record the prompt-injection trust boundary and harden on the skill side**
   (addresses: both Security majors + the near-top-placement and size-bound
   minors; see Tradeoff Analysis). Add a threat note to the plan naming the
   committed team body as attacker-controllable input. Keep the load-bearing
   wrapper for accelerator parity, but re-assert the skill's binding constraints
   *after* the injected block so trusted prose keeps the last word, and consider
   a defensive size cap on the assembled body.

7. **Resolve the shared-anchor question for the whole 0016/0017/0018 arc**
   (addresses: Architecture shared-partial major + registry-discovery,
   two-sources-of-truth, and port-shape minors + the onboarding major). Either
   define an explicit, ordered injection region the registry test enforces
   positionally (so 0017/0018 slot in deterministically) or record why per-skill
   hand-copying with a presence-only test is the deliberate choice for all three
   stories. Confirm the `assemble()` port's extension point against 0017, and add
   a discoverable convention artifact (a note + copy-paste snippet or starter
   template) so future authors aren't reverse-engineering a test.

8. **Apply the small code-quality/standards fixes** (addresses: the no-comments
   major, and the `PROSE`, `reporter`-naming, `read_body`-duplication,
   `Option`-flattening, `is_root_help`-coherence, and `dispatch`-signature
   items). Drop the `trim_blank_lines` inline comment; write `PROSE` so the
   source reads as the output looks; rename `reporter` → `assembler`; extract a
   shared `read_raw` seam; make `render` total over `&ProjectContext`.

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: The plan is architecturally well-grounded: it extends the
established config hexagon (a driven `ReadConfigBody` port, a pure
`ProjectContextAssembler` domain service tested against a fake, and a byte-exact
`render()` in a thin launcher inbound), giving a clean functional-core/
imperative-shell split with minimal blast radius by reusing the already-tested
`frontmatter::split` in-crate. The two areas that warrant scrutiny are
evolutionary fitness — 0016 is explicitly the shared mechanism/anchor for
siblings 0017/0018, yet it defers the shared-partial decision to hand-copied
per-skill lines and leaves the intra-anchor ordering unspecified — and
resilience: passive load-time injection into every skill inherits the config
path's fail-loud policy, so one malformed config body degrades context injection
across all skills.

**Strengths**:
- Clean functional-core/imperative-shell separation: concat/trim/emptiness is
  pure domain logic in the `config` crate (fake-driven), the byte-exact block is
  a single pure inbound `render()` with one `println!`.
- Minimal blast radius by reuse: `frontmatter::split` composed in-crate with no
  visibility change and no new parser; absent/empty stays a no-op.
- Domain-aligned naming; correctly models assembly as a distinct operation vs
  `ConfigService::get`.
- The "every skill" invariant enforced structurally by a registry test; three
  independently-green, mergeable increments.

**Findings**:
- 🟡 (major, medium) *Passive load-time injection inherits fail-loud policy,
  making one malformed config body an all-skills failure* — Phase 1 §3/§4; the
  reader now runs at skill-load in every skill, and the plan doesn't specify how
  the preprocessor handles a non-zero exit. Suggest an explicit degradation
  strategy plus a black-box test.
- 🟡 (major, medium) *Deferred shared-partial mechanism and an under-specified
  placement anchor will be reopened immediately by 0017/0018* — the anchor pins
  region but not ordering among multiple injection lines the siblings add.
- 🔵 (minor, medium) *The no-argument `assemble()` port may not accommodate
  0017's per-skill context without a signature change.*
- 🔵 (minor, medium) *Registry test re-implements platform skill discovery,
  risking divergence from what Claude Code actually loads.*
- 🔵 (minor, high) *`read_body` duplicates `read`'s file-access scaffolding
  instead of sharing a raw-read seam.*
- 🔵 (minor, medium) *Two independent sources of truth for "the set of skills"
  (`plugin.json` vs hardcoded staging path) will drift.*
- 🔵 (suggestion, low) *Dispatch is becoming a wide composition seam as each
  built-in adds a port parameter; consider a `Builtins` struct past 0018.*

### Code Quality

**Summary**: The plan applies the codebase's established hexagonal shape
faithfully, giving a highly testable design with a pure fake-driven assembler
and byte-exact `render`. The maintainability concerns are localised and minor:
one code sketch carries a redundant explanatory comment that violates the repo's
no-comment rule, a load-bearing prose constant is written in an error-prone
escaped form, an inbound parameter is misnamed against its domain role, and a few
small duplication/parameter-growth smells are perpetuated rather than addressed.

**Strengths**:
- The core/assembler split (`combine` + `trim_blank_lines` as pure free
  functions, fake-driven) is excellent for testability.
- Modelling "nothing to inject" as `Option<ProjectContext>` expresses absence in
  the domain type.
- The hexagon mirrors the existing `config` command precisely — no novel
  abstractions to learn.
- Phasing into independent, green, mergeable increments with a test-first
  strategy per phase.

**Findings**:
- 🔵 (minor, high) *Explanatory comment inside `trim_blank_lines` restates the
  code's intent* — violates CLAUDE.md's last-resort-comments rule; drop it.
- 🔵 (minor, medium) *Load-bearing `PROSE` constant written in an error-prone
  escaped form* — express it so the source reads as the output looks.
- 🔵 (minor, high) *`report` parameter named `reporter` but typed as an
  assembler* — rename to `assembler`.
- 🔵 (suggestion, medium) *Absence encoded as `Option`, flattened to empty
  string, then re-derived* — make `render(&ProjectContext)` total, match the
  `Option` in `report`.
- 🔵 (suggestion, medium) *`dispatch` accumulates positional port parameters* —
  consider a `Ports`/`Dependencies` struct before 0017 compounds it.
- 🔵 (suggestion, medium) *`read_body` duplicates the read-or-`None` skeleton of
  `read`* — extract a private `read_raw`.
- 🔵 (minor, low) *Hard-coded `is_root_help` built-in name list extended with no
  coherence test* — consider deriving names from the `Command` tree or a test.

### Test Coverage

**Summary**: The plan is genuinely test-first: every phase carries a "Test
Strategy (write first)" section, assertions are byte-exact where the header/prose
is load-bearing, and it reuses the already-tested `frontmatter::split` rather than
re-proving it. Most acceptance criteria map cleanly to a named test at the right
pyramid level. However, two acceptance criteria lack a named automated test (the
configure-surface action, AC-10) and the new `combine`/`trim` logic is not
exercised against CRLF or whitespace-only-single-body inputs, and no black-box
test covers the malformed-frontmatter error path for `context`.

**Strengths**:
- Every phase explicitly labelled "Test Strategy (write first)", ordering
  red-before-green.
- Load-bearing header/prose guarded by byte-exact literal assertions at the
  inbound, black-box, and eval layers (good mutation coverage).
- Good pyramid balance; the noisy behavioural arm gated behind
  `LUMINOSITY_EVAL_LIVE`.
- Reuses the fully-tested `frontmatter::split` rather than duplicating its
  coverage.

**Findings**:
- 🔴 (major, high) *AC-10 (configure surface names the config-file bodies) has no
  automated test* — covered only under Manual Verification; add a Python
  assertion.
- 🟡 (major, medium) *New combine/trim logic is untested against CRLF bodies* —
  add a CRLF config-core case asserting exact emitted bytes.
- 🟡 (major, medium) *No black-box test for the malformed-frontmatter error path
  of `luminosity context`* — mirror `config.rs`'s malformed-file test.
- 🔵 (minor, medium) *Whitespace-only single body → `None` not named as a distinct
  case.*
- 🔵 (suggestion, medium) *Only one of the two read-error paths is named* — cover
  team-error and personal-error branches.
- 🔵 (suggestion, low) *Placement assertion may pass vacuously for a skill with no
  `##` subsection* — also assert immediately-under-H1.

### Correctness

**Summary**: The plan's data flow (read_body → unwrap_or_default → per-part trim
→ filter → join → render → println) is largely sound and correctly collapses the
both-empty and both-absent cases into a single no-output path. However, the
correctness of the byte-exact output hinges almost entirely on the un-sketched
`trim_blank_lines`, and its stated contract does not pin down the two load-bearing
details that actually determine the result: whether the body's own trailing
newline is stripped and how CRLF bodies are handled. There is also a substantive
mismatch between the prose contract ("trim the combined result") and the sketch
(trim each part, then join).

**Strengths**:
- both-empty vs both-absent unified correctly (`Ok(None)` and `Ok(Some(""))` both
  collapse to `""` via `unwrap_or_default`).
- Whitespace-only body correctly treated as empty and filtered out — no stray
  block or dangling separator.
- Filtering empty parts before the join yields exactly one body with no trailing
  separator for the single-sided cases.
- Read errors propagate fail-loud via `?`, matching convention.
- The `PROSE` constant reproduces the two prose lines byte-for-byte.

**Findings**:
- 🔴 (major, high) *Body's trailing newline must be stripped or the block gains a
  trailing blank line* — `split` returns bodies with `\n`; `render` + `println!`
  add one more, so a naive trim yields `...body\n\n`. State the no-trailing-
  terminator contract and assert output ends in exactly one `\n`.
- 🟡 (major, medium) *Prose says "trim the combined result"; sketch trims each
  part — not equivalent* — the sketch is correct; rewrite the contract to match
  it and remove the combined-result phrasing.
- 🔵 (minor, medium) *CRLF bodies: blank detection, trailing-`\r` stripping, and
  LF-only join are unspecified* — specify CRLF handling and add a CRLF case;
  `str::lines()` silently drops `\r` and can't satisfy byte-for-byte preservation.

### Security

**Summary**: The plan introduces a genuine trust boundary it never names: the
free-form body of the committed team file `.luminosity/config.md` is read verbatim
and injected, near the top, into every skill prompt for every team member who
invokes any skill — a classic cross-user / supply-chain prompt-injection channel.
The plan treats the body purely as a formatting problem with no data/instruction
separation or untrusted-content framing. The `allowed-tools` scoping is a real
mitigating control, but it only gates the reader command itself, not the injected
text once it is in context.

**Strengths**:
- The added `allowed-tools` entry is an exact-match with no wildcard — tighter
  least-privilege than the existing `config *` scope.
- Reading/parsing stay in the CLI; the injected material is data on stdout, not
  re-executed — no shell/command-injection surface.
- The reader emitting nothing by default means the channel is dormant until
  explicit config content activates it.

**Findings**:
- 🔴 (major, high) *Committed team config body is an unacknowledged cross-user
  prompt-injection channel* — document the trust model and treat the output as
  untrusted data.
- 🟡 (major, high) *Wrapper prose promotes injected content to instructions with
  no data/instruction delimiting* — reframe as reference data and delimit;
  hostile bodies can forge `##` headings. (Tradeoff: the wrapper is load-bearing
  for parity — mitigate on the skill side.)
- 🔵 (minor, medium) *Load-bearing near-top placement puts untrusted content ahead
  of the skill's own safety instructions* — re-assert the skill's rules after the
  block.
- 🔵 (minor, medium) *No size bound on injected body enables a cost/
  context-exhaustion attack on every skill invocation* — add a defensive cap.

### Standards

**Summary**: The plan faithfully follows the established config-hexagon
conventions and correctly navigates most hand-synced seams — it is right that no
`pup.ron` block is needed (the new core lives in the pure `config` crate, not a
launcher-crate core), right that `is_root_help` and `lib.rs` must be updated, and
right that `staging.py` needs no change. Two convention issues stand out: the
Phase 2 registry test is placed in a `tests/unit/skills/` tree that no `mise`
test roll-up collects, so it would never run in CI or the `mise run` default; and
the illustrative `trim_blank_lines` carries a descriptive inline comment that
violates the project's no-comments rule.

**Strengths**:
- Correctly resolves the pup.ron seam: the pure `config` crate needs no block
  (matching `service.rs`/`node.rs`); the research's "new core module needs a pup
  block" rule applies only to launcher cores.
- Correctly identifies the `is_root_help` and `lib.rs` updates and the staging
  scoping.
- Mirrors established patterns faithfully (`ReadConfigBody` alongside
  `ReadConfigLevel`, in-crate `frontmatter::split` reuse, pure `render()` +
  single `println!`, `context.rs` black-box harness).
- `allowed-tools` extension correctly scoped and formatted (exact match).
- Acknowledges the Python test conventions (no `__init__.py`, fully annotated,
  ruff ALL + pyrefly strict).

**Findings**:
- 🟡 (major, high) *New test directory not wired into any test roll-up, so it
  never runs in CI or `mise run`* — add a `test:unit:skills` leaf wired into
  `test:unit` (or relocate the test) and update Phase 2's verification list.
- 🟡 (major, high) *Prescribed inline comment violates the non-negotiable
  no-comments convention* — drop the `trim_blank_lines` comment; use a `///`
  contract doc if anything must be recorded.
- 🔵 (suggestion, medium) *Configure-surface heading casing (`## Project context`)
  diverges from the load-bearing `## Project Context` header* — give the doc
  section a distinct title.

### Usability

**Summary**: The plan gives the plugin-global context feature a clean core: a
single `luminosity context` reader that doubles as a preview tool, byte-exact
rendering, and a deliberate silent-empty contract. But the developer-facing
surface has real ergonomic gaps: the injection wiring depends on two hand-copied
elements (the `!`-preprocessor line and a matching `allowed-tools` grant) of which
only one is enforced, there is no discoverable convention or template to onboard
future skill authors, and the intentional silent no-op leaves users with no way to
tell why context did or didn't inject. The configure-surface "action" also
collides with that skill's own "never edit the files yourself" premise.

**Strengths**:
- `luminosity context` doubles as a preview/inspection tool — a concrete feedback
  loop for an otherwise invisible mechanism.
- The render/domain split keeps the emitted block byte-exact and predictable,
  pinned by black-box literal assertions.
- Expanding `configure` to describe the capability improves discoverability.
- The registry test provides a CI backstop against a dropped injection line.

**Findings**:
- 🟡 (major, high) *The `allowed-tools` grant is a second hand-copied element with
  no enforcement and silent runtime failure* — extend the registry test to assert
  the grant.
- 🟡 (major, medium) *No discoverable convention or onboarding for future skill
  authors beyond a failing test* — add a template/note/snippet and a naming
  failure message.
- 🟡 (major, medium) *The intentional silent no-op gives users no way to tell why
  context did not inject* — add a stderr `--explain`/`--verbose` diagnostic.
- 🟡 (major, medium) *The configure-surface "action" contradicts the skill's own
  "never edit the files yourself" premise and isn't executable by the agent* —
  frame body-editing as a human action distinct from `get`/`set`.
- 🟡 (major, medium) *Malformed-config error behaviour under the preprocessor is
  unspecified, with blast radius across every skill* — design graceful
  degradation and add a test.
- 🔵 (minor, medium) *Help text doesn't communicate the empty-output contract, and
  the top-level `context` verb sits apart from the `config` family* — enrich the
  help text; reconfirm the name against 0017.

## Re-Review (Pass 2) — 2026-07-11T21:28:14+00:00

**Verdict:** COMMENT

The author's edits cleanly address the prior review. Of the ~14 majors from pass 1,
every one is resolved or consciously accepted: the trim contract is now byte-precise
and reconciled with its sketch, CRLF is fully specified, the `test:unit:skills`
roll-up (with a mise-wiring coherence assertion) closes the never-ran-in-CI gap, the
registry test enforces both wiring halves and non-vacuous placement, AC-10 has an
automated test, the configure surface is reframed as a user body-edit under a distinct
heading, malformed-config is a specified-and-tested fail-loud path, `--explain` gives
the silent no-op a diagnostic, and the security trust boundary is now an explicit
accepted tradeoff. All of Correctness, Test Coverage, and Standards' prior findings
are fully resolved. The verdict moves REVISE → COMMENT: the plan is acceptable to
implement. One new **major** remains (the fail-loud/`!`-preprocessor blast-radius UX
is unspecified), plus a cluster of low-severity items the `--explain` addition
introduced.

### Previously Identified Issues

- 🟡 **Architecture**: Malformed config breaks the injection path across every skill —
  **Resolved** (specified as fail-loud, tested; author's deliberate choice).
- 🟡 **Architecture**: Deferred shared-partial / under-specified anchor — **Resolved**
  (documented as intentional for the 0016/0017/0018 arc; extension point named).
- 🔵 **Architecture**: `assemble()` port may not fit 0017 — **Resolved** (extension
  point recorded).
- 🔵 **Architecture**: Registry test re-implements platform discovery — **Partially
  resolved** (unreached-`SKILL.md` guard added; still encodes its own walk).
- 🔵 **Architecture**: `read_body` duplicates `read` scaffolding — **Resolved**
  (`read_raw` extraction).
- 🔵 **Architecture**: Two sources of truth (`plugin.json` vs `staging.py`) —
  **Partially resolved / still present** (no coherence check; inert until a 2nd skill
  dir lands).
- 🔵 **Architecture / Code Quality**: `dispatch` widening seam — **Still present**
  (suggestion; deferred by design).
- 🔵 **Code Quality**: `trim_blank_lines` comment — **Resolved** (removed; contract is
  plan prose).
- 🔵 **Code Quality**: `PROSE` escaped form — **Resolved** (readable multi-line literal).
- 🔵 **Code Quality**: `reporter` misnamed — **Resolved** (`assembler`).
- 🔵 **Code Quality**: `Option` flattened to empty string — **Resolved** (`render`
  total, absence handled once).
- 🔵 **Code Quality**: `is_root_help` no coherence test — **Still present** (minor).
- 🔴 **Test Coverage**: AC-10 untested — **Resolved**.
- 🟡 **Test Coverage**: CRLF untested — **Resolved**.
- 🟡 **Test Coverage**: malformed error path untested — **Resolved**.
- 🔵 **Test Coverage**: whitespace-only case unnamed — **Resolved**.
- 🔵 **Test Coverage**: one read-error path / vacuous placement — **Resolved**.
- 🔴 **Correctness**: trailing-newline — **Resolved** (contract guarantees one trailing
  `\n`).
- 🟡 **Correctness**: trim-combined vs trim-each-part — **Resolved** (prose matches
  sketch).
- 🔵 **Correctness**: CRLF unspecified — **Resolved** (mixed LF-separator/CRLF-interior
  documented as intended).
- 🔴🟡 **Security**: both prompt-injection majors + placement/size minors —
  **Acknowledged-accepted** (documented trust boundary; team-vetting owns it).
- 🟡 **Standards**: skills test never runs in CI — **Resolved** (`test:unit:skills`
  leaf + coherence test).
- 🟡 **Standards**: no-comments violation — **Resolved**.
- 🔵 **Standards**: heading casing — **Resolved** (`## Managing project context`).
- 🟡 **Usability**: `allowed-tools` unenforced — **Resolved** (asserted by registry
  test).
- 🟡 **Usability**: no onboarding path — **Partially resolved** (reactive test only; no
  proactive convention note/template).
- 🟡 **Usability**: silent no-op undiagnosable — **Resolved** (`--explain`).
- 🟡 **Usability**: configure-surface contradiction — **Resolved** (reframed as human
  action).
- 🟡 **Usability**: malformed behaviour unspecified — **Resolved** (fail-loud specified).
- 🔵 **Usability**: help text / naming — **Partially resolved** (empty-output contract
  in help; top-level `context` naming unchanged).

### New Issues Introduced

- 🟡 **Usability** (major, medium): *Fail-loud at the `!`-preprocessor boundary has an
  unspecified failure UX with a wide blast radius.* The reader runs at skill-load in
  every skill; a single malformed committed team config breaks every skill's load for
  every user, and the plan specifies the CLI's behaviour (non-zero exit, filename on
  stderr) but not what the user actually sees at the preprocessor boundary — whether
  Claude Code surfaces the named-file stderr actionably or fails opaquely. `--explain`
  doesn't help (it also propagates the error). Recommend adding a Phase 2
  manual-verification step for the malformed-committed-config case so the blast-radius
  UX is proven, not assumed. (Note: the `!`-preprocessor's non-zero-exit behaviour is
  greenfield in this repo — this is partly a platform unknown to pin down.)
- 🔵 **Code Quality** (suggestion): *`has_body` risks a second definition of "empty".*
  `explain`'s `has_body` must use the same `trim_blank_lines(...).is_empty()` predicate
  as `combine`, or the diagnostic can contradict the actual output.
- 🔵 **Architecture / Code Quality** (suggestion): *`--explain` pushes a diagnostic
  concern into the pure domain core.* Adding `explain()` + `ContextDiagnostics` to the
  `AssembleProjectContext` port mixes assembly with observability and causes a
  double-read (assemble then explain). Consider deriving the diagnostic in the launcher
  shell directly from the `ReadConfigBody` port instead.
- 🔵 **Code Quality** (suggestion): *`Level → filename` becomes a third hand-copied
  instance* for the `--explain` line; expose it via `Level` (or carry it on
  `LevelDiagnostic`) as a single source.
- 🔵 **Correctness** (minor, low): *`--explain` emits no per-level diagnostic on a
  malformed body* — `report_explain` calls `report(...)?` first, so the error
  short-circuits before `explain()`. Likely acceptable (the filename is on stderr);
  confirm intent.
- 🔵 **Standards** (suggestion): *`test:unit:skills` must follow the leaf convention* —
  wrap an invoke task with `depends = ["deps:install:python"]`, and update
  `test_mise_wiring.py`'s pinned `test:unit` depends array (not merely add an assertion).
- 🔵 **Standards** (suggestion): *Phase 3's eval `expected_block` is a new hand-synced
  golden* that duplicates `render`'s header/prose; acknowledge the seam or derive it
  from a shared constant.
- 🔵 **Test Coverage** (suggestion): add a both-present-but-one-whitespace unit case and
  pin the `--explain` absent-vs-present-empty stderr distinction in the black-box tier.
- 🔵 **Usability** (suggestion): link `--explain` from the `## Managing project context`
  surface so users have a signpost to verify their edit.

### Assessment

The plan is in good shape and ready to implement. The verdict is COMMENT, not APPROVE,
only because one new major (the fail-loud preprocessor-boundary UX) and a coherent
cluster of `--explain`-related low-severity items are worth a light touch before or
during implementation. The single highest-value follow-up is deciding where the
`--explain` diagnostic lives: moving its derivation into the launcher shell (off the
domain port) would simultaneously retire the domain-pollution, double-read, port-mixing,
and `has_body`-consistency items. None of these block implementation; they are polish on
an otherwise sound plan.

---
*Re-review generated by /accelerator:review-plan*

## Re-Review (Pass 3) — 2026-07-11T23:11:56+00:00

**Verdict:** COMMENT

The second round of edits — the `--explain` consolidation (single-pass `assemble()`
returning `Assembly { context, levels }`; no separate domain `explain()` method or
double read; `has_body` bound to `combine`'s own `trim_blank_lines` predicate;
`Level::filename()` single-source; formatting in the shell's `explain_lines`) plus
the malformed-preprocessor manual-verification step, the `--explain` link from the
configure surface, the `test:unit:skills` invoke-wrapping/pinned-array specifics, and
the eval-golden seam note — resolve the four `--explain` cluster items and both
Standards items from pass 2. Six lenses re-ran (Security skipped: accepted, trust
model unchanged). Verdict holds at COMMENT: the plan is implementation-ready. One
pass-2 major persists (partially de-risked), and the refactor introduced a short tail
of low-severity items — the expected diminishing returns.

### Previously Identified Issues (pass-2 items)

- 🔵 **Architecture**: `--explain` pushed a diagnostic into the pure core —
  **Resolved** (single-pass `Assembly`; formatting in the shell).
- 🔵 **Architecture**: `dispatch` widening — **Still present** (deferred by design).
- 🔵 **Architecture**: `plugin.json` vs `staging.py` drift — **Still present** (inert
  until a 2nd skill dir).
- 🔵 **Architecture**: registry test re-implements discovery — **Partially resolved**
  (fail-loud guard added).
- 🔵 **Architecture**: `read_raw` returning `Split` / possible double-parse — **Still
  present** (the `document` re-split seam is still implicit; see New below).
- 🔵 **Code Quality**: `has_body` second definition of "empty" — **Resolved** (shared
  `trim_blank_lines`).
- 🔵 **Code Quality**: `Level → filename` third copy — **Resolved** (`Level::filename()`).
- 🔵 **Code Quality**: `assemble`+`explain` port mixing — **Resolved** (one method).
- 🔵 **Code Quality**: `dispatch` positional / `is_root_help` coherence — **Still
  present** (deferred).
- 🔵 **Correctness**: `--explain` malformed short-circuit + double read — **Resolved**
  (one pass; malformed documented as intended).
- 🔵 **Test Coverage**: both-present-one-whitespace unit case — **Resolved**.
- 🔵 **Test Coverage**: black-box `--explain` absent-vs-present-empty — **Resolved**.
- 🔵 **Standards**: `test:unit:skills` invoke-wrapping + pinned array — **Resolved**.
- 🔵 **Standards**: eval `expected_block` golden seam — **Partially resolved**
  (acknowledged; not yet guarded by a coherence assertion like the repo's other
  mirrors — see New).
- 🟡 **Usability**: fail-loud `!`-preprocessor blast-radius UX — **Partially resolved**
  (manual-verification step added; still a partial platform unknown with no
  pre-decided contingency — see New).
- 🔵 **Usability**: `--explain` not linked from the surface — **Resolved**.
- 🔵 **Usability**: onboarding / `context` naming — **Still present** (deferred).

### New Issues Introduced

- 🟡 **Usability** (major, medium): *No pre-decided contingency if the malformed-config
  manual verification reveals opaque preprocessor UX.* The step probes what the user
  sees, but the plan doesn't say what to do if the `!`-preprocessor surfaces the
  non-zero exit opaquely (given the blast radius is every skill for every user).
  Recommend recording a fallback in advance — fail-loud-per-skill vs degrade-to-empty
  with the error routed to `--explain` — so the outcome has a path forward, not just a
  discovery.
- 🔵 **Architecture** (minor, medium): *`Level::filename()` pushes a storage concern
  into the pure domain core.* The `.md` on-disk name is an adapter representation
  detail; consider keeping the literals in `FileConfigStore` and carrying the filename
  on `LevelContribution` (or having the launcher get it from the adapter) so the core
  stays persistence-agnostic. (Trades against the Code-Quality/Standards preference for
  the single-source `Level` method — a genuine layering-vs-DRY judgment call.)
- 🔵 **Architecture** (minor, medium): *`read_raw` re-split seam still implicit* — the
  plan should name a `document::parse_frontmatter(&str)` (split-free) entry point so
  `read`/`read_body` split once; otherwise `store.rs` risks a double-split or a wider
  `Split` coupling.
- 🔵 **Standards** (suggestion): *`Level::filename()` naming* departs from the crate's
  underscore-compound convention (`level_path`, `config_dir`, `std::path::file_name`);
  prefer `file_name()`.
- 🔵 **Standards** (suggestion): *eval golden not guarded* — single-source the
  header/prose or add a coherence assertion pinning the eval `expected_block` to the
  same literal the Rust unit test asserts.
- 🔵 **Code Quality** (suggestion): *block-print duplicated* across `report` /
  `report_explain` (extract a tiny `print_block` helper); *`Assembly.levels` as an
  unbounded `Vec`* weakens the exactly-two-levels invariant (consider `[_; 2]`).
- 🔵 **Correctness / Test Coverage** (suggestion): make the *team-then-personal
  ordering* of `Assembly.levels` an explicit asserted invariant; add a 2-CRLF-body
  join test; add a direct `Level::filename()` unit test and enumerate the three
  `LevelContribution` shapes in the `explain_lines` unit test.
- 🔵 **Usability** (minor, low): clarify whether `context --explain` verification is a
  user shell action or agent-assisted; if agent-assisted, the exact wildcard-free
  `allowed-tools` grant would block `--explain` (widen to `... context*`).

*(The summary Testing Strategy's stale `explain()` reference the re-review flagged was
corrected in the plan.)*

### Post-Pass-3 Edits Applied

After pass 3, a final batch of the cheap items was folded into the plan (no fourth
full review run — these are direct applications of the findings above):

- **Malformed-config contingency** recorded in the fail-loud paragraph — if the
  manual verification finds the `!`-preprocessor renders the non-zero exit opaquely,
  the fallback is to stay fail-loud and lean on the direct `luminosity context`
  command (surfaced from the configure surface) as the diagnosis, **not** degrade to
  empty. This closes the lone remaining major.
- **`Level::filename()` → `Level::file_name()`** to match the crate's
  underscore-compound idiom (`level_path`/`config_dir`, `std::path::file_name`), plus
  a direct `level.rs` unit test pinning both filenames.
- **Eval golden guarded** — `expected_block` is built from a single Python
  header/prose snippet and pinned by a coherence assertion against the same literal
  the Rust byte-exact `render` test asserts, so a prose drift fails a Python test.
- **`Assembly.levels`** changed to a fixed `[LevelContribution; 2]` with an explicit,
  asserted team-then-personal ordering invariant; added a two-CRLF-body join test and
  an `explain_lines` three-shape enumeration.

Remaining open items are all deliberately deferred tradeoffs (the `dispatch` struct,
`is_root_help` coherence, the `read_raw`/`document::parse_frontmatter` seam, the
`staging.py` drift, the onboarding note, `context` naming, the `Level::file_name()`
layering-vs-DRY call, and the `context` `allowed-tools` user-vs-agent clarification) —
appropriate to settle at implementation time. Review loop closed at COMMENT.

### Final Verdict — APPROVE (2026-07-11T23:22:55+00:00)

Approved by Toby Clemson. The one remaining major from pass 3 was addressed by the
post-pass-3 malformed-config contingency edit, and every other open item is a
consciously deferred, implementation-time tradeoff. The plan is accepted for
implementation; its status is set to `ready`.

The plan is implementation-ready and the review has converged: pass 1 REVISE → pass 2
COMMENT → pass 3 COMMENT, with each round resolving the prior round's substance and
leaving a shorter, lower-severity tail. The single lingering major is inherently a
partial platform unknown (the `!`-preprocessor's non-zero-exit behaviour, exercised
here for the first time) best closed at implementation by the manual verification plus
a one-line pre-decided contingency. Everything else is suggestion-tier polish or
consciously deferred tradeoffs (`dispatch` struct, `is_root_help` coherence, the
`staging.py`/onboarding/`context`-naming items). Recommend stopping the review loop and
proceeding to implementation, folding the cheap items (naming, the golden coherence
guard, the `levels` ordering/arity, and the malformed contingency line) opportunistically.

---
*Re-review generated by /accelerator:review-plan*
