---
type: codebase-research
id: "2026-07-08-0010-inspect-integration-findings"
title: "Phase 0 Findings: Inspect / inspect_swe Integration Unknowns (0010)"
date: "2026-07-08T00:00:00+00:00"
author: "Toby Clemson"
producer: implement-plan
status: in-progress
work_item_id: "0010"
parent: "work-item:0010"
relates_to: ["plan:2026-07-07-0010-apply-eval-framework-to-configure-skill"]
topic: "Resolving the pre-1.0 Inspect integration unknowns before building the eval"
tags: [research, inspect, inspect-swe, evaluation, configure, phase-0]
repository: "luminosity"
schema_version: 1
---

# Phase 0 Findings: Inspect / inspect_swe Integration Unknowns (0010)

Discovery phase for the plan
`meta/plans/2026-07-07-0010-apply-eval-framework-to-configure-skill.md`. Each
plan question is turned into a recorded fact against the **real** pinned
dependencies before the build phases consume it. Probes were run in a throwaway
`uv` project on the repo's own interpreter (CPython 3.14.4).

## Resolved pins

- **`inspect-ai==0.3.244`**
- **`inspect-swe==0.2.65`**
- **`httpx<1`** — a required third constraint (see item 1).

## 1. Python 3.14 resolution — RESOLVED (with a required httpx constraint)

`inspect-ai==0.3.244` + `inspect-swe==0.2.65` resolve on Python 3.14 alongside
the repo's full existing `build` + `dev` dependency set (97 packages, no
conflict). **No 3.14 contingency is needed.**

**However**, `inspect-ai` declares `httpx` with **no upper bound**, and the
repo's `[tool.uv] prerelease = "allow"` therefore drifts `httpx` to
`1.0.dev3`, which breaks `inspect-ai` at import time
(`ImportError: cannot import name 'HTTPStatusError' from 'httpx'`; the dev
release also drops the bundled `httpcore`). Adding an explicit **`httpx<1`**
constraint pins `httpx==0.28.1` + `httpcore==1.0.9` and `inspect_swe` imports
cleanly. The pin set is therefore **three** entries, not two, and `httpx<1` is
a matched member of the group (bump in lockstep with any inspect-ai major).

## 2. `claude_code()` signature — RESOLVED

`inspect_swe.claude_code(...)` accepts (relevant kwargs): `name`,
`description`, `system_prompt`, **`skills`**, `mcp_servers`, `bridged_tools`,
**`disallowed_tools`**, `centaur`, `attempts`, `model`, `model_config`,
`model_aliases`, `opus_model`, `sonnet_model`, `haiku_model`, `subagent_model`,
`filter`, `auto_mode`, `retry_refusals`, `retry_uncaught_errors`, **`cwd`**,
`env`, `user`, **`sandbox`**, **`version`** (default `'auto'`), `debug`.

- The plan's wired kwargs (`skills=`, `disallowed_tools=`, `version=`) all
  exist. There is **no `max_turns`** kwarg — turn bounding is done via
  Task-level `message_limit` / `time_limit`, as the plan assumes.
- `version` defaults to `'auto'` (not a pin) — Phase 2/3 should pass an explicit
  `version=` if the CLI version must be reproducible, and Phase 3 asserts the
  log-recorded version.

## 3. CLI provisioning model — DEFERRED to a credentialed run

Requires a live `inspect_swe.claude_code()` eval against a Docker sandbox with
an authenticated model API — not runnable in the current environment (no
`ANTHROPIC_API_KEY`; Docker daemon is up). Deferred to the Phase-3 live run (or
a user-run probe). The Phase-2 sandbox is built to the plan's assumption (image
carries the real cross-built launcher at `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`,
skill loaded via `skills=`), and Phase 3 confirms both arms executed the
in-image launcher.

## 4. File-path task loader + import form — RESOLVED

- `inspect_ai.eval(["<path>/configure_eval.py@<arm>"])` loads tasks from an
  `__init__.py`-free tree successfully (mock-model run, status `success`).
- **Import form is load-bearing.** Under Inspect's file-path loader:
  - **Relative imports fail** — `from .scorer import …` raises
    `ModuleNotFoundError` (the loader loads the file as a top-level module with
    no package context).
  - **Fully-absolute namespace imports work** —
    `from tests.evals.skills.configure.scorer import …` and
    `from tests.evals.shared.… import …` resolve, **provided the repo root is on
    `sys.path`** (the loader does not add cwd).
