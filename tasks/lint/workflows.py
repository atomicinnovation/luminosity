import shlex

from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT

_WORKFLOW = ".github/workflows/main.yml"

_STALE_SCHEMA_FALSE_POSITIVE_FOR_VALID_QUEUE_KEY = (
    'unexpected key "queue" for "concurrency" section'
)


@task
def actionlint(context: Context) -> None:
    """Lint GitHub Actions workflows with actionlint (fail-loud)."""
    ignore = shlex.quote(_STALE_SCHEMA_FALSE_POSITIVE_FOR_VALID_QUEUE_KEY)
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            f"actionlint -ignore {ignore} {_WORKFLOW}", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("actionlint reported findings — fix them", code=1)
