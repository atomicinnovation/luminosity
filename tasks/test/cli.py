from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT
from tasks.shared.rust import CLI_CRATE, coverage_enabled


@task
def run(context: Context) -> None:
    """Run cli-crate unit tests (instrumented with coverage unless disabled).

    Coverage is folded into the test run, not a separate task: the default
    instrumented `cargo llvm-cov nextest` pass both runs the tests and reports
    coverage in one go, so coverage runs wherever the tests run. It is
    report-only — no `--fail-under`/threshold, by design.
    """
    command = (
        f"cargo llvm-cov nextest -p {CLI_CRATE} --summary-only"
        if coverage_enabled()
        else f"cargo nextest run -p {CLI_CRATE}"
    )
    with context.cd(str(REPO_ROOT)):
        result = context.run(command, warn=True, pty=False)
    if result.exited != 0:
        raise Exit("nextest: cli tests failed", code=1)
