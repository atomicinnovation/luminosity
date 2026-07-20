from pathlib import Path

from inspect_ai import Task
from inspect_ai._eval.loader import load_tasks

from common.eval import baseline_arm, with_skill_arm
from tests.evals.skills.configure import (
    context_eval,
    instructions_eval,
    values_eval,
)

_SKILL = values_eval.SKILL
_DIR = Path(values_eval.__file__).resolve().parent

_VALUES_WITH_SKILL = with_skill_arm(_SKILL, values_eval.CAPABILITY)
_VALUES_BASELINE = baseline_arm(_SKILL, values_eval.CAPABILITY)
_CONTEXT_WITH_SKILL = with_skill_arm(_SKILL, context_eval.CAPABILITY)
_INSTRUCTIONS_WITH_SKILL = with_skill_arm(_SKILL, instructions_eval.CAPABILITY)


def _spec(capability: str, arm: str) -> str:
    return f"{_DIR / f'{capability}_eval.py'}@{arm}"


class TestTaskConstruction:
    def test_values_with_skill_arm_constructs(self):
        task = values_eval.configure_values_with_skill()
        assert isinstance(task, Task)
        assert task.name == _VALUES_WITH_SKILL

    def test_values_baseline_arm_constructs(self):
        task = values_eval.configure_values_baseline()
        assert isinstance(task, Task)
        assert task.name == _VALUES_BASELINE

    def test_context_with_skill_arm_constructs(self):
        task = context_eval.configure_context_with_skill()
        assert isinstance(task, Task)
        assert task.name == _CONTEXT_WITH_SKILL

    def test_context_declares_no_baseline_arm(self):
        # Passive injection has no no-skill control: without the skill there is
        # no prompt to inject into. The absent arm is the point, not an
        # omission.
        assert not hasattr(
            context_eval, baseline_arm(_SKILL, context_eval.CAPABILITY)
        )

    def test_instructions_with_skill_arm_constructs(self):
        task = instructions_eval.configure_instructions_with_skill()
        assert isinstance(task, Task)
        assert task.name == _INSTRUCTIONS_WITH_SKILL

    def test_instructions_declares_no_baseline_arm(self):
        assert not hasattr(
            instructions_eval,
            baseline_arm(_SKILL, instructions_eval.CAPABILITY),
        )


class TestFilePathLoader:
    def test_every_declared_arm_resolves_by_specifier(self):
        tasks = load_tasks(
            [
                _spec(values_eval.CAPABILITY, _VALUES_WITH_SKILL),
                _spec(values_eval.CAPABILITY, _VALUES_BASELINE),
                _spec(context_eval.CAPABILITY, _CONTEXT_WITH_SKILL),
                _spec(instructions_eval.CAPABILITY, _INSTRUCTIONS_WITH_SKILL),
            ]
        )
        assert {task.name for task in tasks} == {
            _VALUES_WITH_SKILL,
            _VALUES_BASELINE,
            _CONTEXT_WITH_SKILL,
            _INSTRUCTIONS_WITH_SKILL,
        }


class TestNonCollection:
    def test_pytest_collects_no_eval_definition_files(self):
        eval_tree = _DIR.parents[1]
        assert eval_tree.name == "evals"
        assert list(eval_tree.rglob("test_*.py")) == []
        assert list(eval_tree.rglob("*_test.py")) == []
