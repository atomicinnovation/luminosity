---
type: plan
id: "2026-07-09-0015-converge-release-and-signing-onto-accelerator"
title: "Converge the Release & Signing Process onto Accelerator's Proven Pipeline Implementation Plan"
date: "2026-07-08T23:19:01+00:00"
author: Toby Clemson
producer: create-plan
status: done
work_item_id: "work-item:0015"
parent: "work-item:0015"
derived_from: ["codebase-research:2026-07-08-0015-converge-release-signing-onto-accelerator"]
relates_to: ["work-item:0008"]
tags: [release, signing, ci, supply-chain, minisign, github-app]
revision: "6a3d21be49e5b87fddc7faf26486b47c4188f3b6"
repository: "luminosity"
last_updated: "2026-07-08T23:19:01+00:00"
last_updated_by: Toby Clemson
schema_version: 1
---

# Converge the Release & Signing Process onto Accelerator's Proven Pipeline Implementation Plan

## Overview

Luminosity's release pipeline is architecturally near-identical to Accelerator's
proven one but diverges in four handling details and one latent bug. This plan
converges the *shape* — not the crypto — onto Accelerator's: lift signing into a
dedicated task and CI step (attesting after it), add an anti-leak guard before
tagging, adopt a password-less key with the `LUMINOSITY_RELEASE_SECRET_KEY`
secret name, wire the already-provisioned GitHub App releaser identity into the
workflow, and close the remaining diff-pass items (including a wrong-plugin
marketplace call) while authoring a `RELEASING.md`.

Each phase is independently mergeable and driven test-first.

## Current State Analysis

The two pipelines already share minisign detached signatures, an embedded public
key (`build.rs` + `include_str!`), committed per-platform verify shims, SLSA
attestation, four-anchor version coherence, and a re-download-and-verify-before-
undraft gate. The delta is task decomposition, secret handling, and CI identity.

Grounded against live code:

- **Signing is folded into publish.** `tasks/release.py` has a two-way
  `prepare → finalise` split; `_publish` (`tasks/release.py:18-26`) calls
  `sign.sign(context)` as its first step (`:20`). Accelerator has a three-way
  `prepare → sign → finalise` split where `_sign` is "the only task that receives
  the signing secret" and `_publish` never references signing.
- **Attest runs before signing.** The workflow orders every release sequence
  `prepare → attest → finalise` (finalise signs). Accelerator orders
  `prepare → sign → attest → finalise`.
- **Step-level secret scoping already exists.** In
  `.github/workflows/main.yml`, `MINISIGN_SECRET_KEY` / `MINISIGN_KEY_PASSWORD`
  sit only on the three "Finalise" steps (`:288-293`, `:345-350`, `:362-367`),
  never on the `cargo zigbuild` "Prepare" steps. What is missing is a *dedicated
  sign step* separate from publish.
- **No anti-leak guard.** `tasks/git.py:73` does a blanket `git add .`, and
  nothing refuses to commit when a `.key` secret or a staged binary is dirty.
  Accelerator's `_assert_no_leaked_artifacts` is the first call in `_publish`.
- **Password-protected key + minisign-named secret.** `tasks/keys.py` defaults
  to a password-protected key (`-W` only under `--no-password`, `pty=True`);
  `tasks/sign.py` reads `MINISIGN_SECRET_KEY` + `MINISIGN_KEY_PASSWORD` and
  threads the password through `tasks/shared/minisign.py sign()`. Accelerator
  generates password-less (`minisign -G -W -f`), reads only
  `ACCELERATOR_RELEASE_SECRET_KEY`, and has no password variable anywhere.
- **Latent bug.** `prerelease_prepare` calls
  `marketplace.update_prerelease_version(context, plugin="accelerator")`
  (`tasks/release.py:35`); `marketplace-prerelease.json`'s entry is named
  `luminosity`, so the match on `entry["name"] == plugin`
  (`tasks/marketplace.py:51`) never fires and the prerelease marketplace ref is
  never bumped. `release_prepare` correctly passes `plugin="luminosity"`.

### Key Discoveries

- **The broken end-to-end chain is the unset signing secret, not the token.**
  The last failed release run (`28902363518`) failed in `prerelease:finalise`
  with `MINISIGN_SECRET_KEY is not set; cannot sign the release` — the deferred
  first-release follow-up, out of scope here. The chain never reached the push.
