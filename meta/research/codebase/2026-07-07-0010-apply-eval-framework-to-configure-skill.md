---
type: codebase-research
id: "2026-07-07-0010-apply-eval-framework-to-configure-skill"
title: "Research: Apply the Inspect Eval Framework to the configure Skill (0010)"
date: "2026-07-06T23:21:13+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0010"
parent: "work-item:0010"
relates_to: ["codebase-research:2026-07-05-0009-multi-level-configuration-system"]
topic: "Applying the Inspect eval framework to the configure skill"
tags: [research, codebase, evaluation, inspect, configure, skills, mise, invoke]
revision: "62b812f66e50d2a7069d120ebf9680dbc41f6db1"
repository: "luminosity"
last_updated: "2026-07-06T23:21:13+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Apply the Inspect Eval Framework to the configure Skill (0010)

**Date**: 2026-07-06T23:21:13+00:00
**Author**: Toby Clemson
**Git Commit**: 62b812f66e50d2a7069d120ebf9680dbc41f6db1
**Branch**: HEAD (detached; jj-colocated)
**Repository**: luminosity

## Research Question

For work item 0010 ("Apply the Eval Framework to the `configure` Skill"), research
the codebase to educate an implementation, and additionally perform thorough web
research into **Inspect** (UK AISI) so the implementation is grounded in the real
API. Specifically: where does everything the eval must touch live (the `configure`
skill, its CLI contract, the task tree, the test tree, dependency pinning), what
patterns should new code follow, and how do the framework decisions in the spike /
ADR map onto Inspect's actual surface?

## Summary

The work is **entirely greenfield** — no `tests/evals/`, no `inspect-ai`
dependency, no eval task, no `epochs`/`pass_k` code exists yet. Everything the eval
grades against, however, is already shipped and precise: the `configure` skill
(`skills/config/configure/SKILL.md`) is a thin instructional wrapper that tells
Claude to run the Rust `luminosity config get|set` subcommand and echo its stdout
(on success) or its `luminosity: …` stderr line (on failure). That CLI's stdout /
exit-code behaviour is the deterministic **grading oracle** for the eval, and it is
fully characterised below (§"The grading oracle").

Two findings materially change the shape of the implementation versus a naive
reading of the work item:

1. **The pass^k reducer name in the spike/ADR/work-item is wrong, and the
   semantic it names is the opposite of what Inspect's similarly-named reducer
   does.** The documents say `Epochs(k, pass_k(k))` and "Inspect natively computes
   pass^k (all-k-succeed)". Inspect has **no `pass_k`**. Its real reducer
   `pass_at(k)` computes **pass@k = "≥1 of k trials succeeds"** — the *lenient*
   statistic, the opposite of the hard "all-k-succeed" gate the spike wants. The
   correct Inspect reducer for the spike's intended **pass^k (all-k-succeed)**
   semantics is **`at_least(k)` with k equal to the epoch count** (or a small
   custom all-succeed `@score_reducer`). This must be reconciled deliberately, not
   followed literally. (See §"Critical reconciliation".)

2. **Driving Claude Code as the agent under test — flagged as the story's chief
   residual risk — is largely solved off-the-shelf.** Meridian Labs (the Inspect
   team) ships **`inspect_swe`**, whose **`claude_code()` solver** runs the real
   Claude Code CLI in unattended mode as an Inspect solver and proxies its model
   calls back through Inspect. This is the purpose-built version of the work item's
   "hand-built A/B driving Claude Code as an external agent." It requires a Docker
   sandbox, though, which is a real operational cost to weigh against a thinner
   custom-solver approach. (See §"Driving Claude Code".)

The task-tree and gating mechanics are well-templated by existing code: a new
`tasks/eval/` collection registered in `tasks/__init__.py`, `[tasks."eval:…"]`
blocks in `mise.toml` **deliberately absent** from `check`/`default`'s `depends`,
a pure testable helper that computes the verdict, and a thin `@task` wrapper that
`raise Exit(msg, code=1)` below the floor — mirroring `tasks/version.py:check` and
`tasks/pup.py:check` almost line for line. The two-sided threshold unit test copies
`tests/unit/tasks/test_pup.py` / `test_version.py`.

## Detailed Findings

### The `configure` skill and its CLI (what the eval exercises)

