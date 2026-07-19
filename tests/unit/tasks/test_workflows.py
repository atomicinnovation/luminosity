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


PRERELEASE_GATE_JOB = "prerelease"
TEST_UNIT_JOB = "test-unit"
TEST_INTEGRATION_JOB = "test-integration"


def _run_commands(job: dict[str, Any]) -> list[str]:
    return [
        step["run"]
        for step in job.get("steps", [])
        if isinstance(step, dict) and "run" in step
    ]


def _matrix_os(job: dict[str, Any]) -> list[Any]:
    matrix = job.get("strategy", {}).get("matrix", {})
    return _as_list(matrix.get("os"))


def _job_runs_target(job: dict[str, Any], target: str) -> bool:
    return any(target in command for command in _run_commands(job))


def test_check_cli_job_runs_cli_check_and_gates_release(
    wf: dict[str, Any],
) -> None:
    jobs = wf["jobs"]
    assert _job_runs_target(jobs["check-cli"], "mise run cli:check")
    assert "check-cli" in _needs(jobs[PRERELEASE_GATE_JOB])


def test_build_launcher_job_is_a_dual_os_matrix_and_gates_release(
    wf: dict[str, Any],
) -> None:
    jobs = wf["jobs"]
    build_launcher = jobs["build-launcher"]
    assert _job_runs_target(build_launcher, "mise run build:launcher")
    assert set(_matrix_os(build_launcher)) == {"ubuntu-latest", "macos-latest"}
    assert "build-launcher" in _needs(jobs[PRERELEASE_GATE_JOB])


def test_check_supply_chain_job_runs_deny_and_gates_release(
    wf: dict[str, Any],
) -> None:
    jobs = wf["jobs"]
    assert _job_runs_target(jobs["check-supply-chain"], "mise run deny:check")
    assert "check-supply-chain" in _needs(jobs[PRERELEASE_GATE_JOB])


def test_check_architecture_job_runs_pup_and_the_regression(
    wf: dict[str, Any],
) -> None:
    jobs = wf["jobs"]
    architecture = jobs["check-architecture"]
    assert _job_runs_target(architecture, "mise run pup:check")
    assert _job_runs_target(architecture, "mise run test:integration:pup")
    assert "check-architecture" in _needs(jobs[PRERELEASE_GATE_JOB])


def test_existing_test_jobs_still_gate_release(wf: dict[str, Any]) -> None:
    jobs = wf["jobs"]
    assert _job_runs_target(jobs[TEST_UNIT_JOB], "mise run test:unit")
    assert _job_runs_target(
        jobs[TEST_INTEGRATION_JOB], "mise run test:integration"
    )
    needs = _needs(jobs[PRERELEASE_GATE_JOB])
    assert TEST_UNIT_JOB in needs
    assert TEST_INTEGRATION_JOB in needs


def test_test_unit_job_provisions_the_musl_toolchain_on_linux(
    wf: dict[str, Any],
) -> None:
    # test:unit:evals build:launcher:host-builds the single host musl triple;
    # its `ring` dependency's C build needs musl-tools, or cc-rs fails to find
    # x86_64-linux-musl-gcc. The step must be Linux-guarded — macOS builds a
    # darwin triple and has no apt-get.
    musl_steps = [
        step
        for step in _steps(wf["jobs"][TEST_UNIT_JOB])
        if "musl-tools" in step.get("run", "")
    ]
    assert len(musl_steps) == 1
    assert musl_steps[0].get("if") == "runner.os == 'Linux'"


RELEASE_STEP_SEQUENCE = ["prepare", "sign", "attest", "finalise"]
_RELEASE_SEQUENCE_REPETITIONS = {PRERELEASE_JOB: 1, RELEASE_JOB: 2}


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    return [step for step in job.get("steps", []) if isinstance(step, dict)]


def _step_kind(step: dict[str, Any]) -> str | None:
    run = step.get("run", "")
    if "attest-build-provenance" in step.get("uses", ""):
        return "attest"
    if ":prepare" in run:
        return "prepare"
    if ":sign" in run:
        return "sign"
    if ":finalise" in run:
        return "finalise"
    return None


def _release_step_kinds(job: dict[str, Any]) -> list[str]:
    kinds = (_step_kind(step) for step in _steps(job))
    return [kind for kind in kinds if kind is not None]


def _carries_signing_secret(step: dict[str, Any]) -> bool:
    env = step.get("env", {})
    return any(key != "GH_TOKEN" for key in env)


