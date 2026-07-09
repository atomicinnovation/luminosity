---
type: plan-review
id: "2026-07-07-0010-apply-eval-framework-to-configure-skill-review-1"
title: "Plan Review: Apply the Eval Framework to the configure Skill"
date: "2026-07-07T00:21:50+00:00"
author: "Toby Clemson"
producer: review-plan
status: complete
parent: "plan:2026-07-07-0010-apply-eval-framework-to-configure-skill"
target: "plan:2026-07-07-0010-apply-eval-framework-to-configure-skill"
reviewer: "Toby Clemson"
verdict: "APPROVE"
lenses: [architecture, code-quality, test-coverage, correctness, compatibility, portability, standards]
review_number: 1
review_pass: 5
tags: [plan-review, evaluation, inspect, configure, skills]
last_updated: "2026-07-07T11:18:32+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

## Plan Review: Apply the Eval Framework to the configure Skill

**Verdict:** REVISE

This is a well-researched, convention-aware plan: the functional-core/imperative-shell
split (a pure pass^k gate and pure scorer branches), the structural CI-exclusion,
the exact-pin discipline, and — most notably — the deliberate reconciliation of the
non-existent Inspect `pass_k` against a self-documenting custom `all_correct` reducer
all reflect real rigour. The blocking issues are concentrated where the plan meets the
outside world: a **critical** host-build/Docker-architecture mismatch that makes the
live run impossible on a macOS dev host, a large surface of **unverified pre-1.0 /
external-version assumptions** that no unit test exercises (all deferred to a single
Phase 3 live run), and an **under-specified grading oracle** whose determinism claim
rests on data sources the plan never pins (what `actual` is for a get task, the
precedence blind spot, cross-epoch sandbox state). None are fatal to the approach —
Inspect is still the right tool — but they should be resolved in the plan before
implementation begins.

### Cross-Cutting Themes

- **Unverified pre-1.0 / external-version surface** (flagged by: Compatibility,
  Correctness, Test Coverage, Architecture) — The eval's real integration points —
  `claude_code()` kwargs (`skills=`, `disallowed_tools=`), the Inspect log/reducer/metric
  read-back shape, the `Skill` tool-call transcript structure, the Anthropic model
  version, the Claude Code CLI version, and Python 3.14 support for both packages — are
  all assumed but never verified against the versions actually being pinned. Because the
  unit tests feed *synthetic* pass_k values and pure helpers, none of these surfaces are
  exercised until the one-shot Phase 3 live run. This is the plan's dominant risk.
- **The Docker / host-build boundary** (flagged by: Portability, Architecture) — The
  critical binary-architecture mismatch, the unprovisioned Docker daemon, the unpinned
  base image/arch, and the ambiguous binary-staging path all cluster here. The live tier
  has a hard, undocumented runtime coupling that is invisible until it breaks.
- **Grading-oracle under-specification** (flagged by: Correctness, Test Coverage) — The
  scorer's determinism claim is undercut in several places: for get tasks `actual` is the
  agent's conversational completion (not raw CLI stdout); the precedence task cannot
  detect a wrong `--level` write; `.strip()` erases the exact-newline/empty-value
  contract the Rust oracle deliberately pins; and the dataset exercises only 3 of ~13
  characterised behaviours while mislabelling one task "missing/malformed".
- **Dependency-direction coupling** (flagged by: Architecture, Code Quality) — Build
  tooling under `tasks/` takes a hard import on the `tests/` tree, which the repo
  explicitly designs to be non-importable (no `__init__.py`, pytest importlib mode).

### Tradeoff Analysis

- **Bootstrap scope vs coverage completeness**: The plan deliberately scopes the suite
  to 3 tasks (the "extractable later", "not ramping to 20–50 tasks" stance is a sound
  YAGNI decision). Test Coverage's push for more scenarios is largely a *later-ramp*
  concern and should not block. However, the "missing/malformed-key" task that only
  builds the *missing* case is a genuine label/coverage defect independent of scope —
  either add the malformed case or rename the task. Resolve the mislabel; defer the wider
  ramp.
- **Skill-attribution as a hard gate vs a diagnostic**: Correctness and Test Coverage
  disagree on direction — Test Coverage wants the baseline's *non*-invocation asserted
  too, while Correctness warns the with-skill hard-AND on an unverified transcript shape
  could zero out pass^k spuriously. Recommendation: keep attribution but degrade it to a
  logged diagnostic until Phase 3 confirms the transcript shape, then promote it to a
  pass/fail conjunct once the real event structure is captured.

### Findings

#### Critical

- 🔴 **Portability**: `build:launcher` (host-native) cannot supply a binary the Linux
  Docker sandbox can run on a macOS host
  **Location**: Phase 2, Section 5 & 6 — Docker sandbox / mise `depends = [..., "build:launcher"]`
  `build:launcher` release-builds only the *host-native* triples, so on a macOS dev host
  it produces `*-apple-darwin` binaries that cannot execute inside the Linux container
  `inspect_swe.claude_code()` requires; only a Linux host yields the `*-linux-musl`
  binary the image needs. The `launcher` task also never stages the binary to a
  predictable path, so the Dockerfile has no stable source to COPY from. On macOS — a
  first-class dev environment here — the live eval can never work.

#### Major

- 🟡 **Architecture / Code Quality**: Build tooling imports the deliberately
  non-importable `tests/` tree
  **Location**: Phase 2, Section 6 — `tasks/eval/skills.py` (`_run_configure_eval`)
  `from tests.evals.skills.configure import configure_eval` inverts the normal
  tests→tasks direction and relies on implicit-namespace-package resolution the repo
  explicitly avoids (`pyproject.toml` documents the no-`__init__.py` design). A "works
  under pytest, breaks under bare `invoke`/`mise`" hazard. Consider invoking Inspect via
  its log-writing path + `read_eval_log()`, or housing the importable `@task` where the
  task can reach it cleanly.

- 🟡 **Test Coverage / Correctness**: Get/error task grading source is under-specified
  **Location**: Phase 2, Section 2 — the deterministic scorer
  For get tasks the plan grades "the model's captured stdout", but through
  `claude_code()` that is the agent's conversational *completion*, not raw CLI stdout —
  prose framing ("The value is team-v") fails exact match. For error tasks
  `grade_error(exit_code, stderr, marker)` has no concrete source: a completing agent has
  no agent-level exit code/stderr; those live inside a Bash tool-result in the transcript.
  Pin the exact data sources (sandbox re-exec, or transcript extraction) and unit-test the
  extraction/branch-selection, not just the inner comparators.

- 🟡 **Correctness / Compatibility / Code Quality**: `skill_was_invoked` hard-gates the
  with-skill arm on an unverified transcript shape
  **Location**: Phase 2, Section 2 — `skill_was_invoked`
  The helper assumes `tc.function == "Skill"` and `tc.arguments["name"] == "configure"`,
  navigating deep `Any`-typed attributes not verified until Phase 3, yet required as a
  hard AND with the outcome grade. If the tool name, argument key, or event location
  differs, every with-skill sample is marked INCORRECT and pass^k collapses to 0 for a
  spurious reason. Verify against one real log first; consider a logged diagnostic until
  confirmed.

- 🟡 **Test Coverage / Architecture / Compatibility**: The gate's log-reading glue is
  untested and coupled to the pre-1.0 log schema
  **Location**: Phase 2, Section 6 — `_run_configure_eval` / `_pass_k` / `_arm_log`
  `below_floor` is two-sided tested, but the glue that produces its input — filtering
  `log.results.scores` on `reducer == "all_correct"` and reading `metrics["accuracy"].value`
  — has no unit test and is only exercised by the one-shot live run. A wrong reducer
  filter, arm selection, or metric key silently mis-gates. Feed `_pass_k`/`_arm_log` a
  synthetic `EvalLog` fixture (both arms, multiple reducers) in a unit test.

