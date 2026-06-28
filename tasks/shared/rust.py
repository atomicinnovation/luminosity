import os

CLI_CRATE = "luminosity"  # must equal cli/Cargo.toml [package] name

_FALSEY = {"off", "false", "0", "no"}


def coverage_enabled() -> bool:
    """Whether cli tests run instrumented. Read at CALL time, never at import.

    True -> `cargo llvm-cov nextest` (coverage reported); False -> plain
    `cargo nextest run` (faster inner loop). Env-sourced so a developer can
    drop coverage without a source edit; CI leaves it on. Must be called inside
    the task body — a module-level constant would freeze the value at import
    and ignore the env. Any of off/false/0/no (case-insensitive) disables it,
    so a plausible falsey value does not silently leave the slow path on.
    """
    raw = os.environ.get("LUMINOSITY_COVERAGE", "on").strip().lower()
    return raw not in _FALSEY
