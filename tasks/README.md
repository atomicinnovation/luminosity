# Task tree

The repo's dev tasks are declared in `mise.toml` (run them with
`mise run <task>`) and implemented as [invoke](https://www.pyinvoke.org/) tasks in this package. `mise tasks` lists every leaf with its description; this file documents the *shape* of the tree so it only has to be learned once.

## Per-component checks

Each component has a `<component>:check` roll-up that folds that component's format + lint (+ type-check where applicable):

| Component      | Roll-up              | Folds                                        |
|----------------|----------------------|----------------------------------------------|
| Python tooling | `build-system:check` | format + lint + types (ruff, pyrefly)        |
| Shell          | `scripts:check`      | format + lint (shfmt, ShellCheck + bashisms) |
| Rust cli crate | `cli:check`          | format + lint (rustfmt, clippy `-D warnings`); **no tests** |
| Rust kernel crate | `kernel:check`    | format + lint (`-p kernel` rustfmt + clippy); **no tests** |

`kernel:check` is the one deliberate departure from the
"`<component>:check` folds into `check`" pattern: it is a **targeted,
single-crate** (`-p kernel`) roll-up for ad-hoc runs and is **kept out of the
aggregate `check`**. The aggregate covers `kernel` through the single
workspace-wide rustfmt + clippy pass that `cli:check` already runs (plus
`deny:check` / `pup:check`), so adding `kernel:check` to `check` would only pay
a second per-crate tool startup for no extra coverage.

`build-system` is the repo-root Python automation toolchain (this `tasks/`
package + its tests). It is the *component* `build-system:check`, distinct from
the `build:*` *artifact* namespace below (which `build:cli` now populates); the
two are unrelated. Its task descriptions name Python/ruff/pyrefly so
`mise tasks | grep -i python` finds it.

Like the other `<component>:check` roll-ups, `cli:check` is **test-free** —
rustfmt + clippy only. The cli unit tests run via `test:unit:cli` → `test:unit`
→ `test` (the same path the Python suite takes), with **coverage folded into the
test run** (`cargo llvm-cov nextest` by default; `LUMINOSITY_COVERAGE=off` drops
to a plain `cargo nextest run`). There is no separate coverage task.

## Workspace-scope checks

`cargo-deny` (supply-chain + the architectural / native-tls ban-lists) and the
`cargo-pup` nightly lane (intra-crate module-import rules) span the whole
dependency/module graph, so they are top-level `deny:check` / `pup:check`
roll-ups with no `-p` and no per-crate notion — modelled on
`lint:workflows:check` rather than the per-component pattern. Both are static
analysis, not tests, so they belong in `check`.

`pup:check` runs **blocking** on a pinned nightly (everything else is stable)
and **`depends` on `deps:install:pup`** — the rustup-managed nightly + cargo-pup
are not mise `[tools]`, so the check provisions them itself, mirroring how every
Python check `depends` on `deps:install:python`. `deps:install:pup` is
idempotent, so the steady-state cost is small. `LUMINOSITY_PUP_MODE=warn`
downgrades the lane to advisory without a source edit (the documented fallback
for a nightly/cargo-pup break).

## The `build:*` artifact namespace

`build:<crate>` is a **verb-less, per-crate release build** — it compiles and
links the binary (the link step is the point), so it is not a read-only
`:check`. Only binary-producing crates get one (`build:cli`; a library crate
like `kernel` would not). `build:cli` is OS-aware: it release-builds the host's
native triples (the two musl triples on Linux, the two darwin triples on macOS)
and asserts the static-link / arch invariants. It lives in the bare `mise run`
default but **not** in `check` (a release build is heavier than the read-only
checks); CI's `build-cli` matrix covers all four triples across both OSes.

## Family aggregates

`format:check`, `lint:check`, and `types:check` run the corresponding family across every component; `check` runs all of them plus the workspace-scope
`deny:check` / `pup:check`. `fix` applies `format:fix` + `lint:fix` (mechanical
changes only).

`check` is the read-only/static subset CI mirrors — it runs **no tests and no
release build**. The tests run via the `test` roll-up in the `test-unit` /
`test-integration` jobs, and `build:cli` runs in the `build-cli` matrix job;
none of those are in `mise run check`. So a green `check` does **not** imply a
green CI run — the tests and the release build gate separately.

## Conventions (learn once)

- A component name **leads** its roll-up (`build-system:check`, entity-first, like `version:*` / `github:*`) but **trails** in the families (`format:build-system:check`).
- `scripts` has no `types:*` — only `build-system` type-checks. `lint:scripts:check` nests one level deeper (shellcheck + bashisms) because shell has two linters.
- There are `<component>:check` roll-ups but **no** `<component>:fix`. Fix one component via `format:<component>:fix` + `lint:<component>:fix`, or run the top-level `fix`. Shell has no autofixer, so `scripts` is absent from
  `lint:fix` — run `mise run scripts:check` for remaining shell findings.
