import os

from invoke import Context, task

from . import build, changelog, git, github, marketplace, sign, version

_ARTIFACT_MARKERS = (".key", "cli/launcher/bin/luminosity-", "manifest.minisig")


def _refuse_under_ci(task_name: str) -> None:
    """Raise if called from a CI environment."""
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("CI"):
        raise RuntimeError(
            f"{task_name} is the local-dev convenience task; CI must use "
            f"the prepare/finalise split (mise run prerelease:prepare + "
            f"prerelease:finalise). Bypassing the split skips SLSA attestation."
        )


def _assert_no_leaked_artifacts(context: Context) -> None:
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


def _publish(context: Context) -> None:
    version.check(context)
    resolved_version = str(version.read(context, print_to_stdout=False))
    _assert_no_leaked_artifacts(context)
    git.commit_version(context)
    git.tag_version(context)
    git.push(context)
    github.create_release(context, target_version=resolved_version)
    github.upload_and_verify(context, resolved_version)


@task
def prerelease_sign(context: Context) -> None:
    """CI prerelease step 2: sign the staged binaries and manifest."""
    sign.sign(context)


@task
def release_sign(context: Context) -> None:
    """CI stable release step 2: sign the staged binaries and manifest."""
    sign.sign(context)


@task
def prerelease_prepare(context: Context) -> None:
    """CI prerelease part 1: bump version, cross-build binaries, checksum."""
    git.configure(context)
    git.pull(context)
    version.bump(context, bump_type=[version.BumpType.PRE])
    marketplace.update_prerelease_version(context, plugin="luminosity")
    build.release(context)


@task
def prerelease_finalise(context: Context) -> None:
    """CI prerelease part 2: commit, tag, push, release, publish."""
    _publish(context)


@task
def release_prepare(context: Context) -> None:
    """CI stable release part 1: finalise version, marketplace, changelog."""
    git.configure(context)
    git.pull(context)
    version.bump(context, bump_type=[version.BumpType.FINALISE])
    marketplace.update_version(context, plugin="luminosity")
    changelog.release(context)
    build.release(context)


@task
def release_finalise(context: Context) -> None:
    """CI stable release part 2: commit, tag, push, release, publish."""
    _publish(context)


@task
def prerelease(context: Context) -> None:
    """Local-dev only: full prerelease flow without SLSA attestation."""
    _refuse_under_ci("prerelease")
    prerelease_prepare(context)
    prerelease_sign(context)
    prerelease_finalise(context)


@task
def release(context: Context) -> None:
    """Local-dev only: full stable release flow without SLSA attestation."""
    _refuse_under_ci("release")
    release_prepare(context)
    release_sign(context)
    release_finalise(context)
    prerelease_prepare(context)
    prerelease_sign(context)
    prerelease_finalise(context)
