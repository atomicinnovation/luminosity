from invoke import Context, Exit, task

from tasks.shared.eval.gate import below_floor, live_run_enabled
from tasks.shared.eval.run import run_skill_eval


@task
def configure(context: Context) -> None:
    """Run the configure skill eval and gate on the pass^k floor."""
    if not live_run_enabled():
        print("LUMINOSITY_EVAL_LIVE is off; skipping the live eval run")
        return
    fraction = run_skill_eval(context, "configure")
    if below_floor(fraction):
        raise Exit(
            f"eval:skills:configure failed: pass^k {fraction:.3f} "
            f"is below the floor",
            code=1,
        )
