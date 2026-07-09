class InvalidVersionError(Exception): ...


class MinisignError(Exception):
    """A minisign sign/verify invocation failed or could not run at all."""


class EvalReadbackError(Exception):
    """An eval log could not be read back into a trustworthy pass^k fraction."""
