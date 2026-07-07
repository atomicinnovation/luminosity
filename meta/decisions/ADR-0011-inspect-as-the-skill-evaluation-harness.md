---
type: adr
id: "ADR-0011"
title: "Inspect as the Skill-Evaluation Harness"
date: "2026-06-26T07:43:25+00:00"
author: Toby Clemson
producer: create-adr
status: accepted
decision_makers: [Toby Clemson]
parent: "work-item:0005"
relates_to: ["adr:ADR-0004", "adr:ADR-0006", "adr:ADR-0007", "adr:ADR-0008"]
tags: [evaluation, skills, testing, inspect, harness, quality-gate, python]
last_updated: "2026-06-26T07:43:25+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# ADR-0011: Inspect as the Skill-Evaluation Harness

**Date**: 2026-06-26
**Status**: Accepted
**Author**: Toby Clemson

## Context

Skills are the product (ADR-0007), so their quality needs a regression gate as
deliberate as the lint and type checks guarding the rest of the repo. A spike
(work item 0003) was run to choose that harness; this ADR records its
Recommendation. No skill eval exists yet — the harness is selected on verified
mechanism, and the first eval target (the `configure` skill) is built and
evaluated downstream (stories 0009, 0010).

The parent epic's leading hypothesis was Anthropic's `skill-creator`. The spike
reversed it. The decisive constraint, surfaced during the spike, is the
requirement to **run evals from a local `mise`+invoke task and fail at a
threshold**: `skill-creator`'s task-quality loop is interactive and
subagent-driven inside a live Claude Code session with a human at a browser
viewer — there is no headless command that runs tasks, grades them, and exits
non-zero below a bar (verified in the installed source). It therefore cannot be
the automation harness, though it remains useful for interactive authoring.

The forces:

- **Skills-as-product needs a real gate.** A skill regression must fail a build
  the way a type error does, not rely on a human noticing in a viewer.
- **The repo guards its toolchain count.** Three languages are a standing,
  enforced decision (ADR-0004: Python / shell / Rust). A harness that adds a
  fourth toolchain pays a real cost.
- **LLM behaviour is non-deterministic**, so the gate must measure *variance
  across repeated trials*, not a single pass/fail — and on the statistic that
  fits a hard regression gate.
- **The corpus is the source of truth** (ADR-0008). Eval definitions and their
  results should be committed files that diff in VCS, not state in a SaaS store.
- **Token cost is real.** Running every skill eval on every CI build is
  prohibitive; evals must be opt-in, not part of the default sweep.

## Decision Drivers

- A headless, threshold-gating run from a `mise`+invoke build task.
- Variance reporting on the right statistic — pass^k (all-k-trials succeed), the
  correct gate for a hard regression bar — not a pooled mean.
- No new language toolchain beyond the established three.
- A committed-file model for eval definitions and results.
- Lowest maintenance/longevity risk among viable harnesses.
- Evals excluded from the default CI sweep to control token cost.

## Considered Options

1. **Inspect (UK AISI)** — Python-native eval framework; in-process `eval()`,
   native `pass_k(k)` metric, MIT / government-backed.
2. **promptfoo** — declarative YAML eval matrix with a built-in
   pass-rate-threshold exit code and a native `skill-used` assertion; a Node
   tool, recently acquired by OpenAI.
3. **skill-creator (Anthropic)** — purpose-built to evaluate a skill *as a
   skill*, first-party, but an interactive in-session loop with no headless
   gating command.
4. **DeepEval (Confident AI)** — pytest-native Python eval library; no native
   trial-repeat / variance, small-company longevity risk.

(The spike's landscape survey weighed and dismissed a further ~10 platforms and
benchmarks — OpenAI Evals, LangSmith, agentevals/OpenEvals, Braintrust,
Langfuse, Arize Phoenix, TruLens, Ragas, Galileo, Maxim AI/Latitude — each
SaaS-centric, observability-led, or a poor fit for committed skill A/B.)

## Decision

We will **adopt Inspect (UK AISI) as the skill-evaluation harness**, treating
skill evals as a third **test tier** alongside `unit/` and `integration/`.

- **Mechanism.** Inspect is Python-native and runs **in-process** via `eval()`
  inside an invoke task — no new language toolchain (it installs via `uv` and
  lints under the existing ruff/pyrefly). The task runs with
  `epochs=Epochs(k, pass_k(k))`, reads the `pass_k` metric off `log.results`,
  and exits non-zero below the floor. Inspect has no built-in score-threshold
  flag, so this ~3-line gate is wired by hand in the task.
- **Statistic.** The gate is **pass^k** (all k trials succeed), the correct
  statistic for a hard regression bar; Inspect is the only candidate that
  computes it natively (promptfoo gates on a pooled mean).
- **Layout.** Both eval definitions and committed results live under the test
  path, never under `skills/`:

  ```
  tests/evals/skills/configure/
  ├── configure_eval.py     # Inspect @task: dataset + with-skill/baseline solvers + scorer
  ├── dataset.jsonl         # the eval tasks
  └── results/
      └── <timestamp>.json  # committed Inspect log (--log-format json, so it diffs)
  ```

- **Invocation.** Entry point `mise run eval:skills:configure` (roll-up
  `mise run eval`). The eval tier is **excluded from the default `mise run` /
  `check` sweep** so it never runs on every CI build; it is run on demand during
  development, and results are committed by hand.
