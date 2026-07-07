from tasks.shared.env import env_flag_enabled

PASS_K_FLOOR = 0.8


def below_floor(pass_k: float) -> bool:
    return pass_k < PASS_K_FLOOR


def live_run_enabled() -> bool:
    """Whether the live eval run is enabled (``LUMINOSITY_EVAL_LIVE``).

    Read at call time so the run can be disabled per-invocation; any of
    off/false/0/no disables it.
    """
    return env_flag_enabled("LUMINOSITY_EVAL_LIVE", default="on")
