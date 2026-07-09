---
type: plan-validation
id: "2026-07-09-0015-converge-release-and-signing-onto-accelerator-validation"
title: "Validation Report: Converge the Release & Signing Process onto Accelerator's Proven Pipeline"
date: "2026-07-09T08:40:06+00:00"
author: Toby Clemson
producer: validate-plan
status: complete
result: "pass"
target: "plan:2026-07-09-0015-converge-release-and-signing-onto-accelerator"
tags: [release, signing, ci, supply-chain, minisign, github-app]
last_updated: "2026-07-09T08:40:06+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

## Validation Report: Converge the Release & Signing Process onto Accelerator's Proven Pipeline

### Implementation Status

✓ Phase 1: Dedicated sign task and step; attest after sign — Fully implemented
✓ Phase 2: Anti-leak guard before tagging — Fully implemented (extracted to
  `tasks/assertions.py`)
✓ Phase 3: Password-less key convention and secret rename — Fully implemented
✓ Phase 4: GitHub App releaser identity — Fully implemented (wiring only; live
  run deferred by design)
✓ Phase 5: Diff-pass closure and documentation — Fully implemented

Each phase maps to a discrete commit:

- `37aaf8b` Split signing into a dedicated task and CI step (Phase 1)
- `d33042b` Refuse to commit when a secret or staged binary would leak (Phase 2)
- `77a5fbd` Adopt a password-less release key and rename the signing secret
  (Phase 3)
- `a5b0d92` Push the version bump under the GitHub App releaser identity
  (Phase 4)
- `93fb257` Fix the prerelease marketplace plugin name and document releasing
  (Phase 5)
- `4f55f66` Update the release public key to the new signing keypair (Phase 3/5
  key rollout)
- `9820b80` Tidy release tasks and workflow test after review

### Automated Verification Results

✓ Read-only CI mirror passes: `mise run check` (exit 0)
✓ Full tasks unit suite passes: `uv run pytest tests/unit/tasks/` (250 passed)
✓ Phase-relevant suites pass:
  `test_release.py test_workflows.py test_sign.py test_keys.py
  test_assertions.py` (41 passed)
✓ No password/secret remnants: `grep -rn "MINISIGN_KEY_PASSWORD\|MINISIGN_SECRET_KEY" tasks/ .github/`
  returns nothing
✓ No wrong-plugin call: `grep -rn 'plugin="accelerator"' tasks/` returns nothing
✓ `RELEASING.md` exists (8.7 KB); `keys/luminosity-release.pub` present and
  updated to the new keypair

Note: the heavy end-to-end `mise run` default (which additionally runs
`build:launcher` and the coverage-instrumented cli tests) was not run in full;
`mise run check` — the read-only lint/type/format + `deny:check`/`pup:check`
set — was run and is green. This change touches no Rust source, so the launcher
build carries no incremental risk; the cli unit tests are unaffected.

### Code Review Findings

#### Matches Plan:

- **Phase 1** — `_publish` (`tasks/release.py:27-35`) reads commit → tag → push →
  release with no signing; `prerelease_sign` / `release_sign` tasks
  (`:38-47`) delegate to `sign.sign`; the local `prerelease` / `release`
  wrappers chain `prepare → sign → finalise` (`:83-101`). The workflow
  (`.github/workflows/main.yml`) inserts a `Sign` step between `Prepare` and
  `Attest` in all three release sequences, with attest ordered after sign.
- **Phase 2** — The leak guard scans `git status --porcelain` against the
  Luminosity-specific markers `.key` / `cli/launcher/bin/luminosity-` /
  `manifest.minisig` and aborts before `git.commit_version`
  (`tasks/assertions.py`; called at `tasks/release.py:30`). The tracked version
  anchors `checksums.json` / `manifest.json` are deliberately not markers.
