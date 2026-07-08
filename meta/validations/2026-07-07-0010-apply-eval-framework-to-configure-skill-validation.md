---
type: plan-validation
id: "2026-07-07-0010-apply-eval-framework-to-configure-skill-validation"
title: "Validation Report: Apply the Eval Framework to the configure Skill"
date: "2026-07-08T16:19:31+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: pass
parent: "plan:2026-07-07-0010-apply-eval-framework-to-configure-skill"
target: "plan:2026-07-07-0010-apply-eval-framework-to-configure-skill"
tags: [validation, evaluation, inspect, configure, skills]
last_updated: "2026-07-08T20:30:00+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: Apply the Eval Framework to the configure Skill

**Result: `pass`.** An initial validation pass returned `partial` — the tier was
sound but three Phase-3 artefact deliverables were missing, two of which
undermined the very artefact the story exists to produce. All three were closed,
along with five further findings surfaced along the way: a mis-routed `set --level`
that nothing caught, 134 leaked temp workdirs, a self-contradicting findings note,
a `_BYPASS_TOOLS` disallow that did not do what it claimed, and an over-matching
host-path guard. The committed logs come from the third gated run, after those
fixes. This report records the final state and the remediation.

### Implementation Status

- ✓ **Phase 0: Resolve integration unknowns** — implemented. Pins settled
  (`inspect-ai==0.3.244` plus the required `httpx<1`), findings recorded in
  `meta/research/codebase/2026-07-08-0010-inspect-integration-findings.md`. The
  two questions originally deferred to a credentialed run (CLI provisioning,
  transcript shape) were **dissolved rather than answered** by the host-native
  pivot: nothing provisions a CLI, and the transcript became an owned
  `stream-json` interface.
- ✓ **Phase 1: Eval tier scaffold and pass^k gate** — fully implemented.
- ✓ **Phase 2: Eval definition** — implemented as re-architected. Nine dataset
  tasks, deterministic scorer, both arms, native `pass_k` reducer, ADR-0011
  implementation note.
- ✓ **Phase 3: Live run and committed log** — complete. Gated run exits 0;
  **with-skill `pass^k = 1.000`, baseline `0.000`**, both logs committed with
  per-sample provenance and no host paths.

### Automated Verification Results

- ✓ `mise run check` → exit 0 (read-only sweep, still eval-free)
- ✓ `uv run pytest tests/unit -q` → **379 passed**
- ✓ `uv run pytest tests/evals --collect-only` → *no tests collected*
- ✓ `LUMINOSITY_EVAL_LIVE=off mise run eval:skills:configure` → exit 0, no model call
- ✓ `mise run eval:skills:configure` → exit 0 in 295s; gate passed
- ✓ Both committed logs: `status: success`, 27/27 samples, `reducer: pass_k_3`,
  `accuracy` 1.000 / 0.000; readable via `read_eval_log`
- ✓ `inspect_ai.scorer.pass_k` verified from source: `C(correct,k)/C(total,k)`,
  which at `epochs == k` collapses to 1.0 iff all k trials pass — the ADR note's
  inversion of the plan's "Inspect has no `pass_k`" claim is **correct**

### Code Review Findings

#### Matches Plan

- Pure `float -> bool` pass^k gate; call-time `LUMINOSITY_EVAL_LIVE` knob;
  `env_flag_enabled` shared, with `coverage_enabled` migrated onto it and
  `pup_mode` correctly left alone.
- `eval` / `eval:skills` / `eval:skills:configure` declared, roll-ups
  pure-`depends`, all three absent from `check` and `default` — asserted by
  `TestEvalTierWiring`. `test:unit:evals` folded into `test:unit`.
- `readback.require_success` / `arm_log` / `pass_k` fail closed on a non-success
  status, a missing arm, and a missing reducer/metric — never defaulting to a pass.
- Nine dataset tasks, expected values consistent with `cli/launcher/tests/config.rs`;
  skill-vs-baseline comparison advisory, not a gate, per the work item.

#### Deviations from Plan (accepted)

Structural, or forced by the Phase-3 host-native pivot; each is documented in the
findings note.

- **Docker/`inspect_swe` dropped entirely** for host-native `claude -p`, because
  the bridge routes model calls through Inspect's metered provider and cannot use
  a subscription. A meridian-proxy fallback is documented.
