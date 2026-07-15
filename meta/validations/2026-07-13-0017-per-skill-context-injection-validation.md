---
type: plan-validation
id: "2026-07-13-0017-per-skill-context-injection-validation"
title: "Validation Report: Per-Skill Context Injection Implementation Plan"
date: "2026-07-14T08:54:32+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: pass
parent: "plan:2026-07-13-0017-per-skill-context-injection"
target: "plan:2026-07-13-0017-per-skill-context-injection"
tags: [configuration, context-injection, rust-cli, skills, evals]
last_updated: "2026-07-14T08:54:32+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: Per-Skill Context Injection

### Implementation Status

✓ Phase 1: Domain and adapter — Fully implemented
✓ Phase 2: CLI surface — Fully implemented
✓ Phase 3: Skill wiring, contract test, configure surface — Fully implemented
✓ Phase 3a: Record the decision (ADR-0012) — Fully implemented
✓ Phase 4: Eval coverage (CI tier) — Fully implemented
✓ Phase 5: Live eval run — Fully implemented
✓ Phase 6: Full local CI mirror — Fully implemented

Every test named in every phase's "Tests (write first)" list exists. **No planned
test is missing.** Several phases ship a superset.

### Automated Verification Results

✓ Full local CI mirror: `mise run` exits **0** end-to-end, with **no formatter
  churn** (the working tree after the run is unchanged apart from two
  pre-existing `meta/` edits) — so `mise run fix` had genuinely been applied.
✓ Rust workspace: 242 tests pass, 0 skipped (`cargo nextest run`)
✓ Domain + adapter: 117 tests pass (`-p config -p config-adapters`)
✓ Context/skill/source filter: 82 tests pass
✓ Skill wiring: 16 pass (`tests/unit/skills/test_context_injection.py`)
✓ Eval logic: 143 pass (`tests/unit/evals`)
✓ Eval render (new CI tier): 10 pass (`test_context_render.py`)
✓ Exact-list tripwires green **unmodified** — `capabilities(_SKILL) ==
  ["context", "values"]` still holds at `tests/unit/tasks/shared/eval/test_run.py:20`,
  confirming the plan's "no new eval arm, no extra billed baseline" claim.
✓ `.gitignore`: personal skill context ignored outside fixtures, tracked inside;
  team context never ignored. The fixture `context.local.md` is genuinely tracked.

Coverage on the new modules is strong: `config/src/source.rs` 96.30%,
`config/src/context.rs` 93.15%, `config-adapters/src/store.rs` 84.58%,
`launcher/src/context_command/inbound/cli.rs` 97.41%.

**Live eval evidence** (`tests/evals/skills/configure/results/`):

| Arm | pass^k | Samples |
|---|---|---|
| `configure_context_with_skill` | 1.000 | 6/6 (2 behavioural rows × 3 trials) |
| `configure_values_with_skill` | 1.000 | 27/27 |
| `configure_values_baseline` | 0.000 | 27/27 (control — correctly scores zero) |

No absolute host paths leak into the committed logs.

### Code Review Findings

#### Matches Plan

Every acceptance criterion was re-verified **empirically against the compiled
binary**, not merely inferred from the diff:

- **Ordering.** `luminosity context --skill=configure` prints `## Project
  Context` then `## Skill-Specific Context`, separated by exactly one blank line,
  with no trailing blank. Encoded structurally in a pure
  `join_blocks(project_block, skill_block)` whose *parameter order* fixes the
  sequence (`cli/launcher/src/context_command/inbound/cli.rs:110-113`) — as the
  plan intended, not a push-order a future edit could swap.
- **Absent-global.** With no `config.md`, the skill block is the sole block at
  the same structural point.
- **The load-bearing safety property.** `--skill=../../etc --fail-safe` exits
  **0**, keeps the healthy project block intact, and appends a correctly-named
  `## Skill-Specific Context Unavailable` notice — never the misleading project
  one. Without `--fail-safe` it exits 1. A mistyped skill name therefore cannot
  discard a prompt. Validation happens inside `context_cli::run`, not in a clap
  `value_parser` (`skill` is `Option<String>`), which is precisely the trap the
  plan identified.
- **Independent degradation.** A malformed skill context still prints the project
  block, and vice versa; both malformed prints both notices.