- **Skill**: `skills/config/configure/SKILL.md` — the *only* file in the skill
  directory. It does **not** use the `` !`command` `` preprocessor (no live-context
  injection); its frontmatter grants
  `allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)`
  (`SKILL.md:9-10`). It is purely instructional: Claude runs the CLI itself.
- **Skill registration**: `.claude-plugin/plugin.json:10` registers by *category
  directory* — `"skills": ["./skills/config/"]`, not by individual skill.
- **The skill's committed contract** (`SKILL.md:34-64`): manage config *only*
  through the CLI, never read/parse/write files directly. For a successful `get`,
  report the command's stdout; on any non-zero exit, relay the `luminosity: …`
  stderr message verbatim and do **not** guess a value; for `set`, surface any
  conflict message rather than working around it; ask before a `set` when intent
  (level, or get-vs-set) is ambiguous.
- **The CLI it drives** is the Rust launcher's `config` subcommand:
  - Surface (`cli/launcher/src/launch/inbound/cli.rs:36-68`): exactly two actions,
    `get` and `set` (no `list`/`unset`/`delete`). Binary name `luminosity`.
    - `luminosity config get <key> [--level team|personal]`
    - `luminosity config set <key> <value> [--level team|personal]`
  - Handlers: `cli/launcher/src/config_command/inbound/cli.rs` (`get()` 29-42,
    `set()` 44-52, `render()` 54-63).
  - Core service + precedence: `cli/config/src/service.rs`; levels in
    `cli/config/src/level.rs:6-10`.
  - Error taxonomy: `cli/config/src/error.rs`.
  - Boundary/exit handling + stderr prefix: `cli/launcher/src/main.rs:155-163`.
  - Black-box behavioural assertions already exist:
    `cli/launcher/tests/config.rs` (a ready reference for expected values in the
    dataset).

> **Note vs CLAUDE.md**: CLAUDE.md still describes a "large bash config library"
> under `scripts/`. That is stale — config reading is now the Rust `cli/config` /
> `cli/config-adapters` crates. `scripts/` currently holds only
> `lint-bashisms.sh`, and there is no `hooks/` tree. The eval grades Rust CLI
> behaviour, not shell.

### The grading oracle (exact stdout / exit-code contract)

This is what the eval's scorer must assert against. Precise, traced end-to-end:

| Scenario | stdout | exit | stderr |
|---|---|---|---|
| `get` hit | `render(value)` + `\n` (e.g. `v\n`) | 0 | — |
| `get` hit, null/empty value | just `\n` (still success) | 0 | — |
| `set` (any success) | **empty** (no `println!`) | 0 | — |
| `get` miss (no `--level`) | empty | 1 | `luminosity: config key '<key>' is not set` |
| `get` miss (`--level`) | empty | 1 | `luminosity: config key '<key>' is not set at level '<level>'` |
| invalid key (empty/`..`/leading dot) | empty | 1 | `luminosity: invalid config key '<key>': expected dot-separated non-empty segments` |
| path conflict on `set` | empty | 1 | `luminosity: cannot set '<key>': '<at>' is a <existing>, not a <opposite>` |
| malformed config file | empty | 1 | `luminosity: config file '<path>' has malformed frontmatter: <detail>` |
| bad `--level` value | empty | **2** (clap usage error) | clap message naming the bad value |

Key mechanics for the scorer author:
- `render()` (`config_command/inbound/cli.rs:54-63`): `String` verbatim; `Bool` →
  `true`/`false`; `Int` → decimal; `Float` → canonical (`1.5`); `Null` → empty.
- **Precedence**: exactly two levels, `Team` and `Personal`; **Personal wins over
  Team** (`config/src/service.rs:83-99`). Team file `.luminosity/config.md`,
  Personal file `.luminosity/config.local.md` (`config-adapters/src/store.rs:43-48`).
  A `--level`-scoped `get` reads only that level.
- **Every domain error collapses to exit 1** with a `luminosity: ` stderr prefix
  and empty stdout (`error.rs:99-103` → `main.rs:160-163`). The *only* exit-code
  distinctions available are **0 = success, 1 = any domain failure, 2 = clap usage
  error**. So the missing/malformed-key task class (AC1) grades on "non-zero exit +
  expected message substring", while get/set/precedence tasks grade on
  "stdout value equals expected".
