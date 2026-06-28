---
type: codebase-research
id: "2026-06-27-0006-rust-toolchain-guard-rails"
title: "Research: Establishing Rust Toolchain Guard Rails in mise + CI (work item 0006)"
date: "2026-06-27T11:51:56+00:00"
author: Toby Clemson
producer: research-codebase
status: complete
work_item_id: "0006"
parent: "work-item:0006"
relates_to: []
topic: "Establishing Rust Toolchain Guard Rails in mise + CI"
tags: [research, codebase, rust, tooling, ci, mise, guard-rails]
revision: "f4c2765576cf5e35bb58394f1ea9eac54f591fa7"
repository: "luminosity"
last_updated: "2026-06-27T11:51:56+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Research: Establishing Rust Toolchain Guard Rails in mise + CI (work item 0006)

**Date**: 2026-06-27T11:51:56+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: f4c2765576cf5e35bb58394f1ea9eac54f591fa7
**Branch**: jj working copy (colocated; default branch `main`)
**Repository**: luminosity

## Research Question

For work item 0006 ("Establish Rust Toolchain Guard Rails in mise + CI"):
how does the existing build/check system work, what conventions must the new
Rust tasks follow, what Rust scaffolding already exists, and what architectural
decisions (ADRs, sibling work items) constrain the implementation?

## Summary

Work item 0006 wires a Rust toolchain (rustfmt, clippy, cargo-nextest,
cargo-llvm-cov, cargo-deny) into the existing component-based `mise run` task
tree and into CI, mirroring how Python (`build-system`) and shell (`scripts`)
are already enforced. The research surfaced five load-bearing facts:

1. **No Rust code exists yet.** There is no `Cargo.toml`, `Cargo.lock`, `.rs`
   file, or crate directory anywhere in the repo. 0006 is genuinely pre-scaffold
   and is **paired with story 0007** (the scaffold). Neither can fully satisfy
   the two "`mise run` exits 0" acceptance criteria alone — there is nothing to
   lint or test until the scaffold lands.

2. **The task pattern to mirror is well-established and precise.** Every
   component task exists in two layers: a thin declaration in `mise.toml`
   (`run = "invoke <module>.<task>"` or a `depends`-only roll-up) plus a Python
   invoke body under `tasks/` that runs the command with `warn=True` and raises
   `Exit(<actionable message>, code=1)` on failure. Naming: component **leads**
   in its roll-up (`build-system:check`), **trails** in families
   (`format:build-system:check`); `<component>:check` roll-ups exist but there
   is **no `<component>:fix`** roll-up.

3. **The Rust toolchain is already partly provisioned.** `mise.toml:8` pins
   `rust = { version = "1.90.0", components = "rustfmt,clippy" }`, so rustfmt and
   clippy are installed in every CI job already. `tasks/deps.py`,
   `tasks/shared/targets.py`, and `tasks/shared/paths.py` contain Rust-aware
   release scaffolding. **cargo-nextest, cargo-llvm-cov, and cargo-deny are not
   yet pinned**, and no Rust *quality* task or CI job exists yet.

4. **The crate layout named in 0006 (`core`/`adapters`/`cli`) is STALE.** The
   architecture spike (work item 0002, status `done`) and the now-accepted
   ADR-0009 / ADR-0010 supersede the `core`/`adapters`/`cli` triple with a
   subdomain-first workspace: `kernel`, `config`, `config-adapters`, `cli`, and
   one crate per subdomain. The per-crate `cargo <tool> -p <crate>` scoping
   principle in 0006 still holds, but the actual `-p` crate names must come from
   the scaffold (0007) / ADR-0010, not from 0006's illustrative list.

