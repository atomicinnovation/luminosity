---
type: plan-review
id: "2026-07-13-0017-per-skill-context-injection-review-1"
title: "Plan Review: Per-Skill Context Injection Implementation Plan"
date: "2026-07-13T21:50:58+00:00"
author: Toby Clemson
producer: review-plan
status: complete
parent: "plan:2026-07-13-0017-per-skill-context-injection"
target: "plan:2026-07-13-0017-per-skill-context-injection"
reviewer: Toby Clemson
verdict: APPROVE
lenses: [architecture, correctness, test-coverage, code-quality, security, usability, standards, documentation]
review_number: 1
review_pass: 3
tags: [configuration, context-injection, rust-cli, skills, evals]
last_updated: "2026-07-13T23:39:38+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Plan Review: Per-Skill Context Injection Implementation Plan

**Verdict:** REVISE

This is a strong, unusually well-evidenced plan: it extends story 0016's proven
hexagon rather than inventing a new subsystem, correctly identifies the
fail-safe boundary (validation inside `context_cli::run`, not a clap
`value_parser`) as the single most load-bearing design constraint, and makes the
ordering acceptance criterion structurally true by rendering both blocks from
one `format!`. The reasons to revise are not about direction — they are about a
handful of concrete design and mechanism gaps that recur across lenses: a
degrade path that collapses two now-independent failure domains into one
misattributed notice (flagged by six of eight lenses), a stringly-typed
`SKILL_PROSE.replace("{skill}")` template whose only justification is a test and
which fails silently on drift, a golden-pinning chain whose skill-block half has
no stable scraper anchor and whose new behaviour (block composition) is never
pinned to the Rust source, and several code snippets that will not pass the
workspace's own `mise run cli:check`. None is structural enough to force a
redesign; all are cheap to fix in the plan before implementation begins.

### Cross-Cutting Themes

- **The `--fail-safe` degrade path conflates the two independent assemblers**
  (flagged by: correctness, code-quality, architecture, usability, security,
  test-coverage) — The plan states "an `OnFailure::Degrade` read failure at
  *either* assembler renders the existing `## Project Context Unavailable`
  notice and exits zero." Because `run` returns immediately after printing that
  notice today (`context_command/inbound/cli.rs:65-68`), a malformed
  `.luminosity/skills/configure/context.md` — or an invalid `--skill` name —
  will (a) discard the perfectly readable **project** block, and (b) tell the
  user, under a header reading "The project-specific context for this repository
  could not be read", something false about which file failed. The named test
  `an_invalid_skill_name_under_fail_safe_exits_zero_with_a_notice` asserts
  exit-0-plus-a-notice but pins neither the surviving block nor which notice, so
  the wrong behaviour would pass. This is the single highest-value fix in the
  review.

- **`SKILL_PROSE.replace("{skill}", …)` is a fragile template shaped by a test**
  (flagged by: code-quality, correctness, standards, architecture,
  test-coverage) — The literal `{skill}` placeholder plus `str::replace` exists
  only to keep the Rust `const` scrapable by the Python golden test. `replace`
  is untyped and fails silently: a typo in the placeholder (`{skil}`) becomes a
  no-op that ships a literal brace in the prompt, and the Python scraper applies
  the *same* substitution so both agree. It also diverges from the file's
  established inlined-`format!` idiom, forcing the header scraper to special-case
  a second, differently-shaped regex.

- **The golden-pinning chain loses its skill-block half** (flagged by:
  test-coverage, correctness, architecture) — The existing header scraper anchors
  on the named `{PROSE}` interpolation; `render_skill` as written uses positional
  args, so the symmetric scraper has nothing unique to anchor on. More
  fundamentally, the one behaviour this story introduces — two-block composition
  (one blank line between, either omitted when empty) — lives in imperative code
  in `run`, not in any scrapable literal, so it is *restated* in Python rather
  than *pinned* to the Rust source, and can drift silently until a billed live
  run.

- **"Mirror rather than generalise" accretes on a schedule the plan already
  knows** (flagged by: architecture, code-quality, standards) — The duplicated
  artefacts (`SkillAssembly`≈`Assembly`, `SkillContext`≈`ProjectContext`, a
  second assembler, a second `Level::*_file_name`, a seventh `dispatch` arg) are
  mechanism, not domain language; the distinct language lives in the path rule
  and the header/prose regardless. Story 0018 is a known, blocked, structurally
  identical third instance, so the usual "rule of three, wait" defence does not
  apply — and several of these (the `combine.rs` extraction stopping one function
  short of the shared `contribution`/fold; `dispatch` reaching clippy's
  7-argument limit) are cheaper to settle now, at N=2, with 0016's suite green.

- **Several snippets fail the workspace's own lint gate** (flagged by: standards,
  code-quality, documentation) — The `config` crate uniformly carries `# Errors`
  doc sections, `#[derive(Debug, Clone, PartialEq, Eq)]`, `const fn new`, and
  `//!` module docs; the plan's snippets omit them, and `warnings = "deny"` with
  pedantic/nursery enabled turns each omission into a hard `mise run cli:check`
  failure. `Options` gaining `pub skill: Option<String>` silently breaks its
  `Copy` derive and trips `needless_pass_by_value`. These block each phase's own
  automated-verification criterion.

### Tradeoff Analysis

- **Silent-on-unknown-name (deliberate design) vs discoverability (usability)**:
  The plan deliberately declines to validate `--skill` against a known skill set
  — correct, since the CLI has no registry and a clap rejection would breach the
  fail-safe boundary. But the user's mirror-image failure (a mistyped
  *directory*, e.g. `.luminosity/skills/config/` matching the category dir) then
  produces zero feedback, and the nominated remedy (`--explain`) as specified
  cannot distinguish "typo" from "not written yet" and never reveals the
  discovered root. Recommendation: keep silence on the injection path, but have
  `--explain` (only) print the resolved root and enumerate sibling directories
  under `.luminosity/skills/`, which needs no registry.

