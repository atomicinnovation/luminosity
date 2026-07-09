---
type: pr-description
id: "17"
title: "[0015] Converge release process with accelerator"
date: "2026-07-09T08:03:09+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "0015"
parent: "work-item:0015"
relates_to: ["work-item:0008"]
pr_url: "https://github.com/atomicinnovation/luminosity/pull/17"
pr_number: 17
tags: [release, signing, ci, supply-chain, minisign, github-app]
revision: "1d9e6b0fa76377d8fe101f76b11dea3c9b137a5e"
repository: "luminosity"
last_updated: "2026-07-09T08:57:51+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# [0015] Converge release process with accelerator

## Summary

Luminosity's release pipeline was architecturally near-identical to Accelerator's proven one but diverged in a handful of handling details and carried one latent bug. This PR converges the *shape* — not the crypto — onto Accelerator's: signing is lifted into a dedicated task and CI step (attesting after it), an anti-leak guard is added before tagging, the key becomes password-less with the `LUMINOSITY_RELEASE_SECRET_KEY` secret name, the already-provisioned GitHub App releaser identity is wired into the workflow, and the remaining diff-pass items (including a wrong-plugin marketplace call) are closed, with a new `RELEASING.md` runbook authored.

## Changes

- **Dedicated sign step (Phase 1).** Split the two-way `prepare → finalise` release into `prepare → sign → attest → finalise`. New `prerelease:sign` / `release:sign` tasks and mise entries call `sign.sign`; `_publish` no longer signs. The workflow now runs a dedicated `*:sign` step whose `env:` carries the signing secret and nothing else, sitting after prepare (build) and before attest — so signing happens *before* attestation and the secret never shares an environment with crate compilation.
- **Anti-leak guard (Phase 2).** A new `tasks/assertions.py` module exposes `no_leaked_artifacts`, which `_publish` calls before committing the version bump: it runs `git status --porcelain` and refuses to proceed if any dirty line matches Luminosity's markers (`.key`, `cli/launcher/bin/luminosity-`, `manifest.minisig`), so a stray secret or staged binary can't be swept into the blanket `git add .` version-bump commit. The tracked `checksums.json` / `manifest.json` anchors do not trip it.
- **Password-less key + secret rename (Phase 3).** `keys:generate` now always produces a password-less key (`minisign -G -W`, non-interactive, keeping the `--force` refuse-overwrite guard). All password plumbing is removed from `tasks/sign.py`, `tasks/shared/minisign.py`, and `tasks/keys.py`; the CI secret is renamed to `LUMINOSITY_RELEASE_SECRET_KEY` and `MINISIGN_SECRET_KEY` / `MINISIGN_KEY_PASSWORD` are gone from `tasks/` and `.github/`.
- **GitHub App releaser identity (Phase 4).** The `prerelease` and `release` jobs mint an App token via `actions/create-github-app-token` (from `vars.LUMINOSITY_RELEASER_CLIENT_ID` / `secrets.LUMINOSITY_RELEASER_SECRET`) and check out with it, so the version-bump push is authorized past `main`'s protection ruleset. `gh` calls keep using `GITHUB_TOKEN`; only the checkout's persisted push credential changes.
- **Diff-pass closure + docs (Phase 5).** Fixed the latent bug where `prerelease_prepare` passed `plugin="accelerator"` (so the prerelease marketplace ref was never bumped) — it now passes `plugin="luminosity"`. Authored a new `RELEASING.md` operational runbook and slimmed the `CONTRIBUTING.md` signing section down to a pointer plus the corrected step-level (not separate-job) isolation note.
- **New signing keypair.** Replaced the placeholder committed public key at `keys/luminosity-release.pub` with the public half of a fresh password-less keypair.

### Intentional divergences from Accelerator

These differences are deliberate consequences of Luminosity shipping a single launcher (no dispatched sub-binaries, no server/visualiser), not gaps:

- Manifest building is folded into `tasks/sign.py` — there is no standalone `tasks/manifest.py`. `manifest.json` describes one `luminosity` entry across the four platforms.
- No server/visualiser cross-compile or checksum-only distribution path.
- `keys.generate` retains Luminosity's `--force` refuse-overwrite guard, a safety improvement over Accelerator's always-`-f` generator.
- `github.upload_and_verify` vs Accelerator's `upload_and_verify_release` (name only; identical re-verify-before-undraft behaviour).
- Secret-file extension `.key` (Luminosity) vs `.sec` (Accelerator); reflected in the leak-guard markers.
- Minisign is wrapped in `tasks/shared/minisign.py` rather than called inline.

## Context

Implements work item **0015** ("Converge the Release & Signing Process onto Accelerator's Proven Pipeline"), following the plan `meta/plans/2026-07-09-0015-converge-release-and-signing-onto-accelerator.md` and research `meta/research/codebase/2026-07-08-0015-converge-release-signing-onto-accelerator.md` (both added in this PR). Relates to work item 0008 (static binary distribution and launcher). Each phase is independently mergeable and was driven test-first. The completed implementation was validated (result: **pass**) — see `meta/validations/2026-07-09-0015-converge-release-and-signing-onto-accelerator-validation.md`.

## Testing

- [x] Unit tests updated/added across `test_release.py`, `test_assertions.py`, `test_sign.py`, `test_keys.py`, and `test_workflows.py` (dedicated sign step ordered before attest; secret only on sign steps; leak guard aborts on dirty secret/binary and passes on anchor-only changes; password-less signing/generation; App-token step + checkout token in both release jobs; `plugin="luminosity"`).
- [x] No `MINISIGN_KEY_PASSWORD` / `MINISIGN_SECRET_KEY` remnants: `grep -rn "MINISIGN_KEY_PASSWORD\|MINISIGN_SECRET_KEY" tasks/ .github/` returns nothing.
- [x] No wrong-plugin call remains: `grep -rn 'plugin="accelerator"' tasks/` returns nothing.
- [x] Full CI on the head commit is green — unit and integration tests on both OSes, both launcher builds, and the cli, architecture, supply-chain, build-system, and scripts checks all pass. (The `prerelease` / `release` / `approve-release` jobs are correctly skipped on a PR; they run only on push to `main`.)
- [ ] **Post-merge, requires a loaded signing secret:** the next push to `main` runs the `prerelease` job green — the bump commit pushes past the ruleset under the App identity and a signed prerelease is published and re-verified. This is the deferred first-release follow-up; the workflow wiring itself is complete and unit-verified now.

## Notes for Reviewers

- The CI secret rename is a **breaking change to the deploy environment**: the production secret must be provisioned under `LUMINOSITY_RELEASE_SECRET_KEY` (not `MINISIGN_SECRET_KEY`), and no `MINISIGN_KEY_PASSWORD` is needed. Any pre-generated password-protected secret is incompatible — the first-release follow-up generates a fresh password-less keypair and re-embeds the public half.
- Signing/build isolation here is at the **step** level (a dedicated `*:sign` step with a per-step-scoped secret), not a separate job with artifact passing. This is a deliberate, documented choice — see the note in `CONTRIBUTING.md` and the runbook in `RELEASING.md`.
- Worth a close read: `.github/workflows/main.yml` (step ordering and secret scoping across all three release sequences), `tasks/release.py` (the leak guard and the `_publish` reordering), and the new `RELEASING.md`.
