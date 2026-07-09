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

## Release signing and the release pipeline

The operational runbook for cutting a release — the
`prepare → sign → attest → finalise` pipeline, the password-less minisign key
lifecycle and `LUMINOSITY_RELEASE_SECRET_KEY` provisioning, the GitHub App
releaser identity and `main` ruleset bypass, the `release` / `prerelease`
Environments, and recovery / partial-failure triage — lives in
[`RELEASING.md`](RELEASING.md).

One point of signing/build isolation worth stating here: signing runs in a
**dedicated `*:sign` step** whose `env:` carries `LUMINOSITY_RELEASE_SECRET_KEY`
and nothing else, sitting after the prepare (build) step and before attest and
finalise. The secret is scoped to that one step, so a compromised build
dependency in the prepare step is never in the same environment as the key.
Signing is therefore isolated at the **step** level, not split into a separate
job with artifact passing.
