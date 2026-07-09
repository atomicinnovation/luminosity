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

## 3. CLI provisioning model — RESOLVED (by the host-native pivot)

Originally deferred to a credentialed run, then **made moot**: the host-native
pivot dropped `inspect_swe` and Docker entirely, so nothing provisions a CLI on
the eval's behalf. The Claude Code CLI is pinned in `mise.toml [tools]`
(`npm:@anthropic-ai/claude-code@2.1.203`, its native binary fetched by
`deps:install:claude-native`), and the agent resolves the real launcher through
`${CLAUDE_PLUGIN_ROOT}/bin/luminosity` in the staged plugin tree. Confirmed live:
the `init` event lists `plugins: [{name: luminosity, source: luminosity@inline}]`
and the agent's `Bash` commands run the staged binary. The version the agent ran
is stamped into every sample (`claude_cli_version`), so the committed log records
it rather than a plan-time assumption.

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

## 5. Transcript shape — RESOLVED (by the host-native pivot)

Originally deferred to a credentialed run. The pivot **replaced the unknown with
an owned interface**: because the solver drives `claude -p --output-format
stream-json` directly, the transcript is `stream-json` (not an `inspect_swe`
bridge artefact), and `parse_transcript` is the repo's own reader of it. The
shape — `assistant` events carrying `tool_use` blocks, Bash `{"command", …}` and
Skill `{"skill": "luminosity:configure", …}` (namespace-qualified) — is pinned by
`tests/unit/evals/skills/configure/test_solvers.py`.

**The planned `fixtures/golden_transcript.json` was therefore dropped, not
forgotten.** Its purpose was to retro-pin a shape the harness handed us and we
could only guess at; under the pivot the shape is an input we parse and can
assert on directly. The raw-vs-normalised-stdout worry it also hedged is moot for
a further reason: the scorer never grades tool-result text at all — it re-executes
the command (see the outcome re-read below), because a tool result cannot reliably
carry an exit code.

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

## Phase 3, first attempt — blocked on API credit (superseded)

> **Historical.** This section records the metered-API attempt that motivated the
> host-native pivot below. Its blocker is resolved and its "deliverables cannot be
> produced yet" conclusion no longer holds — see *Host-native pivot* and *Phase 3
> outcome*.

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

At the time this blocked every Phase-3 deliverable, since each depends on a
completed run. The pivot below removed the blocker by dropping the metered API
altogether; all of them are now delivered (see *Phase 3 outcome*), except the
golden transcript fixture, which the pivot made unnecessary (item 5).

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
2. **The model bypassed the CLI via `Read`.** Originally "fixed" by
   `--disallowedTools Read/Edit/Write/Grep/Glob/…`, claimed to make the CLI the only
   path to the answer. **That claim was false and the disallow has since been
   dropped.** With `Bash` allowed, `cat`/`grep`/`find` reproduce those tools exactly:
   in the second gated run's baseline arm, 12 of 27 samples read
   `.luminosity/config.md` straight off disk via `Bash` and one of them reported the
   right value — scoring INCORRECT anyway. What actually enforces CLI routing is the
   scorer's `config_command_ran`, which requires the agent to have invoked the
   canonical `luminosity config …` argv. The tool list was redundant with that check
   and merely made the arms look more constrained than they were. Both arms now get
   the same tools (`Bash`, `Read`, `Grep`, `Glob`) and differ only in `Skill`.
3. **Skill invocation was model-sensitive.** Haiku under-triggered on `--level`
   requests; Sonnet triggers reliably. Switched `CLAUDE_MODEL` to
   `claude-sonnet-5` (the realistic target).
4. **The bad-`--level` task was ill-posed.** It expected the agent to blindly
   pass `--level bad` to surface clap's exit-2, but a skill-following model
   correctly declines an invalid level and asks to clarify. Replaced with a
   valid `--level personal` get (clap's exit-2 is already covered by
   `config.rs`).

## Known contamination: the agent inherits the operator's Claude Code config

**Accepted, not fixed.** `claude -p` loads the user-level `CLAUDE_CONFIG_DIR/CLAUDE.md`
and the hooks in that directory's `settings.json`. The eval's agent therefore runs with
whatever personal instructions and hooks the operator happens to have, and the committed
log is **not portable across machines**.

Observed on the authoring machine: the user memory imports an `RTK.md` (a CLI-proxy
tool), and four baseline samples went hunting for it —
`which rtk 2>/dev/null && rtk --help` — instead of looking for `luminosity`. The
with-skill arm shows zero such detours, because the skill gives it a direction. So the
contamination **lands asymmetrically, biasing the baseline downward** and flattering the
A/B contrast.

Bounded, though: the operator's `PreToolUse` hook rewrites `Bash` commands, but
`rtk rewrite` passes `luminosity config …`, `cat`, `grep`, and `find` through unchanged
(verified). The *graded* argv is never rewritten, so grading itself is sound — the
contamination is a distraction on the agent's reasoning, not a corruption of the
measurement.

**Why it is not fixed:** on CLI 2.1.203, subscription auth and context isolation are
mutually exclusive. `--bare` is exactly the isolation switch (skips hooks, auto-memory,
CLAUDE.md discovery) but documents that "OAuth and keychain are never read" — it demands
`ANTHROPIC_API_KEY`. Pointing `CLAUDE_CONFIG_DIR` or `HOME` at a throwaway directory
(with or without seeding `.claude.json`) yields `Not logged in`: the keychain read is
gated on the default config dir. Escaping the contamination therefore means returning to
the metered API the host-native pivot exists to avoid.

