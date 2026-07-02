from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import LAUNCHER_CRATE


@task
def check(context: Context) -> None:
    """Lint the launcher crate with clippy (pedantic + nursery, -D warnings)."""
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(
            f"cargo clippy -p {LAUNCHER_CRATE} --all-targets --all-features "
            "-- -D warnings",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit(
            "clippy reported findings — run `mise run lint:launcher:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Apply clippy's machine-applicable suggestions to the launcher crate."""
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(
            f"cargo clippy -p {LAUNCHER_CRATE} --all-targets --all-features "
            "--fix --allow-dirty --allow-staged",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        # A non-zero exit here means the autofix step itself failed (e.g. an
        # uncompilable tree blocked it) — louder than the formatters' silent
        # fix, since lint:launcher:check would otherwise read clean while
        # nothing was applied.
        print("WARNING: clippy --fix could not apply suggestions — see output")