def _assert_sequence_ordering(job: dict[str, Any], repetitions: int) -> None:
    assert _release_step_kinds(job) == RELEASE_STEP_SEQUENCE * repetitions


def _assert_signing_secret_only_on_sign_steps(job: dict[str, Any]) -> None:
    for step in _steps(job):
        if _carries_signing_secret(step):
            assert ":sign" in step.get("run", ""), (
                f"{step.get('name')} carries the signing secret but does not "
                "run a :sign target"
            )


def _assert_release_step_topology(wf: dict[str, Any]) -> None:
    jobs = wf["jobs"]
    for job_name, repetitions in _RELEASE_SEQUENCE_REPETITIONS.items():
        job = jobs[job_name]
        _assert_sequence_ordering(job, repetitions)
        _assert_signing_secret_only_on_sign_steps(job)


def test_release_step_topology_holds(wf: dict[str, Any]) -> None:
    _assert_release_step_topology(wf)


def _leak_secret_onto_a_prepare_step(jobs: dict[str, Any]) -> None:
    for step in jobs[PRERELEASE_JOB]["steps"]:
        if ":prepare" in step.get("run", ""):
            step.setdefault("env", {})["MINISIGN_SECRET_KEY"] = "x"
            return


def _move_attest_before_sign(jobs: dict[str, Any]) -> None:
    steps = jobs[PRERELEASE_JOB]["steps"]
    sign_index = next(
        i for i, s in enumerate(steps) if ":sign" in s.get("run", "")
    )
    attest_index = next(
        i
        for i, s in enumerate(steps)
        if "attest-build-provenance" in s.get("uses", "")
    )
    steps.insert(sign_index, steps.pop(attest_index))


_KNOWN_BAD_STEP_SHAPES = [
    _leak_secret_onto_a_prepare_step,
    _move_attest_before_sign,
]


@pytest.mark.parametrize("introduce_violation", _KNOWN_BAD_STEP_SHAPES)
def test_step_topology_assertions_reject_each_known_bad_shape(
    wf: dict[str, Any],
    introduce_violation: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(wf)
    introduce_violation(bad["jobs"])
    with pytest.raises(AssertionError):
        _assert_release_step_topology(bad)


SIGNING_SECRET_ENV = "LUMINOSITY_RELEASE_SECRET_KEY"


def test_sign_steps_reference_the_release_secret_key(
    wf: dict[str, Any],
) -> None:
    for job_name in _RELEASE_SEQUENCE_REPETITIONS:
        sign_steps = [
            step
            for step in _steps(wf["jobs"][job_name])
            if ":sign" in step.get("run", "")
        ]
        assert sign_steps
        for step in sign_steps:
            assert SIGNING_SECRET_ENV in step.get("env", {})


def test_no_minisign_password_or_secret_env_remains() -> None:
    text = WORKFLOW.read_text()
    assert "MINISIGN_SECRET_KEY" not in text
    assert "MINISIGN_KEY_PASSWORD" not in text


APP_TOKEN_ACTION = "create-github-app-token"
APP_TOKEN_OUTPUT = "${{ steps.app-token.outputs.token }}"


def _app_token_step(job: dict[str, Any]) -> dict[str, Any] | None:
    for step in _steps(job):
        if APP_TOKEN_ACTION in step.get("uses", ""):
            return step
    return None


def _checkout_step(job: dict[str, Any]) -> dict[str, Any] | None:
    for step in _steps(job):
        if "actions/checkout" in step.get("uses", ""):
            return step
    return None


@pytest.mark.parametrize("job_name", [PRERELEASE_JOB, RELEASE_JOB])
def test_release_job_mints_and_checks_out_with_the_app_token(
    wf: dict[str, Any], job_name: str
) -> None:
    job = wf["jobs"][job_name]

    app_token = _app_token_step(job)
    assert app_token is not None
    assert app_token.get("id") == "app-token"
    provided = app_token.get("with", {})
    assert (
        provided.get("client-id") == "${{ vars.LUMINOSITY_RELEASER_CLIENT_ID }}"
    )
    assert (
        provided.get("private-key")
        == "${{ secrets.LUMINOSITY_RELEASER_SECRET }}"
    )

    checkout = _checkout_step(job)
    assert checkout is not None
    assert checkout.get("with", {}).get("token") == APP_TOKEN_OUTPUT