- 🟡 **Correctness**: Precedence task cannot distinguish a correct personal write from an
  erroneous team overwrite
  **Location**: Phase 2, Section 4 — the set/precedence task
  If the model misroutes to `set --level team core.example personal-v`, the resolving
  `get` still returns `personal-v` and the scorer marks CORRECT — so the task has a blind
  spot for the exact `--level`-routing failure it exists to catch. Grade level-scoped
  reads: `get --level personal` == `personal-v` **and** `get --level team` == the
  pre-seeded `team-v`.

- 🟡 **Correctness**: Follow-up-get oracle and pre-seeded fixtures assume per-epoch
  sandbox isolation
  **Location**: Phase 2, Sections 2, 3, 5 — scorer follow-up get / Docker sandbox / `Epochs(K)`
  The stateful follow-up `get` and pre-seeded `.luminosity` fixtures assume each of k=3
  epochs (and each sample) gets a pristine sandbox. If Inspect reuses a sandbox across
  epochs/samples, a prior `set` leaves state behind and the all-succeed reducer becomes
  non-deterministic. Confirm and document Inspect's sandbox lifecycle; reset state at
  scorer start if it can persist.

- 🟡 **Test Coverage**: Dataset covers 3 of ~13 characterised oracle behaviours; one task
  is mislabelled
  **Location**: Phase 2, Section 4 — the dataset
  The "missing/malformed-key" task builds only the *missing* case. Bad `--level` (exit
  **2**, which `grade_error` does not distinguish from exit 1), malformed frontmatter,
  path-conflict on set, invalid-key, null/empty-value get, and `--level`-scoped get are
  all unexercised. Add at least the malformed case (to honour the label) and a bad-`--level`
  (exit-2) case, and have `grade_error` assert the exit-code class + empty stdout.

- 🟡 **Architecture**: CLI contract duplicated across the Rust/Python boundary with no
  enforced link
  **Location**: Phase 2, Section 4 / Phase 2 Manual Verification
  Expected values and markers are hand-lifted from `cli/launcher/tests/config.rs` and
  validated only "by inspection", so the regression gate can itself silently drift from
  the contract it guards. Add a structural link (assert markers against the Rust
  error-template strings) or explicitly document the accepted duplication and which side
  is authoritative.

- 🟡 **Standards**: Eval-definition snippets omit annotations that pyrefly-strict requires
  **Location**: Phase 2, Sections 1 & 2 — `reducer.py`, `scorer.py`
  `skill_was_invoked(messages, ...)` leaves `messages` unannotated and `all_correct()` /
  its inner `reduce` lack return annotations. CLAUDE.md is explicit that `tests/**` is
  held to the same strict pyrefly standard (no relaxed profile), so as written these would
  fail `mise run build-system:check` — contradicting each phase's "stays green" criterion.

- 🟡 **Compatibility**: `claude_code()` solver kwargs unverified against the pinned pre-1.0
  `inspect_swe`
  **Location**: Phase 2, Section 3 — both solvers
  `skills=` and `disallowed_tools=` are documented but never verified against the version
  being pinned, on a package the research flags as "young pre-1.0 on an evolving bridge
  API". A signature drift fails at Task construction and only surfaces at the live run.
  Introspect the resolved signature and add a construct-without-raising unit test.

- 🟡 **Compatibility**: `inspect-ai` / `inspect-swe` may not support the repo's Python
  3.14 floor
  **Location**: Phase 1, Section 1 — pin the Inspect dependencies
  The repo pins `requires-python = ">=3.14"`; a pre-1.0 package (or a transitive Bridge
  dep) may cap below that, failing `deps:install:python` outright. Resolve+lock against
  3.14 before finalising the pin.

- 🟡 **Compatibility**: `inspect-ai` and `inspect-swe` are a coupled pair pinned
  independently
  **Location**: Phase 1, Section 1 — pin the Inspect dependencies
  `inspect-swe` depends on a specific `inspect-ai` range via `sandbox_agent_bridge()`;
  independent exact pins can conflict now and drift on a lone future bump (the same hazard
  the repo calls out for ziglang/cargo-zigbuild and PUP_NIGHTLY/PUP_VERSION). Pin a
  known-compatible pair and mark them matched.

- 🟡 **Compatibility**: The Anthropic model version is unpinned, so the committed log is
  not reproducible
  **Location**: Phase 2, Section 3 / Phase 3 — committed eval log
  "Model/temperature/seed identical across arms" never says how the model version is
  selected; the committed log (the "durable quality signal") then compares against a
  moving target, and the documented model-drift refresh trigger is unactionable. Pin a
  dated model id and record it in the log metadata.

- 🟡 **Compatibility**: Claude Code CLI version unpinned in the Dockerfile vs the plugin's
  v2.1.144 floor
  **Location**: Phase 2, Section 5 — the Docker sandbox
  The plugin requires Claude Code ≥ v2.1.144 (the skill-preload mechanism the eval
  depends on); an image installing latest/arbitrary CLI can drift the skill-loading and
  headless-flag contract the with-skill arm relies on. Pin the CLI version and record it
  in the log.

- 🟡 **Portability**: The hard Docker dependency is neither provisioned nor fail-fast
  checked
  **Location**: Phase 3 prerequisites / research Open Question 5
  Docker is not in `mise [tools]`, has no `deps:install:*` task, and is documented only as
  Phase-3 prose; with `LUMINOSITY_EVAL_LIVE` on but no daemon, the run fails deep inside
  Inspect's sandbox setup. Document Docker as an out-of-band prerequisite and fail fast
  with a clear message when the daemon is unreachable.

#### Minor

- 🔵 **Test Coverage**: `grade_value`'s double `.strip()` discards the exact-newline and
  empty-value contract
  **Location**: Phase 2, Section 2 — `grade_value`
  The oracle pins *exactly one* trailing newline and distinguishes an empty-string value
  (`\n`, exit 0) from a missing key (empty, exit 1); stripping both sides erases both. If
  the source is raw stdout, compare the exact expected bytes and add an empty-value case.

- 🔵 **Test Coverage**: No deterministic assertion that the baseline arm suppressed the
  skill
  **Location**: Phase 2, Sections 2/3
  If suppression silently fails (a pre-1.0 flag drift), both arms load the skill, the A/B
  becomes meaningless, and both can still pass — checked only by manual Inspect-View.
  Reuse `skill_was_invoked` to assert its negation on the baseline.

- 🔵 **Test Coverage**: Load-bearing dataset targets are cross-checked only manually
  **Location**: Phase 2, Section 8 / Manual Verification
  A wrong `target`/marker produces a green eval that verifies nothing. Derive the expected
  value from the seeded fixture (self-consistency), or tie markers to the known message
  templates so a drift fails the unit suite.

- 🔵 **Correctness**: `pass_k` is read without checking the eval log status succeeded
  **Location**: Phase 2, Section 6 — `_pass_k` / `_arm_log`
  An errored/cancelled run can leave `log.results` `None` or partial; accuracy over a
  subset could falsely pass the gate. Fail closed when `log.status != "success"` or
  `log.results is None`.

- 🔵 **Correctness**: `all_correct` reducer is fail-open on an empty score list
  **Location**: Phase 2, Section 1 — the custom reducer
  `all([])` is `True`, so a sample whose epochs produced no scores reduces to CORRECT,
  inflating pass^k. Guard with `passed = bool(scores) and all(...)` and unit-test the
  empty case.

- 🔵 **Correctness**: Two unstated preconditions — the set/get branch key and the
  `accuracy` metric declaration
  **Location**: Phase 2, Sections 2 & 6
  The value-task set-vs-get discriminator (presumably `metadata["action"]`) is never
  named, and `_pass_k` reads `metrics["accuracy"]` which only exists if the `@scorer`
  declares `metrics=[accuracy(), ...]`. State both explicitly and assert the metric's
  presence.

- 🔵 **Code Quality / Standards**: The env-flag `_FALSEY` set and normalisation are
  duplicated a third time
  **Location**: Phase 1, Section 2 — `tasks/eval/gate.py`
  `_FALSEY` and the strip/lower/`not in` idiom already exist twice in
  `tasks/shared/rust.py`. Extract a shared `env_flag_enabled(name, *, default)` in
  `tasks/shared/` and have all three knobs source it.