- A successful `set` produces **empty** stdout — a subtle oracle point: a
  precedence/set task cannot grade `set` on stdout; it must grade the *subsequent
  `get`* or the exit code.

This directly satisfies the work item's AC2 two grading modes (value-equality for
get/set/precedence; error/non-zero-exit for missing/malformed-key), which the 0010
review specifically hardened.

### Where the eval wires into the build system

- **mise → invoke mapping** (`mise.toml`): a leaf maps a colon-namespaced
  `mise run` name to a dotted invoke path and declares provisioning `depends`;
  roll-up tiers have **no `run`, only `depends`**. Example to mirror
  (`mise.toml:71-96`):
  ```toml
  [tasks."test:unit:cli"]
  depends = ["deps:install:rust-components"]
  run = "invoke test.cli.run"

  [tasks."test:unit"]
  depends = ["test:unit:tasks", "test:unit:cli"]   # roll-up, no run
  ```
- **Excluding a tier from CI is done by omission** — a task is kept out of the
  sweep simply by *not* listing it in `check`'s or `default`'s `depends`
  (`mise.toml:274-280`). Precedent: `test:integration:pup`, `launcher:check`,
  `kernel:check` all exist as ad-hoc entry points deliberately absent from the
  aggregates. So `eval` / `eval:skills:configure` are added as `[tasks.…]` blocks
  and simply **left out** of `check`/`default` — no special flag needed.
- **Collection registration**: add `tasks/eval/__init__.py` building a `Collection`
  (mirror `tasks/test/__init__.py:1-11`) and register it in `tasks/__init__.py`
  via `ns.add_collection(Collection.from_module(eval_))` (note `eval` is a Python
  builtin — import the module `as eval_`). A `skills.configure` leaf mirrors the
  `test.integration` sub-namespace shape.
- **The leaf task pattern** (`tasks/pup.py:7-24`, `tasks/test/cli.py:14-23`,
  `tasks/format/build_system.py:1-15`): house style is
  `with context.cd(str(ROOT)): result = context.run(cmd, warn=True, pty=False)`
  then `if <bad>: raise Exit(msg, code=1)`. Invoke's `Exit` (a `SystemExit`
  subclass) is the house exception, **not** bare `SystemExit`.
- **The gate pattern** (`tasks/version.py:116-148`): keep the *pure decision* in a
  helper (`_mismatching_anchor_files`, trivially unit-testable with no `ctx`) and
  let the `@task` be a thin `if bad: raise Exit(...)` wrapper. This is the exact
  shape for "read `pass^k` off the log → gate": a pure
  `def below_floor(pass_k: float) -> bool` helper + a thin task.
- **Env escape-hatch pattern** (`tasks/pup.py` + `tasks/shared/rust.py:14-25`):
  `pup_mode()`/`coverage_enabled()` read an env knob *inside the task body* (never
  at import) with a `_FALSEY` normalisation set — the model if the eval wants a
  `LUMINOSITY_EVAL_*` knob (e.g. to skip the live run in constrained environments).
- **Shared helpers** (`tasks/shared/`): reuse `REPO_ROOT`/`WORKSPACE_ROOT`
  (`paths.py`), `atomic_write_text` (`files.py`) for writing the committed log,
  add a domain exception to `errors.py` rather than raising bare `Exception`.
  There is **no** generic subprocess wrapper — `context.run(...)` in the task body
  is the convention; don't invent one.

### Where the eval's tests and dataset live

- **Test tree**: unit tests for tasks under `tests/unit/tasks/`; integration under
  `tests/integration/`. Pytest config at `pyproject.toml`
  `[tool.pytest.ini_options]` (line 33); shared fixtures `tests/conftest.py`.
  **No `tests/evals/` exists yet** — it is a new third tier alongside `unit/` and
  `integration/`, and the ADR is explicit that eval definitions *and* results live
  under the test path, **never under `skills/`**.
- **Two-sided gate test template** (`tests/unit/tasks/test_pup.py:27-44`): force the
  bad side with `ctx.run.return_value = MagicMock(exited=1)`, assert the failing
  branch with `with pytest.raises(Exit):`, assert the passing branch by calling the
  task and letting it return. For the pass^k gate the unit test feeds a *synthetic*
  `pass_k` value (below 0.8 → expect `Exit`; ≥ 0.8 → expect clean return),
  satisfying AC6 without a live run — so the gate helper must take the score as a
  plain argument, decoupled from `eval()`.