- **Module layout**: gate/readback/run/staging/workdirs under `tasks/shared/eval/`;
  shared names in a top-level `common/eval.py`, importable from both sides of the
  `tasks/` ↔ `tests/` boundary — which makes the plan's string-literal coherence
  test unnecessary rather than missing.
- **Custom `all_correct` reducer dropped** for native `pass_k(k)`. Verified correct.
- **`dataset.jsonl` → `dataset.json`** (formatter-safe array).
- **The bad-`--level` task replaced** with a valid `--level personal` get, because
  a skill-following model correctly declines an invalid level. `grade_error`'s
  exit-2 clap branch is consequently exercised by unit tests only, not the dataset.
- **`_BYPASS_TOOLS` dropped.** The disallow list (`Read`/`Grep`/`Glob`/…) claimed to
  make the CLI "the only path to the answer". With `Bash` allowed it never did —
  `cat`/`grep`/`find` reproduce those tools, and the baseline used them to read
  `.luminosity/config.md` in 12 of 27 samples. Routing is enforced by the scorer's
  `config_command_ran`, not the tool list. Both arms now receive an identical
  toolset (`Bash`, `Read`, `Grep`, `Glob`) and differ only in `Skill`.
- **Get and error tasks are graded by scorer re-execution, not by the agent's
  transcript output.** `_grade` asserts the agent ran the canonical argv, then
  re-runs it against the seeded fixture. Since the CLI is the oracle and the
  fixture is deterministic, those tasks effectively grade *routing*. This is the
  right call — a tool result cannot reliably carry an exit code — and is now
  recorded in the findings note rather than left as an undocumented narrowing.
- **`fixtures/golden_transcript.json` dropped, not forgotten.** Its purpose was to
  retro-pin a shape the harness handed us; under the pivot the transcript is an
  input the repo parses, pinned by `test_solvers.py`.

#### Findings Raised and Closed

The first six were found by the initial validation pass; the last two by reviewing
the live transcripts. All fixed test-first.

