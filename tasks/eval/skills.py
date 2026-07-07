import sys
from pathlib import Path

from invoke import Context, Exit, task

from tasks.eval import readback
from tasks.eval.gate import below_floor, live_run_enabled
from tasks.shared.paths import REPO_ROOT

_EVAL_DIR = REPO_ROOT / "tests" / "evals" / "skills" / "configure"
_EVAL_FILE = _EVAL_DIR / "configure_eval.py"
_RESULTS_DIR = _EVAL_DIR / "results"

# The sandbox is pinned to a single arch so the committed log is reproducible;
# on Apple Silicon this runs under Docker's amd64 emulation.
_DOCKER_PLATFORM = "linux/amd64"


def _ensure_repo_on_path() -> None:
    # Inspect's file-path loader loads configure_eval.py with no package context
    # and does not add cwd; its absolute `tests.evals.…` imports need the repo
    # root importable. Adjusting sys.path is not importing tests/ from here.
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _require_docker(context: Context) -> None:
    """Fail fast with an actionable message when Docker cannot run the sandbox.

    Guards the out-of-band prerequisite (Docker cannot be mise-pinned): both a
    dead daemon and — given the linux/amd64 pin — missing amd64 emulation on
    Apple Silicon, rather than failing deep inside Inspect's sandbox setup.
    """
    daemon = context.run("docker info", warn=True, pty=False, hide=True)
    if daemon.exited != 0:
        raise Exit(
            "eval:skills:configure: the Docker daemon is unreachable — "
            "start Docker and retry",
            code=1,
        )
    emulation = context.run(
        f"docker run --rm --platform {_DOCKER_PLATFORM} alpine true",
        warn=True,
        pty=False,
        hide=True,
    )
    if emulation.exited != 0:
        raise Exit(
            "eval:skills:configure: cannot run linux/amd64 containers — "
            "enable Docker Desktop's x86/amd64 emulation (Rosetta) and retry",
            code=1,
        )


def _run_configure_eval(context: Context) -> float:
    # Lazy: inspect_ai pulls in numpy/anthropic and is heavy — importing it at
    # module top would tax every unrelated `invoke` command.
    from inspect_ai import eval as inspect_eval  # noqa: PLC0415

    _require_docker(context)
    _ensure_repo_on_path()
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    logs = inspect_eval(
        [
            f"{_EVAL_FILE}@{readback.ARM_WITH_SKILL}",
            f"{_EVAL_FILE}@{readback.ARM_BASELINE}",
        ],
        log_format="json",
        log_dir=str(_RESULTS_DIR),
    )
    with_skill = readback.require_success(
        readback.arm_log(logs, readback.ARM_WITH_SKILL)
    )
    baseline = readback.require_success(
        readback.arm_log(logs, readback.ARM_BASELINE)
    )
    with_skill_fraction = readback.pass_k(with_skill)
    if with_skill_fraction <= readback.pass_k(baseline):
        print(
            "eval:skills:configure: with-skill did not beat baseline "
            "— investigate whether the skill adds value"
        )
    readback.scrub_result_dir(
        _RESULTS_DIR, repo_root=str(REPO_ROOT), home=str(Path.home())
    )
    return with_skill_fraction


@task
def configure(context: Context) -> None:
    """Run the configure skill eval and gate on the pass^k floor."""
    if not live_run_enabled():
        print(
            "LUMINOSITY_EVAL_LIVE is off; skipping the live configure eval run"
        )
        return
    pass_k = _run_configure_eval(context)
    if below_floor(pass_k):
        raise Exit(
            f"eval:skills:configure failed: pass^k {pass_k:.3f} is below "
            f"the floor",
            code=1,
        )