- 🔵 **Code Quality / Standards**: The call-time env-read rationale docstring is dropped
  **Location**: Phase 1, Section 2 — `live_run_enabled`
  `coverage_enabled`/`pup_mode` document the "read at call time, not import" invariant —
  exactly the "why" the comment policy reserves. Without it a future dev may hoist the
  read to a module constant and break the escape hatch. Carry the one-line docstring.

- 🔵 **Compatibility**: Multiple assumed Inspect API-surface details are load-bearing and
  unverified
  **Location**: Phase 2, Sections 1, 3, 6
  `value_to_float`/`score_reducer`/`Epochs` import locations, relative-path resolution for
  `json_dataset`/`compose.yaml`, per-reducer `accuracy` attachment, and the
  `log.results.scores` shape are all assumed on a pre-1.0 package and exercised only live.
  Round-trip a synthetic/fixture `EvalLog` through the read-back in a Phase 2 test.

- 🔵 **Compatibility**: Baseline suppression and attribution hardcode the literal `"Skill"`
  tool name
  **Location**: Phase 2, Sections 2 & 3
  `disallowed_tools=["Skill"]` and `tc.function == "Skill"` are an unpinned contract with
  Claude Code's internal tool naming/transcript schema. In Phase 3, corroborate via the
  log's `system/init` (plugin loaded / not) rather than trusting the name alone.

- 🔵 **Portability**: Dockerfile base image and target architecture unspecified
  **Location**: Phase 2, Section 5
  Docker Desktop runs arm64 on Apple Silicon and x86_64 on Intel; the same `compose.yaml`
  produces different arches, which must match the binary on `PATH`. Pin the base image and
  set `platform:` (or build the binary in-image).

- 🔵 **Portability**: The committed JSON log may bake in environment-specific content and
  version-couple its readability
  **Location**: Phase 3, Section 2
  Inspect logs embed absolute paths/hostnames/versions and are read back via a
  version-tied `read_eval_log`. Confirm the log is scrubbed of host paths (or commit a
  summarised extract), and note the read-back's coupling to the pinned `inspect-ai`.

- 🔵 **Architecture**: The live agent solver has no bounded turn/time budget
  **Location**: Phase 2, Section 3 / Performance Considerations
  No `max_turns`/time limit is set, though `inspect_swe` exposes them and token cost is
  the stated reason for CI-exclusion. A looping agent can burn unbounded tokens. Set an
  explicit per-sample turn/time ceiling, identical across arms.

- 🔵 **Standards**: Snippets carry file-path label comments
  **Location**: Phase 1, Section 3 — `tasks/eval/__init__.py` / `skills.py` snippets
  The `# tasks/eval/__init__.py` headers and the `# must not run the eval` inline comment
  violate the comment policy if transcribed literally. Treat path labels strictly as plan
  captions; deliver files starting directly with imports.

- 🔵 **Standards**: Singular `eval` vs plural `evals` naming for the same concept
  **Location**: Overview / Phases 1 & 2
  `tasks/eval/` + mise `eval` (singular) vs `tests/evals/` + `tests/unit/evals/` (plural)
  forces two spellings. Pick one to mirror the existing `test` collection convention.

#### Suggestions

- 🔵 **Code Quality**: The `configure_scorer(with_skill=...)` flag argument fuses two
  grading concerns
  **Location**: Phase 2, Sections 2 & 3
  A boolean toggling skill-attribution layered over the `expect_error` branch gives one
  scorer two reasons to change. Compose an attribution scorer AND-ed onto the base outcome
  scorer only on the with-skill arm.

- 🔵 **Code Quality**: pass^k semantic read from a metric named `accuracy` without a
  bridging cue
  **Location**: Phase 2, Section 6 — `_pass_k`
  Name the intermediate `all_correct_fraction` (or note that the `accuracy` of the
  `all_correct` reducer *is* pass^k) so a maintainer does not "fix" the gate to a lenient
  metric.

- 🔵 **Portability**: Relative dataset/sandbox paths resolved during an in-process `eval()`
  launched from the task layer
  **Location**: Phase 2, Sections 3 & 6
  Resolve `dataset.jsonl`/`compose.yaml` from the eval module's own `__file__` so
  invocation cwd cannot affect the run.

- 🔵 **Architecture**: The task runner is configure-shaped despite the "extractable later"
  framing
  **Location**: Phases 1/2 — `tasks/eval/skills.py`
  The eval *definition* is parameterised; the *runner* (`_run_configure_eval`, arm names,
  results dir) is not. No action now, but note the runner as the second extraction point.

- 🔵 **Standards**: No intermediate `eval:skills` roll-up node
  **Location**: Phase 1, Section 4 / Phase 2, Section 5 — mise wiring
  The established test tier uses two-level roll-ups (`test` → `test:unit`/`test:integration`).
  Given further skills are anticipated, an `eval:skills` intermediate now avoids a retrofit.

### Strengths

- ✅ The pass^k reconciliation is correct and load-bearing: the plan verified Inspect has
  no `pass_k`, that `pass_at(k)` is the *lenient* opposite, and wires an explicit
  all-succeed reducer whose semantics match the intended hard gate — with a matching
  ADR-0011 correction note.
- ✅ Strong functional-core/imperative-shell separation: the pure `below_floor` gate and
  pure `grade_value`/`grade_error`/`skill_was_invoked` branches are unit-testable with no
  live run, mirroring the `version.py`/`pup.py` pattern.
- ✅ CI-exclusion is a structural property (omission from `check`/`default` `depends`),
  consistent with `launcher:check`/`kernel:check`/`test:integration:pup`, and pinned by a
  wiring unit test.
- ✅ The seam design (Phase 1 introduces `_run_configure_eval` raising not-yet-implemented,
  Phase 2 fills it) keeps each phase independently mergeable and `mise run check` green
  throughout.
- ✅ Convention fidelity: correct `eval as eval_` builtin handling, `replace-imports-with-any`
  for the untyped Inspect surface, exact-pinned dev deps, the `LUMINOSITY_EVAL_LIVE` knob
  following the `LUMINOSITY_COVERAGE`/`LUMINOSITY_PUP_MODE` naming, and invoke `Collection`
  scaffolding line-for-line with `tasks/test/__init__.py`.
- ✅ The set/precedence oracle correctly recognises that a successful `set` emits empty
  stdout and must be graded via a follow-up `get`.
- ✅ Appropriate YAGNI: the A/B scaffold is deliberately not abstracted into a generic
  multi-skill harness, with the tradeoff explicitly acknowledged.

### Recommended Changes

1. **Make the sandbox binary host-independent** (addresses: the critical Portability
   finding, the Docker base-image/arch minor) — Build `luminosity` *inside* a multi-stage
   Dockerfile for the container's musl target so the image is self-contained, or depend on
   `build:release` (cross-builds all four triples, stages to `bin/luminosity-<platform>`)
   and COPY the linux-musl artifact matching a pinned `platform:`. Drop the
   `build:launcher` dependency for the sandbox path.

2. **Turn the deferred integration assumptions into Phase-2 checks** (addresses: the five
   Compatibility majors, the log-glue-untested major, the API-surface minor) — Before
   committing the pin: resolve+lock against Python 3.14, pin `inspect-ai`/`inspect-swe` as
   a matched pair, introspect `claude_code()`'s real signature, and pin the model + Claude
   Code CLI versions (recorded in the log). Add a unit test that constructs both Tasks and
   round-trips a synthetic `EvalLog` through `_pass_k`/`_arm_log`.

3. **Pin the grading oracle's data sources and fix the precedence/error branches**
   (addresses: the get/error grading-source major, the precedence blind-spot major, the
   sandbox-isolation major, the `.strip()` and empty-value minors) — State exactly what
   `actual` is per scenario (prefer sandbox re-exec for determinism); grade precedence via
   level-scoped reads of both files; confirm/reset per-epoch sandbox state; and preserve
   the exact-newline contract.

