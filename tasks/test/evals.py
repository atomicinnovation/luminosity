from invoke import Context, Exit, task

from tasks.shared.sources import repo_root


@task
def run(context: Context) -> None:
    """Run the pytest unit suite for the eval logic (scorer, dataset, wiring).

    The eval-logic tests live under tests/unit/evals; without this leaf the
    test:unit:tasks pass would leave them lint/type-checked but never executed.
    """
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/unit/evals -v", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("eval unit tests failed", code=1)
