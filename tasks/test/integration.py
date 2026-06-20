import os

from invoke import Context, Exit, task

from tasks.shared.sources import repo_root

_EXPECTED_SUITES = 19


def run_shell_suites(context: Context, subtree: str) -> list[str]:
    """Glob-discover and run every executable test-*.sh inside a subtree.

    Returns the sorted list of suites that were discovered and run, so a
    caller can assert a non-zero discovery count and fail loudly if an
    exec bit was dropped (e.g. on an exec-bit-lossy filesystem) rather
    than silently skipping its regression net.
    """
    repo = repo_root()
    root = repo / subtree
    if not root.exists():
        return []
    suites = sorted(
        p.relative_to(repo).as_posix()
        for p in root.glob("**/test-*.sh")
        if p.is_file() and os.access(p, os.X_OK)
    )
    for suite in suites:
        print(f"Running {suite}...")
        context.run(suite)
        print()
    return suites


@task
def scripts(context: Context) -> None:
    """Integration tests for the plugin-wide scripts."""
    suites = run_shell_suites(context, "scripts")
    if len(suites) < _EXPECTED_SUITES:
        raise Exit(
            f"Expected at least {_EXPECTED_SUITES} shell suites, found "
            f"{len(suites)}: {suites}. An exec bit may have been dropped — "
            f"a fail-closed gate is missing from CI.",
            code=1,
        )
