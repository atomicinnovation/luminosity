This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Luminosity is a **Claude Code plugin** — not a conventional application. The shipped product is the set of **skills** (Markdown `SKILL.md` files), **agents**, **hooks**, **templates**, and **scripts** that Claude Code loads. Three language toolchains coexist in one repo, each with its own checks; see Architecture below.

## How we write code

These are non-negotiable. They override convenience.

- **Test-driven development, in its purest form.** Follow the red-green-refactor loop: write a failing test first (red), write the minimum code to pass it (green), then refactor with the safety net in place. Never write production code without a failing test demanding it.
- **Strict domain-driven design.** Model the domain explicitly. Prefer code that is clear, readable, and expresses intent through rich domain language — names and abstractions that mirror how the domain is spoken about, not technical incidental detail.
- **Comments are a last resort.** A comment is a signal that the code failed to express its own intent. Before writing one, do the work to make the code itself clear — rename, extract, restructure. Only keep a comment when it captures something genuinely non-obvious to a skilled developer that no amount of refactoring could convey (e.g. *why* an unusual choice was made, an external constraint, a subtle invariant).

## Build, test, and check

All dev tasks run through **`mise run <task>`** (declared in `mise.toml`, implemented as [invoke](https://www.pyinvoke.org/) tasks under `tasks/`). Run
`mise tasks` for the full leaf list; `tasks/README.md` documents the *shape* of the task tree (learn it once).

**"Done" means `mise run` (the bare default task) exits 0 end-to-end.** That is the full local CI mirror: it applies all formatters and safe lint fixes, runs every lint and type-check, runs the entire test suite (the cli workspace unit tests carry coverage by default — `cargo llvm-cov nextest`), the `build:launcher` host-native release build, and the `deny:check` / `pup:check` static checks. It is heavy (reformats in place, compiles Rust several times). A change is not finished until this is green.

Two faster entry points exist and should be your inner loop:

- `mise run check` — the read-only set CI runs (format + lint + types across all components, plus the workspace-scope `deny:check` / `pup:check` static checks). It is **test-free and build-free**: the cli workspace unit tests run via the `test` roll-up and `build:launcher` runs in the bare `mise run` default, neither in `check`. Must exit 0 before pushing.
- `mise run fix` — apply every formatter + safe lint fix (mechanical only; **no type-checks**, and shell has no autofixer). `lint:fix` now also runs `lint:cli:fix` (clippy `--fix`, machine-applicable only, rewriting a dirty tree via `--allow-dirty --allow-staged`); shell still has no autofixer.
- `mise run <component>:check` — fast single-component loop. Components:
  `build-system`, `scripts` (shell), `cli` (the whole Rust workspace). `cli:check` is rustfmt + clippy only — like the other roll-ups it runs **no tests** (the cli workspace unit tests run via `test:unit:cli` → `test`, carrying coverage by default: `cargo llvm-cov nextest`, disable with `LUMINOSITY_COVERAGE=off`). There is **no `<component>:fix`** roll-up — fix a component via its `format:<c>:fix` + `lint:<c>:fix` tasks. Single-crate `launcher:check` / `kernel:check` (`-p luminosity` / `-p kernel`) exist for ad-hoc runs but stay out of `check` — the workspace `cli:check` already covers every crate in one pass.
- `build:launcher` release-builds the host-native triples (the two musl triples on Linux, the two darwin triples on macOS) and is in the bare `mise run` default — so the full local check exercises it — but **not** in the fast read-only `mise run check`. CI's `build-launcher` matrix covers all four triples across both OSes.

Enforcement is **CI-only — there are no pre-commit hooks.** Run `mise run fix &&
mise run check` yourself before pushing.

PR mergeability is gated by GitHub branch-protection *required checks* (repo
settings, not the workflow YAML); when a CI job is added or renamed, its
required-check name must be registered manually — see the runbook in
`CONTRIBUTING.md`.

### Running a single test

The aggregate `mise run test:*` tasks have no name filter; drop to the underlying runner for one test:

- **Python (tasks/):** `uv run pytest tests/unit/tasks/test_x.py::test_y -v`
- **Shell:** the suites are standalone scripts — run e.g. `bash scripts/test-config.sh`
  or `bash hooks/test-vcs-detect.sh` directly.
- **Rust (cli/launcher/):** `cargo nextest run -p luminosity -E 'test(<name>)'`
  — the plain (uninstrumented) form with nextest's filter syntax. It
  deliberately skips coverage, unlike the default `test:unit:cli` path
  (`cargo llvm-cov nextest`).

## Architecture

### Skills as the product (`skills/`, `agents/`, `templates/`, `hooks/`)

Skills are grouped by category and registered in `.claude-plugin/plugin.json`. Each skill is a `SKILL.md` with YAML frontmatter (`name`, `description`,
`argument-hint`, `allowed-tools`). The non-obvious mechanism: a SKILL.md body runs the supporting CLI via the **`!` preprocessor** (``!`command` ``) at invocation time to inject live context (VCS status, config, per-skill context) into the prompt. Scripts are addressed via `${CLAUDE_PLUGIN_ROOT}` so they resolve from the installed plugin location.

The core design (read the README "Philosophy" section): phases of work, represented by skills, communicate **through the filesystem**, not the conversation. The `meta/` directory is persistent shared memory; each skill reads/writes predictable paths within it. Subagents (`agents/*.md`) do exploratory work in isolated context and return only summaries. Locator agents (find, no Read) are deliberately separated from analyser agents (Read) to keep each context bounded.

### Build system (`tasks/`)

Python invoke tasks, type-checked with **pyrefly (strict preset)** and linted with **ruff (`select = ["ALL"]`)** — both version-pinned exactly in
`pyproject.toml` because their rule sets are version-sensitive. Shared helpers live in `tasks/shared/`. Release/version logic enforces **version coherence**:
`plugin.json`, the server's `Cargo.toml`, and `checksums.json` must agree.

### Rust workspace (`cli/`)

The Cargo workspace root is `cli/` — `cli/Cargo.toml`, `cli/Cargo.lock`, and the
four Rust-workspace tool configs all live there, so `cli/` is a self-contained
workspace (build output is `cli/target/`; the invoke tasks `cd` into `cli/`
before invoking cargo/cargo-deny/cargo-pup). The workspace manifest is
intentionally **versionless, `[package]`-free** — the product version lives in
`cli/launcher/Cargo.toml` (the version-bearing crate `tasks/version.py` keeps
coherent with `plugin.json` / `checksums.json`). Four config files map to roles,
all under `cli/`:

- `cli/Cargo.toml` — workspace members + the shared lint levels. Clippy lint
  **levels** live in `[workspace.lints.clippy]` here (members opt in via
  `[lints] workspace = true`), **not** in `clippy.toml`.
- `cli/clippy.toml` — clippy *configuration* (thresholds, `msrv`), not levels.
- `cli/deny.toml` — cargo-deny supply-chain policy plus the architectural /
  native-tls ban-lists (the cross-crate ban-lists are deliberately inert until
  the workspace splits into multiple crates).
- `cli/pup.ron` — cargo-pup's intra-crate module-import rules, intentionally
  empty in the bootstrap (story 0007 adds the inward-direction layering rules).

The `cli/launcher/` crate is a throwaway bootstrap (a trivial function + test)
so the toolchain has real code to run against; story 0007 replaces its body with
the hexagonal `version` subcommand.

### Shell scripts (`scripts/`, `hooks/`)

A large bash library backs the skills (config reading, VCS detection, frontmatter parsing, migrations). Checked with shfmt + ShellCheck, plus a custom **bashisms** linter (`scripts/lint-bashisms.sh`) that guards a **bash 3.2 floor**
— macOS ships bash 3.2, so bash-4 constructs (associative arrays, `${var,,}`, etc.) are banned. Suspect the 3.2 floor first for any macOS-only shell failure.
`hooks/` contains `SessionStart`/`PreToolUse` hooks (config detection, VCS detection + git-guard, migration reminders).

## Conventions and gotchas

- **Line width is 80 everywhere** (except markdown), set in `.editorconfig` and **duplicated by hand** into `pyproject.toml` (ruff) and `cli/rustfmt.toml` (rustfmt) because those tools don't read `.editorconfig`. shfmt reads it natively. Keep the copies in sync — there is no automated check.
- **`cli/clippy.toml`'s `msrv` is a fourth hand-synced mirror of the `mise.toml` rust pin** (alongside the three 80-col copies) — the same manual-sync hazard. Bump them in lockstep on any rust upgrade; `tests/unit/tasks/test_mise_wiring.py` asserts the `msrv`/rust-pin coherence so a forgotten copy fails loudly.
- **Shell has no autofixer** — `scripts` is absent from `lint:fix`; ShellCheck findings are fixed by hand or with a justified `# shellcheck disable=`.
- Tests deliberately have **no `__init__.py`** (pytest importlib mode). They are held to the **same** ruff and pyrefly (strict) standards as the rest of the codebase — fixture parameters are fully annotated (`mocker: MockerFixture`, `monkeypatch: pytest.MonkeyPatch`, the local `ctx` fixture as `MagicMock`, etc.), there is no relaxed test profile.
- Tooling versions (uv, python, gh, rust, cargo-nextest, cargo-llvm-cov, cargo-deny, shellcheck, shfmt, actionlint) are pinned in `mise.toml`; `mise` provisions them. **cargo-pup + its pinned nightly are the one exception** — *not* in `[tools]` (mise cannot pin two rust toolchains and has no `rust-nightly` short-name), but rustup-provisioned by the `deps:install:pup` task and pinned by `PUP_NIGHTLY` / `PUP_VERSION` in `tasks/shared/rust.py`. `pup:check` `depends` on `deps:install:pup`, so `mise run check` on a fresh checkout installs the nightly + cargo-pup the same way a Python check triggers `uv sync`. Minimum supported Claude Code for the plugin itself is **v2.1.144** (subagent skill-preload mechanism).
- **The cargo-pup lane is blocking on a pinned nightly** while the product build and every other check stay on stable; it is the sole inward-direction architecture enforcer (ADR-0009). If a nightly/cargo-pup bump breaks it, `LUMINOSITY_PUP_MODE=warn` downgrades it to advisory per-environment without a source edit (and the committed default in `pup_mode()` can flip in one line). A *nightly-unavailable* break (the dated nightly GC'd) instead fails in `deps:install:pup` and is recovered by bumping `PUP_NIGHTLY` + `PUP_VERSION` together to a compatible pair.
