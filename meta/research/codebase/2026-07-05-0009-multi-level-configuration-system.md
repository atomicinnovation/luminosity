---
type: codebase-research
id: "2026-07-05-0009-multi-level-configuration-system"
title: "Research: Multi-Level Configuration System — CLI Command + Thin configure Skill (0009)"
date: "2026-07-05T13:38:19+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0009"
parent: "work-item:0009"
relates_to: ["codebase-research:2026-06-27-0006-rust-toolchain-guard-rails", "codebase-research:2026-06-28-0007-scaffold-hexagonal-rust-workspace", "codebase-research:2026-07-03-0008-static-binary-distribution-and-launcher"]
topic: "Implementing the two-level config system as a cross-crate hexagon + thin configure skill"
tags: [research, codebase, configuration, cli, hexagonal-architecture, cargo-deny, cargo-pup, skills, accelerator]
revision: "001076be76210f8e080d44c93eb2bded75f34cc1"
repository: "luminosity"
last_updated: "2026-07-05T13:38:19+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Multi-Level Configuration System — CLI Command + Thin configure Skill (0009)

**Date**: 2026-07-05T13:38:19+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: 001076be76210f8e080d44c93eb2bded75f34cc1
**Branch**: detached HEAD (jj-colocated working copy)
**Repository**: luminosity

## Research Question

For work item 0009 (Multi-Level Configuration System — CLI command + thin
`configure` skill), what is the current state of the codebase that the story
must build on, and what is the accelerator reference it ports from? Specifically:
the hexagon pattern the new `config` / `config-adapters` crate pair must mirror;
the cross-crate dependency-direction enforcement the story is meant to activate;
the accelerator config model, precedence, parsing and gitignore handling; and how
a thin skill invokes the CLI.

## Summary

The story is buildable and the ground beneath it is well-shaped, but the research
surfaced **two material inaccuracies in the work item's own framing** that should
be corrected before planning:

1. **The enforcement mechanism named in the requirements and acceptance criteria
   is wrong.** Requirements and AC (`meta/work/0009-…md:150-153`) say adding
   serde/toml/fs to the `config` core will fail `cargo deny check` "against the
   cross-crate `skip` / `skip-tree` ban-list in `cli/deny.toml`". In cargo-deny,
   `skip` / `skip-tree` **only suppress duplicate-version warnings** for the
   `multiple-versions` check — they cannot ban a crate from a dependency closure.
   The mechanism that actually enforces dependency *direction* is
   `[[bans.deny]]`, optionally scoped with a `wrappers` allow-list — exactly the
   pattern the **already-live native-tls ban** uses (`cli/deny.toml:60-64`). This
   needs to be resolved during planning; see [Enforcement](#area-b--cross-crate-enforcement-cargo-deny--cargo-pup)
   and [Open Questions](#open-questions).

2. **The "single-crate bootstrap" language is stale.** The workspace already has
   three members (`launcher`, `kernel`, `verify`; `cli/Cargo.toml:5`) and
   `cli/pup.ron` already carries two live `Error`-severity module-layering rules.
   Only the cargo-deny `skip` / `skip-tree` lists are genuinely inert (they are
   empty — `cli/deny.toml:68-69`). The work item's 2026-07-04 enrichment note
   half-acknowledges this ("first *cross-crate* hexagon … workspace already
   carries three members"), but the AC and comments still read as if the config
   split is the first crate boundary.

Everything else lines up cleanly. The launcher's `version` subdomain is a
near-perfect template for the new hexagon (core = traits+domain+service,
`inbound/` = clap-facing render, `outbound/` = infra adapter, composition root in
`main.rs`). The output/exit-code contract the AC demands is achievable with the
existing `println!` + `kernel::Error::Failed` → stderr + `ExitCode::FAILURE`
pattern. The accelerator config model (team `.md` committed + personal `.local.md`
gitignored, personal wins, YAML frontmatter, dotted keys, empty-vs-unset via exit
code) is fully understood and portable. The `configure` skill will be the repo's
**first skill of any kind** — there is no `skills/`, `agents/`, `hooks/`, or
`templates/` directory yet.

## Detailed Findings

### Area A — The hexagon pattern to mirror (launcher `version` subdomain)

The launcher crate (`cli/launcher/`) organises each built-in subcommand as its own
hexagon: a module directory with `core` (domain + ports + application service),
`inbound/` (driving adapters), and `outbound/` (driven adapters). Two exist today:
`version` (the clean template) and `launch` (the richer external-dispatch hexagon).
The `config` crate pair should mirror `version`.

**Layering (`cli/launcher/src/version/`)**
- `version/mod.rs:7-9` — the fixed convention: `pub mod core; pub mod inbound; pub mod outbound;`
- `version/core.rs:6-11` — **outbound/driven port** as a trait (`BuildMetadata`),
  which the core depends on (dependency inversion lives here).
- `version/core.rs:14-20` — domain value object (`VersionReport`), no presentation.
- `version/core.rs:23-25` — **inbound/driving port** (`ReportVersion`).
- `version/core.rs:28-47` — **application service** (`VersionReporter<M: BuildMetadata>`),
  generic over the outbound port, `const fn new`. DI is via a **generic type
  parameter (static dispatch)**, not `Box<dyn>`.
- `version/core.rs:49-78` — unit tests using a hand-written `FakeBuildMetadata`.
- `version/inbound/cli.rs:6-15` — pure `render(&VersionReport) -> String` (unit-testable).
- `version/inbound/cli.rs:17-19` — `report(reporter)` performs the side effect via
  `println!` (exactly one trailing newline). **Verified directly.**
- `version/outbound/build_metadata.rs:9-27` — concrete `VergenBuildMetadata`
  implementing the port off build-baked env vars.

**Composition root & DI (`cli/launcher/src/main.rs`)**
- `main.rs:1-3` — documented as the composition root.
- `main.rs:80-88` — `run()` instantiates concrete adapters and injects them into
  `dispatch`: `VersionReporter::new(VergenBuildMetadata)`; the launch resolver is
  swapped between `FixtureResolver` and `LazyProductionResolver` by env
  (`FIXTURE_ENV`) purely because both implement the `ResolveBinary` port.
- `main.rs:44-56` — `LazyProductionResolver` defers heavy wiring so a built-in
  like `version` never touches infrastructure. A `config` built-in should likewise
  stay cheap.

**clap command tree & dispatch**
- `launch/inbound/cli.rs:8-23` — the **entire** command tree is centralised in one
  inbound adapter (not split per hexagon). `#[derive(Parser)] Cli` +
  `#[derive(Subcommand)] Command { Version, External(Vec<OsString>) }`,
  `disable_version_flag = true`, and `#[command(external_subcommand)]` catches
  unknown subcommands. **Adding `config` = a new `Command::Config(ConfigArgs)`
  variant here** with a nested `#[derive(Subcommand)]` for `get`/`set`.
- `launch/mod.rs:21-37` — `dispatch(cli, reporter, resolver, executor)` takes ports
  by `&impl Trait`; a new match arm routes `Config` into the config hexagon's
  inbound adapter.
- `main.rs:98-104` — parse via `Cli::try_parse()` (not `parse()`) so top-level
  `--help` can be augmented.

**Output & exit-code contract (satisfies 0009's AC)**
- Success value: inbound adapter `println!`s the value (value + single `\n`),
  `dispatch` returns `Ok(())`, `main()` → `ExitCode::SUCCESS` (`main.rs:106-107`).
- Empty-but-set: treat a *found* key with empty value as success — `println!` an
  empty string, return `Ok(())` → exit 0 + newline-only stdout.
- Not-found / bad `--level`: return a config error variant that maps to
  `kernel::Error::Failed(String)` (`cli/kernel/src/lib.rs:9-13`); `main()` prints
  `luminosity: {error}` to **stderr** and returns `ExitCode::FAILURE`
  (`main.rs:106-112`) — stdout stays clean, exit non-zero. The rich per-hexagon
  error enum maps to `kernel::Error` via a `From` impl at the dispatch boundary
  (pattern: `launch/core.rs:148-152`).

**Test structure to mirror**
- Unit tests co-located in `core.rs` with in-file fake ports (`version/core.rs:49-78`,
  `launch/core.rs:183-304`). This is where the AC's "core crate's own unit tests
  cover personal-over-team, team-only fall-through, level-scoped reads" lands.
- Black-box integration tests spawning the binary (`cli/launcher/tests/version.rs`,
  `tests/dispatch.rs`) via `env!("CARGO_BIN_EXE_luminosity")`. This is where the
  exact stdout/newline/exit-code CLI contract is asserted.

### Area B — Cross-crate enforcement (cargo-deny + cargo-pup)

**Verified directly against `cli/deny.toml`.** The relevant sections:
- `cli/deny.toml:60-64` — the **live** architectural ban (the working exemplar):
  ```toml
  deny = [
      { crate = "native-tls" },
      { crate = "openssl" },
      { crate = "openssl-sys" },
  ]
  ```
- `cli/deny.toml:65-69` — the **inert** lists, mislabelled as the architectural
  mechanism:
  ```toml
  # Cross-crate architectural ban-lists, scaffolded inert for the single-crate
  # bootstrap; they become load-bearing once the workspace splits into multiple
  # crates.
  skip = []
  skip-tree = []
  ```

**The correction (independently flagged by two agents):** cargo-deny's `skip` and
`skip-tree` are duplicate-version suppression keys for the `multiple-versions`
check — `skip` excludes a package spec, `skip-tree` excludes a subtree, from
"found N versions of X" detection. Neither prevents a crate appearing in another's
closure. So populating them would **not** fail the build when serde/toml/fs enters
`config`'s closure. Dependency-direction enforcement is `[[bans.deny]]`, and to
scope it (the launcher legitimately depends on serde at
`cli/launcher/Cargo.toml:38-39`) you need the `wrappers` allow-list, e.g.
`{ crate = "serde", wrappers = ["config-adapters"] }` → serde may be reached only
*through* `config-adapters`; a direct `config → serde` edge fails
`cargo deny check bans`. The `cargo tree -p config` AC (`…:147-149`) remains a
valid *secondary* signal, but the "authoritative `cargo deny check` failure"
claim only holds if the mechanism is `bans.deny` + `wrappers`, not `skip`.

Also note ADR-0009 itself never says "skip/skip-tree" — it says "`cargo-deny`
ban-lists keep infrastructure crates out of the core's dependency closure"
(`ADR-0009…md:95-105`). The imprecise wording is local to the work item.

**cargo-pup (`cli/pup.ron`)** — **not** empty. Two live rules
(`pup.ron:4-37`): `version_core_imports_only_permitted` and
`launch_core_imports_only_permitted`, each `RestrictImports(allowed_only: [std/core/alloc,
kernel, own subtree], severity: Error)`. `matches` is the resolved module path;
`allowed_only` is the literal use-path. Because `config` is a *cross-crate* split,
its inward direction is enforced by the **Cargo graph + cargo-deny**, not
cargo-pup (pup is intra-crate). If any config logic were to stay as a launcher
module, it would need an analogous pup rule — but per ADR-0010 it must not.

**Workspace wiring**
- `cli/Cargo.toml:1-5` — `resolver = "3"`, `members = ["launcher", "kernel", "verify"]`.
  Adding `config` + `config-adapters` extends this list.
- `cli/Cargo.toml:36-48` — `[workspace.lints.clippy]` levels; each member opts in
  with `[lints] workspace = true` (confirmed in launcher/kernel/verify manifests).
  The new crates must include that stanza.
- `cli/clippy.toml:4` — `msrv = "1.90.0"` (hand-synced mirror of the mise rust pin).
- `tasks/deny.py:6-16` — `deny:check` runs `cargo deny check advisories licenses
  bans sources` from `cli/`. The `bans` category is where the architectural ban is
  enforced.
- `tasks/pup.py:7-24` + `tasks/shared/rust.py:5-8` — `pup:check` runs
  `cargo +{PUP_NIGHTLY} pup`; `PUP_NIGHTLY = "nightly-2026-01-22"`,
  `PUP_VERSION = "0.1.8"`; `LUMINOSITY_PUP_MODE=warn` downgrades to advisory.

### Area C — Accelerator config model (the port source)

Reference scripts under `../accelerator/scripts/` (absolute:
`/Users/tobyclemson/Code/organisations/atomic/company/accelerator/scripts/`).

**Levels & precedence** (`config-common.sh:27-49`) — `config_find_files()` emits
team `.accelerator/config.md` first, then personal `.accelerator/config.local.md`,
one path per line, order deliberate. `config-read-value.sh:117-124` iterates that
order and **does not break on first match** — it keeps the last successful read,
so personal (emitted last) overrides. This is the exact analogue of luminosity's
`.luminosity/config.md` (team) + `.luminosity/config.local.md` (personal, wins).

**YAML frontmatter parsing (bash-3.2)**
- `config-common.sh:74-86` — `config_extract_frontmatter()`: awk isolates the block
  between the first two `---`; requires `---` on line 1; unclosed → exit 1, treated
  as malformed.
- `config-read-value.sh:32-39` — key split on the **first dot only**: `core.example`
  → `SECTION=core`, `SUBKEY=example`.
- `config-read-value.sh:60-91` — nested lookup: find the `core:` block (lenient
  section-start match; section ends only on a new non-indented top-level key, so
  blank lines inside are tolerated), then the indented `example:` line; strips one
  layer of surrounding quotes; **string comparison, not regex** (metachar-safe);
  first match wins.
- **Two-level cap in accelerator** (`a.b.c` is not descended). **ADR-0003
  deliberately drops this cap for luminosity** — "Arbitrary YAML structure … we
  drop Accelerator's two-level `section.key` cap" (`ADR-0003…md:155-157`). 0009's
  proof value `core.example` is only one level of nesting, but the parser design
  should not hard-code a two-level ceiling.

**Empty-vs-unset** (`config-read-value.sh:90,109,119-130`) — carried by the awk
**exit code**, not the value: a present key with empty value prints empty and
exits 0 (found → `FOUND=true`, `RESULT=""`), an absent key exits 1. On `FOUND=true`
the empty value is echoed and **suppresses the default**. This is precisely 0009's
AC distinction (empty-but-set → exit 0 + empty string; unset → exit non-zero).

**Reads vs writes** — reads are full-stack by default; there is **no `--level`
flag** on the base reader (level-scoping exists only as source-attribution in
`config-dump.sh:95-104`). Writes (`config_set_frontmatter_field` /
`config_upsert_frontmatter_field`, `config-common.sh:160-310`) are per-file
primitives taking an explicit path, **top-level fields only**, fail-closed, value
passed via env (not `awk -v`) to avoid `&`/`/`/`\` corruption, with an integrity
re-read and `atomic_write` (temp + rename). **0009 adds level-scoped reads
(`--level`) and level-targeted writes that accelerator's base reader lacks**, and
needs **nested writes** (accelerator only writes top-level keys) — both are net-new
semantics the Rust port must design, not merely mirror.

**No unset sentinel** (ADR-0003 gotcha, `ADR-0003…md:207-211`) — last-writer-wins
offers no way to *unset* a team value from personal; "use the built-in default"
requires setting a concrete value. Worth noting for the schema's future, though
0009's minimal scope may not hit it.

### Area D — The `configure` skill (greenfield) and gitignore

**There are no skills yet.** No `skills/`, `agents/`, `hooks/`, or `templates/`
directory exists; `.claude-plugin/plugin.json:10` has `"skills": []`. The
`configure` skill will be the **first skill of any kind**, the first
`skills` array entry, the first real use of the `!` preprocessor pattern, and the
CLI's first `config` subcommand alongside `version`.

**The `!` preprocessor** (`CLAUDE.md:57`) — a SKILL.md body runs a command at
invocation time via ``!`command` `` and injects stdout into the prompt; scripts/
binaries addressed via `${CLAUDE_PLUGIN_ROOT}`. The CLI entry point is the bash
bootstrap `${CLAUDE_PLUGIN_ROOT}/bin/luminosity` (`bin/luminosity:16-146`), which
fails closed without `CLAUDE_PLUGIN_ROOT`, resolves the platform binary (fetch +
minisign-verify + atomic install on cache miss) and `exec`s it. So the thin skill's
body reads/writes config via `` !`${CLAUDE_PLUGIN_ROOT}/bin/luminosity config get …` ``.

**Thin-skill exemplars in accelerator** — note accelerator's own top-level
`configure` skill is *thick* (a 978-line reference manual, mostly the `help`
action, and it writes config files with Edit/Write, not the CLI). The **thin**
patterns to emulate are accelerator's sibling `paths` and `init` skills, which use
the `!` preprocessor purely to inject `config-read-*` output
(`skills/config/paths/SKILL.md:22`, `skills/config/init/SKILL.md:21-33`).
Luminosity's thin-skill goal (AC `…:154-158`: skill body contains no YAML parsing,
precedence, or path construction; every read/write is a `luminosity config
get`/`set` call) is *stricter* than accelerator's `configure` and closer to
`paths`/`init`.

**Gitignore** — verified directly: `.gitignore:12` currently ignores
`.accelerator/config.local.md` (accelerator's convention) and there is **no**
`.luminosity/` rule. 0009's AC (`…:140-142`) requires ignoring
`.luminosity/config.local.md` while leaving `.luminosity/config.md` tracked. The
accelerator mechanism to mirror (`accelerator-scaffold.sh:32-40`,
`init-project.sh:47-74`): idempotent whole-line append guarded by `grep -qFx`,
git-repo-gated, newline-safe. Accelerator additionally uses a defence-in-depth
inner `.accelerator/.gitignore` (`config.local.md`) — optional for luminosity; the
AC only requires the root rule. **Whether 0009 owns the `.gitignore` write (an
init concern) or just the `config get`/`set` commands is a scope question** — in
accelerator, gitignore is written by `init`, not `configure`.

### Area E — Governing ADRs (all accepted, none superseded)

- **ADR-0003** (multi-level userspace config): fixes `.luminosity/config.md` +
  `.luminosity/config.local.md` (`:137-145`), last-writer-wins personal-last
  (`:140-143`), arbitrary YAML (drop 2-level cap, `:155-157`), CLI as native reader
  with resolution in the hexagonal core (`:147-153`), init gitignores
  `config.local.md` (`:181-182`), no `$HOME` tier (`:217-219`), no unset sentinel
  (`:207-211`). It explicitly retro-fitted 0009's original `.claude/luminosity*.md`
  paths to `.luminosity/` (`:220-224`) and names 0009 as its proof slice (`:234`).
- **ADR-0010** (git-style modular CLI): `config` is a **shared** crate split into
  `config` (domain+app+ports) and `config-adapters` (outbound readers); each
  sub-binary wires its own `config-adapters` at its composition root — **Model 1**;
  launcher-resolves-once (Model 2) is reserved (`:98-102,185-188`). `version` and
  `config` are the two built-ins compiled into the launcher (`:114-115,182-184`).
  Cross-crate (not modules) because the decomposition axis is the subdomain and
  heavy deps must not bleed into every binary (`:87-90,145-148`). **Naming note:**
  ADR-0010 calls the launcher crate `cli`; the actual workspace member is
  `launcher` (renamed by work item 0014).
- **ADR-0009** (thin CLI over hexagonal core): inward dependency direction is the
  load-bearing rule; crate boundaries enforce *between* crates (Cargo graph +
  cargo-deny ban-lists), cargo-pup enforces *inside* a crate (`:95-105`). Crate
  boundaries are "initially inert … until a subdomain is split into separate
  crates" (`:106-108`) — the `config` split is that first split, so it is where
  cross-crate enforcement first bites. Config access is named as an outbound port
  and serde/toml readers as adapters (`:78-87`).

## Code References

- `cli/launcher/src/version/mod.rs:7-9` — hexagon module convention (core/inbound/outbound).
- `cli/launcher/src/version/core.rs:6-47` — ports as traits + domain value object + generic application service.
- `cli/launcher/src/version/inbound/cli.rs:6-19` — pure `render` + side-effecting `report` (`println!`). **Verified.**
- `cli/launcher/src/version/outbound/build_metadata.rs:9-27` — concrete outbound adapter.
- `cli/launcher/src/main.rs:44-56,80-112` — composition root, env-swapped DI, error→stderr→`ExitCode::FAILURE`.
- `cli/launcher/src/launch/inbound/cli.rs:8-23` — centralised clap command tree (where `config` variant is added).
- `cli/launcher/src/launch/mod.rs:21-37` — `dispatch` over `&impl` ports (where `config` arm is added).
- `cli/kernel/src/lib.rs:9-21` — `kernel::Error::Failed(String)` boundary type + `Display`.
- `cli/deny.toml:60-69` — live native-tls ban (`deny=[…]`) vs inert `skip`/`skip-tree`. **Verified.**
- `cli/pup.ron:4-37` — two live intra-crate layering rules (not empty).
- `cli/Cargo.toml:1-5,36-48` — members list + workspace clippy lints.
- `cli/clippy.toml:4` — `msrv = "1.90.0"`.
- `.gitignore:12` — currently ignores `.accelerator/config.local.md`; no `.luminosity/` rule. **Verified.**
- `.claude-plugin/plugin.json:10` — empty `skills` array.
- `bin/luminosity:16-146` — CLI bootstrap entry point resolved via `${CLAUDE_PLUGIN_ROOT}`.
- `../accelerator/scripts/config-common.sh:27-49,74-86,160-310` — file discovery, frontmatter extraction, write primitives.
- `../accelerator/scripts/config-read-value.sh:32-130` — dotted-key split, nested/top-level parsing, empty-vs-unset via exit code.
- `../accelerator/scripts/accelerator-scaffold.sh:32-40` — idempotent gitignore append (`grep -qFx`).

## Architecture Insights

- **Copy `version`, scale to `launch` where needed.** `version` is the minimal
  hexagon; `launch` shows the richer variant (rich error enum + `From` into
  `kernel::Error`, `&impl Trait` ports). Config sits between: it needs a real error
  taxonomy (not-found, bad-level, malformed-frontmatter, io-error) like `launch`,
  but simple dispatch like `version`.
- **The crate split *is* the enforcement.** Once `config` (no serde/toml/fs) and
  `config-adapters` (serde/toml/fs) are separate crates, a `config → serde` edge is
  a compile-time/graph fact. cargo-deny with `bans.deny` + `wrappers` turns that
  into an explicit CI failure; `cargo tree -p config` is the human-readable check.
  cargo-pup is not involved (it is intra-crate).
- **The output contract is a domain concern, not a formatting afterthought.** The
  empty-vs-unset distinction must be modelled in the core (e.g.
  `Option<String>` / a `Resolved { Found(String), NotFound }` type) so the inbound
  adapter can map `Found("")` → print empty + exit 0 and `NotFound` → error + exit
  non-zero. Accelerator carries this in an exit code; luminosity should carry it in
  the type.
- **Thin means thin.** The AC is grep-verifiable: the skill body may contain only
  `luminosity config get`/`set` calls for config access. Accelerator's `paths`/`init`
  are the right mental model, not its `configure`.

## Historical Context

- `meta/decisions/ADR-0003-multi-level-userspace-configuration-model.md` — the config model, layout, precedence; retro-fitted 0009's paths; names 0009 as proof slice.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md` — the hexagon rule and the cargo-pup/cargo-deny enforcement split; "crate boundaries inert until first split".
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md` — the `config`/`config-adapters` shared-crate split, Model 1 composition, built-ins vs external dispatch.
- `meta/decisions/ADR-0007-skills-as-the-product.md` — skills as SKILL.md prose delegating deterministic work to the CLI.
- `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md` — the toolchain/ban-list research; source of the 2026-06-27 note added to 0009.
- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md` — the scaffold that produced the `version` hexagon template.
- `meta/research/codebase/2026-07-03-0008-static-binary-distribution-and-launcher.md` — the `${CLAUDE_PLUGIN_ROOT}/bin/luminosity` invocation contract.
- `meta/reviews/work/0009-multi-level-configuration-system-review-1.md` — existing work-item review (in the working tree).
- `meta/notes/2026-07-01-support-cli-switches-alongside-env-toggles.md` — related config/CLI-switch discussion.
- No plan, dedicated research, or validation exists for 0009 yet.

## Related Research

- `meta/research/codebase/2026-06-27-0006-rust-toolchain-guard-rails.md`
- `meta/research/codebase/2026-06-28-0007-scaffold-hexagonal-rust-workspace.md`
- `meta/research/codebase/2026-07-03-0008-static-binary-distribution-and-launcher.md`
- `meta/research/codebase/2026-07-02-0014-relocate-workspace-crates-under-cli-and-rename-launcher-crate.md`

## Open Questions

1. **Enforcement mechanism (blocking for planning).** The requirement/AC say
   `skip`/`skip-tree`; the correct mechanism is `[[bans.deny]]` + `wrappers`. Which
   way does the story go? Options: (a) correct the work item to `bans.deny` +
   `wrappers` scoping serde/toml/fs to `config-adapters` (matches the live
   native-tls ban, keeps launcher's legitimate serde use); (b) rely on the Cargo
   graph + `cargo tree -p config` as the check and drop the deny claim. Author
   decision needed; this changes the AC text and the `cli/deny.toml` edit.
2. **Does 0009 own the `.gitignore` write and `.luminosity/` scaffolding, or only
   `config get`/`set`?** In accelerator, gitignore/init is a separate `init` skill.
   The 0009 AC asserts the gitignore end-state but the story frames itself around
   the two CLI verbs + thin skill. Clarify whether a `config init` / first-write
   side effect creates `.luminosity/` and edits `.gitignore`, or whether that is
   assumed pre-existing / deferred.
3. **Nested writes.** Accelerator only writes *top-level* frontmatter fields; 0009
   needs to write `core.example` (nested). The Rust port must design nested
   frontmatter insertion/replacement (create the `core:` block if absent), which
   has no accelerator precedent — a genuine net-new piece.
4. **`set` default level.** Still flagged in the work item's Open Questions (team
   vs personal default). Settled as team for now; noted here so planning does not
   silently re-decide it.
5. **`--level` on reads.** Accelerator's base reader has no `--level`; 0009 adds it.
   Confirm the exact semantics: `--level team|personal` reads that single file
   without cross-level resolution, and an unrecognised level exits non-zero
   touching no file (AC `…:127-130`) — a new behaviour to build and test, not port.