- **Frontmatter stripping (author's decision) vs safe handling of user prose
  (correctness)**: Reusing `frontmatter::split` gives one primitive, but
  `context.md` is now free-form user prose. A file whose first line is `---`
  (a Markdown thematic break) is read as opening frontmatter — silently
  discarding the first section, or hard-failing as malformed. The decision to
  strip is sound; the plan should decide and pin the leading-`---` behaviour
  explicitly rather than leave it to `split`'s incidental semantics.

### Findings

#### Critical

_None._

#### Major

- 🟡 **Correctness / Code-Quality / Architecture / Usability / Security / Test-Coverage**: Degrade at either assembler discards the healthy block and misnames the failed file
  **Location**: Phase 2, §2 (empty-output / degrade policy)
  A skill-side read failure (or invalid `--skill` name) under `--fail-safe`
  suppresses a healthy `## Project Context` block and emits a
  `## Project Context Unavailable` notice whose prose names the wrong subsystem.
  Degrade each block independently; add `## Skill-Specific Context Unavailable`;
  pin with a `…_still_prints_the_project_block` black-box test.

- 🟡 **Code-Quality / Correctness / Standards**: `SKILL_PROSE.replace("{skill}", …)` is a stringly-typed template with a silent drift mode
  **Location**: Phase 2, §2 (`SKILL_PROSE` / `render_skill`)
  Bind the interpolated prose to a named local and render with the file's
  existing inlined-`format!` idiom (`let prose = …; format!("…{prose}\n\n{}", …)`),
  so a placeholder typo is a compile error and one scraper regex covers both
  renderers.

- 🟡 **Test-Coverage / Architecture**: Block composition — the one behaviour this story adds — is restated in Python, not pinned to the Rust source
  **Location**: Phase 4, §5 (extend the golden-pinning chain)
  Extract a pure `render_blocks(project, skill) -> Option<String>` with a
  scrapable `const BLOCK_SEPARATOR`, unit-test the four permutations against
  exact bytes, and/or add a CI-tier pytest that shells the compiled binary
  against each fixture and byte-compares stdout (closing the loop with zero
  tokens).

- 🟡 **Test-Coverage**: The header scraper has no stable anchor for `render_skill` as written
  **Location**: Phase 4, §5 / Phase 2, §2
  The positional-arg `format!` gives the symmetric skill-header regex nothing
  unique to bind to; it will silently match the wrong `format!` once a second
  one appears (0018). Fixed by the named-local rewrite above.

- 🟡 **Test-Coverage**: The committed-log gate cannot detect a stale log, so skipping Phase 5 leaves CI green
  **Location**: Phase 5 (live eval run)
  `test_results.py` asserts only that *some* log clears the floor; the existing
  5-sample log satisfies it unchanged after the dataset grows to 10. Add an
  assertion pinning the log's scenario set / sample count to the current dataset.

- 🟡 **Test-Coverage**: The deterministic eval arms grade the binary, not the injection — the new billed rows buy no new confidence
  **Location**: Phase 4, §4 / Phase 5
  Non-behavioural rows re-execute the binary and ignore the transcript, exactly
  duplicating the free Phase-2 black-box suite while costing 12 billed
  invocations. Move deterministic block-comparison to a CI-tier pytest; reserve
  the billed eval for a behavioural row that proves *both* blocks reached the
  model in order.

- 🟡 **Correctness**: The contract test generates the injection line from an unvalidated frontmatter name, reopening the prompt-discard hole
  **Location**: Phase 3, §4 (the contract test)
  A frontmatter `name:` with a space / leading `-` / dot yields an argv that
  clap rejects non-zero *outside* the fail-safe boundary — discarding the whole
  prompt — and the test would pin that broken line as correct. Assert the
  frontmatter name matches `^[A-Za-z0-9_-]+$` (the Python mirror of `SkillName`)
  before building the expected line.

- 🟡 **Correctness / Usability**: A hand-written `context.md` whose first line is `---` is silently truncated or hard-fails
  **Location**: Phase 1, §5 / Testing Strategy edge-case (4)
  The edge-case list covers a `---` inside the body but not at the start. Decide
  and pin the leading-`---` behaviour (treat-as-frontmatter vs preserve), and
  document it on the configure surface.

- 🟡 **Test-Coverage**: `_body()` breaks on the new fixtures and its missing-file fallback hides a mis-pathed fixture
  **Location**: Phase 4, §2-3 (fixtures and dataset rows)
  `_body` hard-codes `.luminosity/<name>` and `split("---", 2)[2]` (IndexError
  on a frontmatter-less file), and returns `""` for a missing file — so a typo'd
  fixture path degrades a scenario to "no context" with nothing failing.
  Generalise `_body`, and assert every claimed fixture file exists on disk.

- 🟡 **Architecture / Standards / Code-Quality**: The `--explain` skill lines reconstruct the path rule in the launcher, contradicting Phase 1's own "path rule lives entirely in config-adapters"
  **Location**: Phase 2, §3 (the `--explain` skill lines)
  The launcher independently rebuilds `skills/<name>/<file>`, so the two
  constructions can drift — silently, in the very diagnostic a user reaches for
  when the block is empty. Have the assembly carry its own resolved paths and
  render whatever it is handed.

- 🟡 **Architecture / Code-Quality / Standards**: "Mirror rather than generalise" duplicates mechanism (not language) on a schedule 0018 already sets
  **Location**: Implementation Approach
  Either generalise now (a two-level-`.luminosity`-document concept: one driven
  port, one `assemble`, distinct language kept in the source variant / path arm /
  renderer), or record an explicit exit criterion so the third copy in 0018 is a
  decision, not a default. Cheapest at N=2 with 0016 green.

- 🟡 **Code-Quality / Test-Coverage**: The `combine.rs` extraction stops one function short of single-sourcing the invariant it claims to
  **Location**: Phase 1, §2 / §4
  `contribution()`/`has_body` and the whole two-level fold stay duplicated in
  `skill.rs`, so the "`has_body` can never disagree" invariant is only
  half-shared. Extract the fold (`assemble_levels(...) -> (Option<String>,
  [LevelContribution; 2])`), and write *direct* tests for the shared primitives
  (they have none today — the plan's "move their unit tests with them" is not
  possible as stated, and drops the two CRLF cases).

- 🟡 **Security**: A committed symlink at the skill path yields arbitrary-file read / injection / DoS
  **Location**: Phase 1, §5 (`skill_context_path` / `read_split`)
  `SkillName` validates the name, but `read_split` follows a symlinked
  `context.md` (or `configure/` dir) to `/etc/passwd`, `~/.aws/credentials`, or
  `/dev/zero`. Reject symlinked components or canonicalise-and-bound the path
  under `.luminosity/skills`, and add it as a named threat + black-box test.

- 🟡 **Security / Architecture**: Per-skill context is an unnamed cross-user / supply-chain prompt-injection channel
  **Location**: Phase 2, §2 (the injected body)
  A committed `.luminosity/skills/<skill>/context.md` — harder to spot in review
  than a top-level config change — is spliced near the top of the prompt as
  apparent instruction. 0016's plan recorded this trust boundary explicitly; this
  plan drops it. Carry the note forward and re-assert the skill's binding
  constraints *after* the injected block.

- 🟡 **Usability**: A mistyped skill directory fails silently and `--explain` as specified cannot diagnose it
  **Location**: What We're NOT Doing / Phase 2, §3
  `--explain` prints `not found` for both levels — indistinguishable from "not
  written yet", and blind to the typo'd sibling directory. Under `--explain`
  only, enumerate existing `.luminosity/skills/` entries and hint when the
  requested one is absent but siblings are present.

- 🟡 **Usability**: `--explain` never discloses the resolved project root or the full path it read
  **Location**: Phase 2, §3
  `discover` walks upward, so a user in a subdirectory can get `not found` while
  staring at the file they wrote. Print the discovered root once and render each
  level line with its full, copy-pasteable path.

- 🟡 **Usability**: The configure-surface section is specified too thinly for a user to succeed
  **Location**: Phase 3, §2
  The configure skill is the *only* user-facing doc surface, yet the section is
  specified only as "names both paths / user action / points at `--explain`" —
  omitting the naming rule (the skill's own `name`, not the `skills/config`
  category dir), that the nested dir is hand-created, the silence-on-wrong-name
  behaviour, and the git-ignored personal level. Enumerate required content and
  extend the tests.

- 🟡 **Standards / Code-Quality / Documentation**: New public surface omits the crate's uniform `# Errors` docs, derives, `const fn`, and `//!` module docs
  **Location**: Phase 1, §2 / §4
  Blocks each phase's own `mise run cli:check`. Mirror `key.rs`/`context.rs`
  item-for-item; give `SkillName` a `Display` impl.

- 🟡 **Standards**: Adding `skill: Option<String>` to `Options` silently breaks its `Copy` derive and by-value signature
  **Location**: Phase 2, §2 (`Options`)
  Resolve in the plan: hold `Option<&'a str>` to keep `Copy`, or drop `Copy` and
  take `&Options`. Show the derive line either way.

- 🟡 **Standards**: The scorer's `--skill configure` argv becomes an unpinned hand-synced mirror of the SKILL.md injection line
  **Location**: Phase 4, §4
  The repo's standing convention pins every such mirror (block-prefix, msrv, mise
  wiring). Add a test scraping the injection line out of `SKILL.md` and asserting
  the scorer reproduces it; extract the argv to a module constant.

