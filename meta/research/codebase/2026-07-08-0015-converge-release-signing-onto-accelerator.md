---
type: codebase-research
id: "2026-07-08-0015-converge-release-signing-onto-accelerator"
title: "Research: Converging Luminosity's Release & Signing Process onto Accelerator's Proven Pipeline"
date: "2026-07-08T22:58:34+00:00"
author: "Toby Clemson"
producer: research-codebase
status: complete
work_item_id: "0015"
parent: "work-item:0015"
relates_to: ["codebase-research:2026-07-03-0008-static-binary-distribution-and-launcher"]
topic: "Converging Luminosity's release & signing process onto Accelerator's proven pipeline"
tags: [research, codebase, release, signing, ci, supply-chain, minisign, github-app]
revision: "cc91a839c0ab90c727e25aa785ff97962b44f200"
repository: "luminosity"
last_updated: "2026-07-08T22:58:34+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# Research: Converging Luminosity's Release & Signing Process onto Accelerator's Proven Pipeline

**Date**: 2026-07-08T22:58:34+00:00 (UTC)
**Author**: Toby Clemson
**Git Commit**: cc91a839c0ab90c727e25aa785ff97962b44f200
**Branch**: (detached / jj working copy — see `jj log`)
**Repository**: luminosity

## Research Question

For work item `0015` — "Converge the Release & Signing Process onto Accelerator's
Proven Pipeline" — establish the precise current shape of Luminosity's release and
signing surface, the precise shape of Accelerator's proven equivalent, and every
concrete divergence between them. The task names four target divergences
(signing-secret isolation, a GitHub App releaser identity, a password-less key
convention, an anti-leak guard) plus a systematic diff pass; this research verifies
each against live code and surfaces additional divergences and nuances that will
shape the implementation plan.

## Summary

The two pipelines are architecturally near-identical, exactly as the work item
states. All four named divergences are **confirmed against live code**, but three
carry material nuances that change how the plan should be scoped:

1. **Signing-secret isolation** — Accelerator has a **three-way
   `prepare → sign → finalise`** task split; the signing secret enters only in a
   dedicated `*:sign` step, and `_sign` is documented as "the only task that
   receives the signing secret." Luminosity has a **two-way `prepare → finalise`**
   split and signs *inside* `_publish` (`tasks/release.py:20`), invoked from the
   `*_finalise` tasks. **Nuance:** Luminosity already scopes the secret at the
   *step* level — the minisign env vars sit only on the workflow's "Finalise" steps,
   never on the "Prepare" steps that run `cargo zigbuild`. So Luminosity already
   satisfies "the secret never shares an env with compilation." What it lacks is a
   *dedicated sign step* separate from the publish logic, and the matching
   `prepare → sign → attest → finalise` ordering. This also fixes a real ordering
   divergence: **Luminosity attests *before* signing** (prepare → attest →
   finalise-that-signs); Accelerator attests *after* signing (prepare → sign →
   attest → finalise).

2. **Releaser identity** — Confirmed: Accelerator mints a GitHub App token
   (`actions/create-github-app-token`) and checks out with it; Luminosity uses the
   default `GITHUB_TOKEN` with no `with:` block. **Important nuance:** the work
   item's stated rationale ("a default-token push does not trigger downstream
   workflows") is imprecise — **both repos put `[skip ci]` in the version-bump
   commit message** (`tasks/git.py:74` in each), so the bump push is deliberately
   *not* the re-trigger mechanism in either repo, and the `prerelease → approve →
   release` chain runs as `needs:`-linked jobs *within a single workflow run*. The
   App identity's real necessity is almost certainly **push authorization under
   `main` branch protection** (a default `GITHUB_TOKEN` cannot push the bump commit
   through required-review branch protection; a GitHub App on the bypass list can).
   This reframing should be validated during planning — see Open Questions.

3. **Key convention** — Confirmed: Accelerator generates a **password-less** key
   (`minisign -G -W -f`) and reads only `ACCELERATOR_RELEASE_SECRET_KEY` (no
   password variable anywhere). Luminosity generates a **password-protected** key
   by default and threads `MINISIGN_KEY_PASSWORD` through every signing call.
   **Nuance:** Luminosity's `keys.generate` *already* supports a `--no-password`
   flag that appends `-W` (`tasks/keys.py:38-40`) — the machinery exists; the work
   is flipping the convention, ripping out the password plumbing, and renaming the
   CI secret to `LUMINOSITY_RELEASE_SECRET_KEY`.