- **Consequence for the build**: every eval module uses fully-absolute
  `from tests.evals.…` imports (no relative `.scorer` / `.solvers`), and
  `_run_configure_eval` ensures `REPO_ROOT` is on `sys.path` before calling
  `inspect_eval`. pytest already puts repo root on `sys.path`
  (`pythonpath = ["."]`), so the unit tests import the same way.

## 5. Transcript shape — DEFERRED to a credentialed run

The real `Bash` tool-result fields and `Skill` tool-use event structure, and
whether stdout is raw or normalised, require a live run to capture. Deferred to
Phase 3, which commits `fixtures/golden_transcript.json` and drives at least one
scorer test from it (the hard gate the plan specifies). Phase-2 scorer helpers
are written against hand-authored stubs of the assumed shape and are structured
so the golden fixture can retro-pin them.

## 6. Reducer / metric read-back shape — RESOLVED (and it reverses the plan's
core reconciliation)

`log.results.scores[*]` carries `.scorer` (str), `.reducer` (str), and
`.metrics[name].value`. A mock-model two-arm run confirmed the read path:
`metrics["accuracy"].value` is the pass^k fraction (all-correct arm → `1.0`,
all-incorrect arm → `0.0`).

**Major reversal — `pass_k` now exists and is exactly the intended statistic.**
The plan's "Critical reconciliation" (carried from the research) states Inspect
has *no* `pass_k` and that its `pass_at(k)` is the lenient pass@k, so a custom
`all_correct` reducer (or `at_least(k)`) is needed. **This is outdated for
`inspect-ai==0.3.244`.** Verified against the installed source
(`inspect_ai/scorer/_reducer/reducer.py`):

- **`pass_k(k)`** — *"Probability that all `k` epoch attempts succeed"*, the
  draw-without-replacement estimator `C(correct, k) / C(total, k)` (arxiv
  2406.12045). With `epochs == k` and all epochs scored (`total == k`), it
  collapses to **`C(correct,k)/C(k,k)` = 1.0 iff all k correct, else 0.0** —
  *identical* to the plan's proposed custom `all_correct` reducer. Records the
  reducer name `pass_k_3`.
- `pass_at(k)` — the lenient pass@k (≥1 of k), as the research warned.
- `at_least(k)` — `≥ k` correct; `at_least(k)` with `k == epochs` also equals
  pass^k, as the research noted.

So the original ADR-0011 / spike / work-item terminology `Epochs(k, pass_k(k))`
is now **literally correct**.

**Decision (recorded 2026-07-08):** wire the native `pass_k(k)` directly
(`Epochs(K, pass_k(K))`). The plan's Phase-2 §1 custom `all_correct` reducer and
`tests/evals/shared/reducers.py` are **dropped**; readback filters the reducer
`pass_k_3` and reads `metrics["accuracy"]`. The Phase-2 §7 ADR note is inverted:
it records that `pass_k` was *confirmed present and correct* as of
`inspect-ai==0.3.244`, superseding the earlier "no pass_k" reconciliation.
`fail_on_error=True` + `require_success` cover the partial-epoch case (native
`pass_k` returns `nan` when `total < k`, but the run fails first), so the custom
reducer's `len == k` guard is not needed.

## Phase 3 live-run validation (partial — blocked on API credit)

A minimal live smoke test (1 sample, 1 epoch) validated the integration chain
end-to-end short of a graded transcript:

- ✅ `build:release` cross-compiles the `linux-x64` musl launcher (statically
  linked ELF) on the macOS host via cargo-zigbuild.
- ✅ The Docker sandbox builds from the repo-root context, COPYs that launcher to
  `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`, and installs the pinned Claude Code
  CLI `2.1.203`.
- ✅ The launcher **runs in-container under amd64 emulation** — `luminosity config
  get core.example` returns the seeded value (exit 0) via both the
  `${CLAUDE_PLUGIN_ROOT}/bin/luminosity` path and `PATH`.
- ✅ `inspect_swe.claude_code()` builds the sandbox via the compose file, launches
  the CLI, and **proxies its model calls to Anthropic** (model
  `claude-haiku-4-5-20251001`, Claude Code's real tool schema resolved — Bash
  with a `command` argument, Write, TaskUpdate, …). This discharges the story's
  chief residual risk: the inspect_swe-driving-Claude-Code integration works.
- ❌ **BLOCKED:** the Anthropic API returns `400 invalid_request_error: "Your
  credit balance is too low to access the Anthropic API"`. The
  `mise.local.toml` key is unfunded, so no model turn completes and no gradeable
  transcript is produced.