5. **0006's scope may be narrower than the ratified guard-rail set.** The spike
   (0002) additionally mandates **cargo-pup on a pinned-nightly lane** (blocking,
   in both `mise run check` and CI), a **cargo-deny ban-list** specifically
   excluding infrastructure crates from light crates' dependency closures, and a
   **CI grep tripwire** against `use crate::{adapters,inbound,outbound}` in
   domain modules. None of these appear in 0006's Requirements. Also, **no
   dedicated ADR ratifies the rustfmt/clippy/nextest/llvm-cov tool choices**
   despite 0006's Assumption A3 claiming they are "ratified as ADRs".

## Detailed Findings

### Component task system — the pattern to mirror

The dev task tree is two-dimensional: a **family** axis (`format` / `lint` /
`types` / `test`) crossed with a **component** axis (`build-system`, `scripts`).
Defined in two layers:

- **`mise.toml`** declares names, descriptions, and the `depends` graph.
  Roll-ups have only `depends` (no `run`); leaves delegate via
  `run = "invoke <module>.<task>"`.
- **`tasks/`** holds the Python invoke bodies with the real logic.

ADR-0006 makes this layering mandatory: inline shell logic in `mise.toml` was an
explicitly **rejected** option, so non-trivial Rust task wiring must live in
invoke/Python, not bash snippets.

The universal invoke idiom (copy exactly for Rust):

```python
@task
def check(context: Context) -> None:
    with context.cd(str(REPO_ROOT)):
        result = context.run("uv run ruff format --check", warn=True, pty=False)
    if result.exited != 0:
        raise Exit(
            "ruff format: drift — run `mise run format:build-system:fix`",
            code=1,
        )
```

`warn=True` + manual exit-code inspection (never letting invoke auto-raise) is
the pattern everywhere; the `Exit` message always names the exact `:fix` task.
`check` runs the read-only variant; `fix` runs the mutating variant and does not
check the exit code.

**Naming convention** (`tasks/README.md:23-28`): component **leads** in its
roll-up (`build-system:check`), **trails** in families
(`format:build-system:check`). `fix` variants are leaf-only. When a component
has multiple linters, `lint:<component>:check` nests a level deeper
(`lint:scripts:shellcheck:check` + `lint:scripts:bashisms:check`).

### How `check`, `fix`, and `default` aggregate (where Rust plugs in)

- `check` (`mise.toml:134-136`) — **what CI mirrors** — aggregates by component
  roll-up: `depends = ["build-system:check", "scripts:check"]`. Rust crate
  roll-ups (and the workspace cargo-deny task) get appended here.
- `fix` (`mise.toml:130-132`): `depends = ["format:fix", "lint:fix"]`.
- `default` (`mise.toml:138-140`): `depends = ["format:fix", "lint:check",
  "types:check", "test"]` — the heavy full local-CI mirror.
- Family aggregates fan across components: `format:check`, `format:fix`,
  `lint:check`, `types:check`. Note `lint:fix` is **Python-only** (shell has no
  autofixer) — a Rust `lint:fix` (clippy `--fix`) could join it.

### Tool version pinning (`mise.toml:4-11`)

Format is `name = "exact.version"`, or a table for components. Tools outside
mise's default registry use a quoted backend prefix
(`"aqua:rhysd/actionlint"`). `rust` already pins `rustfmt,clippy` components
(`mise.toml:8`). **cargo-nextest, cargo-llvm-cov, cargo-deny (and the spike's
cargo-pup + pinned nightly) are not yet pinned** and must be added here, per
ADR-0006's "pin exactly so local mirrors CI" rule.

### CI workflow (`.github/workflows/main.yml`) — the only workflow

- Triggers: `push` to `main`, and `pull_request` (opened/reopened/edited/
  synchronize). No `.github/actions/` composite actions exist.
- CI does **not** call aggregate `mise run check`. It fans into discrete jobs,
  each provisioning tools via `jdx/mise-action@v4.1.0` (`install: true`,
  `cache: true`) then running one `mise run` target:
  - `test-unit` / `test-integration` — matrix `os: [ubuntu-latest,
    macos-latest]`, run `mise run test:unit` / `test:integration`.
  - `check-scripts` (`ubuntu-latest`, no matrix) — `mise run scripts:check`.
  - `check-build-system` (`ubuntu-latest`) — `mise run build-system:check`.
