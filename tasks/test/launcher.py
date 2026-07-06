from invoke import Context, Exit, task

from tasks.shared.paths import WORKSPACE_ROOT
from tasks.shared.rust import LAUNCHER_CRATE, coverage_enabled


@task
def run(context: Context) -> None:
    """Run launcher-crate unit tests (instrumented coverage unless disabled).

    A single-crate (`-p luminosity`) convenience pass; the aggregate workspace
    coverage runs via test:unit:cli. Coverage is folded into the run (default
    `cargo llvm-cov nextest`) and is report-only — no `--fail-under`, by design.
    """
    command = (
        f"cargo llvm-cov nextest -p {LAUNCHER_CRATE} --summary-only"
        if coverage_enabled()
        else f"cargo nextest run -p {LAUNCHER_CRATE}"
    )
    with context.cd(str(WORKSPACE_ROOT)):
        result = context.run(command, warn=True, pty=False)
    if result.exited != 0:
        raise Exit("nextest: launcher tests failed", code=1)
