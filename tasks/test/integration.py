from invoke import Context, Exit, task

from tasks.shared.sources import repo_root


@task
def scripts(context: Context) -> None:
    """Run the pytest integration suite for the shell wrappers."""
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/integration/scripts -v",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("integration script tests failed", code=1)


@task
def tasks(context: Context) -> None:
    """Run the pytest integration suite for the invoke tasks."""
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/integration/tasks -v",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("integration task tests failed", code=1)


@task
def deny(context: Context) -> None:
    """Run the cargo-deny ban-violation regression suite."""
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/integration/deny -v",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("cargo-deny ban regression failed", code=1)


@task
def pup(context: Context) -> None:
    """Run the cargo-pup behavioural regression (needs the nightly lane).

    Isolated in tests/integration/pup/ — not the general suite — because it
    needs the nightly + cargo-pup; it runs only in the check-architecture job,
    which provisions them.
    """
    with context.cd(str(repo_root())):
        result = context.run(
            "uv run pytest tests/integration/pup -v",
            warn=True,
            pty=False,
        )
    if result.exited != 0:
        raise Exit("cargo-pup behavioural regression failed", code=1)
