---
type: work-item
id: "0015"
title: "Converge the Release & Signing Process onto Accelerator's Proven Pipeline"
date: "2026-07-08T22:53:04+00:00"
author: Toby Clemson
producer: create-work-item
status: draft
kind: task
priority: high
relates_to: ["work-item:0008"]
tags: [release, signing, ci, supply-chain, minisign]
last_updated: "2026-07-08T22:53:04+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# 0015: Converge the Release & Signing Process onto Accelerator's Proven Pipeline

**Kind**: Task
**Status**: Draft
**Priority**: High
**Author**: Toby Clemson

## Summary

Luminosity's automated release and signing pipeline is fully built but has never
cut a real release and is effectively broken, while the sibling Accelerator
plugin runs a near-identical pipeline that is proven in production. Adopt the
handful of concrete divergences from Accelerator's process — signing-secret
isolation, a GitHub App releaser identity, a password-less key convention, and
an anti-leak commit guard — so Luminosity's pipeline matches the proven shape
and the two plugins stay maintainable in step. This task covers machinery
parity only; generating the production key and cutting the first live release
are a separate follow-up.

## Context

Luminosity and Accelerator share the same release architecture almost line for
line: minisign detached signatures, a prepare→finalise invoke-task split driven
by a push-to-`main` GitHub Actions workflow, four-triple `cargo zigbuild`
cross-compiles, a build-time-embedded public key (`build.rs` + `include_str!`),
committed per-platform verify shims, SLSA `attest-build-provenance`, version
coherence across `plugin.json` / `Cargo.toml` / `checksums.json` /
`manifest.json`, and a re-download-and-verify step before a release is
un-drafted.

A file-by-file comparison against Accelerator surfaced a small, specific set of
divergences where Accelerator's process is proven and Luminosity's is not:

- **Signing-secret isolation.** Accelerator signs in a dedicated `*:sign`
  workflow step — the only place the signing secret enters the environment,
  deliberately never sharing a job env with `cargo zigbuild` (which runs
  untrusted transitive build scripts). Luminosity signs *inside* `finalise`
  (`tasks/release.py` `_publish`), so `MINISIGN_SECRET_KEY` is exposed to a job
  that also compiled crates. Luminosity's own `CONTRIBUTING.md` (lines 126-133)
  already flags this as a tracked hardening follow-up.
- **Releaser identity.** Accelerator mints a GitHub App token
  (`actions/create-github-app-token`) and checks out with it so the version-bump
  push re-triggers CI. Luminosity uses the default token; a push made with the
  default `GITHUB_TOKEN` does not trigger downstream workflows — the likely
  reason Luminosity's prerelease → approve → release chain does not run
  end-to-end.
- **Key convention.** Accelerator uses a password-less keypair
  (`minisign -G -W -f`); Luminosity uses a password-protected key
  (`MINISIGN_SECRET_KEY` + `MINISIGN_KEY_PASSWORD`).
- **Anti-leak guard.** Accelerator's `_publish` runs
  `_assert_no_leaked_artifacts` (refuses to commit/tag if `.sec` or `dist/` are
  dirty) before tagging; Luminosity's has no equivalent.

## Requirements

