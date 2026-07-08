---
type: plan
id: "2026-07-07-0010-apply-eval-framework-to-configure-skill"
title: "Apply the Eval Framework to the configure Skill Implementation Plan"
date: "2026-07-06T23:40:55+00:00"
author: Toby Clemson
producer: create-plan
status: ready
work_item_id: "work-item:0010"
parent: "work-item:0010"
derived_from: ["codebase-research:2026-07-07-0010-apply-eval-framework-to-configure-skill"]
tags: [plan, evaluation, inspect, configure, skills]
revision: "ea45efa776c78758fafd11967e718f2a13b0e3d9"
repository: "luminosity"
last_updated: "2026-07-07T11:18:32+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Apply the Eval Framework to the configure Skill Implementation Plan

## Overview

Stand up a new **evals** test tier under `tests/evals/skills/configure/` that
uses **Inspect** (UK AISI) to A/B-test the `configure` skill against a
skill-suppressed baseline by driving real Claude Code through
`inspect_swe.claude_code()`, grading each task deterministically against the
`luminosity config` CLI's stdout / exit-code contract. The suite runs on demand
via `mise run eval:skills:configure` (leaf) / `mise run eval` (tier roll-up),
is excluded from CI by omission, and gates on **pass^k ≥ 0.8 over k = 3 trials**
across **nine tasks**. The committed JSON eval log is the durable quality signal.

## Current State Analysis

The work is greenfield on the eval side and precise on the grading side.

- **The skill under test** (`skills/config/configure/SKILL.md:13-64`) is a thin
  instructional wrapper: Claude runs `luminosity config get|set` itself and
  reports stdout on success or the `luminosity: …` stderr line on failure. Its
  `allowed-tools` is scoped to
  `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)` (`SKILL.md:9-10`). Skill
  correctness therefore reduces to the model routing `get`/`set` + key +
  `--level` straight through and echoing the right stream.
- **The grading oracle already exists** as black-box tests
  (`cli/launcher/tests/config.rs`). Confirmed contract:
  - `get` hit → `render(value)` + `\n`, exit 0 (`config.rs:249-258`).
  - `get` hit on empty/null value → just `\n`, exit 0 (`config.rs:159-180`).
  - successful `set` → **empty stdout**, exit 0.
  - `get` miss / invalid key / conflict / malformed file → empty stdout, exit 1,
    `luminosity: …` on stderr (`config.rs:148-157,182-214,232-246`).
  - bad `--level` → exit 2, clap usage error (`config.rs:216-230`).
  - **Personal-over-Team precedence**; a `--level`-scoped `get` reads one level
    (`config.rs:51-98`).
  - Because a successful `set` prints nothing, a `set`/precedence task cannot
    grade on `set` stdout — it must verify a follow-up `get`.
- **Build-system patterns are line-for-line templated**:
  - Leaf/roll-up wiring and exclusion-by-omission from `check`/`default`
    (`mise.toml:71-96,274-280`); precedent for a deliberately-excluded tier is
    `test:integration:pup`, `launcher:check`, `kernel:check`.
  - Collection registration (`tasks/__init__.py:3-19,36-47`,
    `tasks/test/__init__.py:1-11`).
  - Pure-helper-plus-thin-`@task` gate (`tasks/version.py:116-148`) and
    `raise Exit(code=1)` + call-time env knob (`tasks/pup.py:7-24`,
    `tasks/shared/rust.py:28-49`).
  - Two-sided exit test (`tests/unit/tasks/test_pup.py:11-44`) with
    `MagicMock(spec=Context)`.
  - Shared helpers `REPO_ROOT`/`WORKSPACE_ROOT` (`tasks/shared/paths.py:3-4`),
    `atomic_write_text` (`tasks/shared/files.py:7-14`), and the
    `tasks/shared/errors.py` house exceptions.
- **Dependency pinning** goes in `pyproject.toml` `[dependency-groups]` plus `uv.lock`,
  per the repo's exact-pin convention — in the **`build`** group for anything `tasks/`
  imports (as `inspect_ai` is), the `dev` group for test/lint-only tools.
- **pyrefly strictness**: `project-includes` already globs `tests/**/*.py`
  (`pyproject.toml:82-85`); `inspect_ai.*` / `inspect_swe.*` must be added to
  `replace-imports-with-any` (`pyproject.toml:86-91`) so strict type-checking
  does not choke on the untyped third-party surface.

**Critical reconciliation carried from research.** The spike, ADR-0011, and the
work item all say Inspect natively computes pass^k via `pass_k(k)`, wired as
`Epochs(k, pass_k(k))`. Verified against the live Inspect API this is wrong:
Inspect has **no `pass_k`**, and its similarly-named `pass_at(k)` computes the
*lenient* pass@k ("≥ 1 of k succeeds") — the opposite of the intended hard gate.
The intended "all k trials succeed" semantic is expressed by `at_least(k)` with
`k` equal to the epoch count, or by a small custom all-succeed `@score_reducer`.
This plan wires a **self-documenting custom all-succeed reducer** and records a
superseding/implementation note on ADR-0011.

## Desired End State

- `mise run eval:skills:configure` exists, calls Inspect's `eval()` in-process,
  reads the pass^k fraction off `log.results`, and exits non-zero below 0.8.
- The eval tier is absent from `mise run` / `mise run check`, verified by a
  wiring unit test — no eval runs on any CI build.
- The `configure` eval is a well-formed Inspect `@task` in `configure_eval.py`
  (not `test_*`, so pytest does not collect it), addressed by the task layer via a
  file-path specifier so `tasks/` never imports the `tests/` tree, with the nine dataset
  tasks (get-hit, empty-value get, valid-`--level` get, set/precedence, conflict-on-set,
  missing, invalid-key, malformed, bad-`--level`) in `dataset.jsonl`, both a with-skill
  and a skill-suppressed baseline solver over the one dataset (a pinned model and
  identical Task-level limits across arms), and a deterministic scorer that grades the
  CLI's real transcript output (byte-exact stdout / exit-code-plus-marker), verifies
  precedence via level-scoped reads, and records skill invocation.
- The Docker sandbox is host-independent: it consumes the cross-built linux-musl
  binary from `build:release` at a pinned `linux/amd64` platform, so the live run
  works from a macOS dev host, not only Linux.
- The gate helper and scorer grading logic are two-sided unit-tested with no
  live run, and the log read-back glue is covered against a synthetic `EvalLog`.
- A committed `results/<timestamp>.json` log records both arms (with the pinned model
  id and Claude Code CLI version) with a with-skill `pass_k ≥ 0.8`, and ADR-0011
  carries the reducer-terminology correction.

### Key Discoveries

- Grading is fully deterministic and already characterised by
  `cli/launcher/tests/config.rs` — dataset expected values lift straight from it.
- The Docker sandbox that `inspect_swe.claude_code()` requires doubles as the
  clean solution to the empty-`set`-stdout oracle: the scorer runs a follow-up
  `luminosity config get` via `sandbox().exec(...)`.
- "Exclude from CI" is structural (omission from `depends`), not a flag
  (`mise.toml:274-280`).
- The gate must be a pure `float -> bool` helper so its two-sided test needs no
  `eval()` run.

## What We're NOT Doing

- **Not** running evals in CI, nor adding the eval tier to `check`/`default`/any
  workflow — token/Docker cost is the reason the tier is dev-time only.
- **Not** growing the suite to the 20–50 real-failure-derived tasks or raising
  k toward 5–10 — that ramp is background in the work item, not this story.
- **Not** building a generic multi-skill eval-harness abstraction now;
  `configure_eval.py` is structured so the A/B scaffold and scorer are
  *extractable* later, but no second skill is evaluated here.
- **Not** switching to the promptfoo fallback — ADR-0011 selected Inspect; this
  plan realises that decision.
- **Not** editing the `configure` skill or the Rust `config` CLI — the eval
  grades their shipped behaviour.
- **Not** adding a `skill-creator` interactive loop — retained only as an
  optional authoring aid per the spike.

## Implementation Approach

A preliminary discovery phase resolves the pre-1.0 integration unknowns **before any
code is written**, then three independently-mergeable phases build on the answers, each
leaving `mise run check` green and never causing CI to run a live eval:

0. **Resolve integration unknowns** — a short, code-light discovery phase that answers,
   against the real pinned dependencies, the questions the rest of the plan is built on:
   does the pin resolve on Python 3.14; what is `claude_code()`'s real signature; does
   `inspect_swe` consume the sandbox-present CLI or download its own; does a `skills=`
   skill see the image's `${CLAUDE_PLUGIN_ROOT}`; does the Python `eval()` API accept the
   `file.py@task` specifier under the `__init__.py`-free tree; and what is the real
   `Bash`/`Skill` transcript shape. Its output is a recorded findings note (and a captured
   transcript sample) that later phases consume — nothing downstream is built on an
   unverified assumption.
1. **Scaffold + gate** — the tier, its wiring, the pure pass^k gate, and its
   unit tests, with the live run guarded behind an env knob. No Inspect eval
   logic, no Docker, no model calls.
2. **Eval definition** — the Inspect `@task`, dataset, both solvers, the custom
   scorer and reducer, the Docker sandbox, and the ADR note. Everything is
   unit-tested at the logic level; the live run is still not exercised by CI.
3. **Live run + committed log** — the developer runs it once for real, validates
   the `inspect_swe` integration, and commits the JSON log.

TDD throughout the build phases: each unit-testable helper (gate, scorer branches,
reducer, dataset validity, wiring) starts from a failing test.

## Phase 0: Resolve integration unknowns (preliminary)

### Overview

The eval integrates three young, pre-1.0 surfaces — `inspect-ai`, `inspect_swe`, and the
Claude Code CLI over the Agent Bridge — whose exact behaviour the later phases depend on.
Rather than build the full Dockerfile / solver / scorer apparatus on assumptions and
discover a mismatch only at the expensive Phase-3 live run, this phase spends a little
time up front to **turn each assumption into a recorded fact**. It is code-light: throwaway
probes and introspection, no committed product code beyond the findings note.

### Questions to answer (each with how)

1. **Python 3.14 resolution** — run `uv lock` with candidate `inspect-ai` / `inspect-swe`
   pins; confirm they and their Agent-Bridge transitive deps resolve on 3.14. If not,
   choose the Phase-1 §1 contingency (newest resolving pair / isolated lower-python
   subprocess env / promptfoo) and record it.
2. **`claude_code()` signature** — introspect the resolved `inspect_swe` for the real
   kwargs (`skills=`, `disallowed_tools=`, `version=`, limits) so Phase 2 wires only
   parameters that exist.