- **`ctx` fixture** (`tests/unit/tasks/test_test.py:16-24`):
  `MagicMock(spec=Context)` with `m.run.return_value = MagicMock(exited=0)`.
- **Dependency pinning**: add `inspect-ai` (and, if used, `inspect-swe`) to
  `pyproject.toml` `dependencies`/dev-deps and lock in `uv.lock`, per the repo's
  exact-pin convention. Both install via `uv` — no new language toolchain (Inspect
  is Python), preserving the Python/shell/Rust three.
- **Eval-file naming**: name the eval file `configure_eval.py` (an Inspect `@task`
  file), **not** `test_*`, so pytest does not collect it (AC7). The dataset is
  `dataset.jsonl`; committed logs go under `results/<timestamp>.json`.

### Critical reconciliation: pass^k vs Inspect's `pass_at(k)`

The spike (0003), ADR-0011, and the work item all state Inspect natively computes
**pass^k (all-k-succeed)** via `pass_k(k)`, wired as `Epochs(k, pass_k(k))` with
`pass_k` read off `log.results`. Verified against the live Inspect API, this is
wrong on two counts:

- There is **no `pass_k` / `pass_k(k)`** function or reducer in Inspect.
- Inspect's real reducer `pass_at(k)` (from `inspect_ai.scorer`) computes the
  **Codex pass@k estimator — the probability that *at least one* of k trials is
  correct**. That is the *lenient* statistic. Using it as the gate would make the
  bar *easier* with more trials — the exact opposite of a hard regression gate.

The intent in the documents is unambiguous ("all k trials succeed", "the correct
statistic for a hard regression bar"). Inspect *does* express that intent, via a
different reducer:

- **`at_least(k)`** marks a sample correct iff **≥ k of its trials are correct**.
  With `epochs = 3` and reducer **`at_least(3)`**, a sample passes iff **all 3
  trials pass** = pass^k. The `accuracy` metric over that reducer then reports the
  fraction of tasks passing — exactly the "gate fraction ≥ 0.8" the work item's AC5
  describes. String shorthand: `Epochs(3, "at_least_3")`.
- Alternatively, a ~5-line custom `@score_reducer` that returns CORRECT iff every
  epoch is CORRECT makes the "all-k-succeed" semantics explicit and self-documenting
  (recommended for clarity, since `at_least(k)==k` is a slightly subtle idiom).

**At the 3-task/3-trial floor this is partly masked** — the gate collapses to "all
tasks pass all trials" (achievable fractions 0, ⅓, ⅔, 1; ≥ 0.8 ⇒ 1.0). But the
reducer choice determines the semantics the moment the suite grows past 3 tasks or
k rises toward 5–10 (the ramp commitment). Wire `at_least(k)` (or the custom
reducer), **not** `pass_at(k)`. This discrepancy should be recorded against the ADR
(a superseding note or an implementation ADR) so the docs and code agree.

The mechanical read-back path (from live API research):
```python
log = eval(task, model=..., epochs=Epochs(3, at_least(3)), log_format="json")[0]
score = log.results.scores[0]          # EvalScore; .reducer == "at_least_3"
pass_k = score.metrics["accuracy"].value   # the gate fraction
```
(With multiple reducers you get one `EvalScore` per reducer in
`log.results.scores`, distinguished by `.reducer` — filter on it.)

### Inspect core API (grounded, with links)

Docs root: https://inspect.aisi.org.uk/ · Repo:
https://github.com/UKGovernmentBEIS/inspect_ai · PyPI:
https://pypi.org/project/inspect-ai/ (verified against `main` reference docs, Jul
2026; version stamped on PyPI/CHANGELOG, not in-page).

