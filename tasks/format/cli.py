from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT


@task
def check(context: Context) -> None:
    """Check formatting across the whole workspace with rustfmt (read-only)."""
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run("cargo fmt --all --check", warn=True, pty=False)
    if result.exited != 0:
        raise Exit(
            "rustfmt: drift — run `mise run format:cli:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format the whole workspace in place with rustfmt."""
    with context.cd(str(WORKSPACE_ROOT)):
        context.run("cargo fmt --all", warn=True, pty=False)