- **Phase 3** — Password-less throughout: `tasks/keys.py` always emits
  `minisign -G -W -f`, no `no_password` parameter, no `pty=True`, retains the
  `--force` overwrite guard, and prints `LUMINOSITY_RELEASE_SECRET_KEY`
  guidance with no passphrase line. `tasks/sign.py` reads
  `LUMINOSITY_RELEASE_SECRET_KEY` only; `tasks/shared/minisign.py sign()` has no
  `password` keyword or stdin plumbing. The workflow's `*:sign` steps carry the
  single `LUMINOSITY_RELEASE_SECRET_KEY` env; no `MINISIGN_*` names remain.
- **Phase 4** — Both `prerelease` and `release` jobs mint the App token via
  `create-github-app-token` (pinned by SHA, id `app-token`) referencing
  `vars.LUMINOSITY_RELEASER_CLIENT_ID` + `secrets.LUMINOSITY_RELEASER_SECRET`,
  and their Checkout steps consume `${{ steps.app-token.outputs.token }}`.
- **Phase 5** — `prerelease_prepare` passes `plugin="luminosity"`
  (`tasks/release.py:56`); `RELEASING.md` authored and accurate to the
  post-convergence pipeline, key lifecycle, App identity, environments, and
  recovery triage; `CONTRIBUTING.md` corrected to describe a step-level (not
  job-level) signing isolation and the password-less convention.
- **Tests** — `test_workflows.py` structurally asserts the
  `prepare → sign → attest → finalise` ordering, secret-only-on-sign-steps, the
  `LUMINOSITY_RELEASE_SECRET_KEY` reference, the App-token wiring, and rejects
  two known-bad step shapes (secret leaked onto a prepare step; attest moved
  before sign). `test_assertions.py` covers the leak guard's three scenarios.

#### Deviations from Plan (all neutral or improvements):

- **Leak guard relocated and promoted.** The plan sketched a private
  `_assert_no_leaked_artifacts` inline in `tasks/release.py`; the
  implementation extracted it to `tasks/assertions.py` as a public
  `no_leaked_artifacts` invoke `@task`. Cleaner separation; its behavioural
  tests moved to `test_assertions.py` (the exact secret/binary/anchor cases the
  plan specified for `test_release.py`), while `test_release.py` retains a
  guard-ordering test. Behaviour is unchanged and fully covered.
- **Docstrings say "part 2/part 3"** rather than the plan's "step 2/step 3" for
  the sign/finalise tasks. Cosmetic.

#### Potential Issues (minor):

- **Doc drift in `RELEASING.md:129`** — the leak-guard paragraph still names
  `_assert_no_leaked_artifacts`, the pre-extraction inline name. The shipped
  code exposes `assertions.no_leaked_artifacts`. Purely cosmetic, but the
  runbook should name the real symbol. (The other stale references are in
  `meta/work/0015-...md`, a historical work item — leave as-is.)

### Manual Testing Required:

1. First-release follow-up (explicitly out of scope of this plan):
  - [ ] Provision the production secret under `LUMINOSITY_RELEASE_SECRET_KEY`,
    then confirm the next push to `main` runs the `prerelease` job green with
    the bump commit pushed past the ruleset under the App identity and a signed
    prerelease published and re-verified.
  - [ ] Confirm the pushed bump commit's author is the App identity, not the
    default Actions bot.
2. PR authoring:
  - [ ] The PR description lists each recorded intentional divergence
    (manifest folded into `tasks/sign.py`; no server/visualiser path;
    `--force` guard retained; `upload_and_verify` naming; `.key` vs `.sec`;
    `tasks/shared/minisign.py` wrapper).

These two open items are the plan's own remaining `[ ]` boxes — the first is
deferred to the first-release follow-up by design; the second is a PR-authoring
step, not a code deliverable. Neither blocks a `pass`.

### Recommendations:

- Fix the `RELEASING.md:129` symbol name to `assertions.no_leaked_artifacts` on
  the next docs touch (or fold it into the PR).
- When authoring the PR, carry the recorded intentional-divergence list from
  Phase 5 so reviewers see each Accelerator delta is deliberate.
- Track the first-signed-release follow-up as its own work item so the deferred
  live verification is not lost.
</content>
