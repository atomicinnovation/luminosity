import os

_FALSEY = {"off", "false", "0", "no"}


def env_flag_enabled(name: str, *, default: str) -> bool:
    """Whether an env-var boolean flag is enabled, read at CALL time.

    The value is normalised (strip + lower-case); any of off/false/0/no counts
    as disabled, so a plausible falsey value does not silently leave a flag on.
    ``default`` is the string used when the variable is unset. Must be called
    inside a task body — a module-level constant would freeze the value at
    import and ignore the env.
    """
    return os.environ.get(name, default).strip().lower() not in _FALSEY