- 🟡 **Standards**: Phases 5 and 6 are not increments, and the plan never states the per-phase mergeability property 0016's did
  **Location**: Phase 5 / Phase 6
  Fold Phase 6 into every phase's Success Criteria (as 0016 did), keep Phase 5 as
  the live-run step, add the explicit "each phase is a mergeable increment"
  sentence, and move the already-applied story correction out of Phase 1's
  Changes Required.

- 🟡 **Documentation**: ADR-0003 promised to record per-skill extension internals as decisions; this story builds them yet records nothing durable
  **Location**: What We're NOT Doing ("Not raising a Luminosity ADR")
  ADR-0003 describes the per-skill surface as single-file `context.md`; this
  story makes it two-level and strips frontmatter — both divergences recorded
  only in the ephemeral work-item/plan. Amend ADR-0003 (or raise a short
  successor) and update its layout text and its in-body "ADR-0020" citations.

#### Minor

- 🔵 **Correctness**: `shutil.copytree` into the pre-created `.luminosity` dir raises `FileExistsError`
  **Location**: Phase 4, §1
  `_seed` does `destination.mkdir()` before copying; drop that line or pass
  `dirs_exist_ok=True`, and make the new `test_solvers.py` assert placement and
  content, not merely "didn't raise".

- 🔵 **Correctness**: The scorer re-executes `context --skill configure` without `--fail-safe`
  **Location**: Phase 4, §4
  The two forms diverge exactly on the failure paths this story adds. Re-execute
  the injected argv verbatim (`--skill configure --fail-safe`).

- 🔵 **Test-Coverage**: No test pins the composed degrade output when only the skill file is malformed
  **Location**: Phase 2, §2 and tests
  Add `…_names_the_skill_file_in_the_notice` and
  `…_still_prints_the_healthy_project_block`.

- 🔵 **Test-Coverage**: No test pins that `--explain` without `--skill` emits only the two config lines
  **Location**: Phase 2, §3
  Add `explain_without_a_skill_reports_only_the_config_levels` with an exact-line
  assertion, not `contains`.

- 🔵 **Test-Coverage**: The git-ignore acceptance criterion has no automated test — only a manual `git check-ignore`
  **Location**: Phase 3, §3
  A subtly over-broad pattern that also swallowed `context.md` is a data-loss
  bug. Add a unit test shelling `git check-ignore` for team/personal ×
  inside/outside-fixtures.

- 🔵 **Architecture / Code-Quality / Standards**: `Level::skill_context_file_name` accretes file-kind knowledge onto a level-identity type
  **Location**: Phase 1, §3
  0018 forces a third accessor. Give `Level` its qualifier (`""`/`".local"`) and
  let each artefact compose its name, or introduce a small document-kind concept.

- 🔵 **Architecture / Code-Quality**: Block ordering is composed inside imperative `run`, so the headline invariant is observable only through a process spawn
  **Location**: Phase 2, §2 and tests
  Extract a pure `compose`/`render_blocks` and unit-test the four permutations;
  reduce `run` to assemble → compose → print-once. (Same fix as the
  composition-pinning major.)

- 🔵 **Architecture / Code-Quality / Standards**: `dispatch` reaches seven parameters; 0018's assembler is the eighth and trips `too_many_arguments`
  **Location**: Phase 2, §4
  Bundle the injected ports into a `Ports`/`Handlers` struct now, while it is a
  two-line change, and build it once in `main.rs` instead of per resolver branch.

- 🔵 **Code-Quality / Standards**: `read_split(&self, path)` never uses `self` (trips `unused_self`) and is named for its return type
  **Location**: Phase 1, §5
  Make it a free function beside `io_error`/`display`; name it for intent
  (`read_document` / `read_and_split`).

- 🔵 **Standards**: New module names break the crate's noun-per-concept convention
  **Location**: Phase 1, §2
  `combine.rs` is a verb; `skill.rs` actually holds skill *context*. Prefer
  `body.rs`/`levels.rs` and `skill_context.rs` (`module_name_repetitions` is
  already allowed).

- 🔵 **Standards**: `SkillAssembly` reuses `LevelContribution` from `context.rs`, coupling two sibling domain modules
  **Location**: Phase 1, §4
  Move `LevelContribution` into the shared module (or `level.rs`) so neither
  sibling depends on the other; note the `Assembly`/`SkillAssembly` naming
  asymmetry.

- 🔵 **Standards**: The `--explain` lines use a different grammar from the established diagnostic
  **Location**: Phase 2, §3
  Keep `<level> (<path>): <state>`; lead with the level, disambiguate with the
  path, don't replace the level word with `skill <name>`.

