---
type: pr-description
id: "8"
title: "On-demand static-binary distribution and launcher (0008)"
date: "2026-07-04T21:07:02+00:00"
author: "Toby Clemson"
producer: describe-pr
status: complete
work_item_id: "work-item:0008"
parent: "work-item:0008"
pr_url: "https://github.com/atomicinnovation/luminosity/pull/8"
pr_number: 8
tags: [rust, distribution, launcher, cross-compile, minisign, reqwest, cargo-zigbuild]
revision: "2b39dc650570078ae8bcc94ae4efa23c425f8f63"
repository: "luminosity"
last_updated: "2026-07-04T21:07:02+00:00"
last_updated_by: "Toby Clemson"
schema_version: 1
---

# On-demand static-binary distribution and launcher (0008)

## Summary

Implements work item 0008: a complete on-demand static-binary distribution pipeline and the Rust launcher that consumes it. One host cross-compiles four fully static Unix triples, minisign-signs them alongside a signed release manifest under enforced version coherence, and the `luminosity` launcher routes unknown subcommands through a fetch → verify (sha256 + in-process minisign) → cache → exec path rooted in a key-bound trust chain (not TLS). This turns the pre-cut hexagonal skeleton from 0007 into a working product surface.

## Changes

### Distribution pipeline (Python `tasks/`)

- **Four-triple cross-compile** via `cargo-zigbuild` (`build.release`): builds all four shipped triples from one host, stages `luminosity-{platform}` + `.debug.tar.gz`, and writes sha256s into `checksums.json`. Verification is host-aware (macOS `lipo`/`otool`; Linux-building-darwin via `llvm-objdump --macho`), and darwin builds pin an explicit `MACOSX_DEPLOYMENT_TARGET`.
- **minisign signing + signed manifest** (`tasks/sign.py`, `tasks/shared/minisign.py`): detach-signs each binary and emits a name-keyed, per-platform `manifest.json` (bare-hex sha256 + inline signature read back from the emitted `.minisig`, so the inline and detached copies cannot drift), then signs the manifest itself (`manifest.minisig`).
- **Version coherence** (`tasks/version.py`): a single-writer `write()` and a `version:check` audit across all four anchors (`plugin.json`, `cli/launcher/Cargo.toml`, `checksums.json`, `manifest.json`), wired into `mise run check` and enforced as a fail-closed precondition on the release path.
- **Release upload/verify** (`tasks/github.py`): uploads binaries, debug archives, signatures, and the manifest, then re-downloads and minisign-verifies every asset against the committed key before un-drafting — with every tool-invocation failure mapped to `AssetVerificationError` so a transient hiccup preserves the draft + tag rather than destroying them.
- Keypair generation (`tasks/keys.py`) and pinned provisioning of zig/`cargo-zigbuild`/minisign (`tasks/deps.py`, `mise.toml`, `pyproject.toml`).

### Rust launcher (`cli/launcher/`)

- **External-subcommand dispatch + exec**: a dedicated `launch` module owns `External(Vec<OsString>)` routing and process-replacing `exec` (exit codes and signals propagate; non-UTF-8 arguments survive verbatim); the `version` hexagon stays clean.
- **kernel error taxonomy**: a small shared `kernel::Error` with a launcher-local `ResolutionError` mapping at the boundary, replacing the uninhabited placeholder.
- **Real resolution adapter**: blocking `reqwest` (rustls + `ring` + bundled webpki-roots + `hickory-dns`) fetch → sha256 + in-process minisign verification against the embedded release key → atomic cache write keyed by name+version+checksum → exec, re-verifying the signature before every exec including cache hits. Composed of small collaborators (Fetcher, Verifier, CacheStore, CacheRootResolver) with a plugin-root writable+exec probe and XDG fallback.
- **Manifest-driven help**: `--help` lazily reads the signed manifest to synthesise an external-subcommands section (built-ins never touch the manifest), and `foo --help` is delegated to the resolved child.
- The release public key is embedded from a single committed file via `build.rs`.

### Bootstrap and root of trust

