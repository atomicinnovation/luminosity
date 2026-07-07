from invoke import Context, Exit, task

from tasks.eval.gate import below_floor, live_run_enabled


def _run_configure_eval(context: Context) -> float:
    raise NotImplementedError(
        "the configure eval run is wired in a later phase"
    )


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
