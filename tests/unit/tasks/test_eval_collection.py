from pathlib import Path

import pytest
from inspect_ai import Task
from inspect_ai._eval.loader import load_tasks

from tests.evals.shared.names import ARM_BASELINE, ARM_WITH_SKILL
from tests.evals.skills.configure import configure_eval

_EVAL_FILE = Path(configure_eval.__file__).resolve()


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    # Constructing a Task with model="anthropic/…" eagerly initialises the
    # provider client, which needs the key present (never called here). A dummy
    # keeps the construction test hermetic on a keyless CI runner.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-construction-only")


class TestTaskConstruction:
    """Both arms build against the pinned claude_code signature without raising.

    Pins that version=, message_limit, time_limit, fail_on_error, and the
    Epochs(k, pass_k(k)) reducer are all accepted.
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