- 🔵 **Standards**: The `cargo nextest` verification commands omit the `cd cli &&` the workspace layout requires
  **Location**: Phase 1 / Phase 2 Success Criteria
  Prefix each cargo line with `cd cli &&`, matching 0016's plan.

- 🔵 **Standards**: `pup:check` is credited with enforcing the serde-free core, which it does not govern
  **Location**: Phase 1 Success Criteria
  The serde ban is `deny.toml` alone; `pup.ron` governs only launcher-crate
  module imports. Attribute the guarantee to `deny:check`.

- 🔵 **Test-Coverage**: `combine`/`trim_blank_lines` have no direct tests today, so "move their unit tests with them" is impossible and drops CRLF coverage
  **Location**: Phase 1, §2
  Write direct tests (incl. the two CRLF cases) in the shared module; pare the
  skill suite to what is genuinely distinct.

- 🔵 **Test-Coverage**: Nothing pins the frontmatter `name` to the directory name users actually type
  **Location**: Phase 3, §4
  Add `test_the_frontmatter_name_matches_the_skill_directory_name` to the
  parametrized wiring class.

- 🔵 **Documentation**: The `context` subcommand's top-level clap help still describes only project context
  **Location**: Phase 2, §1
  Update the `Command::Context` summary so `--skill` is discoverable from
  `luminosity --help`.

- 🔵 **Usability**: Nothing lowers activation energy — no scaffolding, and the agent lacks the grant to create the file
  **Location**: Desired End State / Phase 3, §2
  At minimum print copy-pasteable absolute paths under `--explain` and render the
  configure commands with the concrete skill name.

- 🔵 **Security**: The `SkillName` allow-list admits reserved device names and has no length bound
  **Location**: Phase 1, §4
  Low likelihood (the argument is trusted SKILL.md text). Optionally cap length /
  screen Windows device names, or document the intentional omission.

- 🔵 **Security**: Personal context leaves the machine, and eval-log scrubbing covers paths not content
  **Location**: Phase 5 / Phase 3, §3
  Note that per-skill personal context is transmitted to the model like any
  other, and committed fixtures/logs must carry only opaque sentinels.

#### Suggestions

- 🔵 **Correctness / Test-Coverage**: The Python `_trim` model and Rust `trim_blank_lines` disagree on a CRLF final line
  **Location**: Phase 4, §2 / §5
  Normalise `_trim` (`rstrip("\r")` on the last kept line) or add a
  `.gitattributes` `text eol=lf` for the fixtures.

- 🔵 **Architecture / Documentation**: The `config` crate's charter and error prose drift toward "everything read from `.luminosity/`"
  **Location**: Phase 1, §4
  `MalformedFrontmatter` renders "config file '<path>'" for a broken skill
  context. Restate the crate charter or generalise the error prose to name the
  file rather than assert its kind.

- 🔵 **Code-Quality / Standards**: `Assembly` reads ambiguously once `SkillAssembly` exists
  **Location**: Phase 1, §4
  Rename `Assembly` → `ProjectAssembly` in lockstep — a mechanical rename that
  keeps the pair symmetric.

- 🔵 **Usability**: The invalid-skill-name message states the rule but not the remedy
  **Location**: Phase 1, §4
  Name the flag and give an example: `invalid --skill name '<name>': … (e.g.
  'configure')`.

- 🔵 **Standards**: The `injection_line` helper breaks the file's `_`-prefix private-helper convention
  **Location**: Phase 3, §4
  Name it `_injection_line`; keep a public `INJECTION_TEMPLATE` as the pinned
  artefact; state how the expected name is parsed from frontmatter.

- 🔵 **Documentation**: The configure-surface spec should pin literal `<skill-name>` placeholder vs concrete `configure`
  **Location**: Phase 3, §2
  State which form the prose and `TestConfigureSurface` assertions expect.

### Strengths

- ✅ The one-command / one-`format!` decision makes the ordering and
  absent-global acceptance criteria structurally true rather than a fragile
  two-line SKILL.md convention — and correctly removes the need for a new
  subcommand, an `allowed-tools` change, an `is_root_help` entry, and a second
  fail-safe boundary.
- ✅ Keeping skill-name validation inside `context_cli::run` rather than a clap
  `value_parser` — because a clap error exits non-zero *before* `--fail-safe` is
  consulted, discarding the whole prompt — is a genuinely sharp insight derived
  from the `!` preprocessor's failure mode, verified against `main.rs`, and
  carried by an explicit load-bearing test.
- ✅ `SkillName` as an allow-list newtype constructed only via `parse`, with
  `skill_context_path(&SkillName, …)`, makes name-based path traversal
  unrepresentable at the port boundary — explicitly better than the accelerator's
  unvalidated `$SKILL_NAME` interpolation it declines to port.
- ✅ The hexagon's purity is preserved and re-verified (`deny:check`) rather than
  assumed; the plan correctly reads the serde ban as living in `deny.toml`.
- ✅ Extending the existing `context` eval capability rather than adding a billed
  arm keeps the three exact-list tripwires green unmodified.
- ✅ Upgrading the registry-walking contract test to derive the expected `--skill`
  argument from each SKILL.md's own frontmatter closes the realistic copy-paste
  failure a literal cannot see.
- ✅ The plan's edge-case analysis (`---` thematic break *inside* the body, CRLF
  reuse, the `{skill}`-in-a-name injection question) is unusually thorough and
  mostly correct.
- ✅ Migration Notes "None" is correctly and explicitly justified: the feature is
  purely additive and the no-`--skill` path is unchanged and already pinned.
- ✅ The plan's document shape closely mirrors the sibling 0016 plan, with correct
  frontmatter and a verified ADR-0020 claim.

### Recommended Changes

1. **Degrade the two assemblers independently** (addresses: the degrade-path
   conflation across six lenses). Assemble project and skill contexts
   separately; render whichever succeeded; append a distinct
   `## Skill-Specific Context Unavailable` notice (naming the skill and its file)
   for a skill-side failure. Add black-box tests
   `a_malformed_skill_context_under_fail_safe_still_prints_the_project_block` and
   `…_names_the_skill_file_in_the_notice`. State whether `--explain` still prints
   on degrade.

2. **Replace `SKILL_PROSE.replace("{skill}")` with a named-local `format!`**
   (addresses: the fragile-template theme; the header-scraper-anchor major).
   `let prose = SKILL_PROSE.replace("{skill}", skill.as_str()); format!("##
   Skill-Specific Context\n\n{prose}\n\n{}", context.body)` — or give `SkillName`
   a `Display` impl and interpolate directly. Keeps the literal scrapable, makes
   a placeholder typo a compile error, and lets one scraper regex cover both
   renderers.