- **Symlink containment.** A `context.md` symlinked to `/etc/hosts` is refused
  with `UnsafePath`, degrading to a skill notice. Both sides are canonicalised, so
  a legitimate file under a symlinked root (macOS `/tmp` → `/private/tmp`) is
  still read.
- **Mapping-only frontmatter strip.** `---\nSection A\n---\nSection B` is injected
  **whole** — no silent prose loss. A YAML mapping is stripped; an unterminated
  fence fails loud.
- **Both absent** emits zero bytes and exits 0.
- **`--explain`** prints the root plus four root-relative paths, and honours *both*
  degrade sub-cases: a malformed valid-named source still surfaces its two
  attempted paths (`unreadable`), while an `InvalidSkillName` prints a single
  name-only line with **no** fabricated path — exactly as specified.
- **Hexagon purity.** `cli/config` declares exactly one dependency (`kernel`,
  itself dependency-free). No serde, YAML, or filesystem crate enters the core.
- **`dispatch` stayed at six collaborators** — `AssembleContext` replaced
  `AssembleProjectContext` in the existing slot; no parameter was added.
- **Injection line** is byte-exact with the `--skill=configure` **equals** form,
  sits **above** the skill's binding constraints (the security requirement), and
  needs no `allowed-tools` change.
- **Registry walk and vacuity guard preserved** in the contract test, so future
  skills auto-enrol.
- **ADR-0012** records both divergences and the layout, referencing ADR-0003.

#### Deviations from Plan

All are benign; two are improvements.

- **`context_paths()` became a `locate()` port method plus a `SourceLocation`
  domain type** (`cli/config/src/context.rs:53-57`, `:79-82`, `:100-103`;
  `cli/config-adapters/src/store.rs:179-188`). The plan specified an *inherent*
  adapter query. Same design goal — the path rule stays single-sourced and the
  launcher never rebuilds `skills/<name>/<file>` — reached through a different
  seam. Behaviourally identical (verified). Cost: the driven port now carries a
  purely diagnostic method every fake must implement.
- **Paths are made root-relative in the adapter** (`store.rs:71-73`) rather than
  absolute-then-stripped in the renderer. Cleaner; the launcher no longer does
  string surgery on paths.
- **The gitignore test was split into four** (`TestGitignore`,
  `tests/unit/skills/test_context_injection.py:189-205`) rather than the single
  planned `test_gitignore_hides_personal_but_tracks_team`. A superset.
- **ADR-0012 landed as `accepted`, not `proposed`** (plan success criterion said
  proposed). All 12 ADRs in `meta/decisions/` are `accepted`, so this is the house
  convention, and frontmatter and body agree. Worth knowing: under the repo's own
  immutability rule, a later correction now needs a further successor ADR rather
  than an edit.
- **`SkillName::as_str` carries no `///` summary** (`cli/config/src/source.rs:41-44`)
  — the only new public fn without one, so the plan's "every new public item
  carries a `///` summary" manual check is not *literally* true. Cosmetic; no
  `missing_docs` lint exists to catch it.
- **The `## Managing project context` section gained `--skill=` in prose, not in
  the fenced command** (`skills/config/configure/SKILL.md:57-58`). Arguably better
  — it keeps the copy-pasteable project command unscoped.
- **The `InvalidSkillName` explain line does not use the specified grammar.** The
  plan (line 834-836) specified `skill: invalid name '<value>' — expected …`. The
  implementation pushes the bare `error.to_string()`
  (`cli/launcher/src/context_command/inbound/cli.rs:218`), which renders as
  `invalid skill name '../../etc': expected non-empty alphanumeric, '-', or '_'`
  — no `skill:` prefix, so the line does not carry the level/source grammar the
  other explain lines use. The behavioural contract the plan cared about (a single
  name-only line, **no** fabricated path lines) is honoured; only the prefix is
  missing. The test (`cli/launcher/tests/context.rs:554`) asserts the substring and
  the absence of `skills/`, so it does not pin the prefix either way.

#### Potential Issues

Ranked. None blocks the plan; the first two are worth a follow-up.

