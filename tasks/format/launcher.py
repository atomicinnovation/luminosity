from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import LAUNCHER_CRATE


@task
def check(context: Context) -> None:
    """Check launcher-crate Rust formatting with rustfmt (read-only)."""
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(
            f"cargo fmt -p {LAUNCHER_CRATE} --check", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit(
            "rustfmt: drift — run `mise run format:launcher:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format the launcher crate in place with rustfmt."""
    with context.cd(str(WORKSPACE_ROOT)):
        context.run(f"cargo fmt -p {LAUNCHER_CRATE}", warn=True, pty=False)
