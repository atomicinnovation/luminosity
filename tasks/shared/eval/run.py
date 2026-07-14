import os
import platform
import sys
import tempfile
from importlib import import_module
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


def host_binary() -> Path:
    """Return the host-native release launcher, or fail actionably.

    Shared with the eval-logic tier, which byte-compares the compiled binary's
    stdout against the committed goldens — a raw FileNotFoundError there would
    say nothing about the build that produces it.

    Raises:
        Exit: when `build:launcher` has not produced the artifact.

    """
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


def capabilities(skill: str) -> list[str]:
    """Return the capabilities of `skill` that carry an eval.

    A skill's eval directory holds one `<capability>_eval.py` per capability it
    is graded on. Every capability declares a with-skill arm; a baseline arm is
    optional, because not every capability has one that would be a control (see
    `arms`).
    """
    return sorted(
        path.stem.removesuffix("_eval")
        for path in (EVALS_SKILLS_DIR / skill).glob("*_eval.py")
    )


def arms(skill: str, capability: str) -> list[str]:
    """Return the arm names a capability's eval declares, with-skill first.

    The with-skill arm is mandatory. The baseline arm is declared only where a
    no-skill run is a genuine control: passive context injection, for one, has
    none — without the skill there is no prompt to inject into, so a no-skill
    run would be a different experiment, not a control. The eval module is the
    single source of that decision; this reads it off the tasks it declares.
    """
    module = import_module(f"tests.evals.skills.{skill}.{capability}_eval")
    declared = [with_skill_arm(skill, capability)]
    baseline = baseline_arm(skill, capability)
    if hasattr(module, baseline):
        declared.append(baseline)
    return declared


def run_skill_eval(context: Context, skill: str) -> float:
    from inspect_ai import eval as inspect_eval  # noqa: PLC0415  (heavy; lazy)

    _preflight_claude(context)
    _ensure_repo_on_path()
    os.environ[PLUGIN_DIR_ENV] = str(
        staging.stage_plugin(
            repo_root=REPO_ROOT, host_binary=host_binary(), dest=_STAGING_DIR
        )
    )
    results = results_dir(skill)
    results.mkdir(parents=True, exist_ok=True)
    skill_dir = EVALS_SKILLS_DIR / skill
    declared = {
        capability: arms(skill, capability)
        for capability in capabilities(skill)
    }
    logs = inspect_eval(
        [
            f"{skill_dir / f'{capability}_eval.py'}@{arm}"
            for capability, capability_arms in declared.items()
            for arm in capability_arms
        ],
        log_format="json",
        log_dir=str(results),
        max_samples=_MAX_CONCURRENT_SAMPLES,
    )

    def fraction(arm: str) -> float:
        return readback.pass_k(
            readback.require_success(readback.arm_log(logs, arm))
        )

    graded = []
    for capability, capability_arms in declared.items():
        with_arm = with_skill_arm(skill, capability)
        with_fraction = fraction(with_arm)
        print(f"eval: arm {with_arm!r} pass^k {with_fraction:.3f}")
        graded.append(with_fraction)
        base_arm = baseline_arm(skill, capability)
        if base_arm in capability_arms and with_fraction <= fraction(base_arm):
            print(
                f"eval: {skill} {capability} with-skill did not beat baseline "
                f"— investigate whether the skill adds value"
            )
    readback.scrub_result_dir(
        results,
        repo_root=str(REPO_ROOT),
        home=str(Path.home()),
        tmp_dirs=_tmp_dirs(),
    )
    cleanup_workdirs(Path(tempfile.gettempdir()))
    # The caller gates on one fraction, so the weakest capability decides: every
    # with-skill arm must clear the floor for the skill's eval to pass.
    return min(graded)
