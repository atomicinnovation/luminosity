from invoke import Context, task

_ARTIFACT_MARKERS = (".key", "cli/launcher/bin/luminosity-", "manifest.minisig")


@task
def no_leaked_artifacts(context: Context) -> None:
    """Abort if a signing secret or staged binary would leak into a commit."""
    result = context.run("git status --porcelain", hide=True, warn=True)
    offenders = [
        line
        for line in result.stdout.splitlines()
        if any(marker in line for marker in _ARTIFACT_MARKERS)
    ]
    if offenders:
        joined = "\n".join(offenders)
        raise RuntimeError(
            "refusing to commit: a signing secret or staged binary would be "
            f"swept into the version-bump commit:\n{joined}"
        )
