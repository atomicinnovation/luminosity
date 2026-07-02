from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT


@task
def check(context: Context) -> None:
    """Check kernel-crate Rust formatting with rustfmt (read-only)."""
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(
            "cargo fmt -p kernel --check", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit(
            "rustfmt: drift — run `mise run format:kernel:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format the kernel crate in place with rustfmt."""
    with context.cd(str(WORKSPACE_ROOT)):
        context.run("cargo fmt -p kernel", warn=True, pty=False)
