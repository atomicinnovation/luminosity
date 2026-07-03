import os
from pathlib import Path

import pathspec


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_under_workspaces(rel: str) -> bool:
    return rel.split("/", maxsplit=1)[0] == "workspaces"


def _is_in_scope(rel: str) -> bool:
    if not rel:
        return False
    return not _is_under_workspaces(rel)


_VCS_METADATA_DIRS = (".git/", ".jj/")


def _ignore_spec(repo: Path) -> pathspec.GitIgnoreSpec:
    # Only the root .gitignore is honoured, not nested ones — sufficient
    # because every ignored shell script lives under a root-ignored tree (e.g.
    # node_modules/); revisit with per-directory spec layering if a nested
    # .gitignore ever needs to hide a .sh file.
    gitignore = repo / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.is_file() else []
    return pathspec.GitIgnoreSpec.from_lines([*lines, *_VCS_METADATA_DIRS])


# Extensionless shell scripts the `*.sh` glob would miss. The bootstrap entry
# point is named for the command it fronts (`bin/luminosity`, not `*.sh`), so it
# is registered here explicitly — the bash-3.2 floor matters most on this file.
_EXTENSIONLESS_SHELL_SOURCES: tuple[str, ...] = ("bin/luminosity",)


def _is_ignored_dir(
    spec: pathspec.GitIgnoreSpec, rel_dir: Path, name: str
) -> bool:
    path = f"{name}/" if rel_dir == Path() else f"{rel_dir / name}/"
    return spec.match_file(path)


def _walk_for_shell_files(
    repo: Path, spec: pathspec.GitIgnoreSpec
) -> list[str]:
    # A filesystem walk, not `git ls-files`: git ls-files is blind inside a jj
    # workspace (git resolves to the parent repo, whose index does not track
    # the workspace), which silently emptied the scan and let unformatted
    # scripts reach CI. A walk behaves identically under git (CI) and jj.
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = Path(dirpath).relative_to(repo)
        dirnames[:] = [
            d for d in dirnames if not _is_ignored_dir(spec, rel_dir, d)
        ]
        for filename in filenames:
            if not filename.endswith(".sh"):
                continue
            rel = filename if rel_dir == Path() else str(rel_dir / filename)
            if not spec.match_file(rel) and _is_in_scope(rel):
                found.append(rel)
    return found


def _present_extensionless_sources(
    repo: Path, spec: pathspec.GitIgnoreSpec
) -> list[str]:
    return [
        source
        for source in _EXTENSIONLESS_SHELL_SOURCES
        if (repo / source).is_file()
        and _is_in_scope(source)
        and not spec.match_file(source)
    ]


def shell_sources(root: Path | None = None) -> list[str]:
    """In-scope shell sources, repo-relative and sorted.

    Gitignored directories are pruned during the walk so large ignored trees
    (e.g. `node_modules`) are never descended into.
    """
    repo = root or repo_root()
    spec = _ignore_spec(repo)
    walked = _walk_for_shell_files(repo, spec)
    extras = _present_extensionless_sources(repo, spec)
    return sorted([*walked, *extras])