- **Bootstrap floor.** For `configure` in this epic: **≥ 3 tasks gated at pass^k
  ≥ 0.8 over k = 3 trials** — an explicit bootstrap smoke-test, with a ramp
  commitment toward the 20–50 real-failure-derived tasks that 2025–2026 guidance
  recommends, raising k as token budget allows.
- **skill-creator is retained as an optional, interactive authoring aid** —
  useful for hands-on authoring and blind A/B comparison, but not the gating
  harness.

We chose Inspect because it alone satisfies the hard requirement (headless,
threshold-gating, from a build task) on the *correct* metric, adds no new
toolchain, and carries the lowest longevity risk. **promptfoo** was the strong
runner-up — its built-in exit-code gate and turnkey skill A/B are genuine
advantages — but it gates on a pooled mean rather than pass^k, adds a Node
toolchain, and carries OpenAI-acquisition drift risk; it is the pre-vetted
fallback. **skill-creator** was rejected as the harness because its loop is
interactive and cannot gate headlessly. **DeepEval** was rejected for lacking
native variance/repeat and its small-company longevity risk.

## Consequences

### Positive

- Skill quality gets a real, headless regression gate that fails a build below a
  threshold, run from the same `mise` task runner as every other check.
- The gate measures variance on pass^k, the methodologically right statistic for
  a hard regression bar.
- No fourth language toolchain — Inspect is Python, installs via `uv`, and lints
  under the existing ruff/pyrefly setup (ADR-0004 preserved).
- Eval definitions and results are committed files that diff in VCS, fitting the
  corpus-as-source-of-truth model (ADR-0008).
- Excluding evals from the default sweep keeps token cost off every CI build
  while still gating on demand.

### Negative

- Inspect leaves the with-skill-vs-baseline A/B and skill-invocation detection to
  the author (promptfoo provides these turnkey) — a one-time authoring cost.
- The pass^k threshold check is hand-wired in the invoke task; Inspect ships no
  turnkey score-gate flag.
- The harness was selected on verified mechanism, not a live run against
  `configure` (which does not yet exist); an Inspect-driving-Claude-Code
  integration detail could bite during story 0010.

### Neutral

- `skill-creator` stays installed as an optional authoring/A-B convenience, not a
  necessity — a standing dual-tool distinction.
- The bootstrap floor (≥ 3 tasks, pass^k ≥ 0.8, k = 3) is explicitly provisional;
  the ramp toward 20–50 real-failure tasks is triggered by the first material
  `configure` behaviour change or first uncovered real-world failure.
- promptfoo is the pre-vetted fallback if the external-agent A/B proves awkward
  in 0010; its longevity under OpenAI stewardship is worth a re-check if invoked.
- Eval files are named so pytest does not collect them (Inspect `@task` files,
  not `test_*`), keeping the eval tier on the Inspect runner while sharing the
  `tests/` root — an implementation detail owned by story 0010.

## Implementation Notes (2026-07-08, story 0010)

Applying the harness surfaced one correction to this ADR's mechanism, recorded
here rather than by superseding the decision (the decision — Inspect, pass^k,
dev-time/committed — stands unchanged):

- **`pass_k(k)` is real and correct as of `inspect-ai==0.3.244`.** Earlier 0010
  research (written against an older Inspect) concluded Inspect had *no* `pass_k`
  and that the pass^k gate needed a custom all-succeed reducer or `at_least(k)`.
  Verified against the installed 0.3.244 source, `inspect_ai.scorer.pass_k(k)`
  exists and computes *"the probability that all k epoch attempts succeed"* — the
  draw-without-replacement estimator `C(correct, k) / C(total, k)`. With
  `epochs == k` (this eval's configuration) it collapses to 1.0 iff all k trials
  pass, else 0.0, so its `accuracy` metric over the tasks *is* pass^k. This ADR's
  original `Epochs(k, pass_k(k))` wording is therefore literally correct; the
  implementation wires the native reducer directly (no custom reducer), reading
  the fraction off `log.results.scores[*]` where `reducer == "pass_k_<k>"` and
  `metrics["accuracy"].value`. (`pass_at(k)` remains the *lenient* pass@k and is
  not used.)
- The full Phase-0 integration findings (Python 3.14 resolution, the required
  `httpx<1` constraint, the `claude_code()` signature, the file-path loader's
  absolute-import requirement) are recorded in
  `meta/research/codebase/2026-07-08-0010-inspect-integration-findings.md`.

## References

- `meta/work/0003-skill-evaluation-framework-selection.md` — Feeding spike; its
  Recommendation is the source of this decision.
- `meta/work/0005-record-spike-dependent-architecture-decisions-as-adrs.md` —
  Owning story (decision 11 of the baseline set).
- `meta/work/0010-apply-eval-framework-to-configure-skill.md` — Downstream story
  applying the harness to the `configure` skill as the first eval target.
- `meta/decisions/ADR-0004-three-toolchain-split.md` — The three-toolchain
  constraint this decision honours by staying in Python.
- `meta/decisions/ADR-0006-mise-invoke-task-runner.md` — The task runner the eval
  tier plugs into.
- `meta/decisions/ADR-0007-skills-as-the-product.md` — Establishes skills as the
  product this harness gates.
- `meta/decisions/ADR-0008-filesystem-as-message-bus-and-knowledge-corpus.md` —
  The committed-file model the eval definitions and results follow.
- Anthropic, "Demystifying evals for AI agents" (Jan 2026) — the methodology the
  bootstrap floor and ramp are measured against.
