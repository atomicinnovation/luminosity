import re
from typing import TYPE_CHECKING

from common.eval import (
    ACCURACY_METRIC,
    TRIALS,
    WORKDIR_PREFIX,
    pass_k_reducer,
)
from tasks.shared.errors import EvalReadbackError
from tasks.shared.files import atomic_write_text

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from inspect_ai.log import EvalLog

_PASS_K_REDUCER = pass_k_reducer(TRIALS)

_MACHINE_SPECIFIC_ROOTS = r"(?:/private)?/(?:Users|home|var/folders)/"
_UNSCRUBBED_WORKDIR = rf"/tmp/{WORKDIR_PREFIX}"  # noqa: S108  (a regex, not a path)

HOST_PATH_PATTERN = re.compile(
    rf"(?:{_MACHINE_SPECIFIC_ROOTS}|{_UNSCRUBBED_WORKDIR})[^\s\"';]*"
)


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


def scrub_paths(
    text: str, *, repo_root: str, home: str, tmp_dirs: Iterable[str] = ()
) -> str:
    replacements = [
        *((tmp_dir, "<tmp>") for tmp_dir in tmp_dirs),
        (repo_root, "."),
        (home, "~"),
    ]
    most_specific_first = sorted(
        replacements, key=lambda pair: len(pair[0]), reverse=True
    )
    for needle, replacement in most_specific_first:
        text = text.replace(needle, replacement)
    return text


def scrub_result_dir(
    results_dir: Path,
    *,
    repo_root: str,
    home: str,
    tmp_dirs: Iterable[str] = (),
) -> None:
    tmp_dirs = list(tmp_dirs)
    for log in results_dir.glob("*.json"):
        atomic_write_text(
            log,
            scrub_paths(
                log.read_text(),
                repo_root=repo_root,
                home=home,
                tmp_dirs=tmp_dirs,
            ),
        )
