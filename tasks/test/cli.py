from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import coverage_enabled


@task
def run(context: Context) -> None:
    """Run the whole workspace's unit tests (instrumented unless disabled).

    A single `--workspace` pass covers every crate in one process, so coverage
    is folded into the test run (default `cargo llvm-cov nextest`) and there is
    no cross-crate profraw collision to isolate. It is report-only — no
    `--fail-under`/threshold, by design.

    The arg-driven test fixture (`tests/fixtures/`) is excluded from the
    coverage report: it is spawned as a subprocess, never instrumented in-run,
    so it would otherwise skew the report as permanent 0%-covered scaffolding.
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
