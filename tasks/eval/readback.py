"""Read the pass^k fraction back off an Inspect eval log, and scrub host paths.

The `tasks/` package cannot import the non-packaged `tests/` tree, so the arm /
reducer / metric identifiers are literals here; `test_eval_readback` asserts
they equal `tests/evals/shared/names.py`, turning a rename into a test failure.
"""

from typing import TYPE_CHECKING

from tasks.shared.errors import EvalReadbackError

if TYPE_CHECKING:
    from pathlib import Path

    from inspect_ai.log import EvalLog

ARM_WITH_SKILL = "configure_with_skill"
ARM_BASELINE = "configure_baseline"
# inspect-ai names the pass_k reducer `pass_k_<k>`; with epochs == k its
# `accuracy` metric IS pass^k — the fraction of tasks passing all k trials.
PASS_K_REDUCER = "pass_k_3"  # noqa: S105 (a reducer name, not a secret)
ACCURACY_METRIC = "accuracy"


def arm_log(logs: list[EvalLog], name: str) -> EvalLog:
    for log in logs:
        if log.eval.task == name:
            return log
    raise EvalReadbackError(f"no eval log for arm {name!r}")


def require_success(log: EvalLog) -> EvalLog:
    """Return the log iff it ran to a scored success, else raise.

    Guards against reading a passing fraction off an errored/cancelled run over
    a partial sample set (paired with fail_on_error so a dropped epoch fails).
    """
    if log.status != "success" or log.results is None:
        raise EvalReadbackError(
            f"eval arm {log.eval.task!r} did not succeed "
            f"(status={log.status!r})"
        )
    return log


def pass_k(log: EvalLog) -> float:
    """Return the pass^k fraction: `accuracy` over the `pass_k_<k>` reducer.

    Its metric name is `accuracy`, but over the pass_k reducer its meaning *is*
    pass^k, not a lenient mean. Raises (never defaults to a passing value) when
    no such record is present, so a reducer/metric-name drift fails loudly.
    """
    for score in log.results.scores:
        if score.reducer == PASS_K_REDUCER:
            metric = score.metrics.get(ACCURACY_METRIC)
            if metric is not None:
                return metric.value
    raise EvalReadbackError(
        f"no {PASS_K_REDUCER!r}/{ACCURACY_METRIC!r} record in "
        f"arm {log.eval.task!r}"
    )


def scrub_paths(text: str, *, repo_root: str, home: str) -> str:
    """Relativise absolute host paths so a committed log is environment-free.

    Repo paths become repo-relative; any remaining home-rooted path collapses to
    `~`, so the durable artifact carries no developer's home directory.
    """
    return text.replace(repo_root, ".").replace(home, "~")


def scrub_result_dir(results_dir: Path, *, repo_root: str, home: str) -> None:
    for log in results_dir.glob("*.json"):
        scrubbed = scrub_paths(log.read_text(), repo_root=repo_root, home=home)
        log.write_text(scrubbed)