- `bin/luminosity`: a bash-3.2 entry point that fetches the launcher on first use and verifies its signature against the plugin-committed key using a vendored per-triple `minisign-verify` shim (`cli/verify/`) before exec, failing closed — a binary cannot verify itself, so the shim is the root of trust delivered over the marketplace channel.

### Supply chain

- The reqwest/rustls closure is declared `default-features = false` so the native-tls/openssl ban in `deny.toml` is not tripped; a deny regression test asserts no `native-tls`/`openssl`/`aws-lc`/native-cert crate enters the launcher tree and that `ring` is present.

### Post-validation follow-up (this branch)

After validating the plan (`meta/validations/2026-07-03-0008-...-validation.md`), the following review findings were addressed on this branch: the `gh` download-timeout guard on the signature re-verify path; the production fetcher now pins the https scheme; `version:check` names every anchor on a no-majority split; the fetch total timeout was widened to a 300s aggregate deadline; and end-to-end test-coverage gaps (manifest-decoupled built-ins, invalid plugin root, unrunnable shim) were closed.

## Context

- Work item: `meta/work/0008-on-demand-static-binary-distribution-and-launcher.md`
- Plan: `meta/plans/2026-07-03-0008-static-binary-distribution-and-launcher.md`
- Validation report: `meta/validations/2026-07-03-0008-static-binary-distribution-and-launcher-validation.md` (result: partial — all automated checks green; operational items blocked)
- Relevant ADRs: ADR-0002 (zero-setup static-binary distribution), ADR-0009 (thin CLI over a hexagonal core), ADR-0010 (git-style modular CLI of on-demand static binaries)

This PR is **stacked on #7** (`0014-relocate-workspace-crates`) and targets that branch as its base; review it after or alongside #7.

## Testing

- [x] `mise run` (the full local CI mirror) exits 0 end-to-end: all formatters/lints/type-checks, the cli workspace tests with coverage, `build:launcher`, `deny:check`, and `pup:check`.
- [x] Rust: 53 launcher tests pass, including dispatch/exec propagation, the hermetic fetch→verify→cache→exec resolution suite against a local mock server (with a second non-release key), and the https-scheme refusal.
- [x] Python: unit + integration task suites pass, including the sign/manifest round-trip against a shared fixture, the `version:check` desync-naming tests, and the upload-path signature-mismatch/timeout guards that preserve the draft + tag.
- [x] Shell: the hermetic entry-point suite passes (host-triple detection, cache reuse, poisoned/tampered cache refusal, non-release-key refusal, PATH-decoy rejection, read-only-root XDG fallback, invalid-root and unrunnable-shim fail-closed).
- [x] Supply chain: `deny:check` + the deny regression test confirm the rustls closure carries no native-tls/openssl/aws-lc and no native-cert crate.
- [ ] End-to-end fetch of a real signed asset from a real release (blocked — needs the real keypair and a pipeline-provisioned test release; exercised hermetically against a mock server/local release).

## Notes for Reviewers

- **Operational blockers (validation result is "partial").** The committed release public key is a placeholder; the real minisign keypair + GitHub `release`-environment secrets (`MINISIGN_SECRET_KEY` / `MINISIGN_KEY_PASSWORD`), the CI-gated e2e smoke, and required-check registration are not creatable from the repo and remain to be provisioned before a real release cut.
- **The rustls trap.** reqwest must stay `default-features = false`; its default native-tls feature would trip `deny.toml`. This is the single most load-bearing dependency-declaration constraint.
- **Deliberate deferrals (recorded in the validation report, not ADR-0010 which is immutable).** Advisory file locking and download size/free-space bounding were judged disproportionate for a single-user cache that already writes via atomic rename; a per-read/idle fetch timeout is infeasible on blocking reqwest without a direct tokio dependency.
- **Still open (not actioned this pass).** The bootstrap re-implements the cache-root probe/XDG chain in bash rather than single-sourcing it from the launcher (drift risk, no coherence test), and the bootstrap trusts a single committed key so the documented verify-any-of rotation is not yet achievable at the root-of-trust layer.
