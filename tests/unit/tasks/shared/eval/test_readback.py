from types import SimpleNamespace
from typing import Any

import pytest

from common.eval import (
    TRIALS,
    WORKDIR_PREFIX,
    baseline_arm,
    pass_k_reducer,
    with_skill_arm,
)
from tasks.shared.errors import EvalReadbackError
from tasks.shared.eval import readback
from tasks.shared.eval.readback import HOST_PATH_PATTERN as _ABSOLUTE_HOST_PATH


def _metric(value: float) -> Any:
    return SimpleNamespace(value=value)


def _score(reducer: str, accuracy: float) -> Any:
    return SimpleNamespace(
        reducer=reducer, metrics={"accuracy": _metric(accuracy)}
    )


def _log(
    task: str, *, status: str = "success", scores: list[Any] | None = None
) -> Any:
    results = None if scores is None else SimpleNamespace(scores=scores)
    return SimpleNamespace(
        eval=SimpleNamespace(task=task), status=status, results=results
    )


class TestArmLog:
    def test_selects_the_named_arm(self):
        logs = [_log("configure_with_skill"), _log("configure_baseline")]
        assert readback.arm_log(logs, "configure_baseline").eval.task == (
            "configure_baseline"
        )

    def test_missing_arm_raises(self):
        with pytest.raises(EvalReadbackError):
            readback.arm_log([_log("configure_with_skill")], "nope")


class TestRequireSuccess:
    def test_scored_success_passes(self):
        log = _log("a", scores=[_score("pass_k_3", 1.0)])
        assert readback.require_success(log) is log

    def test_non_success_status_raises(self):
        log = _log("a", status="error", scores=[_score("pass_k_3", 1.0)])
        with pytest.raises(EvalReadbackError):
            readback.require_success(log)

    def test_missing_results_raises(self):
        with pytest.raises(EvalReadbackError):
            readback.require_success(_log("a", scores=None))


class TestPassK:
    def test_reads_accuracy_over_the_pass_k_reducer(self):
        log = _log("a", scores=[_score("mean", 0.5), _score("pass_k_3", 0.8)])
        assert readback.pass_k(log) == 0.8

    def test_missing_pass_k_reducer_raises_never_defaults(self):
        log = _log("a", scores=[_score("mean", 1.0)])
        with pytest.raises(EvalReadbackError):
            readback.pass_k(log)

    def test_missing_accuracy_metric_raises(self):
        bad = SimpleNamespace(
            reducer="pass_k_3", metrics={"stderr": _metric(0)}
        )
        with pytest.raises(EvalReadbackError):
            readback.pass_k(_log("a", scores=[bad]))


class TestScrubPaths:
    HOME = "/Users/dev"
    REPO = f"{HOME}/Code/luminosity"
    TMP = "/var/folders/yn/hashed0000gn/T"
    REAL_TMP = f"/private{TMP}"

    def _scrub(self, text: str) -> str:
        return readback.scrub_paths(
            text,
            repo_root=self.REPO,
            home=self.HOME,
            tmp_dirs=[self.TMP, self.REAL_TMP],
        )

    def test_relativises_repo_and_home_paths(self):
        text = (
            f'{{"eval": "{self.REPO}/tests/evals/x.json", '
            f'"cache": "{self.HOME}/.cache/inspect"}}'
        )
        scrubbed = self._scrub(text)
        assert self.HOME not in scrubbed
        assert "./tests/evals/x.json" in scrubbed
        assert "~/.cache/inspect" in scrubbed

    def test_relativises_the_sample_workdir_outside_home(self):
        text = f'{{"workdir": "{self.TMP}/configure-eval-abc"}}'
        assert self._scrub(text) == '{"workdir": "<tmp>/configure-eval-abc"}'

    def test_relativises_the_resolved_tmp_prefix(self):
        text = f'{{"stderr": "{self.REAL_TMP}/configure-eval-abc/.luminosity"}}'
        scrubbed = self._scrub(text)
        assert self.REAL_TMP not in scrubbed
        assert "<tmp>/configure-eval-abc/.luminosity" in scrubbed

    def test_no_absolute_host_path_survives(self):
        text = " ".join(
            [
                f"{self.REPO}/tests",
                f"{self.HOME}/.cache",
                f"{self.TMP}/w",
                f"{self.REAL_TMP}/w",
            ]
        )
        assert _ABSOLUTE_HOST_PATH.search(self._scrub(text)) is None


class TestHostPathPattern:
    def test_flags_machine_specific_roots(self):
        for path in (
            "/Users/dev/Code/x",
            "/home/dev/Code/x",
            "/var/folders/yn/hashed/T/w",
            "/private/var/folders/yn/hashed/T/w",
            f"/tmp/{WORKDIR_PREFIX}abc123",
        ):
            assert _ABSOLUTE_HOST_PATH.search(path) is not None, path

    def test_ignores_agent_authored_paths_that_carry_no_machine_identity(self):
        for path in (
            "/tmp/out.txt",
            "/tmp/err.txt",
            "/usr/bin/env",
            "/etc/hosts",
        ):
            assert _ABSOLUTE_HOST_PATH.search(path) is None, path


class TestSharedContract:
    def test_reducer_name_matches_the_trial_count(self):
        assert pass_k_reducer(TRIALS) == "pass_k_3"

    def test_arm_naming_convention(self):
        assert with_skill_arm("configure") == "configure_with_skill"
        assert baseline_arm("configure") == "configure_baseline"
