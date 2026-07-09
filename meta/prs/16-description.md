---
type: pr-description
id: "16"
title: "[0010] Add eval framework, initially tested on `/configure`"
date: "2026-07-08T20:36:32+00:00"
author: Toby Clemson
producer: describe-pr
status: complete
work_item_id: "0010"
parent: "work-item:0010"
relates_to: ["adr:ADR-0011", "work-item:0003", "work-item:0009"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/16"
pr_number: 16
tags: [evaluation, inspect, skills, configure, testing]
revision: "58bd04bbd4275559f93a7dc292ca60e28fea505a"
repository: "luminosity"
last_updated: "2026-07-08T20:36:32+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# [0010] Add eval framework, initially tested on `/configure`

## Summary

Stands up a skill-evaluation tier — a third test tier alongside `unit/` and `integration/` — built on [Inspect](https://inspect.aisi.org.uk) (UK AISI), and applies it to the `configure` skill as the first target. Skills are the product (ADR-0007), so this gives them the same kind of regression gate that lint and type-checks give the rest of the repo: `mise run eval:skills:configure` runs a with-skill-vs-baseline A/B over a 9-task dataset, gates on **pass^k ≥ 0.8 over k = 3 trials**, and exits non-zero below the floor. The tier is deliberately excluded from CI to control token cost; the committed Inspect JSON log is the durable quality signal instead.

The committed run scores **with-skill `pass^k = 1.000`, baseline `0.000`** — the skill is what makes a model route through the `luminosity config` CLI rather than reading `.luminosity/config.md` off disk.

This implements work item 0010 and discharges the behavioural-equivalence validation that story 0009 deferred to it.

## Changes

**Eval tier (new)**

- `tests/evals/skills/configure/` — an Inspect `@task` file with two arms (`configure_with_skill`, `configure_baseline`) over one 9-task `dataset.json`, a deterministic scorer, seeded fixtures, and two committed JSON logs under `results/`. The dataset covers get, level-scoped get, set/precedence, and four error paths (unsettable parent key, unset key, invalid key syntax, malformed frontmatter).
- Eval files are named as Inspect `@task` files, not `test_*`, so pytest does not collect them while the tier shares the `tests/` root.

**Gate and task wiring**

- `tasks/shared/eval/` — `gate` (pure `float -> bool` pass^k floor), `readback` (arm/status/reducer/metric extraction plus host-path scrubbing), `run` (drives Inspect in-process), `staging` (stages a real host-native launcher into a plugin tree), `workdirs` (sweeps per-sample temp dirs).
- `mise run eval:skills:configure` → `eval:skills` → `eval`, all three absent from `check` and the bare `mise run` default — asserted by `TestEvalTierWiring`. A `LUMINOSITY_EVAL_LIVE=off` knob makes the skip path free.
- `common/eval.py` — shared identifiers importable from both sides of the `tasks/` ↔ `tests/` boundary, so arm names and the reducer name cannot drift apart.
- `tasks/shared/env.py` — `env_flag_enabled`, read at call time; `coverage_enabled` migrated onto it.

**Dependencies**

- `inspect-ai==0.3.244` plus a required `httpx<1` constraint (inspect-ai leaves `httpx` unbounded, and the repo's `prerelease = "allow"` otherwise drifts to a broken `1.0.dev*`).
- `node` + `npm:@anthropic-ai/claude-code@2.1.203` pinned in `mise.toml` `[tools]`, with a `deps:install:claude-native` task to run the postinstall mise's npm backend skips — the same rustup-provisions-cargo-pup pattern. Node is **dev-tier only**; it is not a fourth product toolchain (ADR-0004 holds).

**Documentation**

- ADR-0011 gains an implementation note recording one correction (below).
- `meta/research/codebase/2026-07-08-0010-inspect-integration-findings.md` records the Phase-0 findings, the host-native pivot, the calibration findings, the alternatives considered, and a library-feature audit confirming each hand-built piece earns its place.
- A validation report records eight findings raised and closed.

## Context

- Work item: `meta/work/0010-apply-eval-framework-to-configure-skill.md`
- Decision: `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md`
- Feeding spike: work item 0003 (chose Inspect over `skill-creator`)
- Plan: `meta/plans/2026-07-07-0010-apply-eval-framework-to-configure-skill.md`
- Validation: `meta/validations/2026-07-07-0010-apply-eval-framework-to-configure-skill-validation.md`

## Testing

- [x] `mise run check` → exit 0 (read-only sweep; still eval-free)
- [x] `uv run pytest tests/unit -q` → **379 passed**, of which **125** are new eval-tier tests
- [x] `uv run pytest tests/evals --collect-only` → *no tests collected* (the naming convention holds)
- [x] `LUMINOSITY_EVAL_LIVE=off mise run eval:skills:configure` → exit 0, no model call, no cost
- [x] The pass^k gate is verified **two-sided** and independent of any live run: a synthetic `0.66` asserts a non-zero exit, a synthetic `1.0` asserts exit 0 (`tests/unit/tasks/eval/test_skills.py`)
- [x] Both committed logs re-verified from this branch: `status: success`, 27/27 samples completed, `reducer: pass_k_3`, `accuracy` 1.000 / 0.000
- [x] Zero absolute host paths remain in the committed logs (scanned with `HOST_PATH_PATTERN`'s own regex → 0 hits across both files)
- [x] Readback fails **closed** — non-success status, missing arm, and missing reducer/metric each raise rather than defaulting to a pass
- [ ] **Not re-run in this session:** the live `mise run eval:skills:configure`. It needs an authenticated `claude` and real token spend. The author's gated run completed in 295 s at exit 0; its committed logs are the artifact verified above. Re-run it locally if you want to see the gate close for yourself.
- [ ] **Not covered by design:** ask-before-ambiguous-set. Deterministic outcome grading cannot express it — a conscious boundary stated in the plan.

## Notes for Reviewers

Four things are worth your attention, in descending order of consequence.

**1. The host-native pivot is a real deviation from ADR-0011's mechanism.** The plan assumed `inspect_swe.claude_code()` driving a Dockerised CLI. That bridge routes every model call through Inspect's *metered* `anthropic/…` provider, so it cannot run on a Claude subscription — and the API key on hand was unfunded. The eval was re-architected to drive `claude -p --output-format stream-json` host-natively, dropping the bridge and Docker while keeping the Inspect framework (epochs, `pass_k` reducer, scorer, `EvalLog`). The cost of that trade is the hand-rolled `parse_transcript`. A **fallback is documented**: restore the bridge behind a local meridian proxy, with zero code change. The decision itself (Inspect, pass^k, dev-time/committed) is unchanged, so this is recorded as an ADR implementation note rather than a superseding ADR — please push back if you think it warrants the stronger treatment.

**2. The committed log is not portable across machines.** `claude -p` loads the operator's user-level `CLAUDE.md` and hooks. On the authoring machine the user memory imports an `RTK.md`, and four baseline samples went hunting for `rtk` instead of `luminosity`; the with-skill arm shows no such detours. **The contamination therefore biases the baseline downward and flatters the A/B contrast.** Grading itself is sound — the operator's `PreToolUse` hook passes the graded argv through unrewritten (verified). It is accepted, not fixed: on CLI 2.1.203, subscription auth and context isolation are mutually exclusive (`--bare` gives isolation but never reads OAuth/keychain). Read the baseline as a *lower bound*. The lever, when portability matters, is `--bare` plus a funded `ANTHROPIC_API_KEY`.

**3. `1.000` is one stochastic draw, not a strong claim.** The first gated run scored `0.889` — a single conflict-on-set flake — which is the more honest picture of the gate's headroom. The skill-attribution conjunct added in review can only ever *lower* a score, and it lowered nothing. Also note the baseline's `0.000` is a `pass^k`, not a per-sample zero: one baseline sample did score CORRECT, but pass^k requires all three epochs to pass. The baseline is not structurally incapable — it simply does not route through the CLI reliably without the skill, which is exactly what the eval measures.

**4. ADR-0011's `pass_k` claim was inverted, in the ADR's favour.** Earlier 0010 research (against an older Inspect) concluded Inspect had *no* `pass_k` and that a custom all-succeed reducer was needed. Verified against the installed `0.3.244` source, `inspect_ai.scorer.pass_k(k)` exists and is `C(correct,k)/C(total,k)`, which at `epochs == k` collapses to 1.0 iff all k trials pass. The ADR's original `Epochs(k, pass_k(k))` wording was literally correct all along; the custom reducer is dropped and the native one wired directly. (`pass_at(k)` is the *lenient* pass@k and is deliberately not used.)

**Two narrowings you should know about**, both deliberate and now documented:

- **Get and error tasks grade *routing*, not transcript output.** The scorer asserts the agent ran the canonical argv, then **re-executes** it against the seeded fixture rather than trusting the agent's reported text — a tool result cannot reliably carry an exit code, and the CLI is the oracle.
- **`_BYPASS_TOOLS` was dropped because it never did what it claimed.** A disallow list of `Read`/`Grep`/`Glob` supposedly made the CLI "the only path to the answer", but with `Bash` allowed, `cat`/`grep`/`find` reproduce them — and the baseline used exactly that in 12 of 27 samples. Routing is enforced by the scorer's `config_command_ran`. Both arms now receive an identical toolset and differ **only** in `Skill`.

**Follow-up work, not blocking:**

- Revisit `fail_on_error=True` resilience before the documented 20–50-task / k 5–10 ramp — it currently conflates transient infra failure with model failure. Acceptable at 9 tasks × k=3.
- Produce one committed log under `--bare` + a funded `ANTHROPIC_API_KEY`, so the durable signal is free of the operator's `CLAUDE.md` and hooks.