4. **Decouple build tooling from the tests tree** (addresses: the dependency-direction
   major) — Invoke Inspect via its log-writing path + `read_eval_log()`, or relocate the
   importable `@task`, so `tasks/` does not import `tests/`.

5. **Fix the coverage/label and correctness edge cases** (addresses: the dataset-coverage
   major, the reducer fail-open minor, the status-check minor, the unstated-preconditions
   minor) — Add the malformed and bad-`--level` (exit-2) tasks (or rename the mislabelled
   one), guard the empty-score reducer, fail closed on non-`success` log status, and name
   the set/get discriminator + declare the `accuracy` metric.

6. **Close the standards/quality gaps** (addresses: the annotation major, the docstring/
   `_FALSEY`/comment/naming minors) — Fully annotate the eval modules (they are
   pyrefly-strict), carry the call-time-read docstring, extract the shared env-flag helper,
   strip snippet path-label comments, reconcile eval/evals naming, and set a per-sample
   turn/time budget on both solver arms.

---
*Review generated by /accelerator:review-plan*

## Per-Lens Results

### Architecture

**Summary**: Architecturally disciplined — clean functional-core/imperative-shell split,
structural CI-exclusion, and a corrected Inspect API assumption kept in sync with ADR-0011.
The main structural risks are a dependency-direction inversion (strict-typed `tasks/`
importing the non-packaged `tests/evals/` tree) and an unenforced cross-language
duplication of the CLI contract, both consequences of inherited constraints rather than
avoidable mistakes but neither acknowledged as a tradeoff.

**Strengths**:
- Strong functional-core/imperative-shell separation (`below_floor`, `grade_value`,
  `grade_error`, `skill_was_invoked` pure; model/Docker I/O behind `_run_configure_eval`).
- CI-exclusion is structural (omission from `check`/`default`), matching
  `launcher:check`/`kernel:check`/`test:integration:pup`, pinned by a wiring test.
- Reconciles the wrong `pass_k(k)` assumption against the real API + records an ADR-0011
  note.
- Seam design lets each phase leave `mise run check` green and keeps the gate testable.
- A/B scaffold deliberately not over-abstracted (appropriate YAGNI).

**Findings**:
- **major** (medium) — *Build-tooling package imports the non-packaged test tree*
  (Phase 2 §6). `from tests.evals.skills.configure import configure_eval` inverts
  tests→tasks direction and relies on PEP-420 resolution the repo avoids; a
  works-under-pytest/breaks-under-`mise` hazard. Decouple via `read_eval_log()` or a
  packaged eval path.
- **major** (medium) — *CLI contract duplicated across the Rust/Python boundary with no
  enforced link* (Phase 2 §4 / Manual Verification). Expected values lifted from
  `config.rs` and validated only by inspection; the gate can silently drift from the
  contract it guards. Add a structural link or document the authoritative side.
- **minor** (medium) — *Gate extraction couples the imperative shell to Inspect's pre-1.0
  log schema* (Phase 2 §6). `_pass_k` reaches into `log.results.scores`; an Inspect bump
  can reshape it invisibly to CI. Unit-test the extraction against a synthetic `EvalLog`.
- **minor** (medium) — *Live agent solver has no bounded turn/time budget* (Phase 2 §3 /
  Performance). No `max_turns`/time limit though token cost justified CI-exclusion. Set an
  explicit ceiling, identical across arms.
- **suggestion** (low) — *Task seam is configure-shaped despite the "extractable later"
  framing* (Phases 1/2). The eval def is parameterised; the runner is not. Note the runner
  as the second extraction point.

### Code Quality

**Summary**: Well-structured for maintainability — pure `float -> bool` gate, pure
grading decisions split from sandbox I/O, TDD-driven, mirroring `tasks/pup.py` /
`tasks/shared/rust.py`. Main concerns: a dependency-direction smell (build code importing
the `tests/` tree the repo designs to be non-importable), brittle deep-attribute traversal
over untyped Inspect objects, and some drift from existing conventions (duplicated env-flag
idiom, dropped rationale docstrings, a flag-argument scorer).

**Strengths**:
- Pass^k gate is a pure `below_floor(pass_k: float) -> bool` decoupled from any live run.
- Scorer separates pure `grade_value`/`grade_error`/`skill_was_invoked` from sandbox I/O.
- The `_run_configure_eval` seam is a clean incremental design.
- The `all_correct` reducer is named for clarity over the subtle `at_least(k)==k` idiom.

**Findings**:
- **major** (high) — *Build code imports from the deliberately non-importable `tests/`
  tree* (Phase 2 §6). Contradicts `pyproject.toml:75-77` (no `__init__.py`, `INP001`
  disabled under `tests/**`). Relocate the `@task` or invoke Inspect by path/CLI.
- **minor** (high) — *Env-flag idiom and `_FALSEY` set duplicated a third time* (Phase 1
  §2). Extract a shared `env_flag_enabled` in `tasks/shared/`.
- **minor** (medium) — *Call-time env-read rationale docstrings dropped despite claiming to
  mirror `rust.py`* (Phase 1 §2). Carry the one-line invariant docstring.
- **minor** (medium) — *Brittle deep-attribute traversal over untyped Inspect messages*
  (Phase 2 §2). Annotate `messages` and pin the transcript shape in a unit test.
- **suggestion** (medium) — *Flag-argument scorer fuses two grading concerns* (Phase 2
  §2/3). Compose attribution as a separate AND-ed scorer on the with-skill arm.
- **suggestion** (medium) — *pass^k semantic read from a metric named `accuracy` without a
  bridging cue* (Phase 2 §6). Name the intermediate `all_correct_fraction`.

### Test Coverage

**Summary**: The pure-helper decomposition is genuinely unit-testable and the
two-sided/threshold, non-collection, and mise-wiring-isolation tests are well-conceived.
But the plan's own claim that grading "covers the CLI contract" overstates it: the dataset
exercises only 3 of ~13 characterised behaviours, the critical log-reading glue and the
scorer's branch selection are untested except by the once-only live run, and `grade_value`'s
`.strip()` discards the exact-newline/empty-value contract the oracle pins.

**Strengths**:
- Gate/scorer/reducer split into pure ctx-free helpers unit-testable with no `eval()`.
- Mise-wiring test asserts the tier is declared but absent from `check`/`default`.
- Non-collection test guards against accidental token-spending execution.
- The `LUMINOSITY_EVAL_LIVE` skip path is unit-tested.

**Findings**:
- **major** (high) — *The gate's log-reading glue (`_pass_k`/`_arm_log`) is untested except
  by the once-only live run* (Phase 2 §6). Feed a synthetic `EvalLog` with both arms and
  multiple reducers.
- **major** (medium) — *Get-task grading source is ambiguous* (Phase 2 §2). The
  `claude_code()` completion is the model's final message, not raw stdout; prose framing
  fails exact match. Decide per scenario and unit-test the extraction.
- **major** (high) — *Dataset covers 3 of ~13 oracle behaviours; error taxonomy largely
  unexercised, and "missing/malformed" only tests missing* (Phase 2 §4/§2). Add malformed,
  bad-`--level` (exit 2), and null/empty-value; make `grade_error` assert exit class +
  empty stdout.
- **minor** (high) — *`grade_value`'s double `.strip()` discards the exact-newline/empty-
  value contract* (Phase 2 §2). Compare exact bytes; add an empty-value case.
- **minor** (medium) — *No deterministic assertion that the baseline suppressed the skill*
  (Phase 2 §2/3). Assert `skill_was_invoked` negation on the baseline.
- **minor** (medium) — *Load-bearing dataset targets cross-checked only manually* (Phase 2
  §8 / Manual Verification). Derive expected from the seeded fixture or tie markers to
  templates.

### Correctness

**Summary**: The core reconciliation (custom all-succeed reducer, strict `<` gate) is
sound and the pure-helper split gives correct boundary behaviour. The material risks are in
the scorer's oracle: the precedence task cannot distinguish a correct personal write from a
team overwrite, the get/error branches grade against under-specified/non-existent data
sources, and sandbox-isolation and transcript-shape assumptions are load-bearing yet
unverified until Phase 3.

