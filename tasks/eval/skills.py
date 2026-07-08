import os
import platform
import sys
from pathlib import Path

from invoke import Context, Exit, task

from tasks.eval import readback, staging
from tasks.eval.gate import below_floor, live_run_enabled
from tasks.shared.paths import REPO_ROOT, binary_path

_EVAL_DIR = REPO_ROOT / "tests" / "evals" / "skills" / "configure"
_EVAL_FILE = _EVAL_DIR / "configure_eval.py"
_RESULTS_DIR = _EVAL_DIR / "results"
_STAGING_DIR = REPO_ROOT / "cli" / "target" / "eval-plugin"

# The env var the eval solver + scorer read to find the staged plugin (its
# bin/luminosity is the real launcher, and its dir is claude's --plugin-dir).
PLUGIN_DIR_ENV = "LUMINOSITY_EVAL_PLUGIN_DIR"

# Bound concurrent `claude -p` sessions so the subscription's rate limits are
# not tripped (fail_on_error would otherwise fail the whole run on a 429).
_MAX_CONCURRENT_SAMPLES = 4


def _ensure_repo_on_path() -> None:
    # Inspect's file-path loader loads configure_eval.py with no package context
    # and does not add cwd; its absolute `tests.evals.…` imports need the repo
    # root importable. Adjusting sys.path is not importing tests/ from here.
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _host_binary() -> Path:
    machine = platform.machine()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    os_name = "darwin" if platform.system() == "Darwin" else "linux"
    return binary_path(f"{os_name}-{arch}")


def _preflight_claude(context: Context) -> None:
    """Fail fast with an actionable message when the pinned claude cannot run.

    Guards the out-of-band prerequisite: the native binary must be provisioned
    (deps:install:claude-native) and the CLI authenticated (a Claude
    subscription login), rather than failing deep inside a per-sample run.
    """
    if (
        context.run("claude --version", warn=True, pty=False, hide=True).exited
        != 0
    ):
        raise Exit(
            "eval:skills:configure: `claude` is not runnable — run "
            "`mise run deps:install:claude-native`, then `claude login`",
            code=1,
        )


def _run_configure_eval(context: Context) -> float:
    # Lazy: inspect_ai pulls in numpy and is heavy — importing it at module top
    # would tax every unrelated `invoke` command.
    from inspect_ai import eval as inspect_eval  # noqa: PLC0415

    _preflight_claude(context)
    _ensure_repo_on_path()
    plugin_dir = staging.stage_plugin(
        repo_root=REPO_ROOT, host_binary=_host_binary(), dest=_STAGING_DIR
    )
    os.environ[PLUGIN_DIR_ENV] = str(plugin_dir)
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    logs = inspect_eval(
        [
            f"{_EVAL_FILE}@{readback.ARM_WITH_SKILL}",
            f"{_EVAL_FILE}@{readback.ARM_BASELINE}",
        ],
        log_format="json",
        log_dir=str(_RESULTS_DIR),
        max_samples=_MAX_CONCURRENT_SAMPLES,
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
