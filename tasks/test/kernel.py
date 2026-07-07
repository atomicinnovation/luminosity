from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT
from tasks.shared.rust import KERNEL_CRATE, coverage_enabled


@task
def run(context: Context) -> None:
    """Run kernel-crate unit tests (coverage-instrumented unless disabled).

    Runs in an isolated CARGO_TARGET_DIR so the coverage pass cannot collide
    with the cli coverage pass on cargo-llvm-cov's shared profraw directory —
    the two run concurrently under the parallel test:unit roll-up, and
    cargo-llvm-cov is not safe to run twice against one target dir.
    """
    command = (
        f"cargo llvm-cov nextest -p {KERNEL_CRATE} --summary-only"
        if coverage_enabled()
        else f"cargo nextest run -p {KERNEL_CRATE}"
    )
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            command,
            warn=True,
            pty=False,
            env={"CARGO_TARGET_DIR": "target/llvm-cov-kernel"},
        )
    if result.exited != 0:
        raise Exit("nextest: kernel tests failed", code=1)