4. **Anti-leak guard** — Confirmed absent in Luminosity. Accelerator's
   `_assert_no_leaked_artifacts` (`tasks/release.py:38-49`) runs `git status
   --porcelain`, refuses to proceed if any line contains `.sec`, `dist/release/`,
   or `dist/`, and is the **first** call in `_publish` (before commit/tag/push).
   Luminosity has no equivalent, and its `git.commit_version` does a blanket
   `git add .` (`tasks/git.py`), so a stray artifact *would* be swept into the bump
   commit. **Nuance:** Luminosity's markers differ — its secret file uses the
   **`.key`** extension (not `.sec`), and its staging path is whatever
   `tasks/shared/paths.py` defines (not read in this pass).

**Additional divergences found by the diff pass** (Requirement 5): Accelerator has
a standalone `tasks/manifest.py` that Luminosity folds into `tasks/sign.py`;
Luminosity attests before signing; the two repos use different secret-file
extensions; and Luminosity tracks a `manifest.json` version anchor Accelerator only
optionally checks. Most are intentional consequences of Luminosity having a single
launcher with no dispatched sub-binaries and no server. Details in
[Additional Divergences](#component-area-7-additional-divergences-from-the-diff-pass).

## Detailed Findings

### [Component/Area 1] Luminosity release orchestration — `tasks/release.py`

Two-way split with signing folded into publish.

- **`_publish(context)`** (`tasks/release.py:18-26`) is the shared publish sequence,
  and signing is its **first** step:
  1. `version.check(context)` — `:19`
  2. `sign.sign(context)` — `:20` ← **signing happens here**
  3. `git.commit_version(context)` — `:22`
  4. `git.tag_version(context)` — `:23`
  5. `git.push(context)` — `:24`
  6. `github.create_release(...)` — `:25`
  7. `github.upload_and_verify(...)` — `:26`
- Tasks: `prerelease_prepare` (`:29-36`) and `release_prepare` (`:45-53`) run
  `build.release(context)` (the four-triple compile); `prerelease_finalise`
  (`:39-42`) and `release_finalise` (`:56-59`) call `_publish` only.
- `_refuse_under_ci(task_name)` (`:8-15`) raises if `GITHUB_ACTIONS`/`CI` is set,
  forcing CI onto the prepare/finalise split (identical to Accelerator's guard).
- Local-dev wrappers `prerelease` (`:62-67`) and `release` (`:70-77`) chain
  prepare+finalise in one process (the `release` wrapper also re-cuts the next
  prerelease line).
- **No anti-leak guard** exists in `release.py`, `sign.py`, or `keys.py`.

### [Component/Area 2] Luminosity signing & keys — `tasks/sign.py`, `tasks/keys.py`

- **Secret entry** (`tasks/sign.py`): `_SECRET_KEY_ENV = "MINISIGN_SECRET_KEY"`
  (`:25`), `_KEY_PASSWORD_ENV = "MINISIGN_KEY_PASSWORD"` (`:26`), both read inside
  the `sign` task (`:103`, `:106`); absent secret raises `Exit` (`:104-105`).
- The secret is materialised to a mode-`0600` `release.key` inside a
  `tempfile.TemporaryDirectory` (`:107-110`), used to sign each staged binary
  (`sign_binaries`, `:72-82`), write the manifest (`write_manifest`, `:85-93`),
  then sign the manifest itself (`:113-115`). The `password` is threaded to every
  `minisign.sign(...)` call.
- Luminosity builds and signs its `manifest.json` **inside `sign.py`**
  (`build_manifest` `:29-54`, `write_manifest` `:85-93`) — no separate manifest
  module.
- **`tasks/keys.py`** `generate` task (`:9-55`) runs
  `minisign -G -f -p <pub> -s <sec>` (`:30-42`), appending **`-W` only when
  `no_password=True`** (`:38-40`), `pty=True` for the interactive passphrase. It
  prints guidance to store the secret in `MINISIGN_SECRET_KEY` and its passphrase
  in `MINISIGN_KEY_PASSWORD`. So the password-less machinery is already present but
  is not the default.

### [Component/Area 3] Luminosity CI workflow — `.github/workflows/main.yml`

Three release-related jobs plus an approval gate; each release sequence is a
**prepare → attest → finalise** trio (note: attest is *before* the signing, which
lives inside finalise).

- **`prerelease`** job (`:240-293`), `macos-latest`, `needs:` all eight check jobs,
  `concurrency: luminosity-release` (`cancel-in-progress: false`, `queue: max`),
  `permissions: id-token/contents/attestations: write`. Steps: Checkout (`:268-269`)
  → mise (`:271-276`) → **Prepare prerelease** `mise run prerelease:prepare`
  (`:278-281`) → **Attest** `attest-build-provenance`, subject
  `cli/launcher/bin/luminosity-*` (`:283-286`) → **Finalise prerelease**
  `mise run prerelease:finalise` (`:288-293`).
- **`approve-release`** job (`:295-303`), `environment: release` — the gate is the
  environment's protection rules, body is a no-op echo.
- **`release`** job (`:305-367`), `needs: approve-release`, deliberately **no**
  `environment` block (so the lock does not enclose the Waiting job). Contains
  **both** the stable cut (Prepare/Attest/Finalise stable, `:335-350`) and the
  post-stable prerelease re-cut (`:352-367`) as consecutive step trios in one job.
- **Signing secret env** (`MINISIGN_SECRET_KEY`, `MINISIGN_KEY_PASSWORD`) appears
  **only on the three "Finalise" steps** (`:288-293`, `:345-350`, `:362-367`),
  never on Prepare (compile) steps. So the secret already never shares an env with
  `cargo zigbuild`.
- **Token**: every job checks out with `actions/checkout@…v5` and **no `with:`
  block** (`:268-269`, `:325-326`) → default `GITHUB_TOKEN`, default
  `persist-credentials`. `gh` calls use `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}`.
  **No `actions/create-github-app-token` anywhere.**
- **Cross-compile**: four triples via `cargo zigbuild --release --bin
  {LAUNCHER_CRATE} --target {triple}` inside `build.py:release` (`:200-225`), run by
  the Prepare steps.

### [Component/Area 4] Accelerator release orchestration — `tasks/release.py`, `tasks/signing.py`

The reference three-way split.

- **Six CI tasks**: `prerelease_prepare/_sign/_finalise` (`:82-107`) and
  `release_prepare/_sign/_finalise` (`:110-139`); wrappers `prerelease` (`:145-151`)
  and `release` (`:154-167`, runs stable lane then a fresh prerelease lane).
- **`_sign`** (`:52-66`): "The only task that receives the signing secret." Opens
  `signing.resolve_secret_key()` as a context manager, signs staged binaries, emits
  the signed manifest — all scoped to the `with` block.
- **`_publish`** (`:69-76`): reads version → **`_assert_no_leaked_artifacts`
  (`:71`, first)** → `git.commit_version`/`tag_version`/`push` → `create_release`
  → `upload_and_verify_release`. **Never references signing.**
- **`_assert_no_leaked_artifacts`** (`:38-49`, markers at `:20`):
  `_ARTIFACT_MARKERS = (".sec", "dist/release/", "dist/")`; greps `git status
  --porcelain`; raises `RuntimeError` on any offender before any commit/tag.
- **`signing.py`**: `SECRET_KEY_ENV = "ACCELERATOR_RELEASE_SECRET_KEY"` (`:20`),
  **no password variable**. `sign_file` runs `minisign -S -s <key> -x <sig> -m
  <target>` (`:24-34`) — no `-W`, no password on stdin. `resolve_secret_key`
  (`:71-95`) is a `@contextmanager` that materialises the env secret to a mode-0600
  `release.sec` temp file (CI path) or yields a local dev key, failing closed if
  neither exists. `generate` (`:98-129`) runs `minisign -G -W -f -p <pub> -s <sec>`
  (`:113`) — **password-less by design**.

### [Component/Area 5] Accelerator CI workflow & docs — `.github/workflows/main.yml`, `RELEASING.md`

- **Ordering is `prepare → sign → attest → finalise`** in every cycle. Prerelease
  job steps: App token (`:377-382`) → Checkout w/ token (`:384-387`) → mise →
  cache → Prepare (`:407-410`) → **Sign** (`:415-418`) → Attest (`:420-426`) →
  Finalise (`:427-430`). The `release` job runs two full cycles (stable then
  post-stable prerelease) in one locked job (`:522-564`).
- **Dedicated `*:sign` steps** carry *only*
  `env: ACCELERATOR_RELEASE_SECRET_KEY: ${{ secrets.ACCELERATOR_RELEASE_SECRET_KEY }}`;
  in-workflow comment (`:412-414`) states the secret is deliberately absent during
  the `cargo zigbuild` Prepare step. No password variable exists.
- **GitHub App token** (`:377-382`, `:486-491`): `actions/create-github-app-token`
  with `client-id: ${{ vars.ACCELERATOR_RELEASER_CLIENT_ID }}` and
  `private-key: ${{ secrets.ACCELERATOR_RELEASER_SECRET }}`; checkout consumes
  `steps.app-token.outputs.token` (`:384-387`, `:493-496`).
- **`RELEASING.md`** documents the whole procedure, the `prepare→sign→attest→
  finalise` shape, `minisign -G -W -f` password-less key generation
  (`gh secret set ACCELERATOR_RELEASE_SECRET_KEY < keys/accelerator-release.sec`),
  the strict pub-key rollout sequence, required-review-as-signing-control, the
  `release`/`prerelease` Environments, and out-of-band SLSA verification.
- **Secret/variable names**: `ACCELERATOR_RELEASE_SECRET_KEY` (signing),
  `ACCELERATOR_RELEASER_SECRET` (App private key), `vars.ACCELERATOR_RELEASER_CLIENT_ID`
  (App client id), `GITHUB_TOKEN` (gh calls).

### [Component/Area 6] Luminosity release documentation — `CONTRIBUTING.md`

- **No `RELEASING.md` and no `docs/` directory exist** — `CONTRIBUTING.md`
  (lines 64-133) is the sole release/signing doc. This is itself a divergence:
  Accelerator has a dedicated 14 KB `RELEASING.md`.
- Lines **126-133** ("Signing/build isolation (known follow-up)") already flag the
  isolation work — but frame it as splitting signing into a **separate CI job that
  consumes built artefacts via job artifacts**. **This over-states what Accelerator
  actually does**: Accelerator uses a separate *step* (secret per-step scoped), not
  a separate *job* with artifact passing. The work item correctly scopes to the
  Accelerator step-shape; the plan should not over-engineer a separate job.
- Documents only the **password-protected** convention (line 79 "choose a strong
  passphrase"; secrets `MINISIGN_SECRET_KEY` + `MINISIGN_KEY_PASSWORD`, lines
  82-84). No mention of a GitHub App releaser identity or default-token limits.
- Contains the branch-protection required-checks runbook (lines 7-62), the key-
  rotation overlap-window model (98-104), compromise response (106-111), and the
  vendored verify-shim policy (119-124) — all of which have Accelerator analogues in
  `RELEASING.md` and should be carried into any new Luminosity `RELEASING.md`.

### [Component/Area 7] Additional divergences from the diff pass

Beyond the four named divergences (Requirement 5 asks for these to be closed or
recorded as intentional):

- **Manifest module structure** — Accelerator has a standalone `tasks/manifest.py`
  (dispatch manifest for its sub-binaries: `collect_entries`, `build_manifest`,
  `emit_manifest`); Luminosity folds manifest building into `tasks/sign.py`.
  *Likely intentional*: Luminosity ships a single launcher with **no dispatched
  sub-binaries**, so a full dispatch-manifest module is unnecessary. Record as
  intentional.
- **Attestation ordering** — Luminosity attests **before** signing; Accelerator
  attests **after** signing. *Closed by* the sign-step refactor (Requirement 1),
  which reorders to `prepare → sign → attest → finalise`.
- **Secret-file extension** — Accelerator `.sec`, Luminosity `.key`. Matters for
  the anti-leak guard's marker list (must use `.key` for Luminosity).
- **`github` finalise function name** — `upload_and_verify` (Luminosity) vs
  `upload_and_verify_release` (Accelerator). Cosmetic; both re-download and
  re-verify every asset before the single `--draft=false` undraft, preserving the
  draft+tag on `AssetVerificationError` and deleting the tag on other errors.
- **Version anchors** — Luminosity's `version.write` updates four anchors including
  `manifest.json` (`tasks/version.py:80-95`); Accelerator updates plugin.json,
  server + workspace `Cargo.toml`, checksums.json (manifest.json only optionally).
  *Intentional* — different product shapes (Luminosity's version-bearing crate is
  `cli/launcher/Cargo.toml`; Accelerator has a server crate).
- **No server / visualiser** — Accelerator cross-compiles a server + frontend;
  Luminosity has neither. Per the work item's stated assumption, the checksum-only
  server distribution path is excluded. *Intentional.*
- **Minisign invocation** — Accelerator calls `minisign` directly via `subprocess`
  in `signing.py`; Luminosity wraps it in `tasks/shared/minisign.py`
  (`minisign.sign(...)`). Structural, not behavioural.

## Code References

### Luminosity (target of change)
- `tasks/release.py:18-26` — `_publish`; **signing is folded in at `:20`**
- `tasks/release.py:8-15` — `_refuse_under_ci`
- `tasks/sign.py:25-26,103-115` — minisign secret + password env, temp-key signing
- `tasks/sign.py:29-54,85-93` — in-module manifest build/write
- `tasks/keys.py:30-42` — `minisign -G -f` (+`-W` only when `--no-password`)
- `tasks/git.py:67-74` — `commit_version` with `git add .` + `[skip ci]`
- `tasks/git.py:35-52` — `push` (atomic branch+tag)
- `tasks/github.py:182-244` — `upload_and_verify` (re-verify, undraft)
- `tasks/version.py:80-95` — four-anchor `write` (incl. manifest.json)
- `tasks/build.py:200-225` — four-triple `cargo zigbuild` release build
- `.github/workflows/main.yml:240-293` — `prerelease` job (prepare→attest→finalise)
- `.github/workflows/main.yml:305-367` — `release` job (stable + post-stable re-cut)
- `.github/workflows/main.yml:288-293,345-350,362-367` — minisign secret env (Finalise only)
- `bin/luminosity` — fail-closed bootstrap: fetch + minisign-verify launcher per exec
- `CONTRIBUTING.md:64-133` — sole release/signing doc; **126-133** isolation follow-up

### Accelerator (reference)
- `tasks/release.py:52-66` — `_sign` (sole secret-receiving task)
- `tasks/release.py:38-49` + `:20` — `_assert_no_leaked_artifacts` + markers `(".sec","dist/release/","dist/")`
- `tasks/release.py:69-76` — `_publish` (leak-guard first, no signing)
- `tasks/signing.py:20,71-95` — `ACCELERATOR_RELEASE_SECRET_KEY`, `resolve_secret_key` ctx-manager
- `tasks/signing.py:98-129` — password-less `minisign -G -W -f`
- `tasks/manifest.py` — standalone dispatch-manifest module (no Luminosity peer)
- `.github/workflows/main.yml:377-387,486-496` — App token mint + checkout-with-token
- `.github/workflows/main.yml:415-418,527-530,549-552` — dedicated `*:sign` steps
- `RELEASING.md` — full documented procedure

## Architecture Insights

- **The convergence is a *shape* change, not a crypto change.** Both repos already
  share minisign detached signatures, an embedded public key (`build.rs` +
  `include_str!`), committed per-platform verify shims, SLSA attestation, four-anchor
  version coherence, and a re-download-and-verify-before-undraft gate. The work is in
  task decomposition, secret handling, and CI identity — matching the work item's
  "machinery parity only" scope.
- **Luminosity is closer than the work item's framing suggests.** Step-level secret
  scoping already keeps the minisign key out of the compile environment; the
  `--no-password` key path already exists in `keys.generate`; the finalise re-verify
  gate already exists. The delta is: (a) lift signing into its own `sign` task/step
  and reorder attest after it, (b) add the leak guard, (c) flip the password default
  and rename the secret, (d) add the App identity.
- **The `[skip ci]` finding reframes the App-identity rationale.** Because both repos
  mark the bump commit `[skip ci]` and chain `prerelease → approve → release` via
  `needs:` inside one workflow run, the App token is not needed to "re-trigger
  downstream CI." Its plausible real role is authorizing the bump *push* under `main`
  branch protection. The plan should confirm this before assuming the App fixes the
  broken end-to-end chain — the true failure may be a push rejected by branch
  protection, or an unrelated failure in an earlier step.
- **Documentation parity is an implicit divergence.** Accelerator's `RELEASING.md`
  is the operational source of truth; Luminosity has only a `CONTRIBUTING.md` section
  whose isolation note *mis-describes* the target (separate job vs separate step).
  Converging likely means authoring a Luminosity `RELEASING.md` and correcting that
  note.
- **Anti-leak markers must be Luminosity-specific.** Accelerator keys on `.sec` +
  `dist/`; Luminosity secrets use `.key` and stage elsewhere (`tasks/shared/paths.py`,
  not read here). The guard must key on Luminosity's actual extensions/paths, and it
  matters because `commit_version` does a blanket `git add .`.

## Historical Context

- `meta/decisions/ADR-0002-zero-setup-static-binary-distribution.md` — foundational
  decision to ship prebuilt statically-linked binaries; "sha256 alone is not trust,
  in-process signature verification is" underpins the whole signing model.
- `meta/decisions/ADR-0010-git-style-modular-cli-of-on-demand-static-binaries.md` —
  the on-demand fetch/launcher model; frames why Luminosity's manifest is simpler.
- `meta/decisions/ADR-0009-thin-cli-over-a-hexagonal-ports-and-adapters-core.md` —
  the workspace/version-subcommand structure.
- `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md` (in-progress)
  — the primary build-out of this pipeline; `0015` hardens/aligns it.
- `meta/plans/2026-07-03-0008-static-binary-distribution-and-launcher.md` — richest
  source on the current pipeline's design (67 signing/distribution mentions).
- `meta/research/codebase/2026-07-03-0008-static-binary-distribution-and-launcher.md`
  — prior codebase research on the launcher/minisign/zigbuild/SLSA surface.
- `meta/reviews/plans/2026-07-03-0008-…-review-1.md` and the matching work-item review
  — quality lenses already applied to this pipeline.
- `meta/work/0002-…` (done) — the distribution/signing spike; `0007` — version
  subcommand; `0014` — launcher-crate relocation/rename.

## Related Research

- `meta/research/codebase/2026-07-03-0008-static-binary-distribution-and-launcher.md`
  — the immediate predecessor; this research extends it with the Accelerator
  comparison.

## Open Questions

1. **Is a rejected bump *push* (not downstream triggering) the real reason
   Luminosity's chain doesn't run end-to-end?** Given both repos use `[skip ci]` and
   chain jobs via `needs:` in one run, confirm during planning whether the default
   `GITHUB_TOKEN` is blocked by `main` branch protection when pushing the version
   bump — which the App identity would fix — versus some other failure. Consider
   checking a failed Actions run's logs for the actual failure point.
2. **What are Luminosity's exact leak-guard markers?** `tasks/shared/paths.py` was
   not read in this pass; the guard needs Luminosity's real staging directory plus
   the `.key` extension (and `.gitignore` already blocks `*.key`).
3. **Should the `*:sign` isolation be a separate step (Accelerator's actual shape)
   or the separate *job* CONTRIBUTING.md currently describes?** The work item scopes
   to the step-shape; confirm and correct the CONTRIBUTING.md note accordingly.
4. **Does converging include authoring a Luminosity `RELEASING.md`?** Accelerator's
   is the operational source of truth; Luminosity has none. Decide whether doc parity
   is in scope for `0015` or a follow-up.
5. **GitHub App provisioning is a hard external dependency** (work item Dependencies):
   the App must be registered with `LUMINOSITY_RELEASER_CLIENT_ID` (var) +
   `LUMINOSITY_RELEASER_SECRET` (secret) — naming to mirror Accelerator — before the
   identity requirement can be completed.