- **`main` is protected by an active ruleset, and the App identity's role is
  push authorization.** The ruleset "Default" (id `18226099`) enforces
  `pull_request` + `required_status_checks` + `non_fast_forward` + `deletion`.
  Its bypass list is `OrganizationAdmin`, an admin `RepositoryRole`, and one
  `Integration` (a GitHub App, `bypass_mode: always`). The default
  `GITHUB_TOKEN` is not on it, so once a signing secret exists the finalise push
  would be rejected. A GitHub App on the bypass list is what authorizes it. Both
  repos `[skip ci]` the bump and chain `prerelease → approve → release` via
  `needs:` in one run, so the App was never about "re-triggering CI".
- **The App is already created and wired.** `vars.LUMINOSITY_RELEASER_CLIENT_ID`
  (repo variable) and `secrets.LUMINOSITY_RELEASER_SECRET` (repo secret) exist,
  and the `Integration` is on the ruleset bypass list. This phase only wires the
  workflow to them.
- **Leak-guard markers must be Luminosity-specific.** `git ls-files` shows only
  `checksums.json` + `manifest.json` are tracked under `cli/launcher/bin/` (both
  legitimate version anchors that must *not* trip the guard). The staged
  binaries, per-binary `.minisig`, and `manifest.minisig` are gitignored
  (`.gitignore:37-38`), and secret keys are `*.key` (`.gitignore:41`). So the
  markers are `.key` / `cli/launcher/bin/luminosity-` / `manifest.minisig`, not
  Accelerator's `.sec` / `dist/`.
- **`tasks/git.py` is byte-identical between the two repos** — the leak guard is
  the safety net for that repo's own blanket `git add .`.
- **Test drivers already exist**: `tests/unit/tasks/test_workflows.py` (YAML
  topology via `yaml.safe_load`), `test_sign.py`, `test_keys.py`. There is no
  `test_release.py` yet — this plan adds it.

## Desired End State

- `tasks/release.py` exposes distinct `prerelease_sign` / `release_sign` tasks;
  `_publish` performs no signing; `_publish` refuses to commit when a secret or
  staged binary is dirty.
- The workflow orders every release sequence `prepare → sign → attest →
  finalise`, the signing secret enters only the `*:sign` steps, and both the
  `prerelease` and `release` jobs mint and check out with the App token.
- The release keypair is password-less; `MINISIGN_KEY_PASSWORD` and every
  password code path are gone; signing reads `LUMINOSITY_RELEASE_SECRET_KEY`.
- The `plugin="accelerator"` prerelease-marketplace bug is fixed.
- A `RELEASING.md` documents the pipeline; the CONTRIBUTING.md isolation note is
  corrected to describe a step (not a job) and the password-less convention.
- Every remaining Accelerator divergence is closed or recorded as intentional in
  the PR description.
- `mise run` exits 0 end-to-end.

Verify by: `mise run` green; `uv run pytest tests/unit/tasks/ -v` green; the
workflow YAML shows the sign steps carrying the only signing-secret env and the
App-token steps feeding checkout; a grep for `MINISIGN_KEY_PASSWORD` /
`MINISIGN_SECRET_KEY` / `plugin="accelerator"` across `tasks/` and the workflow
returns nothing.

## What We're NOT Doing

- **Not** generating the production keypair, loading
  `LUMINOSITY_RELEASE_SECRET_KEY`, or cutting the first live signed release —
  the explicit follow-up.
- **Not** registering the GitHub App or editing the ruleset bypass list —
  already done out-of-band by the maintainer; this plan only references the
  provisioned variable + secret.
- **Not** demonstrating the full stable `approve → release` chain live — a
  successful *prerelease* under the App identity is the agreed success signal.
- **Not** splitting signing into a separate *job* with artifact passing (what the
  current CONTRIBUTING.md note wrongly promises) — Accelerator uses a per-step-
  scoped secret, which the sign-step refactor delivers.
- **Not** changing the crypto/trust model, adding a standing drift-check between
  the repos, or adding a server/visualiser distribution path (Luminosity has no
  server binary).