3. **Extract and unit-test the block composition; pin it (and the deterministic
   eval scenarios) at the CI tier** (addresses: composition-not-pinned;
   deterministic-arms-grade-the-binary; stale-log gate). Add a pure
   `render_blocks(...)` with a scrapable `const BLOCK_SEPARATOR`; add a CI-tier
   pytest that shells the compiled binary against each fixture and byte-compares
   stdout; add a committed-log assertion pinning the log's scenario set to the
   dataset; reserve the billed live eval for a behavioural row proving both
   blocks reach the model in order.

4. **Make every snippet pass `mise run cli:check` as written** (addresses: the
   lint-gate theme). Add `# Errors` sections, `#[derive(Debug, Clone, PartialEq,
   Eq)]`, `const fn new`, and `//!` module docs to the new surface; resolve the
   `Options` `Copy`/by-value question explicitly; make `read_split` a free
   function; prefix verification commands with `cd cli &&`; attribute the
   serde-closure guarantee to `deny:check` alone.

5. **Close the frontmatter-name / traversal / silent-typo gaps** (addresses: the
   unvalidated-contract-name major; the symlink major; the leading-`---` major;
   the discoverability majors). Assert the frontmatter `name` matches the Rust
   allow-list before building the injection line; reject/canonicalise symlinked
   skill paths and add a threat + test; decide and pin the leading-`---`
   behaviour; have `--explain` (only) print the discovered root and enumerate
   sibling `.luminosity/skills/` directories.

6. **Settle the generalisation-vs-mirror question before 0018 forces it**
   (addresses: the accretion theme). Either extract the whole two-level fold
   (not just `combine`/`trim_blank_lines`) and record an explicit exit criterion
   for 0018, or bundle `dispatch`'s ports into a struct now. Move file-kind
   knowledge off `Level`.

7. **Fix the eval plumbing details** (addresses: `_seed` FileExistsError; scorer
   argv without `--fail-safe`; `_body` breakage; the CRLF `_trim` mismatch).
   Drop the pre-`mkdir`; re-execute the injected argv verbatim; generalise
   `_body` and assert fixture files exist; normalise the Python trim model.

8. **Restructure the phases and the durable docs** (addresses: phases-not-
   increments; ADR-0003 durability). Fold Phase 6 into each phase's Success
   Criteria, state the per-phase mergeability property, move the already-applied
   story correction out of Changes Required; amend ADR-0003 (or raise a
   successor) for the two-level + frontmatter-stripping divergences and its
   in-body ADR-0020 citations; update the `context` subcommand help; enumerate
   the configure-surface section's required content.

## Per-Lens Results

### Architecture

**Summary**: A disciplined, well-evidenced extension of 0016's hexagon — domain
core stays serde/fs-free, `SkillName` makes traversal unrepresentable at the
port boundary, and the single-command decision turns ordering into a structural
property. The core "mirror rather than generalise" decision does not survive
scrutiny (what is duplicated is mechanism, not language) and accretes on the
schedule 0018 already sets. Three sharper structural issues warrant fixing
before build: the `--explain` path duplication contradicting Phase 1's own
purity criterion; the degrade path collapsing two independent failure domains
into one misleading notice; and block ordering composed imperatively in `run`
rather than in a pure, unit-testable function.

**Strengths**: One-command/one-`format!` ordering; the fail-safe validation
insight; `SkillName` allow-list newtype; re-verified hexagon purity; shared
combination primitives preserving the `has_body` invariant; eval-capability
extension avoiding a new billed arm; contract-test name derivation.

**Findings**: (major) mirror-vs-generalise accretion [medium]; `--explain`
path-rule duplication [high]; degrade conflation [high]. (minor)
`Level::skill_context_file_name` open-closed erosion [high]; ordering composed
in `run` not a pure fn [high]; `dispatch` parameter growth [high]. (suggestion)
`config` crate charter/error-prose drift [medium]; `SKILL_PROSE` lexical
cross-language contract [medium].

### Correctness

**Summary**: Unusually rigorous about the two properties that matter most — the
byte-level output composition (verified correct in all four permutations) and
the fail-safe boundary (verified against `main.rs`: `try_parse` → `error.exit()`
before dispatch). The material gaps are elsewhere: the degrade path discards a
healthy block and misattributes the failure; the contract test generates the
injection line from an unvalidated frontmatter name, reopening the
prompt-discard hole; a leading-`---` in user prose is silently truncated; and
several Phase-4 Python helpers (`_seed`, `_body`, `_rust_header`) will not
survive the changes as written.

**Strengths**: The one-`println!` byte claim; the fail-safe reasoning; the
`{skill}`-in-a-name safety (allow-list rejects braces, `replace` never re-scans);
the `---`-in-body round-trip; CRLF reuse; frontmatter-name derivation.

**Findings**: (major) degrade discards + misnames [high]; contract test on
unvalidated name [medium]; leading-`---` truncation [medium]. (minor) copytree
FileExistsError [high]; `_body`/`_rust_header` not reusable [medium]; scorer
argv drops `--fail-safe` [high]. (suggestion) Python `_trim` vs Rust CRLF
disagreement [high].

### Test Coverage

**Summary**: The Rust tiers are close to exhaustive and the black-box isolation
claim checks out (and matters more than the plan lets on — `CARGO_TARGET_TMPDIR`
is inside the repo, so the `.git` marker is load-bearing). The weaknesses are
above the Rust line: the golden chain restates the new block-composition rather
than pinning it; the skill-header scraper has no stable anchor; the live-eval
gate cannot detect a stale log; the deterministic eval arms re-grade the binary
(duplicating the free black-box suite) instead of observing the prompt; and
several ACs (git-ignore, malformed-skill degrade shape) have no named test.

**Strengths**: Verified black-box isolation; fail-safe tested at both ends;
reusing the four existing fixtures as free absent-coverage; tripwires kept green;
vacuity guard preserved; a named `_seed` regression test.

**Findings**: (major) composition restated not pinned [high]; scraper anchor
[high]; stale-log gate [high]; deterministic arms grade the binary [high]; no
composed-degrade test [medium]; `_body` breakage hides mis-pathed fixtures
[medium]. (minor) "move their unit tests" impossible + CRLF dropped [high]; no
`--explain`-without-`--skill` test [high]; git-ignore AC untested [medium];
frontmatter-name vs directory-name unpinned [medium]. (suggestion) `_seed` test
should assert placement [high].

### Code Quality