- **Task anatomy** (https://inspect.aisi.org.uk/tasks.html): a `@task` fn returns
  `Task(dataset=, solver=, scorer=, epochs=, name=)`. Lifecycle
  setup → solver → scorer → epoch-reduce → metrics → `EvalLog`.
- **Datasets** (https://inspect.aisi.org.uk/datasets.html): `json_dataset("dataset.jsonl")`
  auto-detects JSONL; each line's `input`/`target`/`id`/`metadata` map onto a
  `Sample`. Custom field names via `FieldSpec`, or a `record_to_sample` callable.
  Put the "expected error marker" for missing/malformed tasks in
  `Sample.metadata` (reachable as `state.metadata`).
- **Solvers** (https://inspect.aisi.org.uk/solvers.html): a solver is
  `(TaskState, generate) -> TaskState`. Built-ins `generate()`,
  `system_message(...)`, `chain(...)`, `prompt_template(...)`; custom via
  `@solver`. **A/B**: cleanest is two `Task`s (or one parameterised `@task` with an
  arm flag) sharing one dataset/scorer/model, differing only in the solver chain;
  `eval()` also takes a `solver=` that overrides the task's solver for arm B. Keep
  model/temperature/seed identical across arms.
- **Scorers** (https://inspect.aisi.org.uk/scorers.html,
  https://inspect.aisi.org.uk/custom-scorers.html): built-ins `match(location=…)`,
  `includes()`, `exact()`. For this eval, author **one custom `@scorer`** that
  branches on `state.metadata["expect_error"]`: error case → CORRECT iff the marker
  appears in `state.output.completion`; value case → CORRECT iff
  `output.strip() == target.text.strip()`. Return `Score(value=CORRECT|INCORRECT,
  answer=…, explanation=…)`; `@scorer(metrics=[accuracy(), stderr()])`.
- **In-process `eval()`** (https://inspect.aisi.org.uk/reference/inspect_ai.html):
  `eval(tasks, model=, solver=, epochs=, log_dir=, log_format=…) -> list[EvalLog]`
  (one per task; blocks, manages its own event loop — use `eval_async` only inside
  a running loop). Read results off `log.results.scores[*].metrics[name].value`;
  `log.status` ∈ started|success|cancelled|error.
- **Epochs / reducers** (https://inspect.aisi.org.uk/reference/inspect_ai.scorer.html):
  `Epochs(epochs, reducer)`; reducers `pass_at(k)`, **`at_least(k)`**,
  `mean_score`, `max_score`, `median_score`, `mode_score`; string shorthands
  `"pass_at_1"`, `"at_least_3"`, `"mean"`. **Use `at_least(k)` for pass^k** (see
  reconciliation above).
- **Log formats** (https://inspect.aisi.org.uk/eval-logs.html): default `.eval`
  (binary, compact) vs `.json` (text, diffable). Force JSON with
  `eval(..., log_format="json")` / `INSPECT_LOG_FORMAT=json` /
  `--log-format=json`. `read_eval_log()` / `write_eval_log()` /
  `read_eval_log_samples()` from `inspect_ai.log` read logs back (both formats via
  `format="auto"`); `header_only=True` skips samples. The work item's committed
  `results/<timestamp>.json` is exactly the JSON format for VCS-diffability.

### Driving Claude Code as the agent under test

This is the work item's flagged residual risk ("no live prototype was run; the
first throwaway run should validate the Inspect-driving-Claude-Code A/B"). Findings:

- **Off-the-shelf: `inspect_swe.claude_code()`** — Meridian Labs' package ships a
  `claude_code()` solver that runs the real Claude Code CLI in unattended mode as
  an Inspect solver and **proxies its model calls back through Inspect** (so you get
  model-agnostic routing, token/time limits, and full transcript capture for free).
  Params include `skills=`, `mcp_servers=`, `disallowed_tools=`, `system_prompt=`,
  `model=`, `version=`. Docs:
  https://meridianlabs-ai.github.io/inspect_swe/claude_code.html · repo:
  https://github.com/meridianlabs-ai/inspect_swe. **Caveat**: it is built on
  `sandbox_agent_bridge()` and **requires a Docker (or k8s) sandbox**, and it is a
  young pre-1.0 package on an evolving bridge API — pin versions.
- **The seam it's built on: the Agent Bridge**
  (https://inspect.aisi.org.uk/agent-bridge.html) — `sandbox_agent_bridge()` for
  CLI/any-language agents (stands up a proxy on `localhost:13131`; point
  `ANTHROPIC_BASE_URL` at it), `agent_bridge()` for in-process Python. The older
  `bridge()` is **deprecated** — use the newer names, pin the version.
- **Thinnest custom route**: a custom `@solver` (or a `@modelapi` provider,
  https://inspect.aisi.org.uk/extensions-model-api.html) that shells out to
  `claude -p … --output-format json` and treats stdout as the generation. This
  needs **no Inspect sandbox** but forgoes the bridge's automatic model-routing +
  transcript, shifting skill-detection and model-swap burden onto the author. Given
  the `configure` skill just needs Claude to run one CLI command and echo output,
  this thin route may be the pragmatic first prototype; `inspect_swe` is the richer
  path if the agent loop/isolation matters.
- **Claude Code headless flags** (https://code.claude.com/docs/en/headless,
  https://code.claude.com/docs/en/cli-reference): `-p/--print`,
  `--output-format text|json|stream-json`, `--model`, `--allowedTools`,
  `--permission-mode` (`dontAsk` for locked-down runs), `--max-turns`,
  `--mcp-config`/`--plugin-dir`/`--agents`, `--json-schema`. **Gotcha**: `--bare`
  *skips* skill/plugin/MCP discovery — do **not** use it when the whole point is to
  exercise a skill (or explicitly re-add the plugin via `--plugin-dir`).
  `/skill-name` in the prompt string is expanded in `-p` mode.
- **Skill-invocation detection** (the work item's "author's responsibility"): the
  reliable signal is a first-class **`Skill` tool-use event** in the transcript.
  Via Claude Code directly: run `--output-format stream-json --verbose` and filter
  content blocks for `{"type":"tool_use","name":"Skill"}` matching the skill name
  (the `system/init` event also lists loaded plugins — fail early if the plugin
  didn't load). Via Inspect: scan the log `transcript` for the `Skill` tool event.
  Prior art: promptfoo normalises this into a `skill-used` assertion
  (https://www.promptfoo.dev/docs/guides/test-agent-skills/) — a concrete pattern
  to copy, and the reason promptfoo is the pre-vetted fallback.

## Code References

- `skills/config/configure/SKILL.md:9-64` — the skill: allowed-tools scope +
  instructional contract (report stdout on success, relay stderr verbatim on
  failure).
- `.claude-plugin/plugin.json:10` — skill registration by category directory.
- `cli/launcher/src/launch/inbound/cli.rs:36-68` — `config get|set` CLI surface,
  `--level team|personal`.
- `cli/launcher/src/config_command/inbound/cli.rs:29-63` — `get`/`set` handlers and
  `render()` (the stdout format).
- `cli/launcher/src/main.rs:155-163` — exit-code mapping (0/1/2) and `luminosity: `
  stderr prefix.
- `cli/config/src/service.rs:83-99` — Personal-over-Team precedence resolution.
- `cli/config/src/level.rs:6-10` — the two levels.
- `cli/config/src/error.rs:63-103` — error message templates; all collapse to
  exit 1.
- `cli/launcher/tests/config.rs` — black-box behavioural assertions (ready
  reference for dataset expected values).
- `mise.toml:71-96,274-280` — leaf/roll-up wiring; exclusion-by-omission from
  `check`/`default`.
- `tasks/__init__.py:22-68`, `tasks/test/__init__.py:1-11` — collection
  registration idioms.
- `tasks/version.py:116-148` — pure-helper + thin-`@task`-gate pattern (copy for
  the pass^k gate).
- `tasks/pup.py:7-24` — two-sided (warn/deny) gate with `raise Exit(..., code=1)`.
- `tasks/shared/{paths,files,rust,errors}.py` — reusable helpers.
- `tests/unit/tasks/test_pup.py:27-44`, `test_version.py:16-102` — two-sided
  exit-behaviour test templates (copy for AC6).
- `pyproject.toml` (`[tool.pytest.ini_options]`, dependencies) + `uv.lock` — where
  `inspect-ai` is pinned.

## Architecture Insights

- **The eval grades a Rust CLI's observable behaviour, not the skill's prose.**
  Because `configure`'s SKILL.md is a pass-through wrapper, the skill's correctness
  reduces to Claude routing `get`/`set` + key + `--level` straight through and
  echoing the right stream. The grading oracle is therefore fully deterministic and
  already covered by `cli/launcher/tests/config.rs` — the dataset's expected values
  can be lifted from those tests.
- **"Exclude from CI" is a structural property, not a flag.** The build system's
  convention of composing tiers *only* via `mise.toml` `depends` means the eval
  tier is excluded simply by not being referenced — consistent with how
  `launcher:check`/`kernel:check`/`test:integration:pup` already sit outside the
  aggregates.
- **Gate logic belongs in a pure, ctx-free helper.** Every existing gate
  (`version.py`, `pup.py`) separates the decision from the `@task`; the pass^k gate
  should too, so AC6's two-sided test feeds the helper a synthetic score with no
  `eval()` run.
- **Inspect adds no toolchain but the *live run* adds a real runtime dependency**
  (authenticated model API + token budget, and — if `inspect_swe` is used — Docker).
  This is precisely why the tier is dev-time/committed, not CI.
- **A shared eval-harness helper is anticipated.** The spike notes the A/B +
  skill-detection authoring cost is "mitigated by a shared eval-harness helper if a
  second skill is later evaluated" — worth structuring `configure_eval.py` so the
  A/B scaffolding and scorer are extractable later.

## Historical Context

- `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md` — the
  accepted decision 0010 applies: Inspect over promptfoo/skill-creator; pass^k ≥ 0.8
  over k=3; dev-time/committed/no-CI; layout `tests/evals/skills/configure/`. Names
  the metric `pass_k(k)` — the term this research reconciles to `at_least(k)`.
- `meta/work/0003-skill-evaluation-framework-selection.md` — the spike: framework
  rationale, the "no live prototype" residual risk, the promptfoo fallback trigger
  ("if the external-agent A/B proves awkward"), and the ramp to 20–50 tasks / k
  toward 5–10.
- `meta/reviews/work/0010-apply-eval-framework-to-configure-skill-review-1.md` —
  APPROVE after two passes. Load-bearing corrections now baked into the ACs: AC2
  defines *two* grading modes (value-equality vs error/non-zero-exit for
  missing/malformed keys — a genuine implementation point), AC3 records both A/B
  arms with the baseline "for attribution only" (below-baseline = investigate, not
  fail), AC6 is the two-sided gate test, and model-version drift was added as a
  third eval-refresh trigger (alongside first material behaviour change / first
  uncovered real failure).
- `meta/work/0009-multi-level-configuration-system.md` +
  `meta/plans/2026-07-05-0009-multi-level-configuration-system.md` +
  `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md` +
  `meta/prs/9-description.md` — the configure skill/CLI under test; closing 0010
  also discharges the behavioural-equivalence validation 0009 deferred.
- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — parent
  epic (assumption A4: apply, not just decide, the eval recommendation within the
  epic).
- No `meta/plans/` or `meta/research/` document for 0010 exists yet — this is the
  first research artifact for the story.

## Related Research

- `meta/research/codebase/2026-07-05-0009-multi-level-configuration-system.md` —
  the configuration system that produced the CLI this eval grades.

## Open Questions

1. **pass^k reducer**: confirm `at_least(k)` (or a custom all-succeed
   `@score_reducer`) as the wired reducer, and record a superseding/implementation
   note against ADR-0011 so the `pass_k(k)` terminology is corrected rather than
   silently followed. (Strong recommendation: `at_least(k)`.)
2. **Claude-Code driving approach**: thin custom `@solver`/`@modelapi` shelling out
   to `claude -p --output-format json` (no sandbox, simplest for a pass-through
   skill) **vs** `inspect_swe.claude_code()` (richer, but Docker-sandbox + pre-1.0
   dependency). The first throwaway run (per the spike) should decide; promptfoo is
   the fallback if either proves awkward.
3. **Skill-invocation detection depth**: is asserting the `Skill` tool-use event
   required for the bootstrap, or is outcome-grading (stdout/exit) alone sufficient
   for the ≥3-task floor? AC2 grades on outcome; skill-detection may be a later
   ramp addition.
4. **`set`-task oracle**: since a successful `set` emits empty stdout, precedence
   tasks must grade the *follow-up `get`* (or exit code). Confirm the dataset models
   set/precedence as a two-step (set then get) or as a get against a pre-seeded
   fixture config file.
5. **Environment provisioning**: does the eval task need a `deps:install:*`-style
   `depends` (e.g. to ensure Docker / the built `luminosity` binary is present), and
   should a `LUMINOSITY_EVAL_*` env knob gate the live run for constrained
   environments (mirroring `pup_mode()`/`coverage_enabled()`)?
