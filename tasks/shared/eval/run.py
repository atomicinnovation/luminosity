import os
import platform
import sys
import tempfile
from pathlib import Path

from invoke import Context, Exit

from common.eval import PLUGIN_DIR_ENV, baseline_arm, with_skill_arm
from tasks.shared.eval import readback, staging
from tasks.shared.eval.locations import EVALS_SKILLS_DIR, results_dir
from tasks.shared.eval.workdirs import cleanup_workdirs
from tasks.shared.paths import REPO_ROOT, binary_path

_STAGING_DIR = REPO_ROOT / "cli" / "target" / "eval-plugin"
_MAX_CONCURRENT_SAMPLES = 4


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _host_binary() -> Path:
    machine = platform.machine()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    os_name = "darwin" if platform.system() == "Darwin" else "linux"
    return binary_path(f"{os_name}-{arch}")


def _tmp_dirs() -> set[str]:
    tmp = Path(tempfile.gettempdir())
    return {str(tmp), str(tmp.resolve())}


def _preflight_claude(context: Context) -> None:
    probe = context.run("claude --version", warn=True, pty=False, hide=True)
    if probe.exited != 0:
        raise Exit(
            "eval: `claude` is not runnable — run "
            "`mise run deps:install:claude-native`, then `claude login`",
            code=1,
        )


def run_skill_eval(context: Context, skill: str) -> float:
    from inspect_ai import eval as inspect_eval  # noqa: PLC0415  (heavy; lazy)

    _preflight_claude(context)
    _ensure_repo_on_path()
    os.environ[PLUGIN_DIR_ENV] = str(
        staging.stage_plugin(
            repo_root=REPO_ROOT, host_binary=_host_binary(), dest=_STAGING_DIR
        )
    )
    eval_file = EVALS_SKILLS_DIR / skill / f"{skill}_eval.py"
    results = results_dir(skill)
    results.mkdir(parents=True, exist_ok=True)
    with_arm, base_arm = with_skill_arm(skill), baseline_arm(skill)
    logs = inspect_eval(
        [f"{eval_file}@{with_arm}", f"{eval_file}@{base_arm}"],
        log_format="json",
        log_dir=str(results),
        max_samples=_MAX_CONCURRENT_SAMPLES,
    )
    with_skill = readback.require_success(readback.arm_log(logs, with_arm))
    baseline = readback.require_success(readback.arm_log(logs, base_arm))
    with_skill_fraction = readback.pass_k(with_skill)
    if with_skill_fraction <= readback.pass_k(baseline):
        print(
            f"eval: {skill} with-skill did not beat baseline "
            f"— investigate whether the skill adds value"
        )
    readback.scrub_result_dir(
        results,
        repo_root=str(REPO_ROOT),
        home=str(Path.home()),
        tmp_dirs=_tmp_dirs(),
    )
    cleanup_workdirs(Path(tempfile.gettempdir()))
    return with_skill_fraction