**Summary**: Well-shaped for maintainability — mirrors 0016, validates inside
the fail-safe boundary, tests-first in rich domain language. Weaknesses cluster
in three places: the stringly-typed `SKILL_PROSE.replace` that fails silently on
drift; the degrade path conflating two blocks into one misleading notice; and a
shared-primitive extraction that stops one function short of single-sourcing the
invariant it claims. Several snippets also will not pass the workspace's denied
pedantic/nursery lint set.

**Strengths**: The fail-safe reasoning; `Options` as a boundary DTO; the
allow-list; one-command ordering; path-first `read_raw` recut; comment-bar
respected.

**Findings**: (major) `SKILL_PROSE.replace` silent drift [high]; degrade
conflation [high]; `combine.rs` extraction stops short [high]. (minor)
`read_split` `unused_self`/naming [high]; missing doc/derive/const hygiene
[high]; `Level` file-kind accretion [medium]; `dispatch` data clump [high].
(suggestion) `Assembly`/`SkillAssembly` naming asymmetry [medium].

### Security

**Summary**: Several genuinely good choices — allow-list newtype, validation
inside the fail-safe boundary, an `--explain` that reports presence not content.
But it inherits and slightly widens 0016's untrusted-content problem without
carrying forward 0016's explicit trust-boundary note, and never considers that
the new `.luminosity/skills/<name>/` tree can be planted with symlinks or
special files — turning a committed repo file into an arbitrary-file read and an
injection channel. Name-based traversal is defeated; path-based (symlink)
traversal and the degrade fallback under a hostile file are unexamined.

**Strengths**: allow-list over deny-list; single-entry newtype enforcement;
validation inside the fail-safe boundary; `--explain` not a disclosure surface;
correct `.gitignore` pattern.

**Findings**: (major) committed-symlink arbitrary read / injection / DoS
[medium]; unnamed cross-user prompt-injection channel [high]. (minor) malformed
skill file suppresses the project block [medium]; allow-list admits device names
/ no length bound [low]; personal context leaves the machine, scrubbing covers
paths not content [low].

### Usability

**Summary**: Extends an already-good surface in the most predictable direction,
and the `--skill` help correctly frames it as additive. But the feature's only
success path is a hand-created, exactly-named nested directory that nothing
scaffolds, lists, or validates — and the chosen remedy (`--explain`) is specified
in a shape that cannot diagnose the two most likely causes (a mistyped name, a
config root discovered elsewhere) because it prints neither the resolved root nor
the level per line. The reused degrade notice also misattributes a skill failure
to the project config.

**Strengths**: one-command rendering; the `--skill` help wording; validation
inside `run`; mirroring the project-context model; contract-test name derivation;
manual-verification walks the real user path.

**Findings**: (major) mistyped dir fails silently + `--explain` can't diagnose
[high]; `--explain` hides the resolved root [high]; degrade misattribution +
unspecified partial-failure policy [high]; configure surface specified too thinly
[medium]. (minor) skill `--explain` lines drop the level label [high]; no
scaffolding / agent lacks the grant [medium]; `context` top-level help stale
[high]. (suggestion) invalid-name message lacks a remedy [medium].

### Standards

**Summary**: Unusually well-grounded — mirrors 0016's shape, correctly reads the
serde ban as `deny.toml`-only, verifies the ADR-0020 claim (Luminosity's series
ends at ADR-0011, no ADR-0020), and reads the existing `context*` grant as
already covering `--skill`. The gaps are almost entirely in the snippets:
missing `# Errors`, missing derives, and the `Options` `Copy` break each fail
`mise run cli:check`. Two structural gaps stand out: the scorer's `--skill`
argv is a new unpinned hand-synced mirror (the repo pins every such mirror), and
Phases 5-6 are not increments, so the phase set is not uniformly mergeable the
way 0016's explicitly was.

**Strengths**: verified ADR-0020 claim; sound `deny:check` analysis; correct
grant reading; validation inside the fail-safe boundary; tripwires preserved;
frontmatter matches 0016; one file-reading primitive.

**Findings**: (major) missing `# Errors` [high]; missing derives/`//!` [high];
`Options` `Copy` break [high]; unpinned scorer argv [high]; Phases 5-6 not
increments [medium]. (minor) verb-named modules [medium]; `LevelContribution`
sibling coupling [high]; `Level` file-kind accretion [medium]; `--explain`
grammar drift [high]; missing `cd cli &&` [high]; `pup:check` misattribution
[high]; `{skill}`/`replace` idiom divergence [medium]. (suggestion)
`injection_line` naming [medium]; `dispatch` `too_many_arguments` for 0018
[high].

### Documentation

**Summary**: The plan is itself exemplary documentation and correctly targets
the real user surface (the configure SKILL.md) rather than the stub README,
mirroring 0016. The dominant risk is durability: ADR-0003 explicitly promised to
record per-skill extension internals as their own decisions, yet this story
builds that surface and diverges from the accelerator twice while recording
those decisions only in the ephemeral work-item/plan. Secondary gaps: the stale
`context` subcommand help and the new public surface not explicitly held to the
crate's thorough doc-comment standard.

**Strengths**: documents on the surface the project actually uses; extends the
golden-pinning chain so the prose lives in one authoritative place; Migration
Notes "None" correctly justified; self-documenting contract test.

**Findings**: (major) ADR-0003 durability gap [medium]. (minor) stale `context`
subcommand help [high]; new public surface not held to the doc standard [medium];
ADR-0020 fix doesn't reach ADR-0003's in-body citation [medium]. (suggestion)
configure-surface placeholder-vs-concrete ambiguity [low].

---
*Review generated by /accelerator:review-plan*

## Re-Review (Pass 2) — 2026-07-13

**Verdict:** REVISE (converging — direction confirmed sound; remaining items are
plan-precision fixes, several trivial)

The rewrite adopted all four author design decisions (independent degradation,
generalise-now, symlink rejection, mapping-only frontmatter strip) plus the
mechanical fixes, and every lens confirmed the direction: "materially
strengthens", "a genuine DDD improvement", "materially improves documentation
durability". The prior review's dominant themes are resolved. What the second
pass surfaced is a batch of **specify-the-mechanism-more-precisely** findings
(15 major, all medium/low confidence, none critical) — a handful are genuine
(the symlink check will fail the macOS black-box tests as specified; a snippet
won't compile; the CI render test can't find its binary), the rest are
cheap precision or naming refinements. This is normal convergence, not a
reversal.

### Previously Identified Issues

- 🟡 **Degrade-path conflation** (was flagged by 6 lenses) — **Resolved.**
  Independent per-source degradation with a distinct `## Skill-Specific Context
  Unavailable` notice; correctness, security, and usability confirm the fix
  produces correct bytes and the right file attribution.
