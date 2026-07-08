from pathlib import Path

from inspect_ai import Task
from inspect_ai._eval.loader import load_tasks

from tests.evals.shared.names import ARM_BASELINE, ARM_WITH_SKILL
from tests.evals.skills.configure import configure_eval

_EVAL_FILE = Path(configure_eval.__file__).resolve()


class TestTaskConstruction:
    """Both arms build without raising (mockllm model needs no API key).

    Pins that the custom solver, scorer, and Epochs(k, pass_k(k)) reducer wire
    together into a Task.
    """

    def test_with_skill_arm_constructs(self):
        task = configure_eval.configure_with_skill()
        assert isinstance(task, Task)
        assert task.name == ARM_WITH_SKILL

    def test_baseline_arm_constructs(self):
        task = configure_eval.configure_baseline()
        assert isinstance(task, Task)
        assert task.name == ARM_BASELINE


class TestFilePathLoader:
    """The eval loads via Inspect's file-path loader (the live-run mechanism),
    not a plain pytest import, so the absolute-import form is confirmed cheaply.
    """

    def test_both_arms_resolve_by_specifier(self):
        tasks = load_tasks(
            [
                f"{_EVAL_FILE}@{ARM_WITH_SKILL}",
                f"{_EVAL_FILE}@{ARM_BASELINE}",
            ]
        )
        assert {task.name for task in tasks} == {ARM_WITH_SKILL, ARM_BASELINE}


class TestNonCollection:
    def test_pytest_collects_no_eval_definition_files(self):
        eval_tree = _EVAL_FILE.parents[2]
        assert eval_tree.name == "evals"
        assert list(eval_tree.rglob("test_*.py")) == []
        assert list(eval_tree.rglob("*_test.py")) == []
