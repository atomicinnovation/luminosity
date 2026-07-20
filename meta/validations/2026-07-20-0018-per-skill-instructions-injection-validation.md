---
type: plan-validation
id: "2026-07-20-0018-per-skill-instructions-injection-validation"
title: "Validation Report: Per-Skill Instructions Injection Implementation Plan"
date: "2026-07-20T14:18:45+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: pass
parent: "plan:2026-07-20-0018-per-skill-instructions-injection"
target: "plan:2026-07-20-0018-per-skill-instructions-injection"
tags: [configuration, instructions-injection, rust-cli, skills, evals]
last_updated: "2026-07-20T14:18:45+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: Per-Skill Instructions Injection Implementation Plan

### Implementation Status

✓ Phase 0: Fragment kernel rename — Fully implemented
✓ Phase 1: The instructions domain kind — Fully implemented
✓ Phase 2: The `instructions` subcommand — Fully implemented
✓ Phase 3: Skill wiring, contract test, and the configure surface — Fully implemented
✓ Phase 4: Eval coverage (CI tier) — Fully implemented
✓ Phase 5: Live eval run — Fully implemented
✓ Phase 6: Full local CI mirror — Fully implemented

All seven phases landed as seven `[0018]` commits (`omyzvotu` … `yrprvkps`),
each an independently green increment, exactly as the plan's mergeability
section specified. The working copy is clean.

### Automated Verification Results

✓ Read-only CI check set: `mise run check` (format + lint + types across all
  components, `deny:check`, `pup:check`) — exit 0
✓ Rust workspace unit + black-box suite with coverage: `mise run test:unit:cli`
  — exit 0 (TOTAL region coverage 91.75%; `instructions_command/inbound/cli.rs`
  at 98.90% region)
✓ Isolated adapter instructions tests: `cargo nextest run -p config-adapters -E
  'test(instructions)'` — 10/10 passed
✓ Isolated launcher instructions tests: `cargo nextest run -p luminosity -E
  'test(instructions)'` — 16/16 passed (one benign nextest LEAK annotation, not
  a failure)
✓ Contract test: `pytest tests/unit/skills/test_instructions_injection.py` —
  11/11 passed
✓ Eval-logic tests: `mise run test:unit:evals` — 114 passed, 0 xfailed (matches
  the plan's Phase 5 claim that the `xfail(strict=True)` markers were removed
  once the live log landed)
✓ Capability tripwires: `mise run test:unit:tasks` — 351 passed
✓ `.gitignore` behaviour verified with `git check-ignore`: personal
  `instructions.local.md` ignored; team `instructions.md` tracked; fixture
  `instructions.local.md` tracked (negation works)
✓ **Full local CI mirror: bare `mise run` — exit 0 end-to-end** (the definition
  of "done"; exercises `build:launcher` and the whole suite with coverage)

No automated check fails.

### Code Review Findings

#### Matches Plan:

- **Phase 0 rename is complete and behaviour-neutral.** The kernel module is
  `cli/config/src/fragment.rs`; no stale `ContextSource` / `AssembledContext` /
  `ContextAssembler` / `AssembleContext` / `ReadContextBody` symbols survive in
  the kernel (`fragment.rs`, `lib.rs`). The launcher's `context_command`
  renderers and `## Project Context` / `## Skill-Specific Context` headers
  remain context-named, as the plan required at that edge.
- **Phase 1 kind-bearing arms exactly as specified.** `FragmentSource` in
  `cli/config/src/source.rs:59-63` carries `ProjectContext`,
  `SkillContext(SkillName)`, `SkillInstructions(SkillName)`; the module doc
  states instructions are always skill-scoped so a project-instructions state is
  unrepresentable. `fragment_path` (`store.rs:71-80`) matches each arm to its
  base name via the extracted `skill_dir` helper (`store.rs:67`), yielding
  `context{qualifier}.md` / `instructions{qualifier}.md`.
- **Phase 1's non-exhaustive-match decision took the plan's preferred path.**
  The context command projects a command-local two-variant `ContextSource`
  (`Project | Skill`) onto `FragmentSource` only at the assembly boundary
  (`context_command/inbound/cli.rs:49-60`), so its render match never sees
  `SkillInstructions`. `grep` confirms **zero** panicking macros
  (`unreachable!`/`todo!`/`unimplemented!`/`panic!`) anywhere in `cli/*/src/` —
  the structural narrowing was used, not the `unreachable!` fallback, honouring
  the workspace's panic-free convention.