- 🟡 **`SKILL_PROSE.replace` silent drift** — **Resolved.** The inline
  `format!("…{skill}…")` capture is verified valid Rust (Display via `impl<T:
  Display> Display for &T`), compile-checked, and still scrapable.
- 🟡 **Composition not pinned to Rust / scraper anchor** — **Partially
  resolved.** `BLOCK_SEPARATOR` + a generalised header scraper + a CI render
  test are added; but the CI render test's binary-location story is unspecified
  and likely broken at the `test:unit:evals` tier (new major, below), and the
  pure `compose(&[String])` still doesn't *encode* ordering (new major, below).
- 🟡 **Mirror-vs-generalise accretion** — **Resolved** via generalise-now; the
  `ContextSource`/one-port/one-assembler decomposition is clean and confirmed by
  architecture and code-quality.
- 🟡 **Snippets fail the lint gate** — **Mostly resolved** (derives, `# Errors`,
  `const fn`, `Options` losing `Copy`, `cd cli &&`, `pup:check` re-attribution);
  but the rewrite **introduced** a new one: `render_skill_unavailable` takes an
  unused `skill_name` (new major, below).
- 🟡 **Symlink traversal** — **Partially resolved.** The control + `UnsafePath`
  variant exist, but the spec is too thin to implement safely (new major,
  below).
- 🟡 **Prompt-injection trust boundary** — **Still present.** The rewrite did
  not carry 0016's trust-boundary note forward; security re-flagged it (still
  present, below).
- 🟡 **Contract test on unvalidated name** — **Resolved** (allow-list assertion
  + directory-name match); one residual edge (a leading `-` still admitted) is a
  new minor, below.
- 🟡 **Leading `---` truncation** — **Resolved** via mapping-only strip; two
  sub-cases (malformed-YAML injected whole; leading `---` with no close fails
  loud) are a new minor to pin, below.
- 🟡 **`--explain` path duplication + hidden root** — **Resolved** by threading
  the path through `LevelBody`/`LevelContribution`; but three new `--explain`
  gaps emerged (silent on degrade error; relative-vs-absolute example mismatch;
  root marker not sourced), below.
- 🟡 **Configure surface thin** — **Resolved.** Content enumerated against the
  project-context register with concrete-name assertions.
- 🟡 **Phases 5/6 not increments** — **Resolved.** Explicit mergeability
  statement + folded criteria.
- 🟡 **ADR-0003 durability** — **Partially resolved.** A well-specified section
  was added, but the record is owned by no phase, so it can still slip (still
  present, below).
- 🔵 **Assorted minors** (`Level` accretion, `dispatch` args, `read_split`
  `unused_self`, module naming, `cd cli &&`, `pup:check`, `--explain` grammar,
  git-ignore test, `_seed` FileExistsError, scorer `--fail-safe`) — **Resolved.**

### New Issues Introduced (or newly surfaced by the rewrite)

- 🟡 **Symlink containment is under-specified** (correctness, security). The
  containment *root* is not stated to be canonicalised — on macOS `/tmp` →
  `/private/tmp`, so the Phase-1 adapter tests and black-box tests (which root
  under `CARGO_TARGET_TMPDIR`/`temp_dir()`) would spuriously hit `UnsafePath`.
  Also: `canonicalize` requires existence (vs. missing-file-stays-`Ok(None)`),
  and only a symlinked *file* is tested, not a symlinked directory component.
  **The most substantive item to fix.**
- 🟡 **`render_skill_unavailable(skill_name, error)` never uses `skill_name`**
  (correctness, code-quality, standards — 3 lenses). Unused param under
  `warnings = "deny"` → won't compile as written. Drop the param (the error
  already carries the path) or interpolate it.
- 🟡 **The pure `compose(&[String])` doesn't encode ordering** (architecture).
  The headline "structurally true" claim isn't delivered by the signature — the
  order is still set by push-order in `run`. Give it ordered params:
  `compose(project: Option<String>, skill: Option<String>)`.
- 🟡 **The CI render test can't locate/build the binary** (test-coverage).
  `test_context_render.py` under `test:unit:evals` neither builds `launcher` nor
  sets `LUMINOSITY_EVAL_PLUGIN_DIR`; specify a `build:launcher` depends +
  `host_binary_path()`, or an in-test `cargo build`.
- 🟡 **Live-run scope + stale-log gate are unspecified/inconsistent**
  (test-coverage). Nothing filters the dataset to behavioural rows, so the
  "2 arms not 5" cost claim is unsubstantiated; and the gate mixes a
  full-dataset scenario set with a behavioural-only count. Add the dataset
  filter (or a `context_behavioural_dataset.json`) and make both gate halves
  reference the same subset.
- 🟡 **`--explain` goes silent for a source that errors under `--fail-safe`**
  (usability). No `Assembly` on the degrade path → no level lines, exactly when
  the user is debugging. Surface the attempted paths + an `unreadable`/`unsafe`
  state even on error.
- 🟡 **`--explain` example shows relative paths but the data flow yields
  absolute** (usability). `display(&path)` is absolute; decide relative-to-root
  (matches the example) vs absolute and state it.
- 🟡 **Two module `//!` docs are now inaccurate** (documentation). `context.rs`
  ("project-context … config-file bodies") and `context_command/inbound/cli.rs`
  ("the byte-exact `## Project Context` block … fail-safe policy") describe only
  the project case; flag both for a rewrite.
- 🟡 **Prompt-injection trust boundary still unnamed** (security). Carry 0016's
  note forward; state the injected body is untrusted committed data and require
  the skill's binding constraints to sit after the block.
- 🟡 **The successor ADR is owned by no phase** (documentation). Make it a
  concrete deliverable with a success criterion; leave only amend-vs-successor
  to the author.
- 🟡 **New public types lack item-level `///` docs** (documentation). The Phase 1
  checklist lists derives/`# Errors`/`const fn`/`//!` but not the per-item `///`
  summaries the `config` crate carries uniformly (`ContextSource`, `LevelBody`,
  `Context`, the two traits).
