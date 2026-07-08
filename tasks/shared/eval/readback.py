from typing import TYPE_CHECKING

from common.eval import ACCURACY_METRIC, TRIALS, pass_k_reducer
from tasks.shared.errors import EvalReadbackError

if TYPE_CHECKING:
    from pathlib import Path

    from inspect_ai.log import EvalLog

_PASS_K_REDUCER = pass_k_reducer(TRIALS)


def arm_log(logs: list[EvalLog], name: str) -> EvalLog:
    for log in logs:
        if log.eval.task == name:
            return log
    raise EvalReadbackError(f"no eval log for arm {name!r}")


def require_success(log: EvalLog) -> EvalLog:
    if log.status != "success" or log.results is None:
        raise EvalReadbackError(
            f"eval arm {log.eval.task!r} did not succeed "
            f"(status={log.status!r})"
        )
    return log


def pass_k(log: EvalLog) -> float:
    for score in log.results.scores:
        if score.reducer == _PASS_K_REDUCER:
            metric = score.metrics.get(ACCURACY_METRIC)
            if metric is not None:
                return metric.value
    raise EvalReadbackError(
        f"no {_PASS_K_REDUCER!r}/{ACCURACY_METRIC!r} record in "
        f"arm {log.eval.task!r}"
    )


def scrub_paths(text: str, *, repo_root: str, home: str) -> str:
    return text.replace(repo_root, ".").replace(home, "~")


def scrub_result_dir(results_dir: Path, *, repo_root: str, home: str) -> None:
    for log in results_dir.glob("*.json"):
        scrubbed = scrub_paths(log.read_text(), repo_root=repo_root, home=home)
        log.write_text(scrubbed)
