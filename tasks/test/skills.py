from invoke import Context, Exit, task

from tasks.shared.sources import repo_root


@task
def run(context: Context) -> None:
    """Run the pytest unit suite for the skill wiring (injection, surfaces).

    The wiring tests live under tests/unit/skills; the directory-scoped
    test:unit:tasks pass does not collect them, so without this leaf they would
    be lint/type-checked but never executed.
    """
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/unit/skills -v", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("skill wiring tests failed", code=1)