- Release jobs (`prerelease`/`release`) are all guarded by
  `if: github.event_name == 'push'`, so they do not run on PRs. They are the
  **only** place Rust is used in CI today (cross-compiling release binaries).
- **No Rust check job, no cargo caching, no `rust-toolchain` action.** Because
  `rust` is in `mise.toml [tools]`, rustfmt/clippy are already installed in every
  job — a Rust check job needs no new toolchain action, only a task to invoke
  and (for speed) cargo build caching (`Swatinem/rust-cache` or `actions/cache`;
  `mise-action`'s cache covers only mise tool binaries, not the cargo target dir).
- **PR mergeability** is enforced by GitHub branch-protection *required checks*
  configured in repo settings (not in YAML). A new Rust job's `name:` (and its
  matrix-expanded contexts) must be added there to actually gate merges. The
  existing job display names are `Run unit tests`, `Run integration tests`,
  `Check scripts`, `Check build system`.
- `tests/unit/tasks/test_workflows.py` parses `main.yml` but asserts only the
  release topology — adding a check job will not break it (and is where a
  presence assertion would live if wanted).

### Line-width / config duplication

`.editorconfig` is the canonical 80-column source; `pyproject.toml` duplicates
it by hand for ruff. ADR-0004 mandates this hand-duplication across toolchains.
**`rustfmt.toml`, `clippy.toml`, `deny.toml`, and `.cargo/` config do not yet
exist** and must be created (CLAUDE.md already references `rustfmt.toml` as the
place the width is duplicated, but the file is absent).

### Existing Rust-aware scaffolding (release path only)

- `mise.toml:23-25` — `deps:install:rust-targets` task.
- `tasks/deps.py:14-17` — `install_rust_targets` runs `rustup target add ...`.
- `tasks/shared/targets.py` — the four cross-compile triples (all Unix:
  `aarch64/x86_64-apple-darwin`, `aarch64/x86_64-unknown-linux-musl`).
- `tasks/shared/paths.py:4-7` — `CLI_DIR = REPO_ROOT / "cli"`,
  `CARGO_TOML = CLI_DIR / "Cargo.toml"`. **Note the tension**: this assumes a
  `cli/` directory at repo root holding a Cargo.toml, which predates the
  multi-crate workspace decision and may need revisiting (see Open Questions).
- `tasks/version.py` — renders `Cargo.toml` and enforces version coherence
  across `plugin.json` / `Cargo.toml` / `checksums.json`.

### Crate layout: 0006's `core/adapters/cli` is superseded

Work item 0002 (spike, `status: done`) **explicitly supersedes** the
`core`/`adapters`/`cli` split that 0001 and 0007 still mention
(0002:106-110): "the decomposition axis is subdomain-first, hexagonal-within."
The ratified workspace (0002:114-155; ADR-0010:87-104):

- **`kernel`** — thin, dependency-light cross-cutting crate (error taxonomy,
  config-access + dispatch/launcher contracts, logging); everything links it.
- **One crate per subdomain** — starts as a single crate with `domain` /
  `application` / `inbound` / `outbound` **modules** (hexarch style); split into
  separate crates only under pressure.
- **`config`** split into `config` (domain+application+ports) and
  `config-adapters` (outbound serde/toml/fs readers).
- **`cli`** — the `luminosity` launcher binary; depends on `kernel` (+ `config`),
  **never** on a subdomain.

`version` and `config` are **built-in** in-process clap subcommands compiled
into `luminosity`; other subdomains arrive via Unix `exec` external dispatch
(ADR-0010:109-116). Workspace-wide HTTP stack is `reqwest` + rustls
(`default-features = false`), pulling `tokio` into the launcher
(ADR-0010:130-131) — the cargo-deny `bans`/`sources` config must tolerate this.

