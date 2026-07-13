import json
from pathlib import Path
from typing import Any

import pytest

from common.eval import (
    ACCURACY_METRIC,
    TRIALS,
    baseline_arm,
    pass_k_reducer,
    with_skill_arm,
)
from tasks.shared.eval.gate import PASS_K_FLOOR
from tasks.shared.eval.readback import HOST_PATH_PATTERN
from tests.evals.skills.configure import context_eval, values_eval
from tests.evals.skills.configure.solvers import CLAUDE_MODEL

_SKILL = values_eval.SKILL
_RESULTS = Path(values_eval.__file__).parent / "results"
_LOGS = sorted(_RESULTS.glob("*.json"))

type Json = dict[str, Any]


def _log(path: Path) -> Json:
    return json.loads(path.read_text())


def _reducer_metrics(log: Json, reducer: str) -> Json:
    for score in log["results"]["scores"]:
        if score["reducer"] == reducer:
            return score["metrics"]
    pytest.fail(f"no {reducer!r} record in {log['eval']['task']!r}")


def test_the_committed_logs_exist():
    assert _LOGS, "the live run's eval logs are the story's durable signal"


@pytest.mark.parametrize("path", _LOGS, ids=lambda p: p.stem)
class TestCommittedLog:
    def test_carries_no_absolute_host_path(self, path: Path):
        leaked = sorted(set(HOST_PATH_PATTERN.findall(path.read_text())))
        assert leaked == [], f"unscrubbed host paths in {path.name}: {leaked}"

    def test_records_the_agent_model_and_cli_version(self, path: Path):
        for sample in _log(path)["samples"]:
            metadata = sample["metadata"]
            assert metadata["claude_model"] == CLAUDE_MODEL
            assert metadata["claude_cli_version"]

    def test_is_a_successful_scored_run(self, path: Path):
        log = _log(path)
        assert log["status"] == "success"
        assert (
            log["results"]["completed_samples"]
            == (log["results"]["total_samples"])
        )


class TestCommittedGate:
    def _arm(self, name: str) -> Json:
        for path in _LOGS:
            log = _log(path)
            if log["eval"]["task"] == name:
                return log
        pytest.fail(f"no committed log for arm {name!r}")

    @pytest.mark.parametrize(
        "capability", [values_eval.CAPABILITY, context_eval.CAPABILITY]
    )
    def test_every_with_skill_arm_clears_the_floor(self, capability: str):
        metrics = _reducer_metrics(
            self._arm(with_skill_arm(_SKILL, capability)),
            pass_k_reducer(TRIALS),
        )
        assert metrics[ACCURACY_METRIC]["value"] >= PASS_K_FLOOR

    def test_the_values_arm_beats_its_baseline(self):
        # Only `values` has a baseline: an agent without the skill can still
        # reach for the CLI. Injection has no such control.
        reducer = pass_k_reducer(TRIALS)
        capability = values_eval.CAPABILITY
        with_skill = _reducer_metrics(
            self._arm(with_skill_arm(_SKILL, capability)), reducer
        )
        baseline = _reducer_metrics(
            self._arm(baseline_arm(_SKILL, capability)), reducer
        )
        assert (
            with_skill[ACCURACY_METRIC]["value"]
            > baseline[ACCURACY_METRIC]["value"]
        )
