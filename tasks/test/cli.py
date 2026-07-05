from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import coverage_enabled


@task
def run(context: Context) -> None:
    """Run the whole workspace's unit tests (instrumented unless disabled).

    The arg-driven test fixture (`tests/fixtures/`) is excluded from the
    coverage report: spawned as a subprocess, it is never instrumented in-run.
    """
    command = (
        "cargo llvm-cov nextest --workspace --summary-only "
        "--ignore-filename-regex 'tests/fixtures/'"
        if coverage_enabled()
        else "cargo nextest run --workspace"
    )
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(command, warn=True, pty=False)
    if result.exited != 0:
        raise Exit("nextest: cli tests failed", code=1)