**Strengths**:
- pass^k reconciliation verified against the live API (no `pass_k`; `pass_at(k)` lenient).
- Strict `<` boundary is correct; two-sided test pins 0.79/0.8/1.0.
- Pure decision functions verifiable without a live run.
- Recognises empty-stdout `set` must be graded via follow-up `get`.

**Findings**:
- **major** (high) — *Precedence task cannot distinguish a correct personal write from an
  erroneous team overwrite* (Phase 2 §4/§2). Grade level-scoped reads of both files.
- **major** (medium) — *get and error branches grade against under-specified/non-existent
  data sources* (Phase 2 §2). No agent-level exit code/stderr for a completing agent; pin
  transcript extraction or sandbox re-exec.
- **major** (medium) — *Follow-up-get oracle and pre-seeded fixtures assume per-epoch/
  per-sample sandbox isolation* (Phase 2 §2/3/5). Confirm Inspect's sandbox lifecycle;
  reset state if it persists.
- **major** (medium) — *`skill_was_invoked` encodes unverified transcript-shape assumptions
  that hard-gate the with-skill arm* (Phase 2 §2). Verify against a real log; consider a
  diagnostic until confirmed.
- **minor** (medium) — *`pass_k` read without checking log status succeeded* (Phase 2 §6).
  Fail closed on non-`success`/`None` results.
- **minor** (medium) — *`all_correct` reducer fail-open on an empty score list* (Phase 2
  §1). Guard with `bool(scores) and all(...)`.
- **minor** (medium) — *Two unstated preconditions: the set/get branch key and the
  `accuracy` metric declaration* (Phase 2 §2/§6). State `metadata["action"]` and require
  `@scorer(metrics=[accuracy(), stderr()])`.

### Compatibility

**Summary**: The plan rests almost entirely on two young pre-1.0 dependencies plus an
external Claude Code CLI and Anthropic model, and its correctness depends on API surfaces
and solver parameters the research flagged as unverified against the pinned versions. The
exact-pin discipline and structural CI-exclusion are sound, but several assumed contracts
(kwargs, log/reducer surface, Python 3.14, unpinned CLI/model) are exactly where a pre-1.0
drift breaks the eval or silently makes the committed log non-reproducible — surfacing only
at the Phase 3 boundary.

**Strengths**:
- Exact-pinning both packages + locking `uv.lock` freezes the Bridge surface.
- `replace-imports-with-any` insulates strict type-checking from the unstable surface.
- The `pass_k`/`pass_at`/`at_least` mismatch already reconciled + ADR-corrected.
- Structural CI-exclusion keeps token/Docker/model-drift cost out of every build.

**Findings**:
- **major** (medium) — *`claude_code()` kwargs (`skills=`, `disallowed_tools=`) unverified
  against the pinned pre-1.0 `inspect_swe`* (Phase 2 §3). Introspect the signature; add a
  construct-without-raising test.
- **major** (medium) — *`inspect-ai`/`inspect-swe` may not declare Python 3.14 support*
  (Phase 1 §1). Resolve+lock against 3.14 before finalising.
- **major** (medium) — *The two are a coupled pair pinned independently* (Phase 1 §1). Pin
  a compatible pair and mark them matched.
- **major** (medium) — *The Anthropic model version is unpinned, so the committed log is
  not reproducible* (Phase 2 §3 / Phase 3). Pin a dated model id in log metadata.
- **major** (medium) — *Claude Code CLI version unpinned vs the v2.1.144 skill-preload
  floor* (Phase 2 §5). Pin the CLI version and record it in the log.
- **minor** (medium) — *Multiple assumed Inspect API-surface details load-bearing and
  unverified* (Phase 2 §1/3/6). Round-trip a synthetic/fixture `EvalLog` through the
  read-back in Phase 2.
- **minor** (medium) — *Baseline suppression and attribution couple to the literal `"Skill"`
  name* (Phase 2 §2/3). Corroborate via `system/init` in Phase 3.

### Portability

**Summary**: Portability-conscious in its CI-exclusion and `LUMINOSITY_EVAL_LIVE`
off-switch, but the live path has a genuine cross-environment blocker: it wires the Linux
Docker sandbox to `build:launcher` (host-native), so a macOS host produces darwin binaries
that cannot run in the container, and `build:launcher` never stages the binary to a
predictable path. The hard Docker dependency is also unprovisioned and undocumented.

**Strengths**:
- `LUMINOSITY_EVAL_LIVE` is a clean environment-independence lever, read at call time.
- Structural CI-exclusion confines the heavy coupling to the dev-time path.
- Both packages exact-pinned + locked for reproducibility.
- The existing `host_targets()` fails loudly on an unsupported host OS.

**Findings**:
- **critical** (high) — *`build:launcher` (host-native) cannot supply a binary the Linux
  Docker sandbox can run on a macOS host* (Phase 2 §5/§6). Build the binary in a multi-stage
  Dockerfile for the container's musl target, or depend on `build:release` and COPY the
  matching linux-musl artifact.
- **major** (high) — *Hard Docker dependency is neither provisioned nor fail-fast checked*
  (Phase 3 / Open Question 5). Document Docker as an out-of-band prerequisite and fail fast
  when the daemon is unreachable.
- **minor** (medium) — *Dockerfile base image and target architecture unspecified — Intel
  vs Apple Silicon divergence* (Phase 2 §5). Pin the base image and set `platform:`.
- **minor** (medium) — *Committed JSON log may bake in environment-specific content and
  version-couple its readability* (Phase 3 §2). Scrub host paths; note the read-back's
  coupling to the pinned `inspect-ai`.
- **suggestion** (low) — *Relative dataset/sandbox paths resolved during an in-process
  `eval()`* (Phase 2 §3/§6). Resolve via the eval module's `__file__`.

### Standards

**Summary**: Strongly convention-aware — mirrors the env-knob + pure-helper-plus-thin-`@task`
idiom, exclusion-by-omission wiring, exact-pin style, correct `eval as eval_` builtin
handling, and the `replace-imports-with-any` convention. Main gaps: annotation
completeness against the no-relaxed-profile pyrefly-strict rule, a missing env-knob
docstring, and minor naming/DRY inconsistencies (singular `tasks/eval/` vs plural
`tests/evals/`, duplicated `_FALSEY`).

**Strengths**:
- Correct `eval as eval_` builtin handling mirroring `format as format_`.
- `inspect_ai.*`/`inspect_swe.*` added to `replace-imports-with-any`.
- Exact-pins in `[dependency-groups] dev` alongside `ruff==`/`pyrefly==`.
- `LUMINOSITY_EVAL_LIVE` follows the existing knob naming + call-time-read; gate is a pure
  helper wrapped by a thin `@task`.
- Structural CI-exclusion + extended `test_mise_wiring.py`.
- Invoke collection scaffolding line-for-line with `tasks/test/__init__.py`.

**Findings**:
- **major** (medium) — *Eval-definition snippets omit annotations pyrefly-strict requires*
  (Phase 2 §1/§2). `messages` unannotated; `all_correct()`/`reduce` lack return types.
  Would fail `build-system:check`. Fully annotate.
- **minor** (high) — *`live_run_enabled()` carries no docstring* (Phase 1 §2), unlike
  `coverage_enabled`/`pup_mode`. Add the call-time-read docstring.
- **minor** (high) — *Snippets carry file-path label comments* (Phase 1 §3). Treat as plan
  captions; deliver files starting at imports; drop the restating inline comment.
- **minor** (medium) — *Singular `eval` vs plural `evals`* (Overview / Phases 1&2). Pick one
  spelling.
- **suggestion** (high) — *`_FALSEY` redefined* (Phase 1 §2). Lift into `tasks/shared/`.
- **suggestion** (medium) — *No intermediate `eval:skills` roll-up node* (Phase 1 §4 /
  Phase 2 §5). Add one now given anticipated further skills, or note the deviation.

## Re-Review (Pass 2) — 2026-07-07T00:53:43+00:00