1. **The plan's "`luminosity context` behaviour is unchanged" claim is not quite
   true.** Migration Notes assert that every existing no-`--skill` behaviour is
   unchanged. Verified false in one narrow case: because `ContextSource::Project`
   now routes through the mapping-checking `read_context_body`, a `config.md`
   whose frontmatter is valid YAML but **not a mapping** (e.g. a sequence) now
   injects the **whole file including the `---` fences** into `## Project
   Context`, where story 0016 injected only the body. Confirmed against the
   binary. Such a `config.md` is already broken *as config*, and the new behaviour
   is arguably safer (no silent loss, consistent with the skill rule) — but it is
   an undocumented, untested change to project-context extraction, and the two
   readers now disagree about the same bytes (`ReadConfigLevel::read` would parse
   that frontmatter as a `Node::Sequence` without error). No test covers it.

2. **The behavioural eval fixtures contradict their own prompts.** Both
   behavioural rows lead with *"Read the luminosity config value `core.example`"*,
   but `context_global_and_skill/.luminosity/config.md` declares `core: team` (a
   scalar — `config get core.example` exits 1, "is not set"), and
   `context_skill_behavioural/` carries **no `config.md` at all**. Every other
   fixture uses `core:\n  example: <v>`, so this looks like a paste slip. The arms
   passed 6/6 because the config read only needs to *route the agent through the
   skill* (where injection fires), not to succeed — but the prompt's premise is
   false, which is exactly the class of fragility Phase 5's own "defect 2" set out
   to remove. Nothing in CI pins prompt↔fixture coherence, so this cannot fail
   until a billed run flakes.

3. **Symlink containment is asymmetric across callers.** `refuse_escaping_path` is
   called only from `read_context_body` (`cli/config-adapters/src/store.rs:86`).
   `ReadConfigLevel::read` and `WriteConfigLevel::write` do not call it — so
   `luminosity config get` still reads *through* an escaping `config.md` symlink,
   and `atomic_write`'s rename would replace that symlink with a regular file,
   while `luminosity context` refuses the very same file. One file, two safety
   contracts depending on the caller. Pre-existing for the config path, but newly
   *asymmetric* now that `Project` routes through the guarded reader.

4. **`--explain` sits outside the `--fail-safe` degrade boundary.**
   `run` propagates the diagnostic's error —
   `for line in explain(assembler, &project, &skill)?`
   (`cli/launcher/src/context_command/inbound/cli.rs:150`) — and both `explain`
   (`:211`) and `source_lines` (`:235`) call the fallible `assembler.locate(...)?`.
   So under `--fail-safe --explain`, a `locate` failure escapes the boundary and
   the process exits non-zero *after* already printing the blocks. Every other
   error inside `run` is absorbed; this one is not, which contradicts `run`'s own
   doc comment (`:128-131`) promising that under `Degrade` the command "succeeds".

   **This cannot discard a prompt**, and the distinction matters: the injected line
   (`skills/config/configure/SKILL.md:16`) never passes `--explain` — it is a
   human-run diagnostic only. The trigger is also very narrow: `locate` is fallible
   *solely* because `discover_store` calls `std::env::current_dir()`
   (`cli/launcher/src/main.rs:108-113`); `FileConfigStore::discover` itself is
   infallible. So it needs a deleted or unreadable cwd. Worth tightening for
   policy coherence (make the explain path degrade too), not urgent.

5. **The Python golden model and the Rust trimmer disagree on interior CRLF.**
   `_trim` (`tests/unit/evals/skills/configure/test_context_dataset.py:163`) strips
   `\r` from *every* line; the Rust trimmer strips only at the end of the last kept
   line (`cli/config/src/context.rs:166-180`, whose own tests pin interior CRLF
   surviving). Inert today — the `.gitattributes` LF pin plus the byte-compare
   against the real binary in `test_context_render.py` would catch drift — but it
   is not "matching the Rust trimmer exactly" as the plan states.

6. **Stale-log hazard in the new coverage gate.** `TestCommittedGate._arm`
   (`tests/unit/evals/skills/configure/test_results.py:71-76`) returns the *first*
   (earliest-timestamped) log matching a task name, and nothing prunes `results/`.
   If a future run's logs were committed alongside an older run's, the new
   dataset-coverage pin would silently grade the stale evidence. Pre-existing, but
   the new pin now depends on it.

7. **The Python skill-name allow-list mirror is one metacharacter looser than the
   Rust one.** `re.match(r"^[A-Za-z0-9_-]+$", ...)` also matches before a trailing
   newline, so `"configure\n"` would pass Python but be rejected by
   `SkillName::parse`. Unreachable today (the name is stripped first);
   `re.fullmatch` would close it.

### Manual Testing Required

