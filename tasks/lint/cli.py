from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT


@task
def check(context: Context) -> None:
    """Lint Rust with clippy (pedantic + nursery + restriction, -D warnings)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo clippy --workspace --all-targets --all-features "
            "-- -D warnings",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit(
            "clippy reported findings — run `mise run lint:cli:fix`", code=1
        )


@task
def fix(context: Context) -> None:
    """Apply clippy's machine-applicable suggestions."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo clippy --workspace --all-targets --all-features "
            "--fix --allow-dirty --allow-staged",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        # A non-zero exit here means the autofix step itself failed (e.g. an
        # uncompilable tree blocked it) — louder than the formatters' silent
        # fix, since lint:cli:check would otherwise read clean while nothing
        # was applied.
        print("WARNING: clippy --fix could not apply suggestions — see output")