- **Not** introducing a standalone `tasks/manifest.py` — Luminosity's single
  launcher has no dispatched sub-binaries, so folding manifest building into
  `tasks/sign.py` stays (recorded as intentional).

## Implementation Approach

Follow red-green-refactor throughout. The workflow YAML is exercised by
`test_workflows.py` parsing it structurally, so YAML changes are driven by
adding failing assertions there first. Task-level behaviour (`_publish` does not
sign; the leak guard aborts; the marketplace plugin name) is driven by a new
`test_release.py`. Signing/key behaviour changes extend `test_sign.py` /
`test_keys.py`.

Phases 1–3 and 5 are mergeable against `main` today. Phase 4 references the
already-provisioned App variable/secret, so it is also mergeable now; observing
a live green prerelease additionally needs a signing secret loaded (the
follow-up). Phase order is a recommended sequence, not a hard dependency chain,
except that Phase 3 edits the sign step introduced by Phase 1 and Phase 2 edits
`_publish` alongside Phase 1 — sequence them in that order to minimise rebasing.

---

## Phase 1: Dedicated sign task and step; attest after sign

### Overview

Lift signing out of `_publish` into `prerelease_sign` / `release_sign`, insert a
`*:sign` CI step between Prepare and Attest, move the signing-secret env onto
those sign steps, and reorder attestation to run after signing.

### Changes Required

#### 1. Release orchestration

**File**: `tasks/release.py`
**Changes**: Remove signing from `_publish`; add the two sign tasks; chain the
local wrappers `prepare → sign → finalise`.

```python
def _publish(context: Context) -> None:
    version.check(context)
    resolved_version = str(version.read(context, print_to_stdout=False))
    git.commit_version(context)
    git.tag_version(context)
    git.push(context)
    github.create_release(context, target_version=resolved_version)
    github.upload_and_verify(context, resolved_version)


@task
def prerelease_sign(context: Context) -> None:
    """CI prerelease step 2: sign the staged binaries and manifest."""
    sign.sign(context)


@task
def release_sign(context: Context) -> None:
    """CI stable release step 2: sign the staged binaries and manifest."""
    sign.sign(context)
```