**Consequently the Phase-3 deliverables cannot be produced yet:** the committed
`results/<timestamp>.json` log, the golden transcript fixture, the CLI-version
assertion, and the promotion of skill-attribution to a scored requirement all
depend on a completed run. They remain open pending funded API credit (or a
funded key), after which `mise run eval:skills:configure` completes them.
Phase-0 items 3 and 5 are correspondingly still only partially answered (the
CLI is driven via the sandbox bridge; the full Bash/Skill transcript shape was
not captured before the billing error).

## Host-native pivot (2026-07-08)

The `inspect_swe` bridge routes every model call through Inspect's metered
`anthropic/…` provider (`ANTHROPIC_BASE_URL=localhost:{bridge.port}` →
`AsyncAnthropic(api_key=…)`), so it **cannot** run on a Claude subscription. To
use a subscription, the eval was re-architected to drive the real `claude` CLI
host-natively — dropping the bridge and Docker while keeping the Inspect
framework (epochs, `pass_k` reducer, scorer, `EvalLog`):

- **Auth:** a custom `@solver` shells out to `claude -p --output-format
  stream-json`, which uses the CLI's own subscription OAuth. Validated live:
  `STATUS: success`, no billing error (the metered-API path is gone).
- **CLI pin:** `node` + `npm:@anthropic-ai/claude-code@2.1.203` via mise
  `[tools]`. mise's npm backend installs with `--ignore-scripts`, so the
  platform-native binary the shim bootstraps isn't fetched — a
  `deps:install:claude-native` task runs the postinstall (the
  rustup-provisions-cargo-pup pattern). Node is dev-tier only (ADR-0004 note).
- **Launcher:** `build:launcher` (host-native) stages the real binary into a
  plugin tree (`stage_plugin`) at `bin/luminosity`; `claude -p --plugin-dir`
  loads it, and the with-skill agent resolves
  `${CLAUDE_PLUGIN_ROOT}/bin/luminosity`. Confirmed live: the init event lists
  `plugins: [{name: luminosity, source: luminosity@inline}]` and the agent runs
  the staged binary.
- **Transcript shape (now known, not assumed):** stream-json `assistant` events
  carry `tool_use` blocks — Bash `{"command": …, "description": …}` and Skill
  `{"skill": "luminosity:configure", "args": …}` (namespace-qualified). The
  scorer's `skill_was_invoked` was corrected to this shape; `parse_transcript`
  is unit-tested against it.

**Dataset format:** the tasks live in `dataset.json` (a pretty-printed JSON
array), not the `dataset.jsonl` the ADR/plan sketch. `json_dataset` selects the
reader by extension — `.jsonl` is one-object-per-line (a formatter that
pretty-prints it corrupts it), whereas a `.json` array is `json.load`-ed and
stays valid under formatting, so the dataset is human-readable and
formatter-safe.

**Eval-design findings (all resolved during calibration):**

1. **Auth is inherited from the environment.** During calibration an unfunded
   `ANTHROPIC_API_KEY` left in `mise.local.toml` overrode the claude.ai login and
   sent every turn to the metered API ("credit balance too low"). That was a
   local misconfiguration, not a design need: the agent env is passed through
   verbatim, so `claude -p` uses whatever the environment provides — the
   subscription login by default, or a deliberately-set API key for operators
   without a subscription.
2. **The model bypassed the CLI via `Read`.** Fixed by `--disallowedTools
   Read/Edit/Write/Grep/Glob/…`, so the only path to the answer is the CLI.
3. **Skill invocation was model-sensitive.** Haiku under-triggered on `--level`
   requests; Sonnet triggers reliably. Switched `CLAUDE_MODEL` to
   `claude-sonnet-5` (the realistic target).
4. **The bad-`--level` task was ill-posed.** It expected the agent to blindly
   pass `--level bad` to surface clap's exit-2, but a skill-following model
   correctly declines an invalid level and asks to clarify. Replaced with a
   valid `--level personal` get (clap's exit-2 is already covered by
   `config.rs`).

**Result:** the first full gated run (Sonnet, CLI 2.1.203) scored with-skill
`pass^k = 0.889` (8/9; only conflict-on-set flaked once) and baseline
`pass^k = 0.000`, committed under `results/`.

## Environment notes

- Docker daemon is up (Docker 29.5.3); Claude Code CLI 2.1.203 is installed
  (above the plugin's v2.1.144 skill-preload floor).
- No `ANTHROPIC_API_KEY` in the environment — the live-model probes (items 3, 5)
  and the Phase-3 run need credentials + token budget supplied by the operator.