- 🔵 **Minors** — a display `path: String` in the serde-free core is a courier
  value (architecture, code-quality: call it a deliberate DTO concession); the
  inline comment in the `read_body` snippet violates the comment bar (code-
  quality, standards: move to a `///`); `Context` / `compose` / `Ports<Rp,Cfg,…>`
  naming (code-quality, standards: prefer `AssembledContext`/`join_blocks`/
  spelled generics); the `Ports` argument-count rationale no longer holds under
  generalise-now (architecture: justify on readability, not the lint); a leading
  `-` still admitted by the allow-list (security: forbid it or use `--skill=`);
  malformed-YAML-injected-whole vs config's loud path (correctness: pin the
  sub-cases); the skill prose says "context above" which dangles in the
  absent-global case (usability); the crate/`ConfigError` name drifts past
  "config" (architecture: note for a follow-up); the render test must replicate
  `grade_block`'s trailing-newline rule and a both-sources-fail case is uncovered
  (test-coverage); the `_body` raise-on-missing conflicts with `_expected_block`
  reading both levels (test-coverage: declare a scenario's sources); the
  whitespace-present-discovered-without-body case may be dropped from the
  rewritten assembler suite (test-coverage: carry it forward).

### Assessment

The plan is close. The generalise-now rewrite is confirmed sound by every lens,
and the prior review's structural themes are resolved. The remaining work is a
second, **smaller and more mechanical** pass: three items would actually bite an
implementer (the un-canonicalised containment root failing the macOS tests, the
unused-parameter compile break, and the CI render test's missing binary), and
the rest are precision, naming, and doc-accuracy refinements plus the two
carry-over items I under-addressed (the prompt-injection note and the
ADR ownership). None reverses a decision; none is critical. One more revision
cycle on these should reach APPROVE.

## Re-Review (Pass 3) — 2026-07-13

**Verdict:** COMMENT (converged — plan is ready to implement; one clean spec fix
recommended, the rest optional polish)

The pass-2 batch landed: every implementer-biting item is confirmed fixed, and
each lens verified its area against the source. Security confirms **both prior
majors are genuinely closed** (symlink containment complete; trust boundary
recorded). Code-quality: "quality is sound; no critical or major findings."
Standards and documentation: all prior findings closed. The one major this round
is a **single issue, flagged by two lenses**, that pass-2 *introduced* — and it
is a two-line spec fix. After merging, that is 1 major / 0 critical → COMMENT.

### Previously Identified Issues (pass-2 items)

- 🟡 **Symlink containment under-specified** — **Resolved.** Both-sides
  canonicalisation, missing-file/absent-parent → `Ok(None)`, dangling symlink →
  `Ok(None)`, file *and* directory-component escapes covered, test per case.
  Correctness and security both verified it is now implementable and closes the
  vector.
- 🟡 **`render_skill_unavailable` unused param** — **Resolved.** Takes only
  `&ConfigError`; header hoisted to a `const` for the 80-col rule.
- 🟡 **`compose` doesn't encode ordering** — **Resolved.** `join_blocks(project,
  skill)` fixes order by signature; architecture and correctness confirm.
- 🟡 **CI render test can't find its binary** — **Resolved.** `host_binary_path()`
  verified to exist (`tasks/shared/eval/run.py:28`); `build:launcher` depends is
  workable (a standards minor notes the cost-profile change, below).
- 🟡 **Live-run scope + stale-log gate inconsistent** — **Resolved.** A separate
  `context_behavioural_dataset.json` (2 rows) is the single source of truth for
  both gate halves; test-coverage confirms internal consistency.
- 🟡 **`--explain` silent on degrade / relative-vs-absolute** — **Partially
  resolved.** Relative paths + dropped marker suffix are clean; but the
  degrade-explain spec was *over*-corrected (new major, below).
- 🟡 **Module docs inaccurate / item `///` docs** — **Resolved** for Phase 1;
  a documentation minor notes Phase 2 lacks the matching verification checkbox.
- 🟡 **Prompt-injection trust boundary** — **Resolved.** Dedicated section;
  security confirms it records the boundary and the constraints-after-block rule.
- 🟡 **Successor ADR owned by no phase** — **Resolved.** Phase 3a with a success
  criterion (placement nit below).
- 🟡 **`Ports` / naming / `--skill=` / leading-hyphen** — **Resolved.** `Ports`
  removed (dispatch verified at 6), `AssembledContext`/`join_blocks`, equals form
  closes the hyphen case on two layers.

### New Issues (introduced by pass 2, or newly surfaced)

- 🟡 **`--explain`-on-degrade is over-specified and self-contradictory for the
  invalid-name case** (architecture major, usability major, correctness minor).
  Pass 2 required a degrading source to "surface the two attempted paths", but an
  `InvalidSkillName` never constructs a path (and the launcher must "never rebuild
  the path"), so the named test is unsatisfiable without reintroducing the exact
  path-duplication the design closes. **The one clean fix to make:** split the
  contract — a *read/unsafe* failure of a valid name surfaces the two attempted
  paths (via a pure adapter `context_paths(source)` query, keeping the path rule
  single-sourced); an *invalid-name* degrade prints a single name-only line
  (`skill: invalid name '<value>' — …`), no path. This is what pass 3 applied.
- 🔵 **Minors / suggestions** (all cheap, most now applied): the leading-`---`
  configure caveat over-generalises "read as frontmatter" (only an *unterminated*
  leading fence degrades; a terminated non-mapping block is preserved) — reword;
  Phase 3a sits physically after Phase 6 — move it after Phase 3; Phase 2 lacks a
  doc-verification checkbox for its `//!` rewrite and new `///` docs (no
  `missing_docs` lint backstops it); the billed `context_global_and_skill` arm
  auto-grades **one** sentinel where two blocks must both land — give it two
  sentinels; `context_behavioural_dataset.json` has no structural/coherence guard
  and its "why two files" rationale is durable only in the plan — add a guard /
  a load-site note; an empty `---\n---\n` fence is injected whole under the
  mapping-only rule — pin the chosen behaviour; the degrade **notice** still
  injects an absolute host path (the `--explain` fix didn't reach it) — relativise
  or record as accepted; `join_blocks(project, skill)` params could read
  `project_block`/`skill_block`; containment should use component-wise
  `Path::starts_with` over fully-canonical paths (guard a `.luminosity-evil/`
  sibling prefix); adding `build:launcher` to `test:unit:evals` changes that
  lane's documented "costs nothing" profile — note it in `tasks/README`.

### Assessment

Converged. The plan is ready to implement. Every structural theme from passes 1
and 2 is closed and verified against the source by the relevant lens; the sole
major is a self-contained over-correction from pass 2 with an obvious two-part
fix, and everything else is minor polish. Pass 3 applied the major fix and the
cheap structural/doc minors; the residual suggestions are recorded for the
implementer. This is an APPROVE-grade plan once the applied fixes settle — the
COMMENT verdict reflects that findings existed to record, not that anything
blocks implementation.

### Verdict: APPROVE (finalised 2026-07-13)

The pass-3 fixes that were applied cleared the one remaining major (the
`--explain`-on-degrade contract split, backed by the pure `context_paths` adapter
query) and the cheap structural/doc minors. No blocking or unaddressed major
remains; the residual items are implementer's-discretion polish, recorded above.
Verdict raised from COMMENT to **APPROVE**; the plan status is set to `ready`.