- **Phase 2 renderer is byte-exact.** `render_instructions`
  (`instructions_command/inbound/cli.rs:55-59`) emits `## Additional
  Instructions`, the three hard-wrapped prose lines with the skill name
  interpolated on line 2, then the fragment body — pinned by
  `renders_the_byte_exact_instructions_block`. The raw `--skill` name is parsed
  **inside** the fail-safe boundary via `command_support::resolve_skill_name`
  (`cli.rs:106-112`), not a clap `value_parser`.
- **Phase 2 shared scaffold extracted as planned.** The fail-safe boundary lives
  once in `cli/launcher/src/command_support/mod.rs` (`OnFailure`, `Outcome`,
  `assemble`, `degrade_explain`, `resolve_skill_name`, explain-line helpers),
  consumed by both `context_command` and `instructions_command` — no
  byte-duplicated boundary.
- **Phase 3 wiring is correct and universal.** `skills/config/configure/SKILL.md`
  carries the context line at the top of the body (line 17) and the instructions
  line as the **very last** content line (line 160 / file end), realising
  "context early / instructions last" via two `!`-lines. Both `context*` and
  `instructions*` grants are present (lines 11–12). The `## Managing
  skill-specific instructions` surface section frames instructions as
  "directives it should *follow*" (line 99), distinct from context.
- **Phase 4/5 eval coverage present and honest.** New `instructions_eval.py`,
  `instructions_scorer.py`, `instructions_dataset.json`, the three fixtures, and
  the grown capability tripwires (`["context", "instructions", "values"]`) all
  landed. The committed live log
  (`…_configure-instructions-with-skill_….json`) contains both the context
  sentinel (Waypoint ×15) and the instructions sentinel (Marker ×26), proving
  both blocks reached the model with the expected ordering. No host paths leak
  into any committed log.

#### Deviations from Plan:

- **Minor, cosmetic — unavailable-notice constant names.** The plan's Phase 2
  sketch named the constants `INSTRUCTIONS_UNAVAILABLE_HEADER` /
  `INSTRUCTIONS_UNAVAILABLE_PROSE`; the implementation uses module-local
  `UNAVAILABLE_HEADER` / `UNAVAILABLE_PROSE`
  (`instructions_command/inbound/cli.rs:20-24`). Semantically identical and
  clearer in context (the module is already instructions-scoped). No behavioural
  difference; the notice text still names the exact file, pinned by
  `the_instructions_unavailable_notice_names_the_skill_file`.

No deviations of substance. Every design decision the plan called out — the
`Fragment` vocabulary, the arm-bearing source enum, the shared fail-safe
scaffold, the equals-form `--skill` inside the boundary, the two-line SKILL.md
placement, behavioural-only eval — is implemented as written.

#### Potential Issues:

- None material. The `config` crate name and `ConfigError` "config file" wording
  remain as-is; the plan explicitly booked these as out-of-scope follow-ups
  (What We're NOT Doing), so their persistence is expected, not a defect.

### Manual Testing Required:

The plan's manual-verification items were confirmed during this validation
against source and committed artifacts; no further manual testing is required to
accept the plan. For completeness, the residual runtime spot-checks a maintainer
may repeat:

1. Rendered prompt coherence:
  - [x] `luminosity instructions --skill=configure` prints the exact block with
    no trailing blank line (pinned by the black-box suite)
  - [x] `luminosity instructions --skill=../../etc --fail-safe` exits 0 with the
    unavailable notice (pinned by
    `an_invalid_skill_name_under_fail_safe_exits_zero_with_a_notice`)

2. Integration:
  - [x] Both a context file and an instructions file present → context near the
    top, instructions last (asserted positionally by the Python contract test
    and behaviourally by the committed ordering log)

### Recommendations:

- **Accept the plan as done.** All success criteria are met and the full CI
  mirror is green.
- Consider raising the booked follow-up story (rename the `config` crate + the
  `ConfigError` taxonomy to the settled `Fragment` vocabulary) so the
  name/contents gap Phase 0 deliberately widened does not linger — the
  `fragment.rs` `//!` doc already signposts the split.
- No action needed on the constant-name deviation; it is an improvement.

### Result

**pass** — every phase is fully implemented, every automated check passes
(including the full local CI mirror at exit 0), and the sole deviation is a
beneficial cosmetic rename.
