class InvalidVersionError(Exception): ...


class MinisignError(Exception):
    """A minisign sign/verify invocation failed or could not run at all.

    Covers both a genuine signature/verification failure and any tooling
    hiccup (absent binary, timeout, non-zero exit) so callers can treat every
    minisign failure mode uniformly rather than letting a tool error escape as
    a generic exception.
    """