The automated suite plus the binary probes above cover every acceptance criterion,
so nothing is strictly outstanding. Two optional confirmations:

1. Rendered skill prompt:
  - [ ] Invoke `/luminosity:configure` in a repo carrying both a `config.md` body
        and a `.luminosity/skills/configure/context.md`, and confirm the rendered
        prompt reads coherently: project context, then skill-specific context,
        then the skill's own constraints.

2. Eval transcript:
  - [ ] `mise run eval:view -- --skill configure` — confirm the
        `context_global_and_skill` transcript shows the agent applying **both**
        conventions (`Lantern` from the project body, `Tier` from the skill body).

### Remediation (applied 2026-07-14, after this report was first filed)

Every finding above has been fixed in a follow-up change; `mise run` remains green
end-to-end. Each fix was driven from a failing test first (the red state was
verified by reverting the fix and watching the new test fail).

| # | Finding | Fix |
|---|---|---|
| 1 | Project-context body change undocumented/untested | Behaviour **kept** (one strip rule for every body beats one safe rule and one silently-truncating one). Pinned by `a_project_context_with_non_mapping_frontmatter_is_injected_whole`; ADR-0012 gained a **Scope of the two rules** section and a Negative consequence recording the change. |
| 2 | Behavioural prompts read a key their fixtures lack | `context_global_and_skill`'s `config.md` now defines `core.example` as a mapping; `context_skill_behavioural` gained a `config.md` carrying that key with **no body**, so no project block appears and its golden is unchanged. New CI test `test_every_behavioural_prompt_reads_a_key_its_fixture_defines` fails free rather than mid-billed-run. |
| 3 | Symlink containment only on the context read path | `refuse_escaping_path` now guards `ReadConfigLevel::read` and `WriteConfigLevel::write` too. Verified: `config get` through a symlinked `config.md` is refused, and `config set --level team` is refused **without clobbering the target**. |
| 4 | `--explain` outside the fail-safe boundary | New `diagnostic()` applies the same degrade policy as the blocks: under `--fail-safe` a diagnostic that cannot be built prints `explain unavailable: <error>` and exits **0**. `--explain` is no longer the one error in `run` that can exit non-zero. |
| 5 | `_trim` vs the Rust trimmer on interior CRLF | `_trim` now strips `\r` only from the last kept line, mirroring the Rust slice semantics. |
| 6 | Stale-log hazard in the coverage gate | `TestCommittedGate._arm` now fails on *more than one* log per arm rather than silently taking the earliest. |
| 7 | Python allow-list looser than Rust | `re.fullmatch` with the anchor-free pattern, so a trailing newline is rejected as Rust rejects it. |
| — | `SkillName::as_str` undocumented | `///` summary added. |
| — | `InvalidSkillName` explain line lacked the `skill:` prefix | `invalid_skill_line` now renders `skill: <error>`, pinned by a unit test. |

The `configure` SKILL.md surface now states the unterminated-`---` hazard for
**every** injected body, not just a skill's.

**One caveat on the committed live-eval evidence.** The logs in
`tests/evals/skills/configure/results/` were produced *before* the fixture
correction in finding 2. They remain representative — the injected blocks are
byte-identical (the fixture change touched only `config.md` frontmatter, never a
body), the sentinels and scenario names are unchanged, and the CI render test
byte-compares the real binary's output against the goldens — so the evidence still
holds. A re-run (`mise run eval:skills:configure`) would nonetheless be the fully
clean thing to do, and is left as a deliberate choice rather than done unbidden,
because it is billed.

### Recommendations

Findings 1–7 are all remediated (see above). What remains is forward-looking:

- **Consider a billed re-run** (`mise run eval:skills:configure`) so the committed
  evidence is produced against the corrected fixtures. Not required — the injected
  blocks are byte-identical and the CI render test pins them against the real
  binary — but it would remove the one caveat on the evidence.
- **Story 0018** should inherit the `instructions.local.md` symmetry flagged in
  ADR-0012's Neutral consequences, and decide the `config`/`ConfigError` naming
  question the plan's Migration Notes deliberately deferred — the domain has
  generalised beyond configuration to all two-level `.luminosity` documents.
- **The plan's Migration Notes are now known to be wrong** on one point ("every
  existing behaviour of `luminosity context` … is unchanged"). The plan is a
  historical artifact and has been left as written; ADR-0012 carries the correct,
  durable record.
