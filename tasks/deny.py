from invoke import Context, Exit, task

from tasks.shared.paths import REPO_ROOT


@task
def check(context: Context) -> None:
    """Check the workspace dependency graph with cargo-deny."""
    with context.cd(str(REPO_ROOT)):
        result = context.run(
            "cargo deny check advisories licenses bans sources",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("cargo-deny reported findings — see output", code=1)
