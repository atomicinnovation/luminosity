import shlex

from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT

_WORKFLOW = ".github/workflows/main.yml"

# Suppress actionlint's stale-schema false positive for the valid GA
# `concurrency.queue` key. Drop once its schema learns the key.
_QUEUE_SCHEMA_LAG = 'unexpected key "queue" for "concurrency" section'


@task
def actionlint(context: Context) -> None:
    """Lint GitHub Actions workflows with actionlint (fail-loud)."""
    ignore = shlex.quote(_QUEUE_SCHEMA_LAG)
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            f"actionlint -ignore {ignore} {_WORKFLOW}", warn=True, pty=False
        )
    if result.exited != 0:
        raise Exit("actionlint reported findings — fix them", code=1)
