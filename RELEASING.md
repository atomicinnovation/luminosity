# Releasing Luminosity

This document is the operational runbook for cutting a Luminosity release:
how the pipeline is shaped, how the signing key and releaser identity are
provisioned, and how to recover when a run fails part-way. Day-to-day
engineering conventions live in `CLAUDE.md`; the branch-protection
required-checks runbook lives in `CONTRIBUTING.md`.

## The pipeline at a glance

A release is cut by pushing to `main`. The workflow
(`.github/workflows/main.yml`) runs the guard-rail jobs, then a linear
`prerelease → approve-release → release` chain wired by `needs:`. Each release
job runs one or more sequences of four steps:

```text
prepare → sign → attest → finalise
```

- **prepare** (`mise run {prerelease,release}:prepare`) bumps the version,
  updates the marketplace refs and changelog, and cross-builds the four
  release triples, computing their checksums. It never sees the signing secret.
- **sign** (`mise run {prerelease,release}:sign`) detach-signs each staged
  binary, assembles `manifest.json`, and signs the manifest. **This is the only
  step that receives `LUMINOSITY_RELEASE_SECRET_KEY`** — the secret is scoped to
  this step's `env:` alone, so a compromised build dependency in the prepare
  step never sits in the same environment as the key.
- **attest** (`actions/attest-build-provenance`) records SLSA provenance for
  the signed binaries.
- **finalise** (`mise run {prerelease,release}:finalise`) runs the leak guard,
  commits the version bump, tags, pushes, creates the draft GitHub release,
  uploads every asset, re-downloads and re-verifies each one against the
  committed public key, and only then un-drafts.

The `prerelease` job runs one such sequence. The `release` job runs two: the
stable release, then a post-stable prerelease re-cut so `main` always carries a
prerelease ahead of the last stable tag.

### One launcher, one manifest

Luminosity ships a single launcher binary per platform — there are no
dispatched sub-binaries and no separate server or visualiser. `manifest.json`
therefore describes one `luminosity` entry across the four platforms, and
manifest assembly lives inside `tasks/sign.py` rather than a standalone
`tasks/manifest.py`. Every release publishes, per platform: the binary, its
`.debug.tar.gz`, and its detached `.minisig`; plus the signed `manifest.json`
(`manifest.minisig`).

## Signing key lifecycle

Releases are integrity-protected with **minisign** (a bare SHA-256 is not
trust; in-process signature verification against a committed public key is).
The single public key committed at `keys/luminosity-release.pub` is the one
source of truth: the bootstrap ships it and `cli/launcher/build.rs` embeds it
into the launcher at build time, so the two never diverge.

### Provisioning the production key (before the first real release)

The committed public key is currently a **placeholder** generated during
implementation. Replace it before cutting a real release:

1. Generate the production keypair: `mise run keys:generate --force`. It is
   **password-less** (`minisign -G -W`) and non-interactive — there is no
   passphrase to choose. It writes the public key to
   `keys/luminosity-release.pub` (commit it) and the secret key to the
   gitignored `keys/luminosity-release.key`, then prints these next steps.
2. Store the secret: `gh secret set LUMINOSITY_RELEASE_SECRET_KEY <
   keys/luminosity-release.key`. There is **no passphrase secret** — the key is
   password-less by design. Then delete the local secret key; it is never
   committed (`.gitignore` blocks `*.key`).
3. Rebuild so the launcher re-embeds the new public key:
   `mise run build:launcher`.

### Rolling out a new public key (strict sequence)

Because the launcher embeds the public key and there is **no launcher
self-update**, the public and secret halves must never be out of step in a
published release. Roll out in this order: generate → commit the new public key
→ set `LUMINOSITY_RELEASE_SECRET_KEY` to the matching secret → rebuild → cut the
release. A release signed by a secret whose public half is not yet embedded (or
vice versa) fails the re-verify-before-undraft gate rather than shipping broken.

### Key rotation

