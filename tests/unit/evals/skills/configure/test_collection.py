from pathlib import Path

from inspect_ai import Task
from inspect_ai._eval.loader import load_tasks

from common.eval import baseline_arm, with_skill_arm
from tests.evals.skills.configure import configure_eval

_EVAL_FILE = Path(configure_eval.__file__).resolve()
_WITH_SKILL = with_skill_arm(configure_eval.SKILL)
_BASELINE = baseline_arm(configure_eval.SKILL)


class TestTaskConstruction:
    def test_with_skill_arm_constructs(self):
        task = configure_eval.configure_with_skill()
        assert isinstance(task, Task)
        assert task.name == _WITH_SKILL

    def test_baseline_arm_constructs(self):
        task = configure_eval.configure_baseline()
        assert isinstance(task, Task)
        assert task.name == _BASELINE


class TestFilePathLoader:
    def test_both_arms_resolve_by_specifier(self):
        tasks = load_tasks(
            [f"{_EVAL_FILE}@{_WITH_SKILL}", f"{_EVAL_FILE}@{_BASELINE}"]
        )
        assert {task.name for task in tasks} == {_WITH_SKILL, _BASELINE}


class TestNonCollection:
    def test_pytest_collects_no_eval_definition_files(self):
        eval_tree = _EVAL_FILE.parents[2]
        assert eval_tree.name == "evals"
        assert list(eval_tree.rglob("test_*.py")) == []
        assert list(eval_tree.rglob("*_test.py")) == []
