import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

if TYPE_CHECKING:
    from collections.abc import Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github/workflows/main.yml"

RELEASE_LOCK = "luminosity-release"
RELEASE_ENVIRONMENT = "release"
RELEASE_JOB = "release"
APPROVAL_GATE_JOB = "approve-release"
PRERELEASE_JOB = "prerelease"


def _as_list(value: str | list[Any] | None) -> list[Any]:
    return [value] if isinstance(value, str) else list(value or [])


def _needs(job: dict[str, Any]) -> list[Any]:
    return _as_list(job.get("needs"))


def _concurrency(job: dict[str, Any]) -> dict[str, Any]:
    declared = job.get("concurrency")
    if isinstance(declared, str):
        return {"group": declared}
    return declared if isinstance(declared, dict) else {}


def _is_approval_gated(job: dict[str, Any]) -> bool:
    return job.get("environment") is not None


def _holds_release_lock(job: dict[str, Any]) -> bool:
    return _concurrency(job).get("group") == RELEASE_LOCK


def _no_approval_gated_job_holds_the_release_lock(
    jobs: dict[str, Any],
) -> None:
    for name, job in jobs.items():
        if _is_approval_gated(job):
            assert not _holds_release_lock(job), (
                f"{name} is approval-gated AND holds the release lock — "
                "the original bug"
            )


def _release_runs_only_after_approval(jobs: dict[str, Any]) -> None:
    """Assert the approval topology by job name.

    prerelease and release carry identical write permissions, so nothing but
    the names tells them apart; the name-agnostic lock invariant above
    backstops a careless rename.
    """
    assert jobs[APPROVAL_GATE_JOB].get("environment") == RELEASE_ENVIRONMENT
    assert APPROVAL_GATE_JOB in _needs(jobs[RELEASE_JOB])
    assert PRERELEASE_JOB in _needs(jobs[APPROVAL_GATE_JOB])


def _approval_gate_holds_no_concurrency_group(
    jobs: dict[str, Any],
) -> None:
    assert "concurrency" not in jobs[APPROVAL_GATE_JOB], (
        "a concurrency group on the approval gate would be held for the whole "
        "approval wait, blocking every later push's gate from reaching its "
        "prompt — the original approval-lane bug"
    )


def _both_release_lock_members_serialise(jobs: dict[str, Any]) -> None:
    members = [
        _concurrency(job) for job in jobs.values() if _holds_release_lock(job)
    ]
    assert len(members) == 2, f"expected 2 lock members, got {len(members)}"
    for member in members:
        assert member.get("queue") == "max"
        assert member.get("cancel-in-progress") is False


def _assert_release_topology(wf: dict[str, Any]) -> None:
    jobs = wf["jobs"]
    _no_approval_gated_job_holds_the_release_lock(jobs)
    _release_runs_only_after_approval(jobs)
    _approval_gate_holds_no_concurrency_group(jobs)
    _both_release_lock_members_serialise(jobs)


@pytest.fixture
def wf() -> dict[str, Any]:
    return yaml.safe_load(WORKFLOW.read_text())


def test_release_topology_holds(wf: dict[str, Any]) -> None:
    _assert_release_topology(wf)


def _regate_the_lock_holding_release_job(jobs: dict[str, Any]) -> None:
    jobs[RELEASE_JOB]["environment"] = RELEASE_ENVIRONMENT


def _make_gate_hold_lock_via_string_shorthand(
    jobs: dict[str, Any],
) -> None:
    jobs[APPROVAL_GATE_JOB]["concurrency"] = RELEASE_LOCK


def _drop_queue_from_lock(jobs: dict[str, Any]) -> None:
    jobs[RELEASE_JOB]["concurrency"].pop("queue")


def _put_a_dedicated_group_on_the_approval_gate(
    jobs: dict[str, Any],
) -> None:
    jobs[APPROVAL_GATE_JOB]["concurrency"] = {
        "group": "luminosity-release-approval",
        "cancel-in-progress": False,
    }


def _let_the_lock_cancel_in_progress(jobs: dict[str, Any]) -> None:
    jobs[RELEASE_JOB]["concurrency"]["cancel-in-progress"] = True


def _remove_the_approval_edge(jobs: dict[str, Any]) -> None:
    edges: list[Any] = []
    jobs[APPROVAL_GATE_JOB]["needs"] = edges


_KNOWN_BAD_SHAPES = [
    _regate_the_lock_holding_release_job,
    _make_gate_hold_lock_via_string_shorthand,
    _drop_queue_from_lock,
    _put_a_dedicated_group_on_the_approval_gate,
    _let_the_lock_cancel_in_progress,
    _remove_the_approval_edge,
]


@pytest.mark.parametrize("introduce_violation", _KNOWN_BAD_SHAPES)
def test_topology_assertions_reject_each_known_bad_shape(
    wf: dict[str, Any],
    introduce_violation: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(wf)
    introduce_violation(bad["jobs"])
    with pytest.raises(AssertionError):
        _assert_release_topology(bad)