1. **Log provenance — the committed log did not record what produced it.**
   `eval.model` reads `mockllm/model` (the solver bypasses Inspect's provider);
   neither `claude-sonnet-5` nor CLI `2.1.203` appeared anywhere in either log.
   *Fixed:* `parse_cli_version` + `provenance()` stamp `claude_model` and
   `claude_cli_version` into every sample; `test_results.py` asserts it on the
   committed logs. The false comment at `test_mise_wiring.py:308-309` (which
   claimed the version was "recorded in the committed eval log") now points at
   that guard. Logs regenerated by a live re-run — **not hand-injected**, since
   fabricating provenance is precisely what the guard exists to prevent.

2. **`scrub_paths` left 66 absolute host paths in the committed logs.** It
   relativised only `$REPO_ROOT` and `$HOME`, but the per-sample workdir lives
   under the system temp root — on macOS `/var/folders/…`, outside `$HOME`. The
   unit test asserted exactly `home not in scrubbed`, so the guard had a hole
   precisely where the leak was. *Fixed:* `scrub_paths` takes `tmp_dirs` and
   replaces longest-prefix-first (so `/private/var/…` is not stranded by its
   symlinked `/var/…` twin); the guard is now a `HOST_PATH_PATTERN` regex applied
   to the committed logs themselves. `scrub_result_dir` also moved to
   `atomic_write_text`.

3. **Skill attribution was recorded but never scored.** `skill_invoked` /
   `skill_expected` sat in `Score.metadata` with nothing consuming them, so a
   with-skill trial that never invoked the skill but typed the right command
   scored CORRECT — the arms were graded identically. *Fixed:* `grade_sample`
   makes `skill_invoked == skill_expected` a conjunct of the verdict, TDD'd
   two-sided. The regenerated logs show 27/27 with-skill samples invoking the
   skill and 0/27 baseline samples doing so.

4. **A mis-routed conflict `set --level` was undetectable.** `config_command_ran`
   ignored `--level` on every `set`, justified by "a set's level correctness
   surfaces in the precedence outcome" — true for the precedence task, but the
   conflict task has no precedence outcome to surface it. *Fixed:* a `set` must
   match a level the task pins, and is free when it pins none (the live log
   confirms the agent legitimately passes an explicit `--level personal` on the
   unpinned precedence task, so exact equality there would false-fail).

5. **Per-sample workdirs were never removed** — 134 stale directories had
   accumulated in the temp root. *Fixed:* `cleanup_workdirs` sweeps them after a
   completed run, keyed on a shared `WORKDIR_PREFIX`; a crashed run deliberately
   keeps its workdirs for reading, and the next run sweeps them.

6. **The findings note contradicted itself** — a stale section still declared the
   Phase-3 deliverables "blocked on API credit". *Fixed:* that section is now
   explicitly historical, and a *Phase 3 outcome* section records the real result.

7. **`_BYPASS_TOOLS` did not do what it claimed** (see *Deviations*). Dropped, with
   calibration finding 2 in the notes rewritten from "fixed by `--disallowedTools`"
   to record that the claim was false and why the scorer is the real enforcement.

8. **`HOST_PATH_PATTERN` over-matched.** Once file tools were restored the agent
   redirected output (`… 1>/tmp/out.txt`), and the guard flagged those as leaked
   host paths — they carry no machine identity. *Fixed:* the pattern now matches
   only machine-specific roots (`/Users/`, `/home/`, `/var/folders/`, and their
   `/private` twin) plus an unscrubbed workdir under `/tmp/{WORKDIR_PREFIX}`, with
   two-sided tests pinning both halves.

### Residual Risks and Coverage Boundaries

Deliberate, and worth carrying forward rather than treating as defects:

- **The `1.000` headline is one stochastic draw**, not evidence of a stricter
  eval. The attribution conjunct can only ever lower a score, and it lowered
  nothing. The first run's `0.889` (a single conflict-on-set flake) is the more
  honest picture of the gate's real headroom, and the plan's own
  *Performance Considerations* already treats a single flake as a re-run signal,
  not a regression.
- **The baseline's `0.000` is a `pass^k`, not a per-sample zero.** In the committed
  run one baseline sample did score CORRECT — it discovered the CLI on `PATH` and
  routed correctly — but `pass^k` requires all three epochs of a task to pass. The
  baseline is not structurally incapable of passing; it simply does not route
  through the CLI reliably without the skill, which is exactly what the eval
  measures.
- **The agent inherits the operator's Claude Code config.** `claude -p` loads the
  user-level `CLAUDE.md` and the hooks from `CLAUDE_CONFIG_DIR`, so the eval runs
  with whatever personal instructions the operator has, and **the committed log is
  not portable across machines**. On the authoring machine the user memory imports
  an `RTK.md`, and four baseline samples went hunting for `rtk` rather than
  `luminosity`; the with-skill arm shows no such detours. The contamination
  therefore lands asymmetrically, biasing the baseline *downward*. Grading itself
  is sound — the operator's `PreToolUse` hook passes `luminosity config …`, `cat`,
  `grep`, and `find` through unrewritten (verified), so the graded argv is never
  altered. Accepted rather than fixed: on CLI 2.1.203 subscription auth and context
  isolation are mutually exclusive (`--bare` provides the isolation but never reads
  OAuth/keychain; `CLAUDE_CONFIG_DIR`/`HOME` overrides yield `Not logged in`).
  The lever, when the portability matters, is `--bare` plus a funded
  `ANTHROPIC_API_KEY`.
- **`fail_on_error=True` conflates transient infra failure with model failure.**
  Acceptable at 9 tasks × k=3; the documented 20–50-task / k 5–10 ramp must
  revisit resilience.
- **Ask-before-ambiguous-set is not covered** by deterministic outcome grading —
  a conscious boundary, stated in the plan.
- **Model/CLI pins drift on their own schedule**, so the committed log is a
  point-in-time record, not an indefinitely reproducible artifact.

### Manual Testing Required

None outstanding. For future reference, the manual loop is:

1. `LUMINOSITY_EVAL_LIVE=off mise run eval:skills:configure` — skip path costs nothing.
2. `mise run eval:skills:configure` with an authenticated `claude` — both arms run,
   logs written, gate passes.
3. Open a committed log in Inspect View — confirm transcripts, the `Skill` event,
   and the baseline contrast.
4. `mise run check` — the eval never runs in the read-only sweep.

### Recommendations

None blocking. Two carried forward as future work:

- Revisit `fail_on_error` resilience before the 20–50-task / k 5–10 ramp.
- Produce one committed log under `--bare` + a funded `ANTHROPIC_API_KEY`, so the
  durable signal is free of the operator's `CLAUDE.md`/hooks and portable across
  machines. Until then the baseline number is a lower bound.