The `prerelease` / `release` local-dev wrappers gain the sign call between
prepare and finalise (and the `release` wrapper's post-stable re-cut likewise):

```python
@task
def prerelease(context: Context) -> None:
    """Local-dev only: full prerelease flow without SLSA attestation."""
    _refuse_under_ci("prerelease")
    prerelease_prepare(context)
    prerelease_sign(context)
    prerelease_finalise(context)
```

#### 2. CI workflow ordering

**File**: `.github/workflows/main.yml`
**Changes**: In each of the three release sequences (prerelease job; stable +
post-stable in the release job), insert a Sign step after Prepare and before
Attest, and move the signing-secret env from the Finalise step onto the Sign
step. The Finalise step keeps only `GH_TOKEN`.

```yaml
      - name: Prepare prerelease
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: mise run prerelease:prepare

      - name: Sign prerelease
        env:
          MINISIGN_SECRET_KEY: ${{ secrets.MINISIGN_SECRET_KEY }}
          MINISIGN_KEY_PASSWORD: ${{ secrets.MINISIGN_KEY_PASSWORD }}
        run: mise run prerelease:sign

      - name: Attest binary provenance
        uses: actions/attest-build-provenance@e8998f949152b193b063cb0ec769d69d929409be # v2
        with:
          subject-path: "cli/launcher/bin/luminosity-*"

      - name: Finalise prerelease
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: mise run prerelease:finalise
```

(The secret env is renamed to `LUMINOSITY_RELEASE_SECRET_KEY` and
`MINISIGN_KEY_PASSWORD` dropped in Phase 3; Phase 1 only relocates it.)

#### 3. Tests

**File**: `tests/unit/tasks/test_release.py` (new)
**Changes**: Drive the separation.

```python
import tasks.release as release_module
from tasks.release import _publish, prerelease, prerelease_sign


def test_publish_does_not_sign(ctx, mocker):
    signed = mocker.patch.object(release_module.sign, "sign")
    mocker.patch.object(release_module.version, "check")
    mocker.patch.object(release_module.version, "read", return_value="1.0.0")
    mocker.patch.object(release_module.git, "commit_version")
    mocker.patch.object(release_module.git, "tag_version")
    mocker.patch.object(release_module.git, "push")
    mocker.patch.object(release_module.github, "create_release")
    mocker.patch.object(release_module.github, "upload_and_verify")
    _publish(ctx)
    signed.assert_not_called()


def test_sign_tasks_delegate_to_sign(ctx, mocker):
    signed = mocker.patch.object(release_module.sign, "sign")
    prerelease_sign(ctx)
    signed.assert_called_once_with(ctx)
```

**File**: `tests/unit/tasks/test_workflows.py`
**Changes**: Add assertions that each release sequence runs a `:sign` target,
that the signing-secret env appears only on sign steps (never on a step running
`:prepare`), and that the attest step follows the sign step. Add a known-bad
shape that relocates the secret onto a prepare step and expect rejection.

### Success Criteria

#### Automated Verification

- [x] New release tests pass: `uv run pytest tests/unit/tasks/test_release.py -v`
- [x] Workflow topology tests pass:
      `uv run pytest tests/unit/tasks/test_workflows.py -v`
- [x] Read-only CI set passes: `mise run check`
- [x] Full local CI mirror passes: `mise run`

#### Manual Verification

- [x] Tracing the signing-secret env in `main.yml` shows it only on `*:sign`
      steps and on no step that runs `cargo zigbuild` / `:prepare`.
- [x] `_publish` reads top-to-bottom as commit → tag → push → release with no
      signing.

---

## Phase 2: Anti-leak guard before tagging

### Overview

Port an `_assert_no_leaked_artifacts` equivalent keyed on Luminosity's markers,
called first in `_publish` so a dirty `.key` secret or staged binary aborts the
release before the blanket `git add .`.

### Changes Required

#### 1. Leak guard

**File**: `tasks/release.py`
**Changes**: Add markers + guard; call it first in `_publish`.

```python
_ARTIFACT_MARKERS = (".key", "cli/launcher/bin/luminosity-", "manifest.minisig")


def _assert_no_leaked_artifacts(context: Context) -> None:
    result = context.run("git status --porcelain", hide=True, warn=True)
    offenders = [
        line
        for line in result.stdout.splitlines()
        if any(marker in line for marker in _ARTIFACT_MARKERS)
    ]
    if offenders:
        raise RuntimeError(
            "refusing to commit: a signing secret or staged binary would be "
            f"swept into the version-bump commit:\n{chr(10).join(offenders)}"
        )
```

`_publish` calls it before `git.commit_version`:

```python
def _publish(context: Context) -> None:
    version.check(context)
    resolved_version = str(version.read(context, print_to_stdout=False))
    _assert_no_leaked_artifacts(context)
    git.commit_version(context)
    ...
```

#### 2. Tests

**File**: `tests/unit/tasks/test_release.py`
**Changes**: A dirty secret/binary aborts before commit; a clean anchor-only
status proceeds.

```python
def test_publish_aborts_when_a_secret_would_leak(ctx, mocker):
    ctx.run.return_value = mocker.MagicMock(
        stdout="?? keys/luminosity-release.key\n"
    )
    mocker.patch.object(release_module.version, "check")
    mocker.patch.object(release_module.version, "read", return_value="1.0.0")
    commit = mocker.patch.object(release_module.git, "commit_version")
    with pytest.raises(RuntimeError):
        _publish(ctx)
    commit.assert_not_called()


def test_publish_allows_clean_version_anchors(ctx, mocker):
    ctx.run.return_value = mocker.MagicMock(
        stdout=" M cli/launcher/bin/checksums.json\n"
        " M cli/launcher/bin/manifest.json\n"
    )
    ... # patch git/github/version; assert commit_version IS called
```

### Success Criteria

#### Automated Verification

- [x] Leak-guard tests pass: `uv run pytest tests/unit/tasks/test_release.py -v`
- [x] Full local CI mirror passes: `mise run`

#### Manual Verification

- [x] A tracked `checksums.json` / `manifest.json` bump does not trip the guard;
      a stray `luminosity-*` binary or `.key` file does.

---

## Phase 3: Password-less key convention and secret rename

### Overview

Adopt the `minisign -G -W -f` password-less keypair, remove every password code
path, and rename the CI signing secret to `LUMINOSITY_RELEASE_SECRET_KEY`.

### Changes Required

#### 1. Signing

**File**: `tasks/sign.py`
**Changes**: Rename the secret env; delete `_KEY_PASSWORD_ENV` and all password
plumbing; drop the `password` argument from `sign_binaries` and the
`minisign.sign` calls.

```python
_SECRET_KEY_ENV = "LUMINOSITY_RELEASE_SECRET_KEY"  # noqa: S105 — env var name


@task
def sign(context: Context) -> None:
    """Sign every binary, build the manifest, and sign the manifest."""
    key_material = os.environ.get(_SECRET_KEY_ENV)
    if not key_material:
        raise Exit(f"{_SECRET_KEY_ENV} is not set; cannot sign the release", 1)
    with tempfile.TemporaryDirectory() as tmp:
        secret_key = Path(tmp) / "release.key"
        secret_key.write_text(key_material)
        secret_key.chmod(0o600)
        sign_binaries(context, secret_key)
        write_manifest()
        minisign.sign(secret_key, MANIFEST, MANIFEST_SIGNATURE)
```

#### 2. Minisign wrapper

**File**: `tasks/shared/minisign.py`
**Changes**: Remove the `password` keyword and the stdin plumbing from `sign()`
so no password-prompt path remains. `subprocess.run` drops the `input=` stdin.

#### 3. Key generation

**File**: `tasks/keys.py`
**Changes**: Always generate password-less — drop the `no_password` parameter,
always append `-W`, drop `pty=True`; keep the `--force` existing-key guard;
update the printed guidance to `LUMINOSITY_RELEASE_SECRET_KEY` with no passphrase
line, provisioning straight from the `.key` file without echoing.

```python
    command = [
        minisign.MINISIGN,
        "-G",
        "-W",
        "-f",
        "-p",
        str(RELEASE_PUBLIC_KEY),
        "-s",
        str(secret_key),
    ]
    context.run(shlex.join(command))
    print(
        "\nGenerated the release keypair:\n"
        f"  public  (commit this):   {RELEASE_PUBLIC_KEY}\n"
        f"  secret  (DO NOT commit): {secret_key}\n\n"
        "Next steps:\n"
        f"  1. gh secret set LUMINOSITY_RELEASE_SECRET_KEY < {secret_key}\n"
        f"  2. Delete the local secret key: rm {secret_key}\n"
        "  3. Rebuild so the launcher re-embeds the new public key: "
        "mise run build:launcher\n"
    )
```

#### 4. CI workflow

**File**: `.github/workflows/main.yml`
**Changes**: Each `*:sign` step's env becomes the single line
`LUMINOSITY_RELEASE_SECRET_KEY: ${{ secrets.LUMINOSITY_RELEASE_SECRET_KEY }}`;
`MINISIGN_KEY_PASSWORD` and `MINISIGN_SECRET_KEY` are removed everywhere.

#### 5. Tests

**File**: `tests/unit/tasks/test_sign.py`
**Changes**: Rename the env in `test_requires_the_secret_key_env` /
`test_signs_each_binary_and_manifest`; drop the `MINISIGN_KEY_PASSWORD`
monkeypatch and any password assertion.

**File**: `tests/unit/tasks/test_keys.py`
**Changes**: Replace `test_password_protected_by_default` /
`test_no_password_passes_the_flag` with a test asserting `-W` is always present
and generation is non-interactive; keep the force / refuse-overwrite tests.

**File**: `tests/unit/tasks/test_workflows.py`
**Changes**: Assert the sign steps reference `LUMINOSITY_RELEASE_SECRET_KEY` and
that no `MINISIGN_KEY_PASSWORD` / `MINISIGN_SECRET_KEY` appears anywhere in the
workflow.

### Success Criteria

#### Automated Verification

- [x] Sign + keys tests pass:
      `uv run pytest tests/unit/tasks/test_sign.py tests/unit/tasks/test_keys.py -v`
- [x] Workflow tests pass:
      `uv run pytest tests/unit/tasks/test_workflows.py -v`
- [x] No password remnants:
      `! grep -rn "MINISIGN_KEY_PASSWORD\|MINISIGN_SECRET_KEY" tasks/ .github/`
- [x] Full local CI mirror passes: `mise run`

#### Manual Verification

- [x] `mise run keys:generate --force` (throwaway dir) produces a key that signs
      and verifies without a passphrase prompt.

---

## Phase 4: GitHub App releaser identity

### Overview

Mint the already-provisioned App token in the `prerelease` and `release` jobs and
check out with it, so the version-bump push is authorized past `main`'s ruleset.

### Changes Required

#### 1. CI workflow

**File**: `.github/workflows/main.yml`
**Changes**: Add a first step minting the App token and switch the Checkout step
to consume it, in both the `prerelease` and `release` jobs.

```yaml
    steps:
      - name: Get releaser token
        id: app-token
        uses: actions/create-github-app-token@… # pin by SHA, v2
        with:
          client-id: ${{ vars.LUMINOSITY_RELEASER_CLIENT_ID }}
          private-key: ${{ secrets.LUMINOSITY_RELEASER_SECRET }}

      - name: Checkout code
        uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5
        with:
          token: ${{ steps.app-token.outputs.token }}
```

`gh` calls keep using `GITHUB_TOKEN`; only checkout's persisted push credential
changes.

#### 2. Tests

**File**: `tests/unit/tasks/test_workflows.py`
**Changes**: Assert both `prerelease` and `release` jobs contain a
`create-github-app-token` step referencing `vars.LUMINOSITY_RELEASER_CLIENT_ID`
and `secrets.LUMINOSITY_RELEASER_SECRET`, and that their Checkout step's
`with.token` is `${{ steps.app-token.outputs.token }}`.

### Success Criteria

#### Automated Verification

- [x] Workflow tests pass:
      `uv run pytest tests/unit/tasks/test_workflows.py -v`
- [x] Full local CI mirror passes: `mise run`

#### Manual Verification

- [ ] After merge, the next push to `main` runs the `prerelease` job green: the
      bump commit is pushed past the ruleset under the App identity and a signed
      prerelease is published and re-verified. (Requires a signing secret loaded;
      if still deferred to the first-release follow-up, this is confirmed then —
      the workflow wiring itself is complete and unit-verified now.)
- [ ] The pushed bump commit's author is the App identity, not the default
      Actions bot.

---

## Phase 5: Diff-pass closure and documentation

### Overview

Fix the wrong-plugin marketplace call, author `RELEASING.md`, correct the
CONTRIBUTING.md isolation note, and record the intentional divergences.

### Changes Required

#### 1. Marketplace bug

**File**: `tasks/release.py`
**Changes**: `prerelease_prepare` passes the correct plugin name.

```python
    marketplace.update_prerelease_version(context, plugin="luminosity")
```

#### 2. Release documentation

**File**: `RELEASING.md` (new)
**Changes**: Author a Luminosity `RELEASING.md` mirroring Accelerator's, adapted
to Luminosity's shape: the `prepare → sign → attest → finalise` structure and
per-step secret scoping; the single-launcher manifest (no dispatched
sub-binaries, no server); the password-less `keys:generate` and
`LUMINOSITY_RELEASE_SECRET_KEY` provisioning; the strict pub-key rollout
sequence; the App releaser identity and the `main` ruleset bypass as the
push-authorization/signing-authority control; the `release` / `prerelease`
Environments; recovery / partial-failure / `AssetVerificationError` triage; and
out-of-band SLSA verification.

**File**: `CONTRIBUTING.md`
**Changes**: Correct the "Signing/build isolation" note (lines 126-133) to
describe a dedicated *step* with a per-step-scoped secret (not a separate job
with artifact passing); update the key-provisioning steps (lines 70-88) to the
password-less convention and `LUMINOSITY_RELEASE_SECRET_KEY`; move the
operational release-signing content into `RELEASING.md`, leaving a pointer and
retaining the branch-protection required-checks runbook.

#### 3. Recorded intentional divergences (PR description)

- Manifest building folded into `tasks/sign.py` (no `tasks/manifest.py`) — single
  launcher, no dispatched sub-binaries.
- No server/visualiser cross-compile or checksum-only distribution path.
- `keys.generate` retains Luminosity's `--force` refuse-overwrite guard (a
  safety improvement Accelerator's always-`-f` generator lacks).
- `github.upload_and_verify` vs Accelerator's `upload_and_verify_release` (name
  only; identical re-verify-before-undraft behaviour).