**Verdict:** REVISE

The plan improved materially after the pass-1 edits: the blocking **critical is
resolved** and the great majority of pass-1 majors are resolved or mitigated. The
verdict stays REVISE only because the deeper second pass surfaced a fresh set of
mostly-medium-confidence issues — two of which are concrete bugs introduced by the
pass-1 edits (a wrong Dockerfile COPY path, and a `max_turns` kwarg that may not exist
on `claude_code()`), the rest being detail-sharpenings and pre-1.0 Phase-3 verification
items. None challenge the approach; the remaining work is tractable and largely
mechanical.

### Previously Identified Issues

- 🔴 **Portability**: `build:launcher` host-native arch mismatch — **Resolved** (now
  `build:release` cross-builds linux-musl + pinned `linux/amd64`). See the new
  COPY-path issue below, though.
- 🟡 **Architecture / Code Quality**: build tooling imports the `tests/` tree —
  **Resolved** (file-path task specifier; dependency direction preserved).
- 🟡 **Portability**: Docker unprovisioned / no fail-fast — **Resolved** (`_require_docker`
  + documented out-of-band prerequisite).
- 🟡 **Correctness**: precedence blind spot — **Resolved** (level-scoped reads of both
  levels; now a cited strength).
- 🟡 **Test Coverage / Architecture / Compatibility**: gate log-reading glue untested —
  **Resolved** (synthetic-`EvalLog` read-back test + `_require_success` fail-closed).
- 🟡 **Correctness / Compatibility / Code Quality**: `skill_was_invoked` hard-gate on an
  unverified shape — **Resolved** (degraded to a logged diagnostic until Phase 3).
- 🟡 **Standards**: annotations omitted (pyrefly-strict) — **Resolved** in the harness
  modules (test-snippet annotations remain shorthand, minor).
- 🟡 **Compatibility**: coupled-pair pinning / Python 3.14 / model version / CLI version —
  **Resolved** (matched-pair lockstep; 3.14 pre-commit gate; pinned model + CLI recorded
  in the log). Residuals: no 3.14 *fallback* defined, CLI now a second version source
  (see new issues).
- 🟡 **Test Coverage / Correctness**: get/error grading source; dataset coverage/label —
  **Partially resolved** (transcript extraction + byte-exact + 5 scenarios + label
  fixed; residual raw-stdout / exit-code / extra-scenario items below).
- 🟡 **Architecture / Correctness**: cross-epoch sandbox isolation — **Still present**
  (the plan now flags it but leaves it a runtime "confirm" rather than designing the
  reset in unconditionally).
- 🟡 **Architecture**: CLI contract Rust→Python duplication — **Partially resolved** (a
  marker-substring check was added, but it compares a Python copy to itself — templates
  live in Rust, so the drift protection is weaker than stated).
- 🔵 Pass-1 minors — **Resolved**: `.strip()`→byte-exact, reducer empty-list guard,
  fail-closed status check, `_FALSEY`/docstring dedup via shared `env_flag_enabled`,
  restating comment removed, `eval:skills` roll-up added, log-scrub note added. **Still
  present**: `eval` vs `evals` naming (deferred by choice; Standards re-flagged it major).

### New Issues Introduced

- 🟡 **Portability / Compatibility**: The Dockerfile `COPY` source is wrong — `build:release`
  stages to `cli/launcher/bin/luminosity-linux-x64` (platform alias, not the Rust
  triple), not `bin/luminosity-<triple>`, and the compose `build.context` must widen to
  reach `cli/launcher/bin/`. A literal implementation would fail to build on every host.
- 🟡 **Compatibility**: `claude_code(max_turns=...)` — the budget kwarg added in pass 1 is
  **not** in the researched `claude_code()` signature (`--max-turns` is a CLI flag). If
  it is not a kwarg both `@task` constructors `TypeError`; bound instead via Task-level
  `message_limit` / `token_limit` / `time_limit`.
- 🟡 **Correctness**: Config-discovery rooting is unspecified — the CLI roots at a `.git`
  boundary walking up from cwd (as `config.rs` sets up), but the sandbox seeds only
  `.luminosity`, and the scorer's follow-up `sandbox().exec` reads don't pin the same cwd
  as the agent's write.
- 🟡 **Correctness**: Byte-exact get grading assumes the `Bash` tool-result captures *raw*
  un-normalised stdout; if the harness trims/collapses output the empty-value `\n` vs
  miss distinction (the reason for no `.strip()`) breaks.
- 🟡 **Correctness**: `grade_error` checks only `exit_code != 0`, so the dataset's pinned
  `exit: 2` (clap) is inert — the exact clap-vs-domain conflation the bad-`--level` task
  was added to catch is not enforced.
- 🟡 **Correctness**: The reducer guards the empty list but not a *partial-k* list — if
  Inspect drops errored epochs, a sample that ran 1 of 3 trials reduces to CORRECT. Pin
  `len(scores) == K` or `fail_on_error`.
- 🟡 **Code Quality**: The magic-string task specifier (`configure_eval.py@configure_with_skill`)
  has no static link to the real `@task` names — a rename breaks only at the live run.
  Add a cheap resolution test.
- 🟡 **Code Quality**: `bash_result` locates a result by substring over free-form shell
  text, ambiguous when the transcript holds the agent's `get` *and* the scorer's
  follow-up `get`s. Match on precise argv / separate the scorer's own exec results.
- 🟡 **Test Coverage**: The gate reads only the with-skill floor and never asserts it
  beats the skill-suppressed baseline; a thin pass-through skill's baseline may also
  clear 0.8, so a green gate proves little about the skill's contribution. (Partly an
  AC3 "baseline for attribution only" tradeoff — worth an explicit differential check or
  a documented decision.)
- 🟡 **Test Coverage**: Over 5 all-succeed tasks, `≥0.8` means 4/5 tasks pass all 3
  trials — a brittle near-all-or-nothing bar against a stochastic model. Pin the task
  count, reason about tolerated trial failures, and document a rerun/flakiness policy.
- 🟡 **Test Coverage**: Dataset still omits conflict-on-`set` (the skill has an explicit
  instruction for it), invalid-key, and the empty/null-value `get` the byte-exact logic
  is built around; ambiguity-handling is inherently outside deterministic grading.
- 🟡 **Portability**: Committed-log environment-independence rests on a manual eyeball
  check, yet the eval is addressed by an absolute `_EVAL_DIR` path and writes an absolute
  `_RESULTS_DIR` — an automated no-absolute-path guard is warranted.
- 🟡 **Architecture**: The generic `all_correct` reducer is co-located in the
  configure-specific dir; hoist it to a shared eval location so the next skill doesn't
  couple laterally.
- 🟡 **Standards**: `eval` (package/tier/namespace) vs `evals` (`tests/evals/`) naming
  split recurs — pick one spelling.
- 🔵 **Minors**: `skill_was_invoked` dereferences possibly-`None` `tc.arguments`;
  `_pass_k` / `bash_result` should fail closed (not crash / not default-pass) when the
  record is absent; the reducer-name↔filter binding is only live-verified; the
  shared-helper test should mirror `tests/unit/tasks/shared/test_env.py`; the
  `coverage_enabled`/`pup_mode` migration onto `env_flag_enabled` is deferred (partial
  DRY); relative imports under the `__init__.py`-free tree need the loader confirmed;
  Claude Code CLI install source in the Dockerfile is unspecified.

### Assessment

The plan is now in good structural shape — the approach is sound and the pass-1
blockers are gone. It is not yet ready to implement verbatim: two pass-1 edits carry
concrete bugs (the Dockerfile COPY path/context and the `max_turns` kwarg), and a
cluster of correctness sharpenings should land before Phase 3 rather than being
discovered in the one costly live run — make the sandbox `.luminosity`/`.git` seed +
reset unconditional (not a runtime "confirm"), enforce the pinned exit code and
partial-k in the pure graders, and decide the gate's differential/flakiness policy. The
remainder are inherent pre-1.0 Phase-3 verification items (transcript shape, `path@name`
loader, reducer-name binding) that are reasonable to accept as explicitly-flagged
assumptions. Recommend one more focused revision on the concrete bugs + correctness
graders, after which APPROVE is within reach.

