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
from tasks.shared.paths import REPO_ROOT, WORKSPACE_ROOT
from tasks.shared.rust import LAUNCHER_CRATE
from tasks.shared.targets import host_triple

_STAGING_DIR = REPO_ROOT / "cli" / "target" / "eval-plugin"
_MAX_CONCURRENT_SAMPLES = 4


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def host_binary_path() -> Path:
    # `build:launcher` (which the eval leaves depend on) leaves its release
    # build in the cargo target dir. The launcher's bin/ dir is only populated
    # by the distribution build, so reading it would stage whatever binary a
    # past release left behind — silently evaluating stale code.
    triple = host_triple(platform.system(), platform.machine())
    return WORKSPACE_ROOT / "target" / triple / "release" / LAUNCHER_CRATE


def _host_binary() -> Path:
    binary = host_binary_path()
    if not binary.is_file():
        raise Exit(
            f"eval: no host launcher at {binary} — run "
            f"`mise run build:launcher`",
            code=1,
        )
    return binary


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


def supplementary_capabilities(eval_file: Path) -> list[str]:
    """Capabilities of a skill covered by an eval beside its paired-arm one.

    A skill may have a capability whose grading model does not fit the
    skill-vs-baseline pairing — passive prompt injection, say, which no agent
    command can be attributed to, and which has no no-skill control at all
    (without the skill there is no prompt to inject into). Such a capability
    gets a `<capability>_eval.py` beside the skill's own eval and rides the
    same run.
    """
    return [
        path.stem.removesuffix("_eval")
        for path in sorted(eval_file.parent.glob("*_eval.py"))
        if path != eval_file
    ]


def supplementary_arm(skill: str, capability: str) -> str:
    """Return the task name a supplementary eval exposes.

    Every arm in a run shares one vocabulary —
    `<skill>[_<capability>]_<control>` — so a supplementary arm reads as what it
    is: the same skill, a named capability, and with-skill (its only possible
    control).
    """
    return with_skill_arm(f"{skill}_{capability}")


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
    capabilities = supplementary_capabilities(eval_file)
    extra_arms = [
        supplementary_arm(skill, capability) for capability in capabilities
    ]
    logs = inspect_eval(
        [
            f"{eval_file}@{with_arm}",
            f"{eval_file}@{base_arm}",
            *(
                f"{eval_file.parent / f'{capability}_eval.py'}@{arm}"
                for capability, arm in zip(
                    capabilities, extra_arms, strict=True
                )
            ),
        ],
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
    fractions = [with_skill_fraction]
    for arm in extra_arms:
        arm_log = readback.require_success(readback.arm_log(logs, arm))
        arm_fraction = readback.pass_k(arm_log)
        print(f"eval: {skill} arm {arm!r} pass^k {arm_fraction:.3f}")
        fractions.append(arm_fraction)
    readback.scrub_result_dir(
        results,
        repo_root=str(REPO_ROOT),
        home=str(Path.home()),
        tmp_dirs=_tmp_dirs(),
    )
    cleanup_workdirs(Path(tempfile.gettempdir()))
    # The caller gates on one fraction, so the weakest arm decides: every arm
    # must clear the floor for the skill's eval to pass.
    return min(fractions)