- Secret-file extension `.key` (Luminosity) vs `.sec` (Accelerator); reflected in
  the leak-guard markers.
- Minisign wrapped in `tasks/shared/minisign.py` rather than called inline.

#### 4. Tests

**File**: `tests/unit/tasks/test_release.py`
**Changes**: Assert `prerelease_prepare` calls
`marketplace.update_prerelease_version` with `plugin="luminosity"`.

```python
def test_prerelease_prepare_updates_the_luminosity_marketplace(ctx, mocker):
    update = mocker.patch.object(
        release_module.marketplace, "update_prerelease_version"
    )
    mocker.patch.object(release_module.git, "configure")
    mocker.patch.object(release_module.git, "pull")
    mocker.patch.object(release_module.version, "bump")
    mocker.patch.object(release_module.build, "release")
    prerelease_prepare(ctx)
    update.assert_called_once_with(ctx, plugin="luminosity")
```

### Success Criteria

#### Automated Verification

- [x] Release tests pass: `uv run pytest tests/unit/tasks/test_release.py -v`
- [x] No wrong-plugin call remains:
      `! grep -rn 'plugin="accelerator"' tasks/`
- [x] Markdown-lint / full local CI mirror passes: `mise run`

#### Manual Verification

- [x] `RELEASING.md` accurately describes the post-convergence pipeline and the
      key + App lifecycles.