**On-disk directory layout is unspecified.** Neither the spike nor the ADRs
commit to `crates/<name>/` vs top-level `<name>/`. A flat workspace root with
top-level crate dirs (so `cli/Cargo.toml` sits alongside `kernel/Cargo.toml`
under a root workspace `Cargo.toml`) is the natural reading consistent with
`paths.py`, but it is a genuine open implementation detail.

### Guard-rail scope: spike mandates more than 0006 lists

The epic's five Rust tools (0001:118-127) are rustfmt, clippy (pedantic +
nursery + cherry-picked restriction lints, `-D warnings`), cargo-nextest
(proptest/insta "where they earn their place"), cargo-llvm-cov, and cargo-deny
(advisories/licenses/bans/sources). The spike (0002:161-171) adds, as **blocking
checks in both `mise run check` and CI**:

- **cargo-pup** (intra-crate module-import rules; ArchUnit-equivalent) on a
  **pinned-nightly lane** while product build + all other checks stay on stable;
  the nightly is pinned in `mise.toml`. Risk: a nightly bump breaking cargo-pup
  blocks all merges (mitigation: pin exact nightly; fallback: downgrade pup to
  advisory).
- **cargo-deny ban-lists** that keep infrastructure crates out of light crates'
  dependency closures — a specific config requirement beyond default
  advisories/licenses/bans/sources, and the enforcement mechanism 0007's "core
  depends on no adapter/IO crate" criterion relies on.
- A **CI grep tripwire** forbidding `use crate::{adapters,inbound,outbound}`
  from `domain` modules — the zero-dependency floor inside leaf crates.

proptest/insta remain optional for the scaffold-era toolchain.

## Code References

- `mise.toml:4-11` — `[tools]` pins; `rust` with rustfmt/clippy already present.
- `mise.toml:23-25` — `deps:install:rust-targets`.
- `mise.toml:77-79` — `scripts:check` roll-up (model for `<crate>:check`).
- `mise.toml:114-116` — `build-system:check` roll-up (model with a workspace-wide
  leaf folded in, like cargo-deny).
- `mise.toml:130-140` — `fix`, `check`, `default` top-level aggregation.
- `tasks/format/build_system.py:6-23` — check/fix idiom (ruff format).
- `tasks/lint/build_system.py:6-23` — lint check/fix idiom (ruff check).
- `tasks/types/build_system.py:6-14` — check-only idiom (pyrefly).
- `tasks/format/scripts.py:12-49` — path-scoped check/fix helper (shfmt).
- `tasks/lint/scripts.py:17-44` — multi-linter component (shellcheck + bashisms).
- `tasks/__init__.py:17-52` — invoke `Collection` namespace assembly (register
  new Rust modules here).
- `tasks/README.md:23-28` — canonical task-tree shape + naming convention.
- `tasks/deps.py:14-17`, `tasks/shared/targets.py`, `tasks/shared/paths.py:4-7` —
  existing Rust-aware release scaffolding.
- `.github/workflows/main.yml:15-93` — test + check jobs (insert Rust job near
  `:77-93`); `:103,147,157` — push-only release guards.
- `.editorconfig`, `pyproject.toml` — line-width-80 duplication precedent.

## Architecture Insights

- **Two-layer task discipline (ADR-0006)**: declaration in `mise.toml`, logic in
  testable Python invoke tasks. New Rust task modules should ship with parallel
  unit tests under `tests/unit/tasks/` asserting the exact command string built
  — matching the TDD mandate in CLAUDE.md.
- **Per-crate scoping is cargo-native**: use `cargo <tool> -p <crate>` rather
  than the path-enumeration helper (`tasks/shared/sources.py`) that shell tools
  need. cargo-deny is workspace-scoped (no `-p`) and is its own task.
