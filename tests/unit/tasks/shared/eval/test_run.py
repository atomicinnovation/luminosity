"""Pin how a skill's eval run is assembled and how its arms are named.

A skill's eval directory holds one `<capability>_eval.py` per capability it is
graded on. Every capability declares a with-skill arm; a baseline arm only where
a no-skill run is a genuine control. All of them ride the one
`eval:skills:<skill>` run, every with-skill arm must clear the pass^k floor, and
every arm names all three things that identify it — skill, capability, control —
so none of them leaves you guessing.
"""

from common.eval import baseline_arm, with_skill_arm
from tasks.shared.eval.run import arms, capabilities
from tests.evals.skills.configure import (
    context_eval,
    instructions_eval,
    values_eval,
)

_SKILL = "configure"


class TestCapabilities:
    def test_discovers_every_capability_of_the_skill(self) -> None:
        assert capabilities(_SKILL) == ["context", "instructions", "values"]

    def test_a_capability_is_named_by_its_eval_file(self) -> None:
        assert values_eval.CAPABILITY in capabilities(_SKILL)
        assert context_eval.CAPABILITY in capabilities(_SKILL)
        assert instructions_eval.CAPABILITY in capabilities(_SKILL)


class TestArms:
    def test_a_capability_with_a_control_declares_both_arms(self) -> None:
        assert arms(_SKILL, "values") == [
            "configure_values_with_skill",
            "configure_values_baseline",
        ]

    def test_a_capability_without_a_control_declares_only_with_skill(
        self,
    ) -> None:
        # Passive injection has no no-skill control: without the skill there is
        # no prompt to inject into. The absent arm is the point, not an
        # omission.
        assert arms(_SKILL, "context") == ["configure_context_with_skill"]

    def test_instructions_declares_only_with_skill(self) -> None:
        assert arms(_SKILL, "instructions") == [
            "configure_instructions_with_skill"
        ]

    def test_the_with_skill_arm_comes_first(self) -> None:
        assert arms(_SKILL, "values")[0] == with_skill_arm(_SKILL, "values")


class TestArmsMatchTheDeclaredTasks:
    # Inspect resolves a task by its function name (`file@task`), while readback
    # matches on the Task's name. A drift between the two would only surface as
    # an unresolvable task minutes into a live run.
    def test_every_arm_of_every_capability_is_a_declared_task(self) -> None:
        modules = {
            values_eval.CAPABILITY: values_eval,
            context_eval.CAPABILITY: context_eval,
            instructions_eval.CAPABILITY: instructions_eval,
        }
        for capability, module in modules.items():
            for arm in arms(_SKILL, capability):
                assert hasattr(module, arm), (
                    f"{capability} does not declare {arm}"
                )

    def test_the_context_module_declares_no_baseline_task(self) -> None:
        assert not hasattr(context_eval, baseline_arm(_SKILL, "context"))
