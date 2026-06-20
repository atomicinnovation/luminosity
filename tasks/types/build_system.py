from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT


@task
def check(context: Context) -> None:
    """Type-check Python with pyrefly (strict preset)."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "uv run pyrefly check --output-format github", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("pyrefly reported type errors", code=1)
