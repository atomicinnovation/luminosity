import shlex
from typing import TYPE_CHECKING

from invoke import Context, Exit, task

from tasks.shared.sources import repo_root, shell_sources

if TYPE_CHECKING:
    from invoke.runners import Result


def _discovered_shell_sources_or_fail() -> list[str]:
    sources = shell_sources()
    if not sources:
        raise Exit(
            "shfmt: no shell sources matched — scope discovery is broken",
            code=1,
        )
    return sources


def _shfmt(context: Context, op_flags: str) -> Result:
    """Run shfmt over every shell source with only operation flags.

    No formatting flags (-i, -ci, …) are passed so shfmt reads `.editorconfig`
    as the single source of truth for style — passing CLI style flags would
    make shfmt ignore EditorConfig entirely and reintroduce local-vs-CI drift.
    """
    args = " ".join(shlex.quote(s) for s in _discovered_shell_sources_or_fail())
    with context.cd(str(repo_root())):
        return context.run(f"shfmt {op_flags} {args}", warn=True, pty=False)


@task
def check(context: Context) -> None:
    """Report shell files that are not shfmt-formatted (read-only)."""
    result = _shfmt(context, "-d")
    if result.exited != 0:
        raise Exit(
            "shfmt: formatting drift detected — run "
            "`mise run format:scripts:fix`",
            code=1,
        )


@task
def fix(context: Context) -> None:
    """Format shell files in place with shfmt, listing the changed files."""
    _shfmt(context, "-l -w")