3. **CLI provisioning model** — run a trivial `inspect_swe.claude_code()` eval against a
   throwaway Docker sandbox and determine whether it **executes the sandbox-present CLI or
   downloads its own**, and whether a `skills=`-loaded skill resolves the image's
   `${CLAUDE_PLUGIN_ROOT}`. This decides the whole Phase-2 §5 sandbox shape (whether the
   Dockerfile's launcher staging is even the path exercised).
4. **File-path task loader** — confirm the in-process `inspect_ai.eval()` accepts the
   `configure_eval.py@configure_with_skill` specifier, and which import form
   (namespace-absolute vs loader-inserted `sys.path` sibling) works for the eval modules
   under the `__init__.py`-free tree; that form is then used uniformly.
5. **Transcript shape** — from the trivial run's log, capture the real `Bash` tool-result
   fields (and whether stdout is raw or normalised) and the `Skill` tool-use event
   structure; commit a small sanitised sample so Phase 2's `bash_result` / `skill_was_invoked`
   unit tests and Phase 3's golden fixture pin the *real* shape, not a guess.
6. **Reducer/metric read-back shape** — confirm `log.results.scores[*].reducer` carries the
   custom reducer's registered name and that `metrics["accuracy"]` is where the
   all-succeed fraction lands, so the Phase-2 `readback` synthetic `EvalLog` matches reality.

### Changes Required

**File**: `meta/research/codebase/…-0010-inspect-integration-findings.md` (or an appendix to
the existing 0010 research) — record each answer, the resolved pins, the chosen 3.14
contingency, the provisioning model, the import form, and a pointer to the captured
transcript sample.

**File**: `tests/evals/skills/configure/fixtures/transcript_shape_sample.json` (new,
sanitised) — the captured `Bash`/`Skill` shapes the later unit tests reference.

### Success Criteria

#### Manual Verification

- [x] `uv lock` resolves the candidate pins on Python 3.14 (or the contingency is chosen
      and recorded). — `inspect-ai==0.3.244`, `inspect-swe==0.2.65`; **plus a required
      `httpx<1`** constraint (see findings note item 1). No contingency needed.
- [x] The `claude_code()` kwargs the plan wires all exist in the resolved `inspect_swe`.
- [ ] The CLI-provisioning model is determined, and the Phase-2 §5 sandbox shape is
      confirmed to match it (sandbox-present launcher vs. `version=`-provisioned).
      **Deferred to the credentialed live run (needs Docker + model API).**
- [x] The `file.py@task` specifier loads under the `__init__.py`-free tree with the chosen
      import form. — **fully-absolute `from tests.evals.…` imports only** (relative
      imports fail under Inspect's loader); repo root on `sys.path`.
- [ ] The captured transcript sample shows the real `Bash`/`Skill` fields, and whether
      stdout is raw (if normalised, Phase 2 grades get-tasks via the `sandbox().exec`
      re-read fallback). **Deferred to the credentialed live run.**

## Phase 1: Eval tier scaffold and pass^k gate

### Overview

Create the eval tier's skeleton and the pass^k gate as a pure, unit-tested
helper, fully decoupled from any live run. After this phase the tier exists, is
excluded from CI, and the gate fails closed below the floor — with no Inspect
task, no Docker, and no model calls yet.

### Changes Required

#### 1. Pin the Inspect dependencies

**File**: `pyproject.toml`, `uv.lock`
**Changes**: Add `inspect-ai` and `inspect-swe` to `[dependency-groups] build`,
exact-pinned to the versions resolved at authoring time (matching the repo's
`ruff==` / `pyrefly==` style), and lock `uv.lock`. They go in **`build`**, not `dev`,
because `tasks/eval/skills.py` imports `inspect_ai` — the `build` group holds every
dependency the `tasks/` build tooling imports (`invoke`, `keepachangelog`, `semver`,
`pathspec`, `ziglang`, …), while `dev` is test/lint tools `tasks/` does not import.
Add `inspect_ai.*` and `inspect_swe.*` to `[tool.pyrefly] replace-imports-with-any`.

`inspect-swe` is built on `inspect-ai`'s `sandbox_agent_bridge()` and constrains a
specific `inspect-ai` range, so the two are a **matched pair**: pick versions that
resolve together and bump them in lockstep (the discipline the repo already applies
to `ziglang` / `cargo-zigbuild` and `PUP_NIGHTLY` / `PUP_VERSION`).

Because `requires-python` is `>=3.14`, resolution against 3.14 is a gate on the pin —
**Phase 0 already ran `uv lock` against 3.14** and recorded that both packages (and their
Agent-Bridge transitive deps) resolve, or chose a contingency. This step commits the pins
Phase 0 settled on. The **contingency ladder** (if Phase 0 found nothing resolves on 3.14,
since pre-1.0 packages and native wheels often lag a new interpreter): in preference order
— (a) pin the newest `inspect-ai`/`inspect-swe` pair that does resolve; (b) scope a lower
`python-version` to the eval tooling only via an isolated `uv` environment — which requires
`_run_configure_eval` to invoke Inspect as a **subprocess** in that environment (not the
in-process import), since `tasks/` runs under the repo's 3.14 interpreter; (c) fall back to
promptfoo, the framework ADR-0011 already pre-vetted for exactly this case. The chosen path
is recorded next to the pin.

```toml
[dependency-groups]
build = [
    "invoke==<pinned>",
    "keepachangelog==<pinned>",
    # … existing build deps …
    "inspect-ai==<pinned>",
    "inspect-swe==<pinned>",
]
```

```toml
replace-imports-with-any = [
    "inspect_ai.*",
    "inspect_swe.*",
    "invoke.*",
    "keepachangelog.*",
    "pathspec.*",
    "semver.*",
]
```

#### 2. The pass^k gate helper and env knob

**File**: `tasks/shared/env.py` (new), `tasks/shared/rust.py`, `tasks/eval/gate.py` (new)
**Changes**: Lift the falsey-normalisation `tasks/shared/rust.py` uses in
`coverage_enabled` (`os.environ.get(...).strip().lower() not in _FALSEY`) into one shared
`env_flag_enabled(name, *, default)` helper, then build the pure pass^k decision and the
call-time live-run knob on top of it. The knob carries the same call-time-read docstring
the existing knobs use, so the escape hatch is not later "simplified" into an import-time
constant. **In the same change, migrate `coverage_enabled` onto `env_flag_enabled`** so the
falsey contract has one definition — its behaviour is unchanged and its existing two-sided
test guards the refactor. **`pup_mode` is left untouched**: it maps to a `warn`/`deny`
string via its own `_PUP_MODES` set and has no boolean-falsey logic, so it neither shares
`_FALSEY` nor gains anything from the helper (forcing an import would add an unused symbol
ruff `select = ["ALL"]` rejects).

```python
_FALSEY = {"off", "false", "0", "no"}


def env_flag_enabled(name: str, *, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() not in _FALSEY
```

```python
from tasks.shared.env import env_flag_enabled

PASS_K_FLOOR = 0.8


def below_floor(pass_k: float) -> bool:
    return pass_k < PASS_K_FLOOR


def live_run_enabled() -> bool:
    """Read ``LUMINOSITY_EVAL_LIVE`` at call time so the live run can be disabled
    per-invocation; off/false/0/no disable it."""
    return env_flag_enabled("LUMINOSITY_EVAL_LIVE", default="on")
```

#### 3. The eval collection and the configure leaf task

**File**: `tasks/eval/__init__.py` (new), `tasks/eval/skills.py` (new)
**Changes**: Build the collection (mirroring `tasks/test/__init__.py`) and the
leaf task. In this phase the task body does not yet import Inspect; it raises a
clear error when the live run is enabled but the eval module is not present,
and is otherwise a thin wrapper around the gate. Phase 2 replaces the body with
the real `eval()` call.

```python
# tasks/eval/__init__.py
from invoke import Collection

from . import skills

ns = Collection()
ns.add_collection(Collection.from_module(skills))
```

```python
# tasks/eval/skills.py
from invoke import Context, Exit, task

from tasks.eval.gate import below_floor, live_run_enabled


@task
def configure(context: Context) -> None:
    """Run the configure skill eval and gate on the pass^k floor."""
    if not live_run_enabled():
        print(
            "LUMINOSITY_EVAL_LIVE is off; skipping the live configure eval run"
        )
        return
    pass_k = _run_configure_eval(context)
    if below_floor(pass_k):
        raise Exit(
            f"eval:skills:configure failed: pass^k {pass_k:.3f} is below "
            f"the floor",
            code=1,
        )
```

`_run_configure_eval` is introduced as a thin seam here (raising a
not-yet-implemented error) and filled in Phase 2, keeping the gate independently
testable now.

**File**: `tasks/__init__.py`
**Changes**: Register the collection under the builtin-safe alias.

```python
from . import (
    build,
    changelog,
    deny,
    deps,
    ...
)
from . import eval as eval_
from . import format as format_
...
ns.add_collection(Collection.from_module(eval_))
```

#### 4. mise wiring (deliberately excluded from CI)

**File**: `mise.toml`
**Changes**: Add the leaf and roll-up, and leave both out of `check` and
`default`.

```toml
[tasks."eval:skills:configure"]
description = "Run the configure skill Inspect eval on demand (live model + Docker; excluded from CI for token cost)"
depends = ["deps:install:python"]
run = "invoke eval.skills.configure"

[tasks."eval:skills"]
description = "Run all skill evals on demand (excluded from CI for token cost)"
depends = ["eval:skills:configure"]

[tasks.eval]
description = "Run every eval tier on demand (excluded from CI for token cost)"
depends = ["eval:skills"]
```

The `eval:skills` intermediate mirrors the two-level `test:unit` / `test:integration`
roll-up shape, so a second skill later slots under `eval:skills` without a retrofit.

#### 5. Unit tests (write first)

**File**: `tests/unit/tasks/shared/test_env.py` (new), `tests/unit/tasks/test_eval_gate.py` (new)
**Changes**: `test_env.py` (under `tasks/shared/`, mirroring the existing
`shared/` test layout) covers `env_flag_enabled` normalisation: default on; unset →
default; and — parametrized with **case/whitespace variants** (`" OFF "`, `"FALSE"`,
`"No"`, `"0"`) mirroring `test_pup.py`'s `['warn', 'Warn', ' warn ', 'WARN']` — that the
`.strip().lower()` is load-bearing, so a regression dropping either normalisation is
caught. `test_eval_gate.py` is the two-sided gate test copying `test_pup.py`'s shape.

```python
class TestBelowFloor:
    def test_below_floor_is_true_under_the_bar(self):
        assert gate.below_floor(0.79) is True

    def test_at_floor_is_false(self):
        assert gate.below_floor(0.8) is False

    def test_above_floor_is_false(self):
        assert gate.below_floor(1.0) is False
```

**File**: `tests/unit/tasks/test_eval_skills.py` (new)
**Changes**: Feed the task a synthetic `pass_k` (monkeypatching the
`_run_configure_eval` seam) and assert the two-sided exit behaviour, plus the
`LUMINOSITY_EVAL_LIVE` skip path.

```python
def test_gates_closed_below_floor(ctx, monkeypatch):
    monkeypatch.setattr(skills, "_run_configure_eval", lambda _c: 0.66)
    with pytest.raises(Exit):
        skills.configure(ctx)

def test_passes_open_at_or_above_floor(ctx, monkeypatch):
    monkeypatch.setattr(skills, "_run_configure_eval", lambda _c: 1.0)
    skills.configure(ctx)

def test_skips_when_live_run_disabled(ctx, monkeypatch):
    monkeypatch.setenv("LUMINOSITY_EVAL_LIVE", "off")
    skills.configure(ctx)
```

**File**: `tests/unit/tasks/test_mise_wiring.py`
**Changes**: Extend the existing wiring assertions to require that
`eval` / `eval:skills` / `eval:skills:configure` are declared but **absent** from
`check`'s and `default`'s `depends`.

### Success Criteria

#### Automated Verification

- [x] Dependencies resolve and lock: `mise run deps:install:python`
- [x] Gate + task + wiring unit tests pass:
      `uv run pytest tests/unit/tasks/shared/test_env.py tests/unit/tasks/test_eval_gate.py tests/unit/tasks/test_eval_skills.py tests/unit/tasks/test_mise_wiring.py -v`
- [x] Python lint + types clean: `mise run build-system:check`
- [x] The eval tier is invocable: `mise run eval:skills:configure` with
      `LUMINOSITY_EVAL_LIVE=off` exits 0 without a model call
- [x] The full read-only sweep still excludes evals and stays green:
      `mise run check`

#### Manual Verification

- [x] `mise tasks` lists `eval` and `eval:skills:configure` and nothing under
      the eval tier appears in `check`/`default` output.

---

## Phase 2: Inspect eval definition, sandbox, and ADR note

### Overview

Fill the eval seam with the real Inspect `@task`: both solvers, the dataset, the
deterministic scorer, the custom all-succeed reducer, and the Docker sandbox.
Everything is unit-tested at the logic level (no live model call), and ADR-0011
gets the reducer-terminology correction. After this phase the eval is fully
defined and CI is still eval-free.

### Changes Required

#### 1. The custom all-succeed reducer and shared eval names

**File**: `tests/evals/shared/names.py` (new), `tests/evals/shared/reducers.py` (new)
**Changes**: The all-succeed reducer is skill-agnostic — the reusable core of every
future skill eval — so it lands in a **shared** `tests/evals/shared/` location from the
outset (the A/B scaffold joins it when a second skill arrives), not in the
configure-specific directory. Alongside it, `names.py` holds the string identifiers that
otherwise couple the `tasks/` gate to the eval definition across the import boundary — the
reducer name, the metric name, and the two arm names — so they have **one authoritative
definition**. `tasks/eval/skills.py` cannot import across the boundary, so it still
references these by literal, but a unit test asserts its literals equal `names.py` (so a
rename fails a fast test, not the live run).

```python
# tests/evals/shared/names.py
REDUCER_NAME = "all_correct"
ACCURACY_METRIC = "accuracy"
ARM_WITH_SKILL = "configure_with_skill"
ARM_BASELINE = "configure_baseline"
```

The reducer returns CORRECT iff **all `k`** epochs are CORRECT — the intended pass^k,
named for clarity rather than the subtle `at_least(k) == k` idiom. It is fully annotated
(pyrefly-strict globs `tests/**`) and takes the epoch count `k`, requiring
`len(scores) == k`: `all([])` is `True`, and a *partial* list (if Inspect drops errored
epochs rather than failing the run) would also score CORRECT — either would inflate
pass^k. Demanding exactly `k` scores fails both closed. (Pair this with pinning
`fail_on_error` so a dropped epoch is caught by `readback.require_success` too.)

```python
from collections.abc import Callable

from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    score_reducer,
    value_to_float,
)

from tests.evals.shared.names import REDUCER_NAME


@score_reducer(name=REDUCER_NAME)
def all_correct(k: int) -> Callable[[list[Score]], Score]:
    to_float = value_to_float()

    def reduce(scores: list[Score]) -> Score:
        passed = len(scores) == k and all(to_float(s.value) == 1.0 for s in scores)
        return Score(value=CORRECT if passed else INCORRECT)

    return reduce
```

The `from tests.evals.shared.names import …` form is the **import mechanism verified
against Inspect's file-path loader** in Phase 2 (see §8): whichever form the loader
supports for a task file addressed as `configure_eval.py@…` under the `__init__.py`-free
tree (namespace-package absolute imports vs. loader-inserted `sys.path` siblings) is the
one used uniformly by the eval modules and their unit tests, chosen once and pinned by a
loader-path test rather than discovered live.

#### 2. The deterministic scorer

**File**: `tests/evals/skills/configure/scorer.py` (new)
**Changes**: One custom `@scorer(metrics=[accuracy(), stderr()])` that grades the
CLI's *actual* observable output — never the model's prose. What the model types into
its final message is unreliable (the skill tells Claude to relay stdout, but it may
frame it: "The value is team-v"), so grading reads the real command result from the
transcript, keyed on `metadata["action"]` (`get` vs `set`) and
`metadata["expect_error"]`:

- **get tasks** (`action == "get"`, `expect_error` false): extract the *agent's own*
  `luminosity config get <key>` `Bash` result — matched on argv tokens (the `get` verb,
  `key`, and `--level` when scoped), **not** a loose substring, so the scorer's own
  follow-up reads and any exploratory `set` on the same key are never mistaken for the
  graded command — and compare its stdout to **`target` plus the oracle's single trailing
  newline** (`target + "\n"`) **byte-for-byte** — the oracle pins exactly one trailing
  newline and distinguishes an empty-value `\n` (target `""` → expected `"\n"`) from a
  missing key, so no `.strip()`. If the agent ran no matching command (`bash_result`
  returns `None`) the task grades **INCORRECT**, not a crash.
- **set/precedence tasks** (`action == "set"`): a successful `set` emits empty stdout,
  so grade the *end state* via level-scoped follow-up reads in the sandbox —
  `get --level personal` must equal the written value **and** `get --level team` must
  still equal the pre-seeded team value, so a mis-routed `set --level team` (which
  would otherwise resolve identically under precedence) is caught. The two-read decision
  is a pure `grade_precedence(personal_read, team_read, expected_new, expected_team)`
  helper — unit-tested against stubbed reads — leaving only the two `sandbox().exec`
  calls in the untested I/O shell, so the mis-routed-set detection cannot silently regress.
  **The two reads carry the oracle's trailing newline** (`personal_read` is `"personal-v\n"`),
  so — exactly as the get path does — the call site passes `expected_new + "\n"` /
  `expected_team + "\n"` (equivalently, strips the single trailing `\n` off each read);
  without this the raw `==` fails on the newline and every precedence trial false-fails.
- **error tasks** (`expect_error` true): extract the failing command's `Bash` result —
  via the same action-keyed extractor, so a conflict-on-`set` task (`action == "set"`)
  matches the agent's failing `set`, not a non-existent `get` — and require empty stdout,
  the expected marker in stderr, and the **exact pinned exit code**: `exit_code ==
  metadata["exit"]` where `exit` is given (the bad-`--level` task pins `2`), else any
  non-zero — so a regression from clap's exit 2 to a domain exit 1 is caught rather than
  passing. The clap case's marker is the offending value (no `luminosity:` prefix); the
  domain cases' marker is the `luminosity: …` fragment.
- **skill attribution**: on the with-skill arm record whether a `Skill` tool-use event
  naming `configure` appears; on the baseline arm record whether it is (wrongly)
  present. Until Phase 3 confirms the real transcript shape this is a **logged
  diagnostic, not a hard pass/fail conjunct**, so an attribution-shape mismatch cannot
  spuriously zero the with-skill pass^k; Phase 3 promotes it to a scored requirement
  (and the baseline's negation to a fail) once the event structure is captured.

The pure decision and extraction functions are split from the sandbox I/O so every
branch is unit-testable against message stubs with no live run. Two shapes are
**Phase-3-verified assumptions**: the `Bash`/`Skill` transcript fields, and that the
`Bash` tool-result preserves *raw, un-normalised* stdout (if the harness trims/collapses
output, the empty-value `\n` case fails byte-exact — the fallback is to grade get-tasks
via a scorer `sandbox().exec` re-read, as the set branch already does). Because the
author-written stubs only encode the *assumed* shape, the Phase-3 capture is a **hard
gate, not a nicety**: the first real run's transcript is committed as a golden fixture
and **at least one scorer test is driven from it** (not only from hand-authored stubs)
before the transcript-shape assumption is trusted, so a real-vs-assumed mismatch fails a
committed test rather than silently mis-grading. All parameters are annotated
(pyrefly-strict globs `tests/**`):

A frozen `CommandResult` value object names the command-result domain concept and
removes the exit/stdout/stderr data clump that would otherwise thread as a bare tuple
through the grading helpers. The get branch calls `grade_value(result.stdout, target +
"\n")`; `grade_value` itself stays a raw byte-equal, and the extractor keys on the task's
`action` verb so it serves both the get and the conflict-`set` error task:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    stdout: str
    stderr: str


def grade_value(actual: str, expected: str) -> bool:
    return actual == expected


def grade_precedence(
    personal_read: str, team_read: str, expected_new: str, expected_team: str
) -> bool:
    return personal_read == expected_new and team_read == expected_team


def grade_error(result: CommandResult, marker: str, expected_exit: int | None) -> bool:
    code_ok = (
        result.exit_code != 0
        if expected_exit is None
        else result.exit_code == expected_exit
    )
    return code_ok and result.stdout == "" and marker in result.stderr


def bash_result(
    messages: list[Any], *, action: str, key: str, level: str | None
) -> CommandResult | None:
    """The last Bash tool call whose argv is the task's
    `luminosity config <action> <key>` (with `--level` when scoped, and requiring
    its absence when unscoped), or None when the agent ran no matching command —
    matched on argv **regardless of the command's exit code**, so a clap-rejected
    `--level bad` is still extracted for `grade_error` to judge. Argv-token matching
    on the verb + key keeps the scorer's own follow-up reads and any exploratory
    command out of the match."""
    ...


def skill_was_invoked(messages: list[Any], name: str) -> bool:
    for message in messages:
        if message.role != "assistant":
            continue
        for call in message.tool_calls or []:
            if call.function == "Skill" and (call.arguments or {}).get("name") == name:
                return True
    return False
```

#### 3. Both solvers and the task

**File**: `tests/evals/skills/configure/configure_eval.py` (new),
`tests/evals/skills/configure/solvers.py` (new)
**Changes**: One parameterised `@task` (arm flag) sharing dataset / scorer /
model, differing only in the `inspect_swe.claude_code()` configuration. `solvers.py`
holds the small `seed_fixtures()` `@solver` that resets (removes, then re-seeds) the
`.git` + `.luminosity` fixture tree **in the sandbox** at the start of every epoch:

- **with-skill arm**: `claude_code(skills=[<configure plugin dir>])` so the
  skill loads.
- **baseline arm**: `claude_code(disallowed_tools=["Skill"])` (skill suppressed;
  the `luminosity` binary is still on `PATH` in the sandbox, so the bare model
  must self-discover the CLI).

Six things keep the two arms fair and the run bounded, reproducible, and independent:

- **Pin the model** to a dated id in `MODEL` (recorded in the committed log) and keep
  temperature / seed identical across arms. Anthropic retires dated snapshots on a
  schedule, so the committed log is a **point-in-time record, not an indefinitely
  re-runnable artifact** — snapshot retirement is the (already-listed) refresh trigger,
  and a later reproduction failure reads as expected, not a regression.
- **Bound the run** with identical **Task-level `message_limit` / `time_limit`** on both
  arms (Inspect `Task` limits; `claude_code()` exposes no `max_turns` kwarg). `MESSAGE_LIMIT`
  is a **loop-guard cap**, not an expected-turns figure: it is sized to the longest task's
  turn count (one CLI call plus a report; a couple for a precedence `set`) with headroom,
  so a looping agent is bounded without truncating a legitimate turn — token cost is the
  reason the tier is CI-excluded.
- **Fail on epoch error** (`fail_on_error=True`) so a dropped/errored epoch fails the run,
  caught by `readback.require_success` and the reducer's `len == k`. **Caveat:** this makes
  the run all-or-nothing, conflating a transient infra failure (network, rate-limit, Docker)
  with a genuine model-behaviour failure. At 9 tasks that is acceptable (read the transcript,
  re-run once); it does **not** scale to the documented 20–50-task / k 5–10 ramp, where a
  transient error becomes near-certain — the ramp must revisit resilience (a bounded
  per-call retry, or Inspect's fractional `fail_on_error` tolerance while still asserting
  `len == k` per surviving sample). Noted, not solved here.
- **Root the agent in the seeded fixture**: the CLI roots config discovery at a `.git`
  boundary, so both the agent's commands and the scorer's follow-up reads must run inside
  the fixture tree. The fixture is seeded at the sandbox's default working directory — the
  cwd `claude_code` runs the agent from — and Phase 3 asserts the agent's `Bash` results
  were produced there before the log is trusted.
- **Guarantee a fresh fixture per sample-epoch via an explicit setup step, not a runtime
  confirm**: the solver is `chain(seed_fixtures(), claude_code(...))` (a small `@solver`),
  and `seed_fixtures` writes **into the sandbox filesystem** — `sandbox().write_file(...)`
  / `exec(...)` at the agent's working directory, **not** host-side Python file I/O, since
  the agent runs inside the container (host writes would leave the container empty and
  mis-grade every task silently). It **removes the whole `.luminosity` subtree, then
  re-seeds** the `.git` boundary + `.luminosity` files (a plain overwrite would leave a
  prior epoch's agent-written `config.local.md` behind — a `set` bleeding forward — since
  that file is not part of the team-only seed). If Inspect isolates sandboxes per
  sample-epoch this is belt-and-braces; if it reuses a container it is the correctness
  guarantee. It assumes epochs of a sample are not run concurrently in one container; if
  they can be, key the working directory on sample-id + epoch so re-seed and reads cannot
  race.
- **Resolve paths from `__file__`** (`dataset.jsonl`, `compose.yaml`) so the in-process
  `eval()` launched from the task layer cannot be broken by the process cwd.

The `claude_code` kwargs (`skills=`, `disallowed_tools=`) are verified against the pinned
`inspect_swe` (a Phase 2 unit test constructs both tasks without raising). If `inspect_swe`
provisions its **own** Claude Code agent rather than consuming the sandbox-present CLI, its
`version=` kwarg is pinned to the same version the Dockerfile records so the two cannot
diverge, and Phase 3 asserts the log-recorded CLI version matches the pin (guarding against
a silent drop below the v2.1.144 skill-preload floor).

```python
from pathlib import Path
from typing import Any

from inspect_ai import Epochs, Task, task
from inspect_ai.dataset import json_dataset
from inspect_ai.solver import chain
from inspect_swe import claude_code

from tests.evals.shared.names import ARM_BASELINE, ARM_WITH_SKILL
from tests.evals.shared.reducers import all_correct

from .scorer import configure_scorer
from .solvers import seed_fixtures

K = 3
MODEL = "anthropic/claude-<pinned-dated-id>"
CC_VERSION = "<pinned-cli-version>"
MESSAGE_LIMIT = 16
_HERE = Path(__file__).parent


def _task(*, with_skill: bool) -> Task:
    agent = (
        claude_code(skills=[str(_CONFIGURE_SKILL_DIR)], version=CC_VERSION)
        if with_skill
        else claude_code(disallowed_tools=["Skill"], version=CC_VERSION)
    )
    return Task(
        dataset=json_dataset(str(_HERE / "dataset.jsonl")),
        solver=chain(seed_fixtures(), agent),
        scorer=configure_scorer(with_skill=with_skill),
        epochs=Epochs(K, all_correct(K)),
        sandbox=("docker", str(_HERE / "compose.yaml")),
        model=MODEL,
        message_limit=MESSAGE_LIMIT,
        fail_on_error=True,
        name=ARM_WITH_SKILL if with_skill else ARM_BASELINE,
    )


@task
def configure_with_skill() -> Task:
    return _task(with_skill=True)


@task
def configure_baseline() -> Task:
    return _task(with_skill=False)
```

#### 4. The dataset

**File**: `tests/evals/skills/configure/dataset.jsonl` (new),
`tests/evals/skills/configure/fixtures/` (new)
**Changes**: Expected values lifted from `cli/launcher/tests/config.rs` (the
authoritative source for every expected value and marker). Each fixture seeds a `.git`
boundary marker alongside its `.luminosity` files, since the CLI roots config discovery
at `.git`. Each dataset line carries `input` (the natural-language request), `target`
(expected value or empty), and `metadata` (`expect_error`, error `marker`, optional
`exit`, `action`, `key`, optional `level`, optional `fixture`). Coverage:

- **get (hit)** — resolve a pre-seeded team value (`action: "get"`, `target: "team-v"`).
- **get (empty value)** — resolve a pre-seeded empty/null value; `target: ""`, so the
  byte-exact `\n`-vs-miss distinction the scorer relies on is actually driven.
- **get (valid `--level`)** — a natural-language request that names a level ("get
  core.example on the team level"); `action: "get"`, `level: "team"`, so the *agent's*
  own `--level`-carrying command is graded via `bash_result`'s level-aware match — the
  skill's first-class `--level` passthrough is exercised, not just supplied by the scorer.
- **set/precedence** — set a personal value over a pre-seeded team value
  (`action: "set"`); the scorer verifies `get --level personal` is the new value and
  `get --level team` still resolves the pre-seeded team value (`target: "personal-v"`).
- **conflict on set** — `set` a key whose parent is already a value; `expect_error:
  true`, `marker: "cannot set"` — the skill has an explicit "surface the conflict"
  instruction, so this exercises a documented behaviour, not just the happy path.
- **missing key** — `get` an unset key; `expect_error: true`, `marker: "is not set"`.
- **invalid key** — `get` a degenerate key (empty or `core..example`); `expect_error:
  true`, `marker: "invalid config key"`, domain `exit 1` — the CLI's own error class
  (`config.rs`), a real "relay stderr verbatim" path the skill must not mishandle.
- **malformed frontmatter** — `get` against a pre-seeded malformed `.luminosity`
  fixture; `expect_error: true`, `marker: "malformed frontmatter"` — so the scenario
  the "missing/malformed" label promised is actually built, not just the missing case.
- **bad `--level`** — `get core.example --level bad`; `expect_error: true`, `exit: 2`, so
  `grade_error` enforces the clap-usage exit distinct from a domain exit 1. It **carries
  `level: "bad"`** in metadata so the scorer calls `bash_result(..., level="bad")` and
  matches the agent's scoped command; `bash_result` matches on argv **regardless of the
  command's exit code** (it returns the result for `grade_error` to judge), so a correctly
  clap-rejected command is still extracted rather than treated as "no matching command".

That is nine tasks (the `pass^k ≥ 0.8` floor then requires ≥ 8 of 9 to pass every trial).

Deterministic outcome-grading cannot cover the skill's *ask-before-ambiguous-set*
behaviour — that is a conscious coverage boundary, noted here, not an oversight.

The dataset-validity unit test asserts each domain task's `marker` is a substring of
the corresponding `luminosity:` message template (the clap bad-`--level` task validates
against the offending-value string, which carries no `luminosity:` prefix) and, where a
fixture pre-seeds the value, derives `target` from that seed — so a copy-drift from
`config.rs` fails the unit suite rather than passing silently. The markers are a Python
transcription of the Rust `error.rs` templates; keeping them in step is a manual
eval-refresh trigger on any error-message change (the Rust templates are not reachable
from Python).

#### 5. The Docker sandbox

**File**: `tests/evals/skills/configure/compose.yaml` (new),
`tests/evals/skills/configure/Dockerfile` (new), `.dockerignore` (new)
**Changes**: A Linux image carrying a **version-pinned** Claude Code CLI (at or above
the plugin's v2.1.144 skill-preload floor) and a plugin tree whose `bin/luminosity` **is
the real launcher** so both arms exercise the real CLI *through the same path the skill
uses*. Several constraints make the image correct and host-independent — critical because
macOS is a first-class dev host and `build:launcher` only ever produces host-native
(darwin) triples that cannot run in a Linux container:

- **Match the skill's invocation path, and bypass the release root-of-trust.** The skill
  runs `${CLAUDE_PLUGIN_ROOT}/bin/luminosity config …` (its `allowed-tools` scope is
  `Bash(${CLAUDE_PLUGIN_ROOT}/bin/luminosity config *)`), but the shipped `bin/luminosity`
  is a bootstrap **shim** that *unconditionally* fetches the launcher from a GitHub release
  and minisign-verifies it against the committed public key — a release that does not exist
  for an in-dev prerelease, and a signature no developer can produce (signing needs the
  CI-only secret in `tasks/sign.py`; `build:release` does **not** sign, and the shim's
  `LUMINOSITY_RELEASE_BASE_URL`/`LUMINOSITY_CACHE_DIR` overrides relocate the fetch but do
  **not** skip verification). Since the eval grades *config behaviour*, not distribution,
  the image **replaces `bin/luminosity` with the cross-built launcher binary itself** at
  that exact path (dropping the shim, the release key, and the verify shim from the eval
  image), and sets `CLAUDE_PLUGIN_ROOT` to that tree. The with-skill arm invokes the real
  launcher via the exact path its `allowed-tools` permits; the baseline arm (skill
  suppressed) finds the same binary on `PATH` to self-discover. A Phase-3 check confirms
  both arms executed the in-image launcher (no network fetch, no `allowed-tools` block).
- The leaf task depends on **`build:release`**, not `build:launcher`: `build:release`
  cross-builds the `*-unknown-linux-musl` triples (via cargo-zigbuild) on any host —
  including macOS — and stages them under `cli/launcher/bin/luminosity-<platform-alias>`
  (from `binary_path()` in `tasks/shared/targets.py`), so the amd64 binary lands at
  `cli/launcher/bin/luminosity-linux-x64`. The `compose.yaml` `build.context` is the
  **repo root** (with a `.dockerignore` excluding `cli/target/`, `.venv`, `node_modules`,
  `.git`, `meta/` so the build context is not the multi-GB tree) so the Dockerfile can
  `COPY cli/launcher/bin/luminosity-linux-x64` (the platform alias, not the Rust triple,
  and under `cli/launcher/bin/`, not the repo-root `bin/` shim tree).
- `compose.yaml` pins `platform: linux/amd64` and copies the matching `linux-x64`
  binary, so every machine uses the same container arch. On Apple Silicon this runs
  under Docker's amd64 emulation (binfmt/Rosetta), which `_require_docker` **actively
  probes** — a `docker run --platform linux/amd64 … true` preflight — so a fresh
  Apple-Silicon host with Rosetta disabled gets the actionable "enable Docker Desktop's
  x86/amd64 emulation" message rather than a deep, obscure sandbox-setup failure. A single
  pinned arch is chosen over host-arch selection of the also-built `linux-arm64` binary so
  the committed signal is reproducible.
- The COPY source (`cli/launcher/bin/luminosity-linux-x64`) and the `platform:` pin are a
  hand-synced mirror of the `('x86_64-unknown-linux-musl', 'linux-x64')` alias in
  `tasks/shared/targets.py` — the same manual-sync hazard the repo already guards for its
  80-col / `msrv` mirrors — so a unit test (extending `test_mise_wiring.py`'s coherence
  style) asserts the Dockerfile's COPY source equals `binary_path("linux-x64")` relative to
  `REPO_ROOT` and the compose platform matches the amd64 triple, failing a cheap test
  rather than the live build if the alias scheme ever changes.
- The Claude Code CLI is installed from a **pinned, immutable source** (a lockfile-pinned
  npm install of the exact version, not a floating `@latest`) via a **multi-stage build**
  so the Node/npm toolchain stays in the builder stage and the runtime image carries only
  the pinned CLI; the npm-registry access is a **build-time prerequisite** noted alongside
  Docker/Rosetta (an air-gapped build would need a mirror). The CLI version is recorded —
  with the `luminosity` build — in the committed log, so the whole sandbox is a
  reproducible contract.

**File**: `mise.toml`
**Changes**:

```toml
[tasks."eval:skills:configure"]
description = "Run the configure skill Inspect eval on demand (live model + Docker; excluded from CI for token cost)"
depends = ["deps:install:python", "build:release"]
run = "invoke eval.skills.configure"
```

#### 6. Fill the eval seam

**File**: `tasks/eval/skills.py`, `tasks/eval/readback.py` (new)
**Changes**: `skills.py` stays a thin gate; the log-parsing/serialisation glue lives in
`readback.py` (`arm_log` / `pass_k` / `require_success` / `scrub_paths`), matching
its already-separate `test_eval_readback.py` test file — one module per concern.
`_run_configure_eval` addresses the eval by **file-path task specifier**
(`configure_eval.py@<arm>`), resolved from `REPO_ROOT`, rather than importing the module —
so the strict-typed `tasks/` package never imports the deliberately non-packaged `tests/`
tree. It runs both arms over the shared dataset, fails closed on a non-success run, reads
each arm's fraction off `log.results`, warns (does not fail) when the skill fails to beat
the baseline, writes the committed JSON via `atomic_write_text`, and returns the with-skill
fraction to the gate. The arm names are string literals here (the boundary forbids
importing `tests/`), but a unit test asserts they equal `tests/evals/shared/names.py`.

```python
def _run_configure_eval(context: Context) -> float:
    from inspect_ai import eval as inspect_eval

    from tasks.eval import readback

    _require_docker()
    logs = inspect_eval(
        [f"{_EVAL_DIR}/configure_eval.py@configure_with_skill",
         f"{_EVAL_DIR}/configure_eval.py@configure_baseline"],
        log_format="json",
        log_dir=str(_RESULTS_DIR),
    )
    with_skill = readback.require_success(readback.arm_log(logs, "configure_with_skill"))
    baseline = readback.require_success(readback.arm_log(logs, "configure_baseline"))
    with_skill_fraction = readback.pass_k(with_skill)
    if with_skill_fraction <= readback.pass_k(baseline):
        print(
            "eval:skills:configure: with-skill did not beat baseline "
            "— investigate whether the skill adds value"
        )
    return with_skill_fraction
```

- `_require_docker` fails fast with an actionable message when the live run is enabled but
  the Docker daemon is unreachable **or** (on Apple Silicon, given the `linux/amd64` pin)
  amd64 emulation is not available — a `docker run --platform linux/amd64 … true` preflight
  — rather than failing deep inside Inspect's sandbox setup. Docker cannot be `mise`-pinned,
  so this is the guard for the out-of-band prerequisite.
- `require_success` raises if `log.status != "success"` or `log.results is None`, so an
  errored/cancelled run never yields a passing fraction over a partial sample set.
- `arm_log` selects the named arm; `pass_k` filters `log.results.scores` on
  `reducer == "all_correct"` and reads `metrics["accuracy"].value` — the fraction whose
  metric name is `accuracy` but whose meaning, over the all-succeed reducer, *is* pass^k
  (bound to a local `all_correct_fraction` at the read site so it is not mistaken for a
  lenient metric). It **raises a clear domain error** (never defaults to a passing value)
  when no `all_correct`/`accuracy` record is present, so a reducer/metric-name drift
  fails loudly rather than silently gating on the wrong number.
- The **skill-vs-baseline check is advisory, not a gate** (per the work item's "baseline
  for attribution only; below-baseline = investigate, not fail"): the gate remains the
  with-skill `pass^k` floor, but a non-improving skill is surfaced rather than hidden.
- Before `atomic_write_text` commits the JSON, `readback.scrub_paths` relativises any
  absolute host paths (`_RESULTS_DIR` / `_EVAL_DIR` roots) so the durable log is
  environment-independent, and a unit test asserts the written JSON carries no
  home-directory substring — an automated guard replacing the manual eyeball check.

#### 7. The ADR note

**File**: `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md`
**Changes**: Add a dated implementation note correcting the `pass_k(k)`
terminology: Inspect has no `pass_k`; its `pass_at(k)` is the lenient pass@k;
the hard pass^k gate is realised by the custom `all_correct` reducer (equivalently
`at_least(k)`), read off `log.results` as the `accuracy` fraction.

#### 8. Unit tests (write first)

**File**: `tests/unit/evals/skills/configure/test_scorer.py`,
`tests/unit/evals/skills/configure/test_dataset.py`,
`tests/unit/evals/shared/test_reducers.py`,
`tests/unit/tasks/test_eval_collection.py` (new),
`tests/unit/tasks/test_eval_readback.py` (new),
`tests/unit/tasks/test_eval_docker_coherence.py` (new)
**Changes** (the eval unit tests **deep-mirror** their source paths, matching the
`tasks/shared/…` ↔ `tests/unit/tasks/shared/…` precedent, so a developer finds them where
the source lives):

- Scorer branches, against realistic message stubs so the transcript-shape assumption
  is pinned: `grade_value` (exact equal / unequal; and via the get call site, stdout
  `team-v\n` matches target `team-v`, and `\n` matches the empty target — the trailing
  newline reconciled, not stripped), `grade_error` (a `CommandResult` with empty stdout +
  marker + `expected_exit` match, including **exit-2 accepted / exit-1-when-2-expected
  rejected** so the clap distinction is enforced, and marker-absent rejected),
  `grade_precedence` (personal==new AND team==seed → True; a team-overwrite → False),
  `bash_result` (verb+key argv match picks the agent's `get` and **not** the scorer's
  follow-up `get`s, an interleaved `set` on the same key, nor a differently-`--level`ed
  command; matches a failing `set` for the conflict task via `action`; matches the scoped
  `--level bad` command despite its non-zero exit; returns `None` when absent),
  `skill_was_invoked` (event present naming `configure` / absent / wrong name /
  **tool call with `None` arguments does not raise**).
- Reducer: all-CORRECT → CORRECT; any-INCORRECT → INCORRECT; **empty list → INCORRECT**;
  **partial list (`len < k`) → INCORRECT**; exactly-`k`-CORRECT → CORRECT.
- Dataset validity: every JSONL line parses and carries its required fields; each *domain*
  error task's `marker` is a substring of the matching message template (the clap
  bad-`--level` task validates against the offending-value string); all **nine** classes
  (get-hit, empty-value, valid-`--level`, set-precedence, conflict, missing, invalid-key,
  malformed, bad-`--level`) are present.
- Read-back (`test_eval_readback.py`): feed `readback.arm_log` / `pass_k` /
  `require_success` a **synthetic `EvalLog`** (both arms, multiple reducers, a non-`success`
  status, and a log with **no `all_correct` record**) and assert the correct arm +
  `accuracy` value are selected, a non-success status raises, and a missing reducer/metric
  raises (never defaults to a pass); and `scrub_paths` over a log with absolute
  `_RESULTS_DIR` / `_EVAL_DIR` paths yields JSON with no home-directory substring.
- Name coherence: the arm/reducer/metric string literals in `tasks/eval/skills.py` /
  `tasks/eval/readback.py` equal `tests/evals/shared/names.py` (`ARM_*`, `REDUCER_NAME`,
  `ACCURACY_METRIC`), and the `configure_eval.py@<arm>` specifiers resolve to the real
  `@task` names — so a rename on either side fails a fast test, not the live run.
- Docker coherence (`test_eval_docker_coherence.py`): the Dockerfile's `COPY` source equals
  `binary_path("linux-x64")` relative to `REPO_ROOT` and the compose `platform:` matches the
  amd64 triple — guarding the hand-synced mirror of `tasks/shared/targets.py`.
- Construction + loader + non-collection: `configure_with_skill()` / `configure_baseline()`
  each construct a `Task` without raising against the pinned `claude_code` signature (also
  pinning that `version=`, `message_limit`, and `fail_on_error` are accepted); the eval
  modules load via the **same mechanism Inspect's file-path loader uses** (exercising the
  `configure_eval.py@<arm>` path, not a plain pytest import) so the chosen import form under
  the `__init__.py`-free tree is confirmed cheaply rather than live; and pytest does not
  collect `configure_eval.py` (not `test_*`).

#### 9. Wire the eval unit suite into the test tier

**File**: `tasks/test/evals.py` (new), `tasks/test/__init__.py`, `mise.toml`,
`tests/unit/tasks/test_mise_wiring.py`
**Changes**: The eval-logic unit tests live under `tests/unit/evals/**`, but the existing
`test:unit:tasks` leaf only runs `tests/unit/tasks` — nothing runs `tests/unit/evals`, so
without this the scorer/reducer/dataset tests would be lint/type-checked but **never
executed** by `mise run`/CI. Add a `test.evals.run` invoke task (`pytest tests/unit/evals`,
mirroring `test.tasks.run`), register it in the `test` collection, add a `test:unit:evals`
mise leaf, and fold it into the `test:unit` roll-up:

```toml
[tasks."test:unit:evals"]
depends = ["deps:install:python"]
run = "invoke test.evals.run"

[tasks."test:unit"]
depends = ["test:unit:tasks", "test:unit:cli", "test:unit:evals"]
```

Extend `test_mise_wiring.py` to assert `test:unit:evals` **is** in `test:unit`'s `depends`
(the mirror of the existing assertion that the live `eval` tier is **absent** from
`check`/`default`) — so the eval unit suite cannot silently fall out of CI.

### Success Criteria

#### Automated Verification

- [x] Scorer/dataset/collection/read-back/coherence unit tests pass, wired into the
      tier: `mise run test:unit:evals` (plus the task-side
      `uv run pytest tests/unit/tasks/test_eval_collection.py tests/unit/tasks/test_eval_readback.py tests/unit/tasks/test_eval_docker_coherence.py -v`).
      **The custom `all_correct` reducer + `tests/evals/shared/reducers.py` were dropped**
      per the native-`pass_k` decision, so there is no `test_reducers.py`; the pass^k
      semantic is covered by the `pass_k_3` readback tests and the Phase-0 probe.
- [x] `configure_eval.py` is not collected by pytest:
      `uv run pytest tests/evals --collect-only` reports no items
- [x] Python lint + types clean across the new modules:
      `mise run build-system:check`
- [x] The eval still runs guarded-off without a model call:
      `LUMINOSITY_EVAL_LIVE=off mise run eval:skills:configure` exits 0
- [x] Full read-only sweep green and still eval-free: `mise run check`

#### Manual Verification

- [x] ADR-0011 renders with the implementation note (inverted to *confirm* `pass_k`
      exists as of inspect-ai 0.3.244) and reads coherently.
- [x] The `dataset.jsonl` expected values match `cli/launcher/tests/config.rs` — validated
      by running the real launcher against every fixture/task (markers, exit codes, and
      stdout all confirmed); markers are also substring-checked in the dataset-validity test.

---

## Phase 3: Live run and committed eval log

> **Status (2026-07-08): BLOCKED on Anthropic API credit.** A 1-sample/1-epoch
> smoke test validated the full integration chain — `build:release` →
> host-independent Docker sandbox → in-container launcher (amd64 emulation) →
> `inspect_swe`-driven Claude Code 2.1.203 → Anthropic model proxy — discharging
> the story's chief residual risk. The run then fails at the model call with
> `400: "Your credit balance is too low to access the Anthropic API"` (the
> `mise.local.toml` key is unfunded). The Phase-3 deliverables below (committed
> log, golden transcript fixture, CLI-version assertion, skill-attribution
> promotion) require a completed run and are **deferred pending funded credit**;
> once funded, `mise run eval:skills:configure` produces them. See the findings
> note for the validated-vs-blocked breakdown.

### Overview

Run the eval for real once — the story's residual-risk throwaway run validating
the `inspect_swe`-driving-Claude-Code integration — and commit the JSON log as
the durable quality signal.

### Changes Required

#### 1. Execute the live eval

**Prerequisite**: Docker running (an out-of-band prerequisite that cannot be
`mise`-pinned — the task fails fast via `_require_docker` when it is absent), an
authenticated Claude Code / model API, and the token budget to run both arms over the
dataset at k = 3.

**Command**:

```bash
mise run eval:skills:configure
```

This cross-builds the linux-musl launcher via `build:release`, spins up the pinned
`linux/amd64` sandbox, runs both arms, gates on the with-skill `pass_k`, and writes
`results/<timestamp>.json`. This live run is where the deferred integration assumptions
are corroborated against a real log. Three of them are **discharged as concrete steps**,
not just observed:

- **Capture the golden transcript fixture** — commit the first real run's transcript as
  `tests/evals/skills/configure/fixtures/golden_transcript.json` and add a scorer test
  driven from it, so the `Bash`/`Skill` shape and the raw-stdout assumption are pinned by
  a committed test (if stdout turns out normalised, switch get-grading to the scorer
  `sandbox().exec` re-read fallback before trusting the suite).
- **Assert the CLI version** — confirm the log-recorded Claude Code CLI version equals the
  pin (so `inspect_swe`'s own provisioning cannot have run a different, sub-v2.1.144 CLI).
- **Confirm the launcher path** — verify both arms executed the staged launcher via
  `${CLAUDE_PLUGIN_ROOT}/bin/luminosity` (no GitHub fetch, no `allowed-tools` block, agent
  cwd inside the seeded `.git` fixture).

Skill attribution is then promoted from a logged diagnostic to a scored requirement —
**TDD**: write the failing `skill_was_invoked`-backed scorer test first (with-skill arm
requires the `configure` Skill event; baseline arm fails if present), then wire it.

#### 2. Commit the eval log

**File**: `tests/evals/skills/configure/results/<timestamp>.json` (new),
`tests/evals/skills/configure/fixtures/golden_transcript.json` (new)
**Changes**: Commit the JSON log (already scrubbed of absolute host paths by
`readback.scrub_paths`, so the durable signal is environment-independent — enforced by
the scrub unit test, not a manual eyeball) and the golden-transcript fixture. Record in the
commit message the with-skill and baseline `pass_k`, the pinned model id, and the Claude
Code CLI version; if with-skill does not exceed baseline, note it as a signal to
investigate rather than a failing outcome. The committed log is a **point-in-time record**
(the pinned model snapshot is retired on Anthropic's schedule) and its read-back is coupled
to the pinned `inspect-ai` version, so a future model-retirement or format-changing bump is
a conscious, documented refresh event, not a reproducible re-run.

### Success Criteria

#### Automated Verification

- [ ] The gated live run exits 0: `mise run eval:skills:configure`
- [ ] The committed log is valid JSON and readable back:
      `uv run python -c "from inspect_ai.log import read_eval_log; read_eval_log('<path>')"`

#### Manual Verification

- [ ] The committed log records both arms over the same dataset with a
      with-skill `pass_k ≥ 0.8`.
- [ ] Inspect View (or `read_eval_log`) shows per-sample transcripts with the
      `Skill` tool-use event on the with-skill arm, and the agent's `Bash` commands
      running via `${CLAUDE_PLUGIN_ROOT}/bin/luminosity` inside the seeded fixture.
- [ ] The golden-transcript fixture is committed and its scorer test passes; the
      log-recorded CLI version equals the pin.
- [ ] The `inspect_swe` integration behaved (skill loaded in the with-skill arm,
      suppressed in the baseline) — the residual risk is discharged.
- [ ] `mise run check` and the bare `mise run` default remain green and never
      trigger the eval.

---

## Testing Strategy

### Unit Tests

- Gate: `below_floor` two-sided at 0.79 / 0.8 / 1.0; `env_flag_enabled` normalisation
  (test at `tests/unit/tasks/shared/test_env.py`, mirroring the `shared/` layout).
- Task wrapper: synthetic `pass_k` below → `Exit`, at/above → clean; disabled live run
  skips; live run enabled but Docker unreachable → clear `Exit`.
- Scorer: `grade_value` (byte-exact incl. trailing-newline reconciliation) /
  `grade_error` (`CommandResult`, exit-code match incl. exit-2 clap + empty stdout +
  marker) / `grade_precedence` (personal==new AND team==seed) / `bash_result` (verb+key+
  level argv match, follow-ups/interleaved excluded, `None`) / `skill_was_invoked` (incl.
  `None` arguments) against message stubs; plus one test driven from the committed golden
  transcript.
- Reducer: exactly-`k`-CORRECT → CORRECT; any-INCORRECT, empty, and partial-`k` → INCORRECT.
- Read-back: `readback.arm_log` / `pass_k` / `require_success` / `scrub_paths` over a
  synthetic `EvalLog` (incl. non-success and missing-reducer → raise; path scrub).
- Name coherence: `tasks/eval` literals equal `tests/evals/shared/names.py`; the `@arm`
  specifiers resolve to the real `@task` names.
- Docker coherence: Dockerfile COPY source == `binary_path("linux-x64")`; compose platform
  == amd64 triple.
- Dataset: schema validity, domain markers substring the templates, all **nine** scenario
  classes present.
- Construction/loader: both `@task`s build without raising against the pinned `claude_code`
  signature and the `version=` / `message_limit` / `fail_on_error` bounds; the eval modules
  load via Inspect's file-path loader path.
- Wiring: the live `eval` tier (`eval` / `eval:skills` / `eval:skills:configure`) is
  declared but **absent** from `check`/`default`; the `test:unit:evals` leaf **is** in
  `test:unit` so the eval unit suite runs in the default `mise run`.
- Non-collection: pytest collects nothing under `tests/evals/`.

### Integration Tests

- The single live run in Phase 3 is the end-to-end integration exercise; it is
  developer-run, not CI, by design.

### Manual Testing Steps

1. `LUMINOSITY_EVAL_LIVE=off mise run eval:skills:configure` — confirm the skip
   path costs no tokens.
2. `mise run eval:skills:configure` with Docker + auth — confirm both arms run,
   the log is written, and the gate passes.
3. Open the log in Inspect View — confirm transcripts, the `Skill` event, and
   the baseline contrast.
4. `mise run check` — confirm the eval never runs in the read-only sweep.

## Performance Considerations

The live run spends real tokens and Docker time (two arms × 9 tasks × k = 3 trials).
This is precisely why the tier is dev-time/committed and excluded from CI. The
`LUMINOSITY_EVAL_LIVE` knob lets constrained environments load the module and run the
unit tests without spending anything.

**Gate brittleness is a deliberate, understood property.** With the all-succeed reducer
each task passes only if all k = 3 trials pass, and the `pass^k ≥ 0.8` floor over 9
tasks means ≥ 8 of 9 tasks must pass every trial — a single flaky trial spread across
two tasks fails the whole gate. Against a stochastic model this is an intentionally hard
bar, not an accident of dataset size: a failure is a signal to read the transcript and
**re-run once** before treating it as a regression (the tier is manually re-runnable by
design). If real-world flakiness proves too high, the documented lever is to raise k or
grow the task count — not to soften the per-task all-succeed semantic. Note the
interaction with `fail_on_error=True` (Phase 2 §3): a transient-infra failure shares this
all-or-nothing verdict, which is why the ramp to 20–50 tasks needs a resilience revisit,
not just more tasks.

## Migration Notes

Essentially additive: a new `tests/evals/` tier (with a `shared/` sub-tree for the
skill-agnostic reducer + names), a new `tasks/eval/` collection (`gate.py`, `skills.py`,
`readback.py`), a shared `tasks/shared/env.py` helper, a repo-root `.dockerignore`, two
new pinned dependencies, and the `eval` / `eval:skills` / `eval:skills:configure` `mise`
tasks. The eval tier is invisible to `check`/`default`. The **one non-additive change** is
mechanical and behaviour-preserving: `coverage_enabled` in `tasks/shared/rust.py` is
migrated onto the shared `env_flag_enabled` so the falsey contract has a single definition
— guarded by its existing two-sided test, so no behaviour changes. (`pup_mode` maps to a
`warn`/`deny` string via `_PUP_MODES`, not a falsey bool, so it is left untouched.)

**Naming deviation (deliberate).** The subject tree is `tests/evals/` (plural) because
ADR-0011 fixes that layout, while the task collection / mise tier / invoke namespace are
singular `eval` to mirror the existing singular `tasks/test/` collection and its
`test` tier. The two spellings are kept intentionally rather than churned: changing
`tests/evals/` would require superseding ADR-0011, and renaming the collection to `evals`
would break symmetry with `test`.

## References

- Work item: `meta/work/0010-apply-eval-framework-to-configure-skill.md`
- Research: `meta/research/codebase/2026-07-07-0010-apply-eval-framework-to-configure-skill.md`
- Decision: `meta/decisions/ADR-0011-inspect-as-the-skill-evaluation-harness.md`
- Spike: `meta/work/0003-skill-evaluation-framework-selection.md`
- Grading oracle: `cli/launcher/tests/config.rs`
- Gate pattern: `tasks/version.py:116-148`; env-knob pattern:
  `tasks/shared/rust.py:28-49`; two-sided test: `tests/unit/tasks/test_pup.py:11-44`
- Skill under test: `skills/config/configure/SKILL.md:9-64`
- Inspect docs: https://inspect.aisi.org.uk/ · `inspect_swe`:
  https://meridianlabs-ai.github.io/inspect_swe/claude_code.html
