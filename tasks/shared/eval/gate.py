from tasks.shared.env import env_flag_enabled

PASS_K_FLOOR = 0.8


def below_floor(pass_k: float) -> bool:
    return pass_k < PASS_K_FLOOR


def live_run_enabled() -> bool:
    return env_flag_enabled("LUMINOSITY_EVAL_LIVE", default="on")
