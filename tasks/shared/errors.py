class InvalidVersionError(Exception): ...


class MinisignError(Exception):
    """A minisign sign/verify invocation failed or could not run at all."""
