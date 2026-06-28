from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT


@task
def check(context: Context) -> None:
    """Check Rust formatting with rustfmt (read-only; fails on drift)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run("cargo fmt --all --check", warn=True, pty=False)
    if result.exited != 0:
        raise Exit(
            "rustfmt: drift — run `mise run format:cli:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format Rust in place with rustfmt."""
    with context.cd(str(REPO_ROOT)):
        context.run("cargo fmt --all", warn=True, pty=False)
