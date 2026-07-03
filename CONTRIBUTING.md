# Contributing

Day-to-day engineering conventions (TDD, the task tree, the 80-column rule,
the bash-3.2 floor) live in `CLAUDE.md` and `tasks/README.md`. This file is the
home for repo-admin runbooks whose audience is a maintainer, not a contributor.

## Branch-protection required checks (runbook)

CI runs the gating jobs (`.github/workflows/main.yml`), but **PR mergeability is
enforced by GitHub branch-protection *required checks*, configured in repo
settings — not in the workflow YAML.** A new CI job does not gate merges until
its display name is added to the protected-branch required-check list. The
automated `tests/unit/tasks/test_workflows.py` guard proves the jobs *exist* and
gate the release pipeline; it cannot prove they are *registered* as required
checks. Keeping the two in sync is this manual step.

### Procedure

1. Open **Settings → Branches → Branch protection rules → `main` → Require
   status checks to pass before merging**.
2. Add each required-check name below. The name must match the workflow job's
   **display name** (the `name:` field) exactly.
3. Save.

### The names to register

The Rust guard-rail jobs (work item 0006) contribute these required checks:

| Job id                | Required-check name(s)                                   |
|-----------------------|----------------------------------------------------------|
| `check-cli`           | `Check cli`                                              |
| `build-launcher`      | `Build launcher (ubuntu-latest)` **and** `Build launcher (macos-latest)` |
| `check-supply-chain`  | `Check supply chain`                                     |
| `check-architecture`  | `Check architecture`                                     |

(Alongside the pre-existing `Run unit tests`, `Run integration tests`,
`Check scripts`, and `Check build system`.)

### Two gotchas

- **A matrix job surfaces one required check *per leg*.** `build-launcher` runs
  on `[ubuntu-latest, macos-latest]`, so it contributes **two** names —
  `Build launcher (ubuntu-latest)` and `Build launcher (macos-latest)`. Both
  must be added, or the un-added OS's release build is not actually gating (e.g.
  omitting the macOS leg leaves a darwin build break ungated). The matrix legs
  build their host-native triples, so dropping a leg drops real triple coverage.
- **A job only appears as a selectable required check *after it has run at least
  once*.** On a brand-new job, push a commit (or open a PR) so it runs, then
  return to the settings page to select it.

### Verifying registration

`test_workflows.py` is necessary but not sufficient — it does not read repo
settings. To close the gap between "jobs exist" and "jobs gate", a maintainer
can audit the registered checks directly:

```sh
gh api repos/{owner}/{repo}/branches/main/protection \
  --jq '.required_status_checks.contexts'
```

and confirm the five Rust-job names above are present.

## Release signing (minisign) — standing operational responsibilities

Releases are integrity-protected with **minisign** (sha256 alone is not trust;
in-process signature verification is, per ADR-0002). These are ongoing
maintainer duties, not one-offs.

### Key provisioning (do this before the first real release)

The public key committed at `keys/luminosity-release.pub` and
`cli/launcher/keys/release.pub` (kept byte-identical by `mise run version:check`)
is currently a **placeholder** generated during implementation. Before cutting a
real release:

1. Generate the production keypair: `minisign -G -p release.pub -s release.key`
   (choose a strong passphrase).
2. Store the **secret** in the GitHub `MINISIGN_SECRET_KEY` secret (the full
   `release.key` contents) and its passphrase in `MINISIGN_KEY_PASSWORD`. The
   secret key is **never** committed (`.gitignore` blocks `*.key`).
3. Replace **both** committed public-key copies with the real public key and
   confirm `mise run version:check` still passes (key coherence).

### Publishing `.minisig` assets

Every release publishes, per binary, a `.minisig` alongside the binary and its
`.sha256`, plus a signed `manifest.json` (`manifest.minisig`). This is automatic
in the release pipeline (`tasks/sign.py` → `upload_and_verify`), which
re-downloads every asset and re-verifies its signature against the committed
public key **before** un-drafting — so a key/secret mismatch is caught at publish
time, not at a user's first fetch.

### Key rotation

Rotate using the **verify-any-of overlap window** (the launcher trusts a small
set of keys): (1) add the new public key to the trusted set and ship a plugin
release trusting **both** old and new; (2) switch signing to the new key; (3)
after the window, drop the old key in a later release. **Bound the window** — an
indefinitely-trusted retired key widens the forgery surface.

### Compromise response

There is **no launcher self-update**, so revoking a leaked key requires cutting a
plugin release that drops it from the trusted set; exposure lasts until users
upgrade. Treat a leaked `MINISIGN_SECRET_KEY` as an incident: rotate immediately
and cut a release dropping the compromised key.

### Bundled-roots refresh cadence

The launcher carries a frozen `webpki-roots` snapshot (it does not read the host
cert store). Bump `webpki-roots` on each release cut so the Mozilla root
snapshot cannot go stale against GitHub's TLS chain under no-self-update.

### Vendored verify shim

The per-triple `minisign-verify` shim (the bootstrap's root-of-trust verifier)
is a trusted, no-self-update component: a shim-side flaw likewise persists until
users upgrade. Refresh its pin on the same cadence and treat a shim
vulnerability as an upgrade-forcing event.

### Signing/build isolation (known follow-up)

The plan calls for signing to run in a **separate CI job** that never shares an
environment with crate compilation (so a compromised build dependency cannot
exfiltrate `MINISIGN_SECRET_KEY`). The current pipeline signs within the release
job's finalise step (after the build step, secret scoped to finalise). Splitting
signing into an isolated job that consumes the built artefacts via job artifacts
is a tracked hardening follow-up.