- [x] The CONTRIBUTING.md note no longer claims a separate signing *job* and no
      longer references a passphrase or `MINISIGN_*` secrets.
- [ ] The PR description lists each intentional divergence.

---

## Testing Strategy

### Unit Tests

- `test_release.py` (new): `_publish` does not sign; sign tasks delegate to
  `sign.sign`; the leak guard aborts on a dirty secret/binary and passes on
  anchor-only changes; `prerelease_prepare` uses `plugin="luminosity"`.
- `test_workflows.py`: sign step present and ordered before attest; signing
  secret only on sign steps; `LUMINOSITY_RELEASE_SECRET_KEY` referenced;
  App-token step + checkout token in both release jobs; new known-bad shapes.
- `test_sign.py` / `test_keys.py`: password-less signing/generation, renamed
  secret, no password path.

### Integration Tests

- None new. The pipeline's live integration is the CI release run itself; the
  local-dev `prerelease` wrapper (`_refuse_under_ci`-guarded) exercises
  prepare → sign → finalise off-CI if a maintainer wants a dry run against a
  fork.

### Manual Testing Steps

1. Grep the workflow: signing secret only on `*:sign` steps; App token feeds
   checkout in `prerelease` + `release`.
2. `mise run keys:generate --force` in a scratch dir → sign + verify a payload
   with no passphrase prompt.
