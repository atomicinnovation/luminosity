from invoke import Context, Exit, task

from tasks.shared.sources import repo_root


@task
def tasks(context: Context) -> None:
    """Run the pytest unit suite for the invoke tasks."""
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/unit/tasks -v", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("unit task tests failed", code=1)