## Re-Review (Pass 3) — 2026-07-07T01:15:57+00:00

**Verdict:** REVISE

The pass-2 revision landed cleanly: both concrete bugs are **verified fixed** (the COPY
path resolves to the real `cli/launcher/bin/luminosity-linux-x64`; `message_limit` /
`fail_on_error` are valid `Task` params where `max_turns` was not), the correctness
graders are hardened, and the standards/naming items are resolved. This pass surfaced
**one genuinely new, high-confidence integration flaw** — the plugin-shim / `allowed-tools`
mismatch — that materially affects the sandbox design and would block the Phase-3 live
run, plus a cluster of deeper logic/coverage refinements. The verdict stays REVISE for
that one substantive finding; the remainder are implementation-time details or inherent
pre-1.0 Phase-3 verification. This is the expected long tail of a deep review — the plan
is close.

### Previously Identified Issues (pass 2)

- 🟡 **Portability/Compatibility**: Dockerfile COPY path — **Resolved & verified**
  (`cli/launcher/bin/luminosity-linux-x64` confirmed against `build.py`/`targets.py`;
  `build.context` = repo root).
- 🟡 **Compatibility**: `max_turns` kwarg — **Resolved** (relocated to Task-level
  `message_limit` / `fail_on_error`, confirmed valid `inspect_ai.Task` params).
- 🟡 **Correctness**: `grade_error` exit-code enforcement / reducer partial-`k` —
  **Resolved** (both now enforced and two-sided tested).
- 🟡 **Code Quality**: magic-string task specifier — **Resolved** (resolution test added).
- 🟡 **Test Coverage**: gate never asserts skill-vs-baseline — **Resolved** (advisory
  differential check, AC3-consistent).
- 🟡 **Correctness**: `_pass_k` fail-closed on absent record — **Resolved**.
- 🟡 **Portability**: committed-log absolute paths — **Resolved** (`_scrub_paths` +
  automated no-home-path test).
- 🟡 **Standards**: `eval`/`evals` naming — **Resolved** (deviation documented).
- 🟡 **Test Coverage**: flakiness policy — **Resolved** (documented; but see the
  fail_on_error infra-vs-behaviour point below).
- 🟡 **Architecture/Correctness**: sandbox isolation + `.git` rooting — **Partially
  resolved** (unconditional per-epoch re-seed + `.git` boundary added; the agent's
  working-directory binding to that fixture, and the concrete re-seed mechanism, remain
  open — see new issues).
- 🟡 **Code Quality/Correctness**: `bash_result` precise matching — **Partially resolved**
  (argv-token match added; still needs the `get`-verb in the match and a `set`-shaped
  variant for the conflict task).

### New Issues Introduced

- 🔴 **Compatibility (high confidence — most important)**: The sandbox puts a **bare
  `luminosity`** binary on `PATH`, but the skill invokes `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`
  — a bootstrap **shim** that fetches + minisign-verifies the launcher from GitHub
  releases, and whose `allowed-tools` scope is `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity
  config *)`. Bare `luminosity` neither matches the `allowed-tools` pattern nor is what
  the shim runs; the shim would try to network-fetch a release that does not exist for an
  in-dev prerelease. **This blocks the live run at the very CLI it grades.** Fix in Phase
  2 §5: provision the full plugin tree, set `CLAUDE_PLUGIN_ROOT`, and pre-stage the
  cross-built launcher at the shim's cache path (with its `.minisig` + verify shim) so
  re-verification passes offline — and confirm the resolved command matches the skill's
  `allowed-tools` scope.
- 🟡 **Correctness**: Trailing-newline reconciliation is unspecified — the oracle prints
  `team-v\n` (and `\n` for empty), grading is raw `actual == expected` with no `.strip()`,
  yet targets are stored without `\n` (`"team-v"`, `""`). Either store targets with `\n`
  or compare `stdout == target + "\n"`; unit-test both.
- 🟡 **Correctness**: The conflict-on-`set` task's failing command is a `set`, but
  `bash_result` is `get`-shaped, so it returns `None` → the task can never pass. Generalise
  the extractor on `action` (get/set) + key/level, and include the verb in the match.
- 🟡 **Correctness**: The agent's working directory is never bound to the seeded `.git`
  fixture — if `claude_code` runs the agent's `Bash` from a different cwd, the upward
  `.git` walk misses the fixture and whole task classes mis-grade. Pin and verify the
  agent cwd.
- 🟡 **Test Coverage**: The **invalid-key** error class (its own `luminosity: invalid
  config key …` template in `config.rs`) is dropped from the 7 tasks — add it. And no task
  exercises the agent routing a **valid** `--level` (only the scorer's own follow-ups and
  the bad-value error do), so the skill's `--level` passthrough is untested — add one.
- 🟡 **Test Coverage**: The scorer/`bash_result`/`skill_was_invoked` unit tests grade
  against author-written stubs of an unverified transcript shape; make the Phase-3
  golden-fixture capture a hard gate and drive at least one scorer test from the real
  sample.
- 🟡 **Portability**: No `.dockerignore` with `build.context` at repo root — every build
  tars the whole tree (incl. the multi-GB `cli/target/` from `build:release`) to the
  daemon. Add one in Phase 2.
- 🟡 **Portability**: `_require_docker` checks daemon reachability but not the amd64
  emulation the pinned `linux/amd64` needs on Apple Silicon — probe it (or name the
  Rosetta/binfmt toggle in the message).
- 🟡 **Architecture**: `fail_on_error=True` conflates a transient infra failure (network,
  rate-limit, Docker hiccup) with a genuine model-behaviour failure in an all-or-nothing,
  no-resume run — fine for 7 tasks, but it does not scale to the documented 20–50-task /
  k 5–10 ramp; note the resilience revisit or add a transient-error budget.
- 🟡 **Compatibility**: Three pre-1.0 seams still verified only live — Python 3.14
  resolution has **no stated contingency** if a transitive dep caps below 3.14; Inspect's
  file-path loader may not honour the `__init__.py`-free **relative imports**; and
  `inspect_swe` may **provision its own Claude Code CLI** (`version=`), making the
  Dockerfile pin moot and the log-stamped version wrong. State the 3.14 fallback, exercise
  the loader path in a Phase-2 test, and reconcile the CLI-version source.
- 🔵 **Minors/polish**: `skills.py` holds four concerns (extract the read-back glue to
  `readback.py`); introduce a `CommandResult` value object (data-clump/primitive-obsession
  in `grade_error`); justify/name `MESSAGE_LIMIT = 16`; migrate `coverage_enabled`/`pup_mode`
  onto `env_flag_enabled` now (or file it) rather than leaving transient triplication;
  deep-mirror the eval unit tests (`tests/unit/evals/skills/configure/`); insert the pyrefly
  `replace-imports` entries alphabetically; confirm the `Epochs` import path; parametrize
  `test_env.py` with case/whitespace variants; note the pinned model's retirement window.

### Assessment

The plan is in strong shape and converging — pass-2's concrete bugs are verified fixed and
the grading logic is now well-defended. Only **one** new finding genuinely changes the
design: the **plugin-shim / `allowed-tools` mismatch**, which must be resolved in Phase 2
§5 before the live run can work. Two correctness logic gaps (trailing-newline
reconciliation, the conflict-`set` extractor) are quick, worth-landing-now corrections.
Everything else is implementation-time detail or inherent pre-1.0 Phase-3 verification that
is reasonable to carry as explicitly-flagged assumptions. Recommend a small targeted edit
for those three items, after which the plan is ready to implement — the remaining long tail
is best resolved against the real Inspect/`inspect_swe` API during TDD, not by further
plan-only iteration.

## Re-Review (Pass 4 — verification) — 2026-07-07T09:20:54+00:00

**Verdict:** REVISE