Rotate using the **verify-any-of overlap window** (the launcher trusts a small
set of keys): (1) add the new public key to the trusted set and ship a plugin
release trusting **both** old and new; (2) switch signing to the new key;
(3) after the window, drop the old key in a later release. **Bound the
window** — an indefinitely-trusted retired key widens the forgery surface.

### Compromise response

There is no launcher self-update, so revoking a leaked key requires cutting a
plugin release that drops it from the trusted set; exposure lasts until users
upgrade. Treat a leaked `LUMINOSITY_RELEASE_SECRET_KEY` as an incident: rotate
immediately and cut a release dropping the compromised key.

## Releaser identity and push authorization

`main` is protected by a ruleset requiring pull requests and passing status
checks and forbidding non-fast-forward pushes. The default `GITHUB_TOKEN` is
**not** on its bypass list, so it cannot push the version-bump commit. A
**GitHub App** is on the bypass list, and the release jobs mint its token as
their first step and check out with it:

- `vars.LUMINOSITY_RELEASER_CLIENT_ID` (repo variable) and
  `secrets.LUMINOSITY_RELEASER_SECRET` (repo secret) identify the App.
- `actions/create-github-app-token` exchanges them for a short-lived token;
  the Checkout step consumes it as its `token:`, so the persisted push
  credential is the App's.

The bump commit carries `[skip ci]`, and the `prerelease → approve → release`
chain runs in one workflow run via `needs:`, so the App is purely about
push authorization — not about re-triggering CI.

## Environments and serialisation

The stable `release` job runs behind the `release` GitHub Environment
(the `approve-release` gate); the `prerelease` job does not. Both release
jobs share the `luminosity-release` concurrency group with `queue: max` and
`cancel-in-progress: false`, so overlapping pushes serialise rather than
racing their version bumps. The approval gate deliberately holds **no**
concurrency group, so a waiting approval never blocks a later push's
prerelease.

## The leak guard

`finalise` uses a blanket `git add .` to stage the version bump, so before it
commits, `_assert_no_leaked_artifacts` scans the porcelain status and aborts if
anything matching a `.key` secret, a staged `cli/launcher/bin/luminosity-`
binary, or `manifest.minisig` is present. The tracked version anchors
(`checksums.json`, `manifest.json`) are deliberately excluded and do not trip
it. This is the safety net for the blanket add.

## Recovery and partial-failure triage

`upload_and_verify` re-downloads every asset and re-verifies its SHA-256,
detached signature, and manifest signature **before** un-drafting, so a
key/secret mismatch or corrupted upload is caught at publish time, not at a
user's first fetch. Two failure modes are handled differently:

- **`AssetVerificationError`** (a re-verification mismatch): the draft release
  **and** its tag are **preserved** for triage, and a forensic alert is emitted.
  A mismatch here usually means the committed public key and the signing secret
  are out of step — re-provision them per the rollout sequence above, delete the
  preserved draft + tag, and re-run.
- **Any other exception** during upload/verify: the draft release and tag are
  **deleted** (`gh release delete --cleanup-tag`) so a re-run starts clean.

If a run dies between `push` and release creation, the atomic branch+tag push
means the tag never lands without its branch commit; re-running from a clean
tree is safe.

## Verifying provenance out of band

SLSA provenance is attested for every signed binary. To verify a downloaded
release binary independently of the launcher:

```sh
gh attestation verify luminosity-<platform> --repo <owner>/luminosity
```

and verify its signature directly with minisign against the committed public
key:

```sh
minisign -V -p keys/luminosity-release.pub \
  -x luminosity-<platform>.minisig -m luminosity-<platform>
```

## Refresh cadences

- **Bundled TLS roots.** The launcher carries a frozen `webpki-roots`
  snapshot (it does not read the host cert store). Bump `webpki-roots` on each
  release cut so the Mozilla root snapshot cannot go stale against GitHub's TLS
  chain under no-self-update.
- **Vendored verify shim.** The per-triple `minisign-verify` shim is a trusted,
  no-self-update root-of-trust component: a shim-side flaw persists until users
  upgrade. Refresh its pin on the same cadence and treat a shim vulnerability as
  an upgrade-forcing event.