**The lever, when it matters:** run the committed eval with `--bare` and a funded
`ANTHROPIC_API_KEY`. Until then, read the baseline number as a *lower* bound on a
skill-less agent, and expect the with-skill/baseline gap to narrow on a clean machine.

## Phase 3 outcome

The first full gated run (Sonnet, CLI 2.1.203) scored with-skill `pass^k = 0.889`
(8/9; only conflict-on-set flaked once) and baseline `pass^k = 0.000`.

Plan validation then found three gaps in that run's artefacts, each since closed
(and the logs regenerated by a second gated run, **with-skill `pass^k = 1.000`,
baseline `0.000`** — the conflict-on-set flake did not recur, which is what a
single stochastic draw is worth):

- **Provenance.** `eval.model` reads `mockllm/model`, because the solver bypasses
  Inspect's provider — so the log said nothing about what actually ran. The solver
  now stamps `claude_model` + `claude_cli_version` into every sample, guarded by
  `tests/unit/evals/skills/configure/test_results.py`.
- **Path scrubbing.** `scrub_paths` relativised only `$REPO_ROOT` and `$HOME`, so
  the per-sample workdir (`/var/folders/…`, outside `$HOME`) leaked 66 absolute
  host paths into the committed logs. It now scrubs the temp root and its resolved
  twin; the guard is a `HOST_PATH_PATTERN` regex applied to the committed logs
  themselves, not a `$HOME` substring check.
- **Skill attribution.** It was recorded in `Score.metadata` but never scored, so
  the with-skill arm could have passed on a lucky bare-model command. `grade_sample`
  now makes `skill_invoked == skill_expected` a conjunct of the verdict.

Two smaller findings were closed alongside: a mis-routed conflict `set --level`
was undetectable (the argv match now enforces a task-pinned `set` level, while
leaving an unpinned one free, since the default and an explicit equivalent are
both correct), and the per-sample workdirs leaked ~54 temp directories per run
(now swept by `cleanup_workdirs` after a completed run — a crashed run keeps them
for reading).

## Alternatives considered: bridge + meridian proxy

Before the host-native rewrite we established a *second* subscription path that
would have **kept the `inspect_swe` bridge** — and therefore its free transcript
population (no `parse_transcript`) and Docker isolation — with **zero code
change**: run a local **meridian** proxy (`rynfar/meridian`), an
Anthropic-compatible `/v1/messages` endpoint backed by Claude Max subscription
OAuth, and set `ANTHROPIC_BASE_URL=http://127.0.0.1:3456` (+ a placeholder
`ANTHROPIC_API_KEY`). The chain would be: sandboxed CLI → inspect bridge →
Inspect's anthropic provider → meridian → Claude Code SDK → subscription. The
load-bearing enabler was verified in the provider source (the standard branch
does `base_url = model_base_url(self.base_url, "ANTHROPIC_BASE_URL")`, so it
honours that env var) and meridian speaks Anthropic-compatible `/v1/messages` —
but the path was **never live-tested**.

We chose host-native `claude -p` over it because meridian is an **unofficial
third-party proxy that handles the subscription credentials**, adds a
double-proxy hop, and needs a background process running; the direct CLI is the
official, no-extra-dependency route. The trade is the hand-rolled CLI driving +
`parse_transcript` (which the bridge would otherwise provide). **This is the
fallback** if that hand-rolled code becomes a burden and the meridian dependency
is acceptable — it restores the bridge (and its transcript handling + isolation)
on the subscription without a rewrite.

## Library-feature audit (does anything hand-built duplicate Inspect?)

A final pass over the Inspect / inspect_swe docs, references, and changelogs
(inspect-ai 0.3.244, inspect_swe 0.2.65 — both the newest at the time)
confirmed every hand-built piece earns its place:

- **The pass^k gate** (read the metric off `log.results`, exit non-zero below
  0.8) — no built-in. Inspect's `fail_on_error` gates *sample errors*, never a
  *score/metric* value; there is no threshold flag or `eval()` parameter for it.
- **The custom `claude -p` solver** — no built-in. `inspect_swe.claude_code()`
  is unconditionally bridge-based (model calls proxied to Inspect's metered
  provider); it exposes no auth/passthrough option, so subscription auth is only
  reachable by driving the CLI directly.
- **`scrub_paths`** — no built-in. `write_eval_log` has no anonymisation /
  path-relativisation option, and the changelog's only `redact` entries are
  unrelated (git-remote credentials, `model_args`).
- **`parse_transcript`** — the one piece with a library equivalent we chose not
  to use. The `sandbox_agent_bridge` *does* populate `state.messages` with native
  Inspect messages automatically (model calls crossing the proxy are recorded),
  so under the bridge no parsing is needed. We hand-roll it only because we
  dropped the bridge for subscription auth — it is a cost of that trade, not a
  library gap. (The scorer's outcome re-read is separate: it exists because the
  tool-result content cannot reliably surface an exit code, and would remain
  even under the bridge.)
- **The `pass_k` reducer is native** (added in 0.3.224) and correctly chosen
  over the lenient `pass_at`. Nuance: `pass_k` returns the draw-without-
  replacement probability `C(correct,k)/C(total,k)`, not a hard boolean — but
  with `epochs == k` and `fail_on_error=True` (so `total == k`) it collapses to
  1.0 iff all k pass, exactly the intended bar. There is no built-in A/B/arm
  comparator; the two-`Task` (skill vs baseline) pattern is the idiomatic one.

## Environment notes

- Docker daemon is up (Docker 29.5.3); Claude Code CLI 2.1.203 is installed
  (above the plugin's v2.1.144 skill-preload floor).
- No `ANTHROPIC_API_KEY` in the environment — the live-model probes (items 3, 5)
  and the Phase-3 run need credentials + token budget supplied by the operator.
