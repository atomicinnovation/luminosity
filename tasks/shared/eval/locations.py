from typing import TYPE_CHECKING

from tasks.shared.paths import REPO_ROOT

if TYPE_CHECKING:
    from pathlib import Path

EVALS_SKILLS_DIR = REPO_ROOT / "tests" / "evals" / "skills"


def results_dir(skill: str) -> Path:
    return EVALS_SKILLS_DIR / skill / "results"


def viewer_log_dir(skill: str | None) -> Path:
    return results_dir(skill) if skill else EVALS_SKILLS_DIR