This verification pass — the reviewers cross-tracing the plan against the *actual* shim,
`build:release`, `rust.py`, and `mise.toml` source — earned its keep: it caught five
**genuinely real, high-confidence defects**, four of them introduced or missed by the
pass-2/3 edits. These are concrete and quick to fix; none reopen the design. The pass-3
tail (differential gate, flakiness, Phase-3 verification) is confirmed resolved.

### Confirmed real defects (must-fix — several are self-inflicted by recent edits)

- 🔴 **Architecture + Portability (high)** — The pass-3 "plugin-shim" fix **cannot work as
  written**: `bin/luminosity` *unconditionally* minisign-verifies the launcher against the
  committed public key, `build:release` does **not** sign (signing needs the CI-only secret
  in `tasks/sign.py`), and the `LUMINOSITY_RELEASE_BASE_URL`/`LUMINOSITY_CACHE_DIR` overrides
  relocate the fetch but **do not skip verification**. So no developer can produce a
  `.minisig` the committed key accepts, and the with-skill arm's `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`
  path is unrunnable. **Fix:** put the *real launcher binary* at `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`
  in the image (bypass the shim/verify entirely — the eval grades config behaviour, not
  distribution); the `allowed-tools` path still matches.
- 🟡 **Test Coverage (high)** — The eval-logic unit tests under `tests/unit/evals/**` have
  **no wired runner**: `test:unit:tasks` only runs `tests/unit/tasks`, and nothing runs
  `tests/unit/evals`. The scorer/reducer/dataset tests — the eval's deterministic core —
  would be lint/type-checked but **never executed** in `mise run`/CI. **Fix:** add a
  `test:unit:evals` leaf, fold it into `test:unit`, and add a wiring assertion.
- 🔴 **Correctness (medium)** — `grade_precedence` has the **same trailing-newline bug** the
  get path fixed: the `sandbox().exec` level-scoped reads return `"personal-v\n"` but targets
  are bare, so `personal_read == expected_new` always fails and the precedence task grades
  INCORRECT every trial. **Fix:** append `"\n"` (or normalise the reads) at the precedence
  call site, mirroring the get path.
- 🟡 **Code Quality (high)** — The `coverage_enabled`/`pup_mode` migration rationale is
  **factually wrong**: in `rust.py`, `_FALSEY` backs `coverage_enabled` only; `pup_mode` uses
  a separate `_PUP_MODES` set with no falsey logic. The instruction to have `pup_mode` "import
  the shared `_FALSEY`" would add an **unused import → ruff F401 → breaks `check`**. **Fix:**
  scope the shared helper to `coverage_enabled` + `live_run_enabled`; drop the `pup_mode`
  clause.
- 🟡 **Standards (medium)** — `inspect-ai`/`inspect-swe` are placed in `[dependency-groups]
  dev`, but `tasks/eval/skills.py` imports `inspect_ai` — every other `tasks/`-imported dep
  (`invoke`, `semver`, `pathspec`, …) lives in the **`build`** group. **Fix:** move them to
  `build` (exact-pin style doesn't determine group).

### Additional confirmed refinements (worth landing)

- 🔵 **Correctness** — `seed_fixtures` must **reset the whole `.luminosity` subtree** (remove
  then seed), not overwrite individual files, else a prior epoch's agent-written
  `config.local.md` survives; and it must **write into the sandbox** (`sandbox().write_file`),
  not host FS.
- 🔵 **Correctness** — the bad-`--level` task must carry `level: "bad"` in metadata and
  `bash_result` must match the scoped command **regardless of exit code**, else the extractor
  returns `None` and the task false-fails.
- 🟡 **Compatibility** — front-load a **minimal Phase-2 spike** confirming `inspect_swe`'s CLI
  provisioning model (consumes the sandbox CLI vs. self-downloads, and whether `skills=`
  sees `${CLAUDE_PLUGIN_ROOT}`) *before* building the full Dockerfile/staging apparatus —
  a construct-without-raising test exercises none of it.
- 🔵 **Architecture** — `build:release` rewrites the committed `cli/launcher/bin/checksums.json`;
  a dev eval run would dirty that tracked coherence file. Stage into a scratch dir the
  Dockerfile COPYs from, or use a narrower single-triple build.
- 🔵 **Compatibility** — 3.14 contingency (b) (isolated lower-python env) conflicts with the
  in-process `from inspect_ai import eval` in `skills.py`; note it requires shelling out to
  that env.
- 🔵 **Compatibility / Portability** — verify the baseline arm suppresses skill **preload**
  (not just `Skill`-tool invocation) in Phase 3; broaden `scrub_paths` beyond the home-dir
  substring (temp roots, `/opt/homebrew`, hostnames); document the supported container runtime
  (Docker Desktop vs Colima/Podman) since the preflight is Docker-CLI-specific.
- 🔵 **Standards / Code Quality** — add a static `CC_VERSION`↔Dockerfile coherence test;
  rename `readback.pass_k` → `pass_k_fraction`; add the `expected_exit is None` and
  first-conjunct-negative `grade_precedence`/`grade_error` unit branches; note the flat-vs-
  deep test-layout split.

### Assessment

Not a regression in quality — the opposite: the plan is now detailed enough that a
source-tracing verification pass finds concrete, real defects instead of hand-waving
concerns. Five are must-fix (four self-inflicted by recent edits, all quick). The single
most important is the **shim/signature impossibility** — the pass-3 sandbox fix does not
actually run, and the clean resolution is to drop the shim and place the real launcher at
the expected path. After the five must-fixes (and ideally the front-loaded `inspect_swe`
provisioning spike, which de-risks the largest remaining unknown), the plan is ready to
implement. Recommend applying the five, then proceeding — the remaining tail is
implementation-time detail.

## Approval (Pass 5) — 2026-07-07T11:18:32+00:00

**Verdict:** APPROVE

The five pass-4 must-fixes are applied and the two follow-on correctness fixes folded in:

- ✅ **Shim/signature impossibility** — the eval image now places the real cross-built
  launcher at `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`, dropping the shim/verify/key
  entirely (the eval grades config behaviour, not distribution).
- ✅ **Unwired eval unit suite** — new `test:unit:evals` leaf folded into `test:unit`,
  guarded by a `test_mise_wiring.py` assertion.
- ✅ **`grade_precedence` trailing newline** — call site now reconciles the `\n`, matching
  the get path.
- ✅ **`pup_mode` false-DRY** — migration scoped to `coverage_enabled` only; `pup_mode`
  left untouched (avoids the ruff F401 that would break `check`).
- ✅ **Dependency group** — `inspect-ai`/`inspect-swe` moved to the `build` group (a
  `tasks/`-imported dependency).
- ✅ **`seed_fixtures`** — writes into the sandbox (`sandbox().write_file`, not host FS) and
  resets the whole `.luminosity` subtree (removes then re-seeds).
- ✅ **bad-`--level` task** — carries `level: "bad"`; `bash_result` matches the scoped
  command regardless of exit code.

Beyond the fixes, a **preliminary Phase 0** was added at the author's direction: a
code-light discovery phase that resolves the pre-1.0 integration unknowns (Python 3.14
resolution, `claude_code()` signature, `inspect_swe` CLI-provisioning model, the
`file.py@task` loader/import form, the real `Bash`/`Skill` transcript shape, the reducer
read-back shape) and records them — so no later phase is built on an unverified assumption.

**Basis for approval.** Over five passes the review drove the plan from an ambitious sketch
to an implementation-ready spec: the design is sound, phases are independently mergeable and
keep `mise run check` green, grading is deterministic and fail-closed, and the pre-1.0
integration risk is front-loaded into Phase 0 rather than deferred to the costly live run.
The residual findings are implementation-time polish (broaden `scrub_paths` beyond the
home-dir substring; document the supported container runtime; a static `CC_VERSION`↔Dockerfile
coherence test; rename `readback.pass_k` → `pass_k_fraction`; add the `expected_exit is None`
and first-conjunct-negative `grade_error`/`grade_precedence` branches) and inherent Phase-0/3
verification items — none blocking. **Approved to proceed to `/accelerator:implement-plan`.**