3. After merge, watch the next push-to-`main` `prerelease` job authorize its
   bump push under the App identity (given a loaded signing secret).

## Performance Considerations

None. Step reordering and an added `git status` check are negligible against the
four-triple `cargo zigbuild` compile that dominates each job.

## Migration Notes

- The CI secret rename is a breaking change to the deploy environment: the
  production secret must be provisioned under `LUMINOSITY_RELEASE_SECRET_KEY`
  (the first-release follow-up), not `MINISIGN_SECRET_KEY`. No
  `MINISIGN_KEY_PASSWORD` is needed.
- Any pre-generated password-protected secret is incompatible; the follow-up
  generates a fresh password-less keypair and re-embeds the public half.

## References

- Original work item: `meta/work/0015-converge-release-and-signing-process-onto-accelerator.md`
- Related research: `meta/research/codebase/2026-07-08-0015-converge-release-signing-onto-accelerator.md`
- Reference implementation (Accelerator): `tasks/release.py`
  (`_sign` / `_publish` / `_assert_no_leaked_artifacts`), `tasks/signing.py`,
  `.github/workflows/main.yml` (`*:sign` + `create-github-app-token`),
  `RELEASING.md`
- Luminosity touch points: `tasks/release.py:18-26`, `tasks/sign.py:25-115`,
  `tasks/keys.py:9-55`, `tasks/shared/minisign.py:13-52`, `tasks/git.py:67-74`,
  `.github/workflows/main.yml:240-367`, `CONTRIBUTING.md:64-133`,
  `tests/unit/tasks/{test_workflows,test_sign,test_keys}.py`
