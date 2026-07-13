"""Pin how a skill's eval run is assembled and how its arms are named.

A skill's eval directory holds its paired-arm eval (`<skill>_eval.py`, the
skill-vs-baseline comparison) and a `<capability>_eval.py` for any capability
whose grading model does not fit that pairing. All of them ride the one
`eval:skills:<skill>` run, all must clear the pass^k floor, and all share one
arm vocabulary — `<skill>[_<capability>]_<control>` — so no arm's name leaves
you guessing which skill it covers or whether the skill was loaded.
"""

from typing import TYPE_CHECKING

from tasks.shared.eval.locations import EVALS_SKILLS_DIR
from tasks.shared.eval.run import supplementary_arm, supplementary_capabilities
from tests.evals.skills.configure import context_eval

if TYPE_CHECKING:
    from pathlib import Path


class TestSupplementaryCapabilities:
    def test_the_skills_own_eval_is_not_a_capability(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "configure_eval.py").touch()
        assert supplementary_capabilities(tmp_path / "configure_eval.py") == []

    def test_a_sibling_eval_names_a_capability(self, tmp_path: Path) -> None:
        (tmp_path / "configure_eval.py").touch()
        (tmp_path / "context_eval.py").touch()
        assert supplementary_capabilities(tmp_path / "configure_eval.py") == [
            "context"
        ]

    def test_capabilities_are_ordered_deterministically(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "configure_eval.py").touch()
        for name in ("zeta_eval.py", "alpha_eval.py"):
            (tmp_path / name).touch()
        assert supplementary_capabilities(tmp_path / "configure_eval.py") == [
            "alpha",
            "zeta",
        ]

    def test_non_eval_modules_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "configure_eval.py").touch()
        for name in ("scorer.py", "solvers.py", "environment.py"):
            (tmp_path / name).touch()
        assert supplementary_capabilities(tmp_path / "configure_eval.py") == []

    def test_the_context_eval_rides_the_configure_run(self) -> None:
        # The real wiring: context injection is graded inside
        # eval:skills:configure, not under an eval task of its own.
        configure_eval = EVALS_SKILLS_DIR / "configure" / "configure_eval.py"
        assert supplementary_capabilities(configure_eval) == ["context"]


class TestSupplementaryArm:
    def test_names_the_skill_the_capability_and_the_control(self) -> None:
        assert (
            supplementary_arm("configure", "context")
            == "configure_context_with_skill"
        )

    def test_the_task_function_name_matches_the_arm_it_declares(self) -> None:
        # Inspect resolves a task by its function name (`file@task`), while
        # arm_log matches on the Task's name. A drift between the two would
        # surface as an unresolvable task at the start of a live run.
        arm = supplementary_arm(context_eval.SKILL, context_eval.CAPABILITY)
        assert hasattr(context_eval, arm)
