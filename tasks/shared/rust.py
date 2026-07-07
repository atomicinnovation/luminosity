import os

from tasks.shared.env import env_flag_enabled

LAUNCHER_CRATE = "luminosity"  # matches cli/launcher/Cargo.toml [package] name
KERNEL_CRATE = "kernel"  # must equal cli/kernel/Cargo.toml [package] name
# PUP_NIGHTLY + PUP_VERSION are a matched pair (cargo-pup's rustc-driver only
# loads under the nightly it was built against); bump them together.
PUP_NIGHTLY = "nightly-2026-01-22"  # cargo-pup v0.1.8 rust-toolchain.toml
PUP_VERSION = "0.1.8"

_PUP_MODES = {"deny", "warn"}


def coverage_enabled() -> bool:
    """Whether launcher tests run instrumented. Read at CALL time, not import.

    True -> `cargo llvm-cov nextest` (coverage reported); False -> plain
    `cargo nextest run` (faster inner loop). Env-sourced so a developer can
    drop coverage without a source edit; CI leaves it on. Any of off/false/0/no
    (case-insensitive) disables it, so a plausible falsey value does not
    silently leave the slow path on.
    """
    return env_flag_enabled("LUMINOSITY_COVERAGE", default="on")


def pup_mode() -> str:
    """cargo-pup blocking mode. Read at CALL time, never at import.

    "deny" -> fail on findings (blocking, per AC6); "warn" -> advisory (log
    only). Default "deny" honours AC6: with an empty pup.ron (the bootstrap)
    "deny" passes trivially, so the only blocking exposure is a nightly/
    cargo-pup toolchain break, recoverable per-environment via
    LUMINOSITY_PUP_MODE=warn without a source edit. The value is normalised
    (strip + lower-case) so an incident-time typo like "Warn"/" warn " still
    activates the escape hatch; an unrecognised value is treated as "deny"
    (fail-closed) but printed as a WARNING so the typo is visible rather than
    silently blocking. NOTE: warn covers a cargo-pup *findings* failure, not a
    toolchain-*unavailable* failure (which fails in deps:install:pup before any
    check runs).
    """
    raw = os.environ.get("LUMINOSITY_PUP_MODE", "deny").strip().lower()
    if raw not in _PUP_MODES:
        print(
            f"WARNING: unrecognised LUMINOSITY_PUP_MODE={raw!r}; using 'deny'"
        )
        return "deny"
    return raw
