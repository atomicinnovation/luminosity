"""Pin how a skill's eval run is assembled.

A skill's eval directory holds its paired-arm eval (`<skill>_eval.py`, the
skill-vs-baseline comparison) and any supplementary single-arm evals whose
grading model does not fit that pairing. All of them must ride the one
`eval:skills:<skill>` run, and all must clear the pass^k floor.
"""

from typing import TYPE_CHECKING

from tasks.shared.eval.locations import EVALS_SKILLS_DIR
from tasks.shared.eval.run import supplementary_arms

if TYPE_CHECKING:
    from pathlib import Path


class TestSupplementaryArms:
    def test_the_skills_own_eval_is_not_a_supplementary_arm(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "configure_eval.py").touch()
        assert supplementary_arms(tmp_path / "configure_eval.py") == []

    def test_a_sibling_eval_is_discovered_by_its_stem(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "configure_eval.py").touch()
        (tmp_path / "context_eval.py").touch()
        assert supplementary_arms(tmp_path / "configure_eval.py") == ["context"]

    def test_siblings_are_ordered_deterministically(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "configure_eval.py").touch()
        for name in ("zeta_eval.py", "alpha_eval.py"):
            (tmp_path / name).touch()
        assert supplementary_arms(tmp_path / "configure_eval.py") == [
            "alpha",
            "zeta",
        ]

    def test_non_eval_modules_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "configure_eval.py").touch()
        for name in ("scorer.py", "solvers.py", "environment.py"):
            (tmp_path / name).touch()
        assert supplementary_arms(tmp_path / "configure_eval.py") == []

    def test_the_context_eval_rides_the_configure_run(self) -> None:
        # The real wiring: context injection is graded inside
        # eval:skills:configure, not under an eval task of its own.
        configure_eval = EVALS_SKILLS_DIR / "configure" / "configure_eval.py"
        assert supplementary_arms(configure_eval) == ["context"]