- **CI mirrors `mise run check` but splits it into jobs.** Keep the new Rust
  component in the aggregate `check` task so local and CI stay in lockstep, and
  add a dedicated `check-<crate>`/`check-rust` job to the workflow.
- **The toolchain is provisioned ahead of use** — adding Rust quality tasks is
  the first actual `cargo` quality invocation in the repo.

## Historical Context

- `meta/decisions/ADR-0004-three-toolchain-split.md` — Rust owns the domain;
  each toolchain carries its own checks, pinned versions, CI lanes; 80-col width
  hand-duplicated. Does **not** name Rust quality tools.
- `meta/decisions/ADR-0006-mise-invoke-task-runner.md` — governs how the task
  tree/CI is organised; inline-shell logic rejected; `<component>:check` with no
  `:fix`; CI-only enforcement.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md`
  — hexagonal layout; cargo-deny ban-lists keep infra out of the core closure;
  **cargo-pup on pinned-nightly** enforces inward direction.
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md`
  — authoritative crate/workspace layout (`kernel`/`config`/`config-adapters`/
  `cli`/`luminosity-<sub>`); built-in `version`+`config`; reqwest+rustls+tokio.
- `meta/work/0001-baseline-architecture-and-engineering-guard-rails.md` — epic;
  frames guard rails as primarily the Rust toolchain; lists the five tools; the
  toolchain↔scaffold pairing constraint (0001:251-254).
- `meta/work/0002-modular-rust-cli-architecture-and-hexagonal-workspace-layout.md`
  — done spike; supersedes the `core/adapters/cli` split; mandates cargo-pup,
  ban-lists, and the grep tripwire.
- `meta/work/0007-scaffold-hexagonal-rust-workspace-with-version-subcommand.md`
  — draft; paired with 0006; `version` subcommand (version from crate, build
  metadata injected at build time, in-process clap, test-first).
- `meta/reviews/work/0001-...-review-1.md` — review of the epic.
- `meta/plans/` and `meta/research/codebase/` are otherwise empty — no prior
  plan or research exists for 0006.

## Related Research

None — this is the first codebase-research document in
`meta/research/codebase/` (the directory previously held only `.gitkeep`).

## Open Questions

1. **Which crates actually get per-crate tasks?** 0006 says
   `core`/`adapters`/`cli`; the done spike + ADR-0010 say
   `kernel`/`config`/`config-adapters`/`cli`/subdomains. The `-p` names must be
   reconciled with whatever 0007 scaffolds (likely minimal first). 0006's
   Requirements/Acceptance Criteria text should be updated to match.
2. **On-disk crate directory layout** — `crates/<name>/` vs top-level `<name>/`?
   `tasks/shared/paths.py` currently hard-codes `cli/Cargo.toml` at repo root,
   which predates the multi-crate workspace and may need updating.
3. **Is cargo-pup (+ pinned nightly) in scope for 0006?** The spike mandates it
   as a blocking check, but 0006's Requirements omit it. Decide whether 0006
   absorbs the nightly lane, ban-lists, and grep tripwire, or whether they are
   tracked separately.
4. **Which restriction lints are cherry-picked?** 0006's stated open question;
   no ADR or doc fixes the list.
5. **Is there an ADR ratifying the rustfmt/clippy/nextest/llvm-cov choices?**
   0006 Assumption A3 claims so, but the 11 existing ADRs include no dedicated
   Rust-quality-tooling ADR — only ADR-0004 (generic split) and 0009/0010
   (architecture). This may be a gap to close.
6. **Coverage gating** — cargo-llvm-cov is listed but no threshold/enforcement
   policy is specified; `mise run check` exiting 0 only requires it to run.
7. **CI cargo caching** — none exists; the new Rust job will be slow without
   `Swatinem/rust-cache` or an `actions/cache` over the cargo target dir.