- **Isolate the signing secret into a dedicated step.** Refactor
  `tasks/release.py` from `prepare` / `finalise` into `prepare` / `sign` /
  `finalise` (mirroring Accelerator's `_sign`), so signing is lifted out of
  `_publish` and the minisign secret enters the environment only in the `*:sign`
  step. Update the three release job sequences in `.github/workflows/main.yml`
  (prerelease, release, and the re-cut of the next prerelease line) to the
  prepare → sign → attest → finalise ordering.
- **Create and adopt a GitHub App releaser identity.** Register a Luminosity
  release GitHub App in the organisation, wire its client-ID (repo/org variable)
  and private-key secret, mint a token via `actions/create-github-app-token`,
  and check out with it so the version-bump push re-triggers CI. Replace the
  current default-token path.
- **Adopt the password-less key convention.** Move to a `minisign -G -W -f`
  keypair; remove `MINISIGN_KEY_PASSWORD` from the workflow and `tasks/`; update
  `tasks/keys.py` guidance accordingly. Name the CI secret
  `LUMINOSITY_RELEASE_SECRET_KEY`.
- **Add the anti-leak guard.** Port an `_assert_no_leaked_artifacts` equivalent
  into Luminosity's `_publish` so a release aborts before tagging if `.sec` /
  `dist/` (or Luminosity's equivalent staging path) appear dirty.
- **Systematic diff pass.** Compare both repos' release surfaces
  (`tasks/release.py`, `sign.py`/`signing.py`, `github.py`, `version.py`,
  `build.py`, `git.py`; `.github/workflows/main.yml`; the `bin/` bootstrap) and
  either close each remaining unintended divergence or record it as intentional
  in the PR description.

## Acceptance Criteria

- [ ] Given the release workflow is inspected, when tracing where the signing
      secret is set, then it appears in only the `*:sign` step and in no step
      that compiles crates.
- [ ] Given `tasks/release.py`, then `prepare`, `sign`, and `finalise` are
      distinct tasks and no signing occurs inside `_publish`; a unit test
      asserts the separation.
- [ ] Given a merge to `main` under the GitHub App identity, when the
      version-bump commit is pushed, then downstream CI (prerelease → approve →
      release) is triggered end-to-end.
- [ ] Given the release keypair, then it carries no password,
      `MINISIGN_KEY_PASSWORD` is removed everywhere, no password-prompt code
      path remains, and the CI secret is read as `LUMINOSITY_RELEASE_SECRET_KEY`.
- [ ] Given a working tree containing a `.sec` file or `dist/` artifacts, when
      `_publish` runs, then it aborts before tagging; a unit test covers this.
- [ ] Given the diff pass is complete, then every remaining divergence from
      Accelerator's release surface is either closed or documented as
      intentional in the PR.
- [ ] `mise run` (the full local CI mirror) exits 0 end-to-end.

## Open Questions

- None outstanding — the App will be created as part of this task and the
  Luminosity-specific secret name is confirmed.

## Dependencies

- Blocked by: **Organisation-admin access to register the GitHub App** and set
  its client-ID variable + private-key secret. Without the App, the releaser
  identity requirement cannot be completed.
- Relates to: 0008 (On-Demand Static-Binary Distribution & Launcher) — the
  original build-out of this pipeline; this task hardens/aligns it.
- Follow-up (out of scope): generating the production keypair, loading
  `LUMINOSITY_RELEASE_SECRET_KEY`, and cutting the first live signed release.

## Assumptions

- "Adopt their signing and release process" means adopting the CI/task
  orchestration *shape*, since the underlying crypto (minisign, embedded
  pubkey, verify shims, SLSA attestation) is already identical between the
  repos. If a deeper crypto/trust-model change was intended, scope changes.
- Luminosity has no visualiser server binary, so Accelerator's checksum-only
  server distribution path has no Luminosity counterpart and is excluded.

## Technical Notes

- Reference implementation (Accelerator): `tasks/release.py`
  (`_sign`/`_publish`/`_assert_no_leaked_artifacts`), `tasks/signing.py`
  (`resolve_secret_key`, `sign_staged_binaries`), `.github/workflows/main.yml`
  (the `*:sign` step + `actions/create-github-app-token` wiring), and
  `RELEASING.md`.
- Luminosity touch points: `tasks/release.py` (`_publish`), `tasks/sign.py`,
  `tasks/keys.py`, `tasks/git.py`, `.github/workflows/main.yml`, and
  `CONTRIBUTING.md` (Release signing section, lines 64-133, which already
  documents the signing-isolation follow-up).
- The password-less move and the App identity should land together with the
  first-release follow-up in mind: rotating to a real key is that follow-up's
  job, but the secret name and no-password expectation are set here.

## Drafting Notes

- Scope boundary drawn at "machinery parity"; the first live release cut is
  deliberately excluded per the author's decision.
- "Keep the two plugins in sync" interpreted as a point-in-time convergence
  goal, not a standing automated drift check.
- Treated the GitHub App releaser identity as in-scope "release process" even
  though the request was framed around signing — it is the most probable cause
  of the broken push-driven chain.

## References

- Related: 0008 (`meta/work/0008-on-demand-static-binary-distribution-and-launcher.md`),
  0002 (distribution/signing spike), 0007 (version subcommand groundwork)
- Reference repo: Accelerator (`../accelerator` →
  `atomic/company/accelerator`), `RELEASING.md` and `tasks/`
